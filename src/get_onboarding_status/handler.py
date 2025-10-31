import json
import os
import boto3
from decimal import Decimal
from urllib.parse import unquote
from botocore.exceptions import ClientError

# --- Environment Variables ---
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME')
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")

# --- AWS Resources ---
dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table(USERS_TABLE_NAME) if USERS_TABLE_NAME else None

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
    Checks the status of a user's onboarding application.
    """
    
    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }
    
    if not users_table:
        print("FATAL: USERS_TABLE_NAME environment variable not set.")
        return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'GET':
        try:
            user_id = unquote(event['pathParameters']['user_id']).strip()
            if not user_id:
                raise ValueError("User ID is required.")

            print(f"Checking status for user: {user_id}")

            # 1. Get the user record
            response = users_table.get_item(Key={'user_id': user_id})
            user_item = response.get('Item')

            if not user_item:
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
                'wallet_id': user_item.get('wallet_id')
            }

            return {
                "statusCode": 200,
                "headers": GET_CORS_HEADERS,
                "body": json.dumps(status_info, cls=DecimalEncoder)
            }

        except (ValueError, TypeError) as ve:
            return { "statusCode": 400, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": f"Invalid input: {str(ve)}"}) }
        except ClientError as ce:
             return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Database error.", "error": str(ce)}) }
        except Exception as e:
            print(f"Unexpected error: {e}")
            return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "An unexpected error occurred.", "error": str(e)}) }
    else:
         return { "statusCode": 405, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }