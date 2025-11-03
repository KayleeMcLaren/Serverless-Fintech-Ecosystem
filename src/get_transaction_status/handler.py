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
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
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

def get_transaction_status(event, context):
    """
    API: GET /payment/{transaction_id}
    Retrieves a specific transaction by its ID.
    """
    
    # --- Initialize boto3 inside the handler ---
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME) if TABLE_NAME else None
    
    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        logger.info("Handling OPTIONS preflight request for get_transaction_status")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }

    if not table:
        log_message = {
            "status": "error",
            "action": "get_transaction_status",
            "message": "FATAL: DYNAMODB_TABLE_NAME environment variable not set."
        }
        logger.error(json.dumps(log_message))
        return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'GET':
        transaction_id = "unknown"
        log_context = {"action": "get_transaction_status"}
        try:
            transaction_id = unquote(event['pathParameters']['transaction_id']).strip()
            log_context["transaction_id"] = transaction_id
            
            logger.info(json.dumps({**log_context, "status": "info", "message": "Fetching transaction."}))

            response = table.get_item(Key={'transaction_id': transaction_id})
            item = response.get('Item')

            if not item:
                logger.warning(json.dumps({**log_context, "status": "warn", "message": "Transaction not found."}))
                return {
                    "statusCode": 404,
                    "headers": GET_CORS_HEADERS,
                    "body": json.dumps({"message": "Transaction not found."})
                }

            return {
                "statusCode": 200,
                "headers": GET_CORS_HEADERS,
                "body": json.dumps(item, cls=DecimalEncoder)
            }
            
        except ClientError as ce:
             logger.error(json.dumps({**log_context, "status": "error", "error_code": ce.response['Error']['Code'], "error_message": str(ce)}))
             return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Database error.", "error": str(ce)}) }
        except Exception as e:
            logger.error(json.dumps({**log_context, "status": "error", "error_message": str(e)}))
            return {
                "statusCode": 500,
                "headers": GET_CORS_HEADERS,
                "body": json.dumps({"message": "Failed to retrieve transaction.", "error": str(e)})
            }
    else:
         return {
            "statusCode": 405,
            "headers": GET_CORS_HEADERS,
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }