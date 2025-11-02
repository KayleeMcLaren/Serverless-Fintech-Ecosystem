import json
import os
import boto3
from decimal import Decimal
from urllib.parse import unquote
from botocore.exceptions import ClientError
import logging

# Set up logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Environment Variables ---
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME')
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")

# --- CORS Headers ---
OPTIONS_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Credentials": True
}
GET_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Credentials": True
}

# --- DecimalEncoder ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def get_onboarding_status(event, context):
    """
    API: GET /onboarding/{user_id}/status
    Checks the status of a user's onboarding application.
    """
    
    # --- Initialize boto3 inside the handler ---
    dynamodb = boto3.resource('dynamodb')
    users_table = dynamodb.Table(USERS_TABLE_NAME) if USERS_TABLE_NAME else None
    
    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        logger.info("Handling OPTIONS preflight request for get_onboarding_status")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }
    
    if not users_table:
        log_message = {
            "status": "error",
            "action": "get_onboarding_status",
            "message": "FATAL: USERS_TABLE_NAME environment variable not set."
        }
        logger.error(json.dumps(log_message))
        return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'GET':
        user_id = "unknown"
        log_context = {"action": "get_onboarding_status"}
        try:
            user_id = unquote(event['pathParameters']['user_id']).strip()
            log_context["user_id"] = user_id
            
            logger.info(json.dumps({**log_context, "status": "info", "message": "Checking user onboarding status."}))

            # 1. Get the user record
            response = users_table.get_item(Key={'user_id': user_id})
            user_item = response.get('Item')

            if not user_item:
                logger.warning(json.dumps({**log_context, "status": "warn", "message": "User application not found."}))
                return {
                    "statusCode": 404,
                    "headers": GET_CORS_HEADERS,
                    "body": json.dumps({"message": "User application not found."})
                }

            # 2. Return the relevant status information
            status_info = {
                'user_id': user_id,
                'onboarding_status': user_item.get('onboarding_status', 'UNKNOWN'),
                'email': user_item.get('email', ''),
                'created_at': user_item.get('created_at', 0),
                'wallet_id': user_item.get('wallet_id') # Added this in a previous fix
            }

            return {
                "statusCode": 200,
                "headers": GET_CORS_HEADERS,
                "body": json.dumps(status_info, cls=DecimalEncoder)
            }
            
        except ClientError as ce:
             logger.error(json.dumps({**log_context, "status": "error", "error_code": ce.response['Error']['Code'], "error_message": str(ce)}))
             return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Database error.", "error": str(ce)}) }
        except Exception as e:
            logger.error(json.dumps({**log_context, "status": "error", "error_message": str(e)}))
            return {
                "statusCode": 500,
                "headers": GET_CORS_HEADERS,
                "body": json.dumps({"message": "Failed to retrieve status.", "error": str(e)})
            }
    else:
         return {
            "statusCode": 405,
            "headers": GET_CORS_HEADERS,
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }