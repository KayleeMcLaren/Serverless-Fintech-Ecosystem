import json
import os
import boto3
from decimal import Decimal
from urllib.parse import unquote
from botocore.exceptions import ClientError # Import ClientError

# --- CORS Configuration ---
ALLOWED_ORIGIN = "*"
OPTIONS_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "GET, OPTIONS", # Allow GET for fetching
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
    """Helper class to convert a DynamoDB item to JSON."""
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def get_savings_goals(event, context):
    """Retrieves savings goals. Handles OPTIONS preflight."""

    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request for get_savings_goals")
        return {
            "statusCode": 200,
            "headers": OPTIONS_CORS_HEADERS,
            "body": ""
        }
    # --- End CORS Preflight Check ---

    # --- GET Logic ---
    if http_method == 'GET':
        print("Handling GET request for get_savings_goals")
        try:
            wallet_id = unquote(event['pathParameters']['wallet_id']).strip()

            print(f"Querying goals for wallet_id: {wallet_id}")
            response = table.query(
                IndexName='wallet_id-index',
                KeyConditionExpression='wallet_id = :wallet_id',
                ExpressionAttributeValues={
                    ':wallet_id': wallet_id
                }
            )

            items = response.get('Items', [])
            print(f"Found {len(items)} goals.")

            return {
                "statusCode": 200,
                "headers": GET_CORS_HEADERS,
                "body": json.dumps(items, cls=DecimalEncoder)
            }
        except ClientError as ce:
             print(f"DynamoDB ClientError fetching goals: {ce}")
             return {
                "statusCode": 500,
                "headers": GET_CORS_HEADERS,
                "body": json.dumps({"message": "Database error retrieving savings goals.", "error": str(ce)})
            }
        except Exception as e:
            print(f"Error retrieving savings goals: {e}")
            return {
                "statusCode": 500,
                "headers": GET_CORS_HEADERS,
                "body": json.dumps({"message": "Failed to retrieve savings goals.", "error": str(e)})
            }
    else:
        # Handle unsupported methods
        print(f"Unsupported method: {http_method}")
        return {
            "statusCode": 405, # Method Not Allowed
            "headers": GET_CORS_HEADERS,
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }