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
LOG_TABLE_NAME = os.environ.get('TRANSACTIONS_LOG_TABLE_NAME')
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")

# --- (CORS Headers - no changes) ---
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
# ---

# --- (DecimalEncoder - no changes) ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)
# ---

def get_wallet_transactions(event, context):
    """
    Retrieves the latest transaction logs for a given wallet_id.
    """
    
    # --- 3. Initialize boto3 inside the handler ---
    dynamodb = boto3.resource('dynamodb')
    log_table = dynamodb.Table(LOG_TABLE_NAME) if LOG_TABLE_NAME else None
    # ---
    
    # --- (CORS Preflight Check - no changes) ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        logger.info("Handling OPTIONS preflight request for get_wallet_transactions")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }

    if not log_table:
        log_message = {
            "status": "error",
            "action": "get_wallet_transactions",
            "message": "FATAL: TRANSACTIONS_LOG_TABLE_NAME environment variable not set."
        }
        logger.error(json.dumps(log_message))
        return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'GET':
        wallet_id = "unknown"
        try:
            wallet_id = unquote(event['pathParameters']['wallet_id']).strip()
            
            # Use query parameter 'limit' or default to 20
            limit = int(event.get('queryStringParameters', {}).get('limit', 20))

            log_message = {
                "status": "info",
                "action": "get_wallet_transactions",
                "wallet_id": wallet_id,
                "limit": limit
            }
            logger.info(json.dumps(log_message))

            response = log_table.query(
                IndexName='wallet_id-timestamp-index',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('wallet_id').eq(wallet_id),
                ScanIndexForward=False,  # Sort by timestamp descending (newest first)
                Limit=limit
            )
            items = response.get('Items', [])

            return {
                "statusCode": 200,
                "headers": GET_CORS_HEADERS,
                "body": json.dumps(items, cls=DecimalEncoder)
            }
            
        except ClientError as ce:
             log_message = {
                "status": "error",
                "action": "get_wallet_transactions",
                "wallet_id": wallet_id,
                "error_code": ce.response['Error']['Code'],
                "error_message": str(ce)
             }
             logger.error(json.dumps(log_message))
             return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Database error.", "error": str(ce)}) }
        except Exception as e:
             log_message = {
                "status": "error",
                "action": "get_wallet_transactions",
                "wallet_id": wallet_id,
                "error_message": str(e)
             }
             logger.error(json.dumps(log_message))
             return {
                "statusCode": 500,
                "headers": GET_CORS_HEADERS,
                "body": json.dumps({"message": "Failed to retrieve transactions.", "error": str(e)})
            }
    else:
         return {
            "statusCode": 405,
            "headers": GET_CORS_HEADERS,
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }