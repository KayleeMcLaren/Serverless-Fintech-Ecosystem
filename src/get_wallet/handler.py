import json
import os
import boto3
from decimal import Decimal
from urllib.parse import unquote
from botocore.exceptions import ClientError

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Table Name & CORS Origin ---
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*") # Get CORS origin

# --- CORS Headers ---
OPTIONS_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "GET, OPTIONS", # Allow GET
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Credentials": True
}
GET_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Credentials": True
}
# --- End CORS ---

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert a DynamoDB item to JSON."""
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def get_wallet(event, context):
    """Retrieves a wallet by its ID."""

    # Initialize DynamoDB resource inside the function
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME) if TABLE_NAME else None

    # --- 1. ADD CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        logger.info("Handling OPTIONS preflight request for get_wallet")
        return {
            "statusCode": 200,
            "headers": OPTIONS_CORS_HEADERS,
            "body": ""
        }
    # --- End Preflight Check ---

    if not table:
        log_message = {
            "status": "error",
            "action": "get_wallet",
            "message": "FATAL: DYNAMODB_TABLE_NAME environment variable not set."
        }
        logger.error(json.dumps(log_message))
        return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'GET':
        wallet_id = "unknown"
        try:
            wallet_id = unquote(event['pathParameters']['wallet_id']).strip()
            log_message = {
                "status": "info",
                "action": "get_wallet",
                "wallet_id": wallet_id
            }
            logger.info(json.dumps(log_message))

            response = table.get_item(Key={'wallet_id': wallet_id})
            item = response.get('Item')

            if not item:
                log_message = {
                    "status": "warn",
                    "action": "get_wallet",
                    "wallet_id": wallet_id,
                    "message": "Wallet not found in database."
                }
                logger.warning(json.dumps(log_message))
                return {
                    "statusCode": 404,
                    "headers": GET_CORS_HEADERS, # --- 2. USE CORS Variable ---
                    "body": json.dumps({"message": "Wallet not found."})
                }

            return {
                "statusCode": 200,
                "headers": GET_CORS_HEADERS, # --- 2. USE CORS Variable ---
                "body": json.dumps(item, cls=DecimalEncoder)
            }
        except ClientError as ce:
             log_message = {
                "status": "error",
                "action": "get_wallet",
                "wallet_id": wallet_id,
                "error_code": ce.response['Error']['Code'],
                "error_message": str(ce)
             }
             logger.error(json.dumps(log_message))
             return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Database error.", "error": str(ce)}) }
        except Exception as e:
            log_message = {
                "status": "error",
                "action": "get_wallet",
                "wallet_id": wallet_id,
                "error_message": str(e)
             }
            logger.error(json.dumps(log_message))
            return {
                "statusCode": 500,
                "headers": GET_CORS_HEADERS, # --- 2. USE CORS Variable ---
                "body": json.dumps({"message": "Failed to retrieve wallet.", "error": str(e)})
            }
    else:
        return {
            "statusCode": 405,
            "headers": GET_CORS_HEADERS,
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }