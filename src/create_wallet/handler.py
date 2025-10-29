import json
import os
import uuid
import boto3
import time # Import time
from decimal import Decimal
from botocore.exceptions import ClientError # Import ClientError

# --- Table Names ---
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
LOG_TABLE_NAME = os.environ.get('TRANSACTIONS_LOG_TABLE_NAME') # Get log table name
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*") # Get CORS origin

# --- DynamoDB Resources ---
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME) if TABLE_NAME else None
log_table = dynamodb.Table(LOG_TABLE_NAME) if LOG_TABLE_NAME else None

# --- CORS Headers ---
OPTIONS_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Credentials": True
}
POST_CORS_HEADERS = {
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

# --- Transaction Logging Helper ---
def log_transaction(wallet_id, tx_type, amount, new_balance=None, related_id=None, details=None):
    if not log_table:
        print("Log table name not configured, skipping log.")
        return
    try:
        timestamp = int(time.time())
        log_item = {
            'transaction_id': str(uuid.uuid4()),
            'wallet_id': wallet_id,
            'timestamp': timestamp,
            'type': tx_type,
            'amount': amount,
            'balance_after': new_balance if new_balance is not None else Decimal('NaN'),
            'related_id': related_id if related_id else 'N/A',
            'details': details if details else {}
        }
        if isinstance(log_item['balance_after'], Decimal) and log_item['balance_after'].is_nan():
             log_item['balance_after'] = 'N/A' # Store as string 'N/A'

        log_table.put_item(Item=log_item)
        print(f"Logged transaction: {log_item['transaction_id']} for wallet {wallet_id}")
    except Exception as log_e:
        print(f"ERROR logging transaction: {log_e}")
# --- End Helper ---


def create_wallet(event, context):
    """Creates a new digital wallet with a zero balance."""
    
    # --- 1. ADD CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request for create_wallet")
        return {
            "statusCode": 200,
            "headers": OPTIONS_CORS_HEADERS,
            "body": ""
        }
    # --- End Preflight Check ---
    
    if not table:
        print("ERROR: DYNAMODB_TABLE_NAME environment variable not set.")
        return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'POST':
        try:
            wallet_id = str(uuid.uuid4())
            item = {
                'wallet_id': wallet_id,
                'balance': Decimal('0.00'),
                'currency': 'USD'
            }

            table.put_item(Item=item)
            print(f"Wallet {wallet_id} created.")

            # --- 3. ADD Transaction Log ---
            log_transaction(
                wallet_id=wallet_id,
                tx_type="WALLET_CREATED",
                amount=Decimal('0.00'),
                new_balance=Decimal('0.00'),
                details={"message": "Wallet created and initialized"}
            )
            # --- End Log ---

            response_body = {
                "message": "Wallet created successfully!",
                "wallet": item
            }

            return {
                "statusCode": 201,
                "headers": POST_CORS_HEADERS, # --- 2. USE CORS Variable ---
                "body": json.dumps(response_body, cls=DecimalEncoder)
            }
        except Exception as e:
            print(f"Error: {e}")
            return {
            "statusCode": 500,
            "headers": POST_CORS_HEADERS, # --- 2. USE CORS Variable ---
            "body": json.dumps({"message": "Failed to create wallet.", "error": str(e)})
        }
    else:
        return {
            "statusCode": 405,
            "headers": POST_CORS_HEADERS,
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }