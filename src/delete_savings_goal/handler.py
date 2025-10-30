import json
import os
import boto3
import uuid # For transaction ID
import time # For timestamp
from decimal import Decimal
from urllib.parse import unquote
from botocore.exceptions import ClientError

# --- Table Names ---
SAVINGS_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
WALLETS_TABLE_NAME = os.environ.get('WALLETS_TABLE_NAME')
LOG_TABLE_NAME = os.environ.get('TRANSACTIONS_LOG_TABLE_NAME')
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")

# --- AWS Resources ---
dynamodb_resource = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
savings_table = dynamodb_resource.Table(SAVINGS_TABLE_NAME) if SAVINGS_TABLE_NAME else None
wallets_table = dynamodb_resource.Table(WALLETS_TABLE_NAME) if WALLETS_TABLE_NAME else None
log_table = dynamodb_resource.Table(LOG_TABLE_NAME) if LOG_TABLE_NAME else None

# --- CORS Headers ---
OPTIONS_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Credentials": True
}
DELETE_CORS_HEADERS = {
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
             log_item['balance_after'] = 'N/A'

        log_table.put_item(Item=log_item)
        print(f"Logged transaction: {log_item['transaction_id']} for wallet {wallet_id}")
    except Exception as log_e:
        print(f"ERROR logging transaction: {log_e}")
# --- End Helper ---

def delete_savings_goal(event, context):
    """
    Deletes a savings goal. If the goal has a balance > 0,
    it atomically transfers the balance back to the user's wallet.
    """
    
    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request for delete_savings_goal")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }
    # --- End CORS Preflight Check ---

    if not savings_table or not wallets_table or not log_table:
        print("FATAL: Environment variables not configured.")
        return { "statusCode": 500, "headers": DELETE_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'DELETE':
        try:
            goal_id = unquote(event['pathParameters']['goal_id']).strip()
            print(f"Attempting to delete goal: {goal_id}")

            # 1. Get the goal to find its balance and wallet_id
            response = savings_table.get_item(Key={'goal_id': goal_id})
            goal_item = response.get('Item')

            if not goal_item:
                return { "statusCode": 404, "headers": DELETE_CORS_HEADERS, "body": json.dumps({"message": "Savings goal not found."}) }

            current_amount = goal_item.get('current_amount', Decimal('0'))
            wallet_id = goal_item.get('wallet_id')
            goal_name = goal_item.get('goal_name', 'Deleted Goal')

            if not wallet_id:
                 return { "statusCode": 500, "headers": DELETE_CORS_HEADERS, "body": json.dumps({"message": "Goal item is corrupt, missing wallet_id."}) }

            # 2. Perform actions
            if current_amount > 0:
                print(f"Goal has {current_amount}. Refunding to wallet {wallet_id}.")
                dynamodb_client.transact_write_items(
                    TransactItems=[
                        { # Credit wallet
                            'Update': {
                                'TableName': WALLETS_TABLE_NAME,
                                'Key': {'wallet_id': {'S': wallet_id}},
                                'UpdateExpression': 'SET balance = balance + :amount',
                                'ConditionExpression': 'attribute_exists(wallet_id)',
                                'ExpressionAttributeValues': {':amount': {'N': str(current_amount)}}
                            }
                        },
                        { # Delete goal
                            'Delete': {
                                'TableName': SAVINGS_TABLE_NAME,
                                'Key': {'goal_id': {'S': goal_id}}
                            }
                        }
                    ]
                )
                
                # --- 3. FIX: Get new wallet balance with ConsistentRead ---
                new_wallet_balance = 'N/A'
                try:
                    wallet_response = wallets_table.get_item(
                        Key={'wallet_id': wallet_id},
                        ConsistentRead=True # Force strongly consistent read
                    )
                    new_wallet_balance = wallet_response.get('Item', {}).get('balance', 'N/A')
                except Exception as log_get_e:
                    print(f"Could not fetch new balance for logging: {log_get_e}")
                # --- END FIX ---

                log_transaction(
                    wallet_id=wallet_id,
                    tx_type="SAVINGS_REFUND",
                    amount=current_amount,
                    new_balance=new_wallet_balance, # Pass the fetched balance
                    related_id=goal_id,
                    details={"message": f"Refunded from deleted goal: {goal_name}"}
                )
                
            else:
                print("Goal balance is 0. Deleting item.")
                savings_table.delete_item(Key={'goal_id': goal_id})

            return {
                "statusCode": 200,
                "headers": DELETE_CORS_HEADERS,
                "body": json.dumps({"message": "Savings goal deleted and funds refunded."})
            }

        except ClientError as e:
            if e.response['Error']['Code'] == 'TransactionCanceledException':
                 print(f"Transaction failed: {e.response['CancellationReasons']}")
                 return { "statusCode": 400, "headers": DELETE_CORS_HEADERS, "body": json.dumps({"message": "Transaction failed. Could not refund to wallet.", "error": str(e)}) }
            print(f"DynamoDB Error: {e}")
            return { "statusCode": 500, "headers": DELETE_CORS_HEADERS, "body": json.dumps({"message": "Database error.", "error": str(e)}) }
        except Exception as e:
            print(f"Error: {e}")
            return {
                "statusCode": 500,
                "headers": DELETE_CORS_HEADERS,
                "body": json.dumps({"message": "Failed to delete savings goal.", "error": str(e)})
            }
    else:
        return { "statusCode": 405, "headers": DELETE_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }