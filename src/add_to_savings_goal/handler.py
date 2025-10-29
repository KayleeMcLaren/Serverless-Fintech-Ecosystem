import json
import os
import boto3
import uuid # For transaction ID
import time # For timestamp
from decimal import Decimal, InvalidOperation # Import InvalidOperation
from urllib.parse import unquote
from botocore.exceptions import ClientError

# --- CORS Configuration ---
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")
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
dynamodb_resource = boto3.resource('dynamodb') # Use resource for gets/puts
savings_table = dynamodb_resource.Table(SAVINGS_TABLE_NAME) if SAVINGS_TABLE_NAME else None # Use resource client for savings table
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
        goal_name_for_log = 'Savings Goal'
        updated_goal_balance = None # Variable to store the goal's balance
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
            
            # --- Fetch Goal Name BEFORE Transaction ---
            goal_name_from_db = None # Use a temporary variable
            try:
                goal_response = savings_table.get_item(Key={'goal_id': goal_id})
                goal_item = goal_response.get('Item')
                if goal_item:
                    # Use the explicit default string 'Savings Goal' as the fallback
                    goal_name_from_db = goal_item.get('goal_name', 'Savings Goal')
                else:
                    print(f"Warning: Savings goal {goal_id} not found before transaction attempt.")
            except Exception as get_e:
                print(f"Warning: Could not fetch goal name for logging: {get_e}")

            # Assign to goal_name_for_log outside the inner try if found, otherwise keep default
            if goal_name_from_db:
                goal_name_for_log = goal_name_from_db
            # --- End Fetch Goal Name ---

            print(f"Attempting transaction: Move {amount} from wallet {wallet_id} to goal '{goal_name_for_log}' ({goal_id})")

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

            # --- Fetch Updated Goal Balance AFTER Transaction ---
            try:
                updated_goal_response = savings_table.get_item(Key={'goal_id': goal_id})
                updated_goal_item = updated_goal_response.get('Item')
                if updated_goal_item:
                    updated_goal_balance = updated_goal_item.get('current_amount') # Get the new current_amount
            except Exception as get_e:
                print(f"Warning: Could not fetch updated goal balance after transaction: {get_e}")
            # --- End Fetch Updated Goal Balance ---

            # --- Log Transaction (using fetched goal name and balance) ---
            log_transaction(
                wallet_id=wallet_id, # Log against the main wallet
                tx_type="SAVINGS_ADD",
                amount=amount,
                # Pass the GOAL's balance, not the wallet's
                new_balance=updated_goal_balance,
                related_id=goal_id,
                details={
                    "goal_name": goal_name_for_log,
                    "balance_is_goal": True # Flag to indicate this balance is for the goal
                }
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