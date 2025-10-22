import json
import os
import boto3
import uuid # For transaction ID
import time # For timestamp
from decimal import Decimal, InvalidOperation # Import InvalidOperation
from urllib.parse import unquote
from botocore.exceptions import ClientError

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

# --- Table Names ---
SAVINGS_TABLE_NAME = os.environ.get('SAVINGS_TABLE_NAME')
WALLETS_TABLE_NAME = os.environ.get('WALLETS_TABLE_NAME')
LOG_TABLE_NAME = os.environ.get('TRANSACTIONS_LOG_TABLE_NAME') # Get log table name

# --- AWS Resources ---
dynamodb_client = boto3.client('dynamodb') # Use client for transactions
# Need resource client for log table PutItem helper
dynamodb_resource = boto3.resource('dynamodb')
log_table = dynamodb_resource.Table(LOG_TABLE_NAME) if LOG_TABLE_NAME else None

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
            'balance_after': new_balance if new_balance is not None else Decimal('NaN'), # Use NaN marker initially
            'related_id': related_id if related_id else 'N/A',
            'details': details if details else {}
        }
        # Handle NaN for DynamoDB
        if isinstance(log_item['balance_after'], Decimal) and log_item['balance_after'].is_nan():
             log_item['balance_after'] = 'N/A' # Store as string 'N/A'

        log_table.put_item(Item=log_item)
        print(f"Logged transaction: {log_item['transaction_id']} for wallet {wallet_id}")
    except Exception as log_e:
        print(f"ERROR logging transaction: {log_e}")
# --- End Helper ---

def add_to_savings_goal(event, context):
    """
    Atomically moves funds using a DynamoDB transaction and logs it.
    Handles OPTIONS preflight.
    """
    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }
    # --- End CORS Preflight Check ---

    if http_method == 'POST':
        try:
            goal_id = unquote(event['pathParameters']['goal_id']).strip()
            body = json.loads(event.get('body', '{}'))
            wallet_id = body.get('wallet_id')
            amount_str = body.get('amount', '0.00')
            amount = Decimal(amount_str)

            if not wallet_id or amount <= 0:
                return {
                    "statusCode": 400, "headers": POST_CORS_HEADERS,
                    "body": json.dumps({"message": "Valid wallet_id and positive amount are required."})
                }

            print(f"Attempting transaction: Move {amount} from wallet {wallet_id} to goal {goal_id}")

            # Perform the transaction
            dynamodb_client.transact_write_items(
                TransactItems=[
                    { # 1. Debit wallet
                        'Update': {
                            'TableName': WALLETS_TABLE_NAME,
                            'Key': {'wallet_id': {'S': wallet_id}},
                            'UpdateExpression': 'SET balance = balance - :amount',
                            'ConditionExpression': 'balance >= :amount',
                            'ExpressionAttributeValues': {':amount': {'N': str(amount)}}
                        }
                    },
                    { # 2. Credit savings goal
                        'Update': {
                            'TableName': SAVINGS_TABLE_NAME,
                            'Key': {'goal_id': {'S': goal_id}},
                            'UpdateExpression': 'SET current_amount = current_amount + :amount',
                            'ConditionExpression': 'attribute_exists(goal_id) AND wallet_id = :wallet_id_val', # Extra check: ensure goal belongs to wallet
                            'ExpressionAttributeValues': {
                                ':amount': {'N': str(amount)},
                                ':wallet_id_val': {'S': wallet_id} # Add wallet_id to condition
                             }
                        }
                    }
                ]
            )
            print(f"Transaction successful for goal {goal_id}")

            # --- Log Transaction ---
            # NOTE: transact_write_items does not return the final balance.
            # We log 'N/A' for balance_after in this specific case.
            log_transaction(
                wallet_id=wallet_id,
                tx_type="SAVINGS_ADD", # Specific type for this action
                amount=amount,
                new_balance=None, # Indicate balance is unknown from this operation
                related_id=goal_id,
                details={"action": "Add to Savings Goal"}
            )
            # --- End Log ---

            return {
                "statusCode": 200, "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": f"Successfully added {amount} to savings goal."})
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            print(f"DynamoDB ClientError during transaction: {error_code}")
            if error_code == 'TransactionCanceledException':
                reasons = e.response.get('CancellationReasons', [])
                if any(r.get('Code') == 'ConditionalCheckFailed' for r in reasons):
                    print("Transaction failed: Insufficient funds OR goal ID mismatch/not found.")
                    return {
                        "statusCode": 400, "headers": POST_CORS_HEADERS,
                        "body": json.dumps({"message": "Transaction failed. Check wallet balance or savings goal ID."})
                    }
            return {
                "statusCode": 500, "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": "Database error during transaction.", "error": str(e)})
            }
        except (ValueError, TypeError, InvalidOperation) as ve:
            print(f"Input Error: {ve}")
            return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Invalid amount format: {ve}"}) }
        except Exception as e:
            print(f"Unexpected error: {e}")
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "An unexpected error occurred.", "error": str(e)}) }
    else:
        return { "statusCode": 405, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }