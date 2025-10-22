import json
import os
import boto3
from decimal import Decimal
from urllib.parse import unquote
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

# --- CORS Configuration ---
ALLOWED_ORIGIN = "*"
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

LOG_TABLE_NAME = os.environ.get('TRANSACTIONS_LOG_TABLE_NAME')
GSI_NAME = 'related_id-timestamp-index' # Name of the new GSI

dynamodb = boto3.resource('dynamodb')

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

def get_goal_transactions(event, context):
    """Retrieves transaction logs for a specific goal_id. Handles OPTIONS."""

    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request for get_goal_transactions")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }
    # --- End CORS Preflight Check ---

    if not log_table:
        return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error: Log table not found."}) }

    # --- GET Logic ---
    if http_method == 'GET':
        try:
            goal_id = unquote(event['pathParameters']['goal_id']).strip()
            limit = int(event.get('queryStringParameters', {}).get('limit', 10)) # Smaller limit for goal history
            if limit <= 0: limit = 10

            print(f"Querying transactions for related_id (goal_id): {goal_id}, limit: {limit}")

            # Query the new GSI using related_id (which stores goal_id for SAVINGS_ADD)
            response = log_table.query(
                IndexName=GSI_NAME,
                KeyConditionExpression=Key('related_id').eq(goal_id),
                ScanIndexForward=False, # Sorts newest first
                # Filter for only SAVINGS_ADD type if needed, but usually just querying by goal is enough
                # FilterExpression='#type = :typeVal',
                # ExpressionAttributeNames={'#type': 'type'},
                # ExpressionAttributeValues={':typeVal': 'SAVINGS_ADD'},
                Limit=limit
            )

            items = response.get('Items', [])
            print(f"Found {len(items)} transactions for goal {goal_id}.")

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
            return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Failed to get goal transactions.", "error": str(e)}) }
    else:
        return { "statusCode": 405, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }