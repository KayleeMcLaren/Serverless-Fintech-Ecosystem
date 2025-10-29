import json
import os
import boto3
from decimal import Decimal
from urllib.parse import unquote
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

# --- CORS Configuration ---
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")
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
# --- End CORS Configuration ---

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
GSI_NAME = 'wallet_id-index' # GSI on the transactions table

dynamodb = boto3.resource('dynamodb')

if not TABLE_NAME:
    print("ERROR: DYNAMODB_TABLE_NAME environment variable not set.")
    table = None
else:
    table = dynamodb.Table(TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def get_payments_by_wallet(event, context):
    """Retrieves payment transactions for a wallet. Handles OPTIONS."""

    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request for get_payments_by_wallet")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }
    # --- End CORS Preflight Check ---

    if not table:
        return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error: Table not found."}) }

    # --- GET Logic ---
    if http_method == 'GET':
        try:
            wallet_id = unquote(event['pathParameters']['wallet_id']).strip()
            
            print(f"Querying payments for wallet: {wallet_id}")

            # Query the GSI
            response = table.query(
                IndexName=GSI_NAME,
                KeyConditionExpression=Key('wallet_id').eq(wallet_id)
            )

            items = response.get('Items', [])
            
            # Sort in Python (newest first) since GSI has no sort key
            # Use 'created_at' or 'updated_at' for sorting
            items.sort(key=lambda x: x.get('created_at', 0), reverse=True)
            
            print(f"Found and sorted {len(items)} transactions.")

            return {
                "statusCode": 200,
                "headers": GET_CORS_HEADERS,
                "body": json.dumps(items, cls=DecimalEncoder)
            }
        except ClientError as ce:
             print(f"DynamoDB Error: {ce}")
             return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Database error.", "error": str(ce)}) }
        except Exception as e:
            print(f"Error: {e}")
            return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Failed to get payments.", "error": str(e)}) }
    else:
        return { "statusCode": 405, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }