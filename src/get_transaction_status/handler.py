import json
import os
import boto3
from decimal import Decimal
from urllib.parse import unquote
from botocore.exceptions import ClientError # Import ClientError

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

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def get_transaction_status(event, context):
    """Retrieves transaction status. Handles OPTIONS preflight."""

    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request for get_transaction_status")
        return {
            "statusCode": 200,
            "headers": OPTIONS_CORS_HEADERS,
            "body": ""
        }
    # --- End CORS Preflight Check ---

    # --- GET Logic ---
    if http_method == 'GET':
        print("Handling GET request for get_transaction_status")
        try:
            transaction_id = unquote(event['pathParameters']['transaction_id']).strip()
            print(f"Fetching status for transaction_id: {transaction_id}")

            response = table.get_item(Key={'transaction_id': transaction_id})
            item = response.get('Item')

            if not item:
                print(f"Transaction not found: {transaction_id}")
                return {
                    "statusCode": 404,
                    "headers": GET_CORS_HEADERS,
                    "body": json.dumps({"message": "Transaction not found."})
                }

            print(f"Transaction {transaction_id} found with status: {item.get('status')}")
            return {
                "statusCode": 200,
                "headers": GET_CORS_HEADERS,
                "body": json.dumps(item, cls=DecimalEncoder)
            }
        except ClientError as ce:
             print(f"DynamoDB ClientError fetching transaction: {ce}")
             return {
                "statusCode": 500,
                "headers": GET_CORS_HEADERS,
                "body": json.dumps({"message": "Database error retrieving transaction.", "error": str(ce)})
            }
        except Exception as e:
            print(f"Error retrieving transaction: {e}")
            return {
                "statusCode": 500,
                "headers": GET_CORS_HEADERS,
                "body": json.dumps({"message": "Failed to retrieve transaction.", "error": str(e)})
            }
    else:
        print(f"Unsupported method: {http_method}")
        return {
            "statusCode": 405,
            "headers": GET_CORS_HEADERS,
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }