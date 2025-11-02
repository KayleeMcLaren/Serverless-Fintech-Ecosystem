import json
import os
import boto3
from urllib.parse import unquote
from botocore.exceptions import ClientError
import logging # <-- 1. Import logging

# --- 2. Set up logger ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# ---

# --- Environment Variables ---
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
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

def reject_loan(event, context):
    """
    API: POST /loan/{loan_id}/reject
    Updates a PENDING loan to REJECTED.
    """
    
    # --- 3. Initialize boto3 inside the handler ---
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME) if TABLE_NAME else None
    # ---
    
    # --- (CORS Preflight Check - no changes) ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        logger.info("Handling OPTIONS preflight request for reject_loan")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }

    if not table:
        log_message = {
            "status": "error",
            "action": "reject_loan",
            "message": "FATAL: DYNAMODB_TABLE_NAME environment variable not set."
        }
        logger.error(json.dumps(log_message))
        return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'POST':
        loan_id = "unknown"
        log_context = {"action": "reject_loan"}
        try:
            loan_id = unquote(event['pathParameters']['loan_id']).strip()
            log_context["loan_id"] = loan_id
            
            logger.info(json.dumps({**log_context, "status": "info", "message": "Attempting to reject loan."}))

            # Update the loan status in DynamoDB
            response = table.update_item(
                Key={'loan_id': loan_id},
                UpdateExpression="SET #status = :status_val",
                # Condition: Only reject if it's currently PENDING
                ConditionExpression="#status = :pending_val",
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status_val': 'REJECTED',
                    ':pending_val': 'PENDING'
                },
                ReturnValues="ALL_NEW"  # Return the full updated item
            )
            
            updated_item = response.get('Attributes', {})
            logger.info(json.dumps({**log_context, "status": "info", "message": "Loan status updated to REJECTED."}))

            return {
                "statusCode": 200,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": "Loan rejected.", "loan": updated_item})
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            log_context["error_code"] = error_code
            
            if error_code == 'ConditionalCheckFailedException':
                logger.warn(json.dumps({**log_context, "status": "warn", "message": "Loan was not in PENDING state."}))
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
                "body": json.dumps({"message": "Failed to reject loan.", "error": str(e)})
            }
    else:
         return {
            "statusCode": 405,
            "headers": POST_CORS_HEADERS,
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }