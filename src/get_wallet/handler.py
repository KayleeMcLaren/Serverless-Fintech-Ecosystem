import json
import os
import boto3
from decimal import Decimal
from urllib.parse import unquote
from botocore.exceptions import ClientError

# --- Table Name & CORS Origin ---
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*") # Get CORS origin

# --- DynamoDB Resource ---
dynamodb = boto3.resource('dynamodb')
if not TABLE_NAME:
    print("ERROR: DYNAMODB_TABLE_NAME environment variable not set.")
    table = None
else:
    table = dynamodb.Table(TABLE_NAME)

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

    # --- 1. ADD CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request for get_wallet")
        return {
            "statusCode": 200,
            "headers": OPTIONS_CORS_HEADERS,
            "body": ""
        }
    # --- End Preflight Check ---

    if not table:
        print("ERROR: Table resource is not initialized.")
        return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'GET':
        try:
            wallet_id = unquote(event['pathParameters']['wallet_id']).strip()
            print(f"Fetching wallet: {wallet_id}")

            response = table.get_item(Key={'wallet_id': wallet_id})
            item = response.get('Item')

            if not item:
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
             print(f"DynamoDB Error: {ce}")
             return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Database error.", "error": str(ce)}) }
        except Exception as e:
            print(f"Error: {e}")
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