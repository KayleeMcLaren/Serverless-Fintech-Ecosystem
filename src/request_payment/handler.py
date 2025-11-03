import json
import os
import boto3
import uuid
import time
from decimal import Decimal, InvalidOperation
from botocore.exceptions import ClientError
import logging

# Set up logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Environment Variables ---
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")

# --- CORS Headers ---
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

# --- DecimalEncoder ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def request_payment(event, context):
    """
    API: POST /payment
    Creates a 'PENDING' transaction and publishes 'PAYMENT_REQUESTED' event.
    """
    
    # --- Initialize boto3 clients inside the handler ---
    dynamodb = boto3.resource('dynamodb')
    sns = boto3.client('sns')
    table = dynamodb.Table(TABLE_NAME) if TABLE_NAME else None
    
    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        logger.info("Handling OPTIONS preflight request for request_payment")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }
    
    if not table or not SNS_TOPIC_ARN:
        log_message = {
            "status": "error",
            "action": "request_payment",
            "message": "FATAL: Environment variables not set."
        }
        logger.error(json.dumps(log_message))
        return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'POST':
        log_context = {"action": "request_payment"}
        try:
            body = json.loads(event.get('body', '{}'))
            wallet_id = body.get('wallet_id')
            merchant_id = body.get('merchant_id')
            amount_str = body.get('amount')

            log_context["wallet_id"] = wallet_id
            log_context["merchant_id"] = merchant_id

            if not wallet_id or not merchant_id or not amount_str:
                raise ValueError("wallet_id, merchant_id, and amount are required.")
            
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be positive.")

            transaction_id = str(uuid.uuid4())
            timestamp = int(time.time())
            
            log_context.update({
                "transaction_id": transaction_id,
                "amount": str(amount)
            })

            # 1. Create the transaction item
            item = {
                'transaction_id': transaction_id,
                'wallet_id': wallet_id,
                'amount': amount,
                'merchant_id': merchant_id,
                'status': 'PENDING',
                'created_at': timestamp,
                'updated_at': timestamp
            }
            table.put_item(Item=item)
            logger.info(json.dumps({**log_context, "status": "info", "message": "Created PENDING transaction."}))

            # 2. Publish event to SNS
            event_details = {
                'transaction_id': transaction_id,
                'wallet_id': wallet_id,
                'merchant_id': merchant_id,
                'amount': amount
            }
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Message=json.dumps({"event_type": "PAYMENT_REQUESTED", "transaction_details": event_details}, cls=DecimalEncoder),
                Subject="Payment Requested",
                MessageAttributes={
                    'event_type': { 'DataType': 'String', 'StringValue': 'PAYMENT_REQUESTED' }
                }
            )
            logger.info(json.dumps({**log_context, "status": "info", "message": "Published PAYMENT_REQUESTED event."}))

            return {
                "statusCode": 202, # Accepted
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({
                    "message": "Payment request received and is processing.",
                    "transaction_id": transaction_id,
                    "transaction": item 
                }, cls=DecimalEncoder)
            }
            
        except (ValueError, TypeError, InvalidOperation) as ve:
             logger.error(json.dumps({**log_context, "status": "error", "error_message": str(ve)}))
             return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Invalid input: {str(ve)}"}) }
        except ClientError as ce:
             logger.error(json.dumps({**log_context, "status": "error", "error_code": ce.response['Error']['Code'], "error_message": str(ce)}))
             return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "AWS service error.", "error": str(ce)}) }
        except Exception as e:
            logger.error(json.dumps({**log_context, "status": "error", "error_message": str(e)}))
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "An unexpected error occurred.", "error": str(e)}) }
    else:
         return { "statusCode": 405, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }