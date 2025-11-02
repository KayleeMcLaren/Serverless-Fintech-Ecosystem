import json
import os
import boto3
import uuid
import time
from decimal import Decimal, InvalidOperation
from urllib.parse import unquote
from botocore.exceptions import ClientError
import logging # <-- 1. Import logging

# --- 2. Set up logger ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# ---

# --- Environment Variables ---
LOANS_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN') # Payment events topic
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")

# --- (CORS Headers - no changes) ---
OPTIONS_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Credentials": True
}
POST_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Credentials": True
}
# ---

# --- (DecimalEncoder - no changes) ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal): return str(o)
        return super(DecimalEncoder, self).default(o)
# ---

def repay_loan(event, context):
    """
    API: POST /loan/{loan_id}/repay
    Initiates a loan repayment.
    If the amount is > remaining_balance, it adjusts the amount.
    Publishes 'LOAN_REPAYMENT_REQUESTED' event.
    """
    
    # --- 3. Initialize boto3 inside the handler ---
    dynamodb = boto3.resource('dynamodb')
    sns = boto3.client('sns')
    loans_table = dynamodb.Table(LOANS_TABLE_NAME) if LOANS_TABLE_NAME else None
    # ---
    
    # --- (CORS Preflight Check - no changes) ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        logger.info("Handling OPTIONS preflight request for repay_loan")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }
    
    if not loans_table or not SNS_TOPIC_ARN:
        log_message = {
            "status": "error",
            "action": "repay_loan",
            "message": "FATAL: Environment variables not set."
        }
        logger.error(json.dumps(log_message))
        return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'POST':
        loan_id = "unknown"
        log_context = {"action": "repay_loan"}
        try:
            loan_id = unquote(event['pathParameters']['loan_id']).strip()
            body = json.loads(event.get('body', '{}'))
            amount_str = body.get('amount')
            
            log_context["loan_id"] = loan_id

            if not amount_str: raise ValueError("Amount is required.")
            amount = Decimal(amount_str)
            if amount <= 0: raise ValueError("Amount must be positive.")
            
            log_context["amount"] = str(amount)
            
            # 1. Get the loan to find the wallet_id and remaining_balance
            response = loans_table.get_item(Key={'loan_id': loan_id})
            loan_item = response.get('Item')

            if not loan_item:
                logger.warning(json.dumps({**log_context, "status": "warn", "message": "Loan not found."}))
                return { "statusCode": 404, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Loan not found."}) }
            
            if loan_item.get('status') != 'APPROVED':
                 logger.warning(json.dumps({**log_context, "status": "warn", "loan_status": loan_item.get('status'), "message": "Loan is not in 'APPROVED' state."}))
                 return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Loan is not in 'APPROVED' state."}) }
            
            wallet_id = loan_item.get('wallet_id')
            log_context["wallet_id"] = wallet_id
            if not wallet_id:
                 logger.error(json.dumps({**log_context, "status": "error", "message": "Loan item is missing wallet_id."}))
                 return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Loan item is missing wallet_id."}) }

            # 2. Compare Amount to Balance
            remaining_balance = Decimal(loan_item.get('remaining_balance', '0'))
            amount_to_pay = amount

            if amount > remaining_balance:
                logger.info(json.dumps({**log_context, "status": "info", "remaining_balance": str(remaining_balance), "message": "Payment amount exceeds balance. Adjusting to pay off loan."}))
                amount_to_pay = remaining_balance
            
            if amount_to_pay <= 0:
                logger.warning(json.dumps({**log_context, "status": "warn", "remaining_balance": str(remaining_balance), "message": "Loan already paid off."}))
                return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "This loan has already been paid off."}) }

            # 3. Publish the repayment request event
            event_details = {
                'loan_id': loan_id,
                'wallet_id': wallet_id,
                'amount': amount_to_pay,
                'repayment_time': int(time.time())
            }
            
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Message=json.dumps({"event_type": "LOAN_REPAYMENT_REQUESTED", "details": event_details}, cls=DecimalEncoder),
                Subject=f"Loan Repayment Requested: {loan_id}",
                MessageAttributes={
                    'event_type': { 'DataType': 'String', 'StringValue': 'LOAN_REPAYMENT_REQUESTED' }
                }
            )
            
            log_context["amount_processed"] = str(amount_to_pay)
            logger.info(json.dumps({**log_context, "status": "info", "message": "Published LOAN_REPAYMENT_REQUESTED event."}))

            # 4. Return the actual amount processed
            return {
                "statusCode": 202, # Accepted
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({
                    "message": "Repayment request received and is processing.",
                    "amount_processed": amount_to_pay
                }, cls=DecimalEncoder)
            }
            
        except (ValueError, TypeError, InvalidOperation) as ve:
            logger.error(json.dumps({**log_context, "status": "error", "error_message": str(ve)}))
            return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Invalid input: {str(ve)}"}) }
        except ClientError as ce:
             logger.error(json.dumps({**log_context, "status": "error", "error_code": ce.response['Error']['Code'], "error_message": str(ce)}))
             return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Database error.", "error": str(ce)}) }
        except Exception as e:
            logger.error(json.dumps({**log_context, "status": "error", "error_message": str(e)}))
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Failed to request repayment.", "error": str(e)}) }
    else:
         return { "statusCode": 405, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }