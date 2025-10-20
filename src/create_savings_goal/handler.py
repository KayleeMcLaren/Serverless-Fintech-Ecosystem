import json
import os
import uuid
import boto3
import time
from decimal import Decimal
from botocore.exceptions import ClientError # Import ClientError

# --- CORS Configuration ---
ALLOWED_ORIGIN = "http://localhost:5173"
OPTIONS_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS", # Allow POST for creation
    "Access-Control-Allow-Headers": "Content-Type, Authorization", # Common headers
    "Access-Control-Allow-Credentials": True
}
POST_CORS_HEADERS = {
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

def create_savings_goal(event, context):
    """Creates a new savings goal. Handles OPTIONS preflight."""

    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request for create_savings_goal")
        return {
            "statusCode": 200,
            "headers": OPTIONS_CORS_HEADERS,
            "body": ""
        }
    # --- End CORS Preflight Check ---

    # --- POST Logic ---
    if http_method == 'POST':
        print("Handling POST request for create_savings_goal")
        try:
            body = json.loads(event.get('body', '{}'))

            wallet_id = body.get('wallet_id')
            goal_name = body.get('goal_name')
            target_amount_str = body.get('target_amount') # Get as string first

            # Validate target_amount before converting
            if not target_amount_str:
                 raise ValueError("target_amount is required.")
            target_amount = Decimal(target_amount_str)

            if not all([wallet_id, goal_name]) or target_amount <= 0:
                print("Validation failed: Missing fields or non-positive amount.")
                return {
                    "statusCode": 400,
                    "headers": POST_CORS_HEADERS,
                    "body": json.dumps({"message": "Valid wallet_id, goal_name, and positive target_amount are required."})
                }

            goal_id = str(uuid.uuid4())
            item = {
                'goal_id': goal_id,
                'wallet_id': wallet_id,
                'goal_name': goal_name,
                'target_amount': target_amount,
                'current_amount': Decimal('0.00'),
                'created_at': int(time.time())
            }

            table.put_item(Item=item)

            response_body = {
                "message": "Savings goal created successfully!",
                "goal": item
            }

            return {
                "statusCode": 201,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps(response_body, cls=DecimalEncoder)
            }
        except (ValueError, TypeError) as ve: # Catch Decimal conversion errors specifically
            print(f"Input Error: {ve}")
            return {
                "statusCode": 400,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": f"Invalid input format: {ve}"})
            }
        except Exception as e:
            print(f"Error creating savings goal: {e}")
            return {
                "statusCode": 500,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": "Failed to create savings goal.", "error": str(e)})
            }
    else:
        # Handle unsupported methods
        print(f"Unsupported method: {http_method}")
        return {
            "statusCode": 405, # Method Not Allowed
            "headers": POST_CORS_HEADERS, # Still include CORS for error
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }