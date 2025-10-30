import json
import os
import boto3
import uuid
import time
from decimal import Decimal
from urllib.parse import unquote
from botocore.exceptions import ClientError

# --- Table Names & CORS ---
SAVINGS_TABLE_NAME = os.environ.get('SAVINGS_TABLE_NAME')
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
    "Access-Control-Allow-Methods": "POST, OPTIONS", # Allow POST
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Credentials": True
}
POST_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Credentials": True
}

# --- (Keep DecimalEncoder as is) ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

# --- (Keep Transaction Logging Helper as is) ---
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

def redeem_savings_goal(event, context):
    """
    Redeems a completed savings goal.
    Atomically transfers the balance back to the user's wallet and deletes the goal.
    """
    
    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request for redeem_savings_goal")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }
    # --- End CORS Preflight Check ---

    if not savings_table or not wallets_table or not log_table:
        print("FATAL: Environment variables not configured.")
        return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'POST':
        try:
            goal_id = unquote(event['pathParameters']['goal_id']).strip()
            print(f"Attempting to redeem goal: {goal_id}")

            # 1. Get the goal to verify it's complete
            response = savings_table.get_item(Key={'goal_id': goal_id})
            goal_item = response.get('Item')

            if not goal_item:
                return { "statusCode": 404, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Savings goal not found."}) }

            current_amount = goal_item.get('current_amount', Decimal('0'))
            target_amount = goal_item.get('target_amount', Decimal('0'))
            wallet_id = goal_item.get('wallet_id')
            goal_name = goal_item.get('goal_name', 'Redeemed Goal')

            # 2. Check if goal is actually complete
            if current_amount < target_amount:
                print("Goal not yet complete. Cannot redeem.")
                return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Goal is not yet complete. Cannot redeem."}) }
            
            if not wallet_id:
                 return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Goal item is corrupt, missing wallet_id."}) }

            # 3. Perform atomic transaction
            print(f"Goal is complete. Refunding {current_amount} to wallet {wallet_id}.")
            dynamodb_client.transact_write_items(
                TransactItems=[
                    { # Operation 1: Credit the wallet
                        'Update': {
                            'TableName': WALLETS_TABLE_NAME,
                            'Key': {'wallet_id': {'S': wallet_id}},
                            'UpdateExpression': 'SET balance = balance + :amount',
                            'ConditionExpression': 'attribute_exists(wallet_id)',
                            'ExpressionAttributeValues': {':amount': {'N': str(current_amount)}}
                        }
                    },
                    { # Operation 2: Delete the savings goal
                        'Delete': {
                            'TableName': SAVINGS_TABLE_NAME,
                            'Key': {'goal_id': {'S': goal_id}}
                        }
                    }
                ]
            )
            
            # 4. Get new wallet balance for logging
            new_wallet_balance = 'N/A'
            try:
                wallet_response = wallets_table.get_item(
                    Key={'wallet_id': wallet_id},
                    ConsistentRead=True # Force strongly consistent read
                )
                new_wallet_balance = wallet_response.get('Item', {}).get('balance', 'N/A')
            except Exception as log_get_e:
                print(f"Could not fetch new balance for logging: {log_get_e}")

            # 5. Log the redemption
            log_transaction(
                wallet_id=wallet_id,
                tx_type="SAVINGS_REDEEM",
                amount=current_amount,
                new_balance=new_wallet_balance,
                related_id=goal_id,
                details={"message": f"Redeemed goal: {goal_name}"}
            )
            
            return {
                "statusCode": 200,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": "Savings goal redeemed and funds transferred to wallet."})
            }

        except ClientError as e:
            print(f"DynamoDB ClientError during redemption: {e}")
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Error processing redemption."}) }
        except Exception as e:
            print(f"Unexpected error during redemption: {e}")
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Unexpected error occurred."}) }
    else:
        print(f"Unsupported HTTP method: {http_method}")
        return { "statusCode": 405, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Method not allowed."}) }
