import json
import os
import uuid
import boto3
import time
from decimal import Decimal
from botocore.exceptions import ClientError # Import ClientError

# --- CORS Configuration ---
ALLOWED_ORIGIN = "*" # Use "*" for dev, replace with CloudFront URL for prod
OPTIONS_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS", # Allow POST
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
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
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def apply_for_loan(event, context):
    """Creates a new loan application. Handles OPTIONS preflight."""

    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request for apply_for_loan")
        return {
            "statusCode": 200,
            "headers": OPTIONS_CORS_HEADERS,
            "body": ""
        }
    # --- End CORS Preflight Check ---

    # --- POST Logic ---
    if http_method == 'POST':
        print("Handling POST request for apply_for_loan")
        try:
            body = json.loads(event.get('body', '{}'))

            wallet_id = body.get('wallet_id')
            amount_str = body.get('amount')
            interest_rate_str = body.get('interest_rate')
            minimum_payment_str = body.get('minimum_payment')

            # Validate before converting to Decimal
            if not all([wallet_id, amount_str, interest_rate_str, minimum_payment_str]):
                raise ValueError("wallet_id, amount, interest_rate, and minimum_payment are required.")

            amount = Decimal(amount_str)
            interest_rate = Decimal(interest_rate_str)
            minimum_payment = Decimal(minimum_payment_str)

            if amount <= 0 or interest_rate < 0 or minimum_payment <= 0:
                 raise ValueError("Amount and minimum_payment must be positive, interest_rate cannot be negative.")

            loan_id = str(uuid.uuid4())
            item = {
                'loan_id': loan_id,
                'wallet_id': wallet_id,
                'amount': amount,
                'status': 'PENDING',
                'created_at': int(time.time()),
                'interest_rate': interest_rate,
                'minimum_payment': minimum_payment,
                'remaining_balance': amount
            }

            table.put_item(Item=item)

            response_body = {
                "message": "Loan application received successfully!",
                "loan": item
            }

            return {
                "statusCode": 201,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps(response_body, cls=DecimalEncoder)
            }
        except (ValueError, TypeError) as ve: # Catch validation/conversion errors
            print(f"Input Error applying for loan: {ve}")
            return {
                "statusCode": 400,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": f"Invalid input: {ve}"})
            }
        except Exception as e:
            print(f"Error applying for loan: {e}")
            return {
                "statusCode": 500,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": "Failed to apply for loan.", "error": str(e)})
            }
    else:
        print(f"Unsupported method: {http_method}")
        return {
            "statusCode": 405,
            "headers": POST_CORS_HEADERS,
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }