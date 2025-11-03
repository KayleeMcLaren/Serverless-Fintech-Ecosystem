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

def get_savings_goals(event, context):
    """
    API: GET /savings-goal/by-wallet/{wallet_id}
    Retrieves all savings goals for a wallet using the GSI.
    """
    
    # --- Initialize boto3 inside the handler ---
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME) if TABLE_NAME else None
    
    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        logger.info("Handling OPTIONS preflight request for get_savings_goals")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }

    if not table:
        log_message = {
            "status": "error",
            "action": "get_savings_goals",
            "message": "FATAL: DYNAMODB_TABLE_NAME environment variable not set."
        }
        logger.error(json.dumps(log_message))
        return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'GET':
        wallet_id = "unknown"
        log_context = {"action": "get_savings_goals"}
        try:
            wallet_id = unquote(event['pathParameters']['wallet_id']).strip()
            log_context["wallet_id"] = wallet_id
            
            logger.info(json.dumps({**log_context, "status": "info", "message": "Querying GSI for savings goals."}))

            # Query the Global Secondary Index
            response = table.query(
                IndexName='wallet_id-index',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('wallet_id').eq(wallet_id)
            )
            
            items = response.get('Items', [])

            return {
                "statusCode": 200,
                "headers": GET_CORS_HEADERS,
                "body": json.dumps(items, cls=DecimalEncoder)
            }
            
        except ClientError as ce:
             logger.error(json.dumps({**log_context, "status": "error", "error_code": ce.response['Error']['Code'], "error_message": str(ce)}))
             return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Database error.", "error": str(ce)}) }
        except Exception as e:
            logger.error(json.dumps({**log_context, "status": "error", "error_message": str(e)}))
            return {
                "statusCode": 500,
                "headers": GET_CORS_HEADERS,
                "body": json.dumps({"message": "Failed to retrieve savings goals.", "error": str(e)})
            }
    else:
         return {
            "statusCode": 405,
            "headers": GET_CORS_HEADERS,
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }