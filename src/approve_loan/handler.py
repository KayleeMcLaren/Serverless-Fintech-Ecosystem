import json
import os
import boto3
from decimal import Decimal
from urllib.parse import unquote
from botocore.exceptions import ClientError
import logging # <-- 1. Import logging

# --- 2. Set up logger ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# ---

# --- Environment Variables ---
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
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
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)
# ---

def approve_loan(event, context):
    """
    API: POST /loan/{loan_id}/approve
    Updates a PENDING loan to APPROVED and publishes a 'LOAN_APPROVED' event.
    """
    
    # --- 3. Initialize boto3 inside the handler ---
    dynamodb = boto3.resource('dynamodb')
    sns = boto3.client('sns')
    table = dynamodb.Table(TABLE_NAME) if TABLE_NAME else None
    # ---
    
    # --- (CORS Preflight Check - no changes) ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        logger.info("Handling OPTIONS preflight request for approve_loan")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }

    if not table or not SNS_TOPIC_ARN:
        log_message = {
            "status": "error",
            "action": "approve_loan",
            "message": "FATAL: Environment variables not set."
        }
        logger.error(json.dumps(log_message))
        return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'POST':
        loan_id = "unknown"
        log_context = {"action": "approve_loan"}
        try:
            loan_id = unquote(event['pathParameters']['loan_id']).strip()
            log_context["loan_id"] = loan_id
            
            logger.info(json.dumps({**log_context, "status": "info", "message": "Attempting to approve loan."}))

            # Update the loan status in DynamoDB
            response = table.update_item(
                Key={'loan_id': loan_id},
                UpdateExpression="SET #status = :status_val",
                # Condition: Only approve if it's currently PENDING
                ConditionExpression="#status = :pending_val",
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status_val': 'APPROVED',
                    ':pending_val': 'PENDING'
                },
                ReturnValues="ALL_NEW"  # Return the full updated item
            )
            
            updated_item = response.get('Attributes', {})
            logger.info(json.dumps({**log_context, "status": "info", "message": "Loan status updated to APPROVED."}))

            # Publish 'LOAN_APPROVED' event to SNS
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Message=json.dumps({"event_type": "LOAN_APPROVED", "loan_details": updated_item}, cls=DecimalEncoder),
                Subject=f"Loan Approved: {loan_id}",
                MessageAttributes={
                    'event_type': {
                        'DataType': 'String',
                        'StringValue': 'LOAN_APPROVED'
                    }
                }
            )
            
            logger.info(json.dumps({**log_context, "status": "info", "message": "Published LOAN_APPROVED event."}))

            return {
                "statusCode": 200,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": "Loan approved and event published!", "loan": updated_item}, cls=DecimalEncoder)
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            log_context["error_code"] = error_code
            
            if error_code == 'ConditionalCheckFailedException':
                logger.warning(json.dumps({**log_context, "status": "warn", "message": "Loan was not in PENDING state."}))
                return {
                    "statusCode": 409, # Conflict
                    "headers": POST_CORS_HEADERS,
                    "body": json.dumps({"message": "Loan is not in 'PENDING' state. No action taken."})
                }
            else:
                logger.error(json.dumps({**log_context, "status": "error", "error_message": str(e)}))
                return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Database error.", "error": str(e)}) }
        except Exception as e:
            logger.error(json.dumps({**log_context, "status": "error", "error_message": str(e)}))
            return {
                "statusCode": 500,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": "Failed to approve loan.", "error": str(e)})
            }
    else:
         return {
            "statusCode": 405,
            "headers": POST_CORS_HEADERS,
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }