import json
import os
import boto3
import uuid # For transaction ID
import time # For timestamp
from decimal import Decimal, InvalidOperation # Import InvalidOperation
from urllib.parse import unquote
from botocore.exceptions import ClientError

# --- Table Names ---
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
LOG_TABLE_NAME = os.environ.get('TRANSACTIONS_LOG_TABLE_NAME')

# --- DynamoDB Resources ---
dynamodb_resource = boto3.resource('dynamodb')
table = dynamodb_resource.Table(TABLE_NAME)
log_table = dynamodb_resource.Table(LOG_TABLE_NAME) if LOG_TABLE_NAME else None

# --- CORS Configuration ---
ALLOWED_ORIGIN = "*"
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
# --- End CORS Configuration ---

class DecimalEncoder(json.JSONEncoder):
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
        timestamp = int(time.time()) # Ensure timestamp is integer
        log_item = {
            'transaction_id': str(uuid.uuid4()),
            'wallet_id': wallet_id,
            'timestamp': timestamp, # Save timestamp as Number (N)
            'type': tx_type,
            'amount': amount,
            'balance_after': new_balance if new_balance is not None else Decimal('NaN'),
            'related_id': related_id if related_id else 'N/A',
            'details': details if details else {}
        }
        # Handle NaN specifically for DynamoDB put_item
        if isinstance(log_item['balance_after'], Decimal) and log_item['balance_after'].is_nan():
             log_item['balance_after'] = 'N/A' # Store as string 'N/A'
        # Boto3 handles Decimal conversion for valid numbers

        log_table.put_item(Item=log_item)
        print(f"Logged transaction: {log_item['transaction_id']} for wallet {wallet_id}")
    except Exception as log_e:
        print(f"ERROR logging transaction: {log_e}")
# --- End Helper ---

def debit_wallet(event, context):
    """Debits amount from wallet balance and logs transaction. Handles OPTIONS."""

    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }
    # --- End CORS Preflight Check ---

    if http_method == 'POST':
        try:
            wallet_id = unquote(event['pathParameters']['wallet_id']).strip()
            body = json.loads(event.get('body', '{}'))
            amount_str = body.get('amount', '0.00')
            amount = Decimal(amount_str)

            if amount <= 0:
                return {
                    "statusCode": 400,
                    "headers": POST_CORS_HEADERS,
                    "body": json.dumps({"message": "Amount must be positive."})
                }

            # Update wallet balance (with overdraft check)
            response = table.update_item(
                Key={'wallet_id': wallet_id},
                UpdateExpression="SET balance = balance - :amount",
                ConditionExpression="balance >= :amount", # Prevent overdraft
                ExpressionAttributeValues={ ':amount': amount },
                ReturnValues="UPDATED_NEW"
            )
            print(f"Successfully debited wallet {wallet_id}")
            new_balance = response.get('Attributes', {}).get('balance') # Get new balance

            # --- Log Transaction ---
            log_transaction(
                wallet_id=wallet_id,
                tx_type="DEBIT",
                amount=amount,
                new_balance=new_balance, # Pass the balance
                details={"reason": "Direct Withdrawal"}
            )
            # --- End Log ---

            return {
                "statusCode": 200,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps(response['Attributes'], cls=DecimalEncoder)
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConditionalCheckFailedException':
                print(f"Debit failed for wallet {wallet_id}: Insufficient funds.")
                return {
                    "statusCode": 400, # Bad Request
                    "headers": POST_CORS_HEADERS,
                    "body": json.dumps({"message": "Insufficient funds."})
                }
            print(f"ClientError: {e}")
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Database error during debit.", "error": str(e)}) }
        except (ValueError, TypeError, InvalidOperation) as ve:
             print(f"Input Error: {ve}")
             return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Invalid amount format: {ve}"}) }
        except Exception as e:
            print(f"Error: {e}")
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Failed to debit wallet.", "error": str(e)}) }
    else:
        return { "statusCode": 405, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }