import json
import os
import boto3
from decimal import Decimal
from urllib.parse import unquote
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key # Import Key

# --- CORS Configuration ---
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")
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
# --- End CORS Configuration ---

LOG_TABLE_NAME = os.environ.get('TRANSACTIONS_LOG_TABLE_NAME')
dynamodb = boto3.resource('dynamodb')

# Handle potential error if table name is missing
if not LOG_TABLE_NAME:
    print("ERROR: TRANSACTIONS_LOG_TABLE_NAME environment variable not set.")
    log_table = None
else:
    log_table = dynamodb.Table(LOG_TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def get_wallet_transactions(event, context):
    """Retrieves transaction logs for a wallet. Handles OPTIONS."""

    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request for get_wallet_transactions")
        return {
            "statusCode": 200,
            "headers": OPTIONS_CORS_HEADERS,
            "body": ""
        }
    # --- End CORS Preflight Check ---

    # Check if table resource is available
    if not log_table:
        print("ERROR: Log table resource is not initialized.")
        return {
            "statusCode": 500,
            "headers": GET_CORS_HEADERS, # Add headers even for config error
            "body": json.dumps({"message": "Server configuration error: Log table not found."})
        }

    # --- GET Logic ---
    if http_method == 'GET':
        print("Handling GET request for get_wallet_transactions")
        try:
            wallet_id = unquote(event['pathParameters']['wallet_id']).strip()
            # Optional: Get limit from query string, default to 25
            limit = int(event.get('queryStringParameters', {}).get('limit', 25))
            if limit <= 0: limit = 25 # Ensure positive limit

            print(f"Querying transactions for wallet: {wallet_id}, limit: {limit}")

            # Query the GSI, sort descending by timestamp
            response = log_table.query(
                IndexName='wallet_id-timestamp-index',
                KeyConditionExpression=Key('wallet_id').eq(wallet_id),
                ScanIndexForward=False, # Sorts newest first
                Limit=limit
            )

            items = response.get('Items', [])
            print(f"Found {len(items)} transactions.")

            return {
                "statusCode": 200,
                "headers": GET_CORS_HEADERS, # Add headers
                "body": json.dumps(items, cls=DecimalEncoder)
            }
        except ClientError as ce:
             print(f"DynamoDB Error fetching transactions: {ce}")
             return {
                 "statusCode": 500,
                 "headers": GET_CORS_HEADERS, # Add headers
                 "body": json.dumps({"message": "Database error retrieving transactions.", "error": str(ce)})
             }
        except Exception as e:
            print(f"Error getting transactions: {e}")
            return {
                "statusCode": 500,
                "headers": GET_CORS_HEADERS, # Add headers
                "body": json.dumps({"message": "Failed to get transactions.", "error": str(e)})
            }
    else:
        # Handle unsupported methods
        print(f"Unsupported method: {http_method}")
        return {
            "statusCode": 405, # Method Not Allowed
            "headers": GET_CORS_HEADERS, # Add headers
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }