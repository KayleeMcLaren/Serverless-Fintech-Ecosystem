import json
import os
import boto3
import uuid 
import time 
from decimal import Decimal, InvalidOperation
from urllib.parse import unquote
from botocore.exceptions import ClientError

# --- (CORS Headers - no changes) ---
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

# --- Table Names ---
SAVINGS_TABLE_NAME = os.environ.get('SAVINGS_TABLE_NAME')
WALLETS_TABLE_NAME = os.environ.get('WALLETS_TABLE_NAME')
LOG_TABLE_NAME = os.environ.get('TRANSACTIONS_LOG_TABLE_NAME') 

# --- REMOVE BOTO3 CLIENTS FROM GLOBAL SCOPE ---

# --- Transaction Logging Helper ---
def log_transaction(wallet_id, tx_type, amount, new_balance=None, related_id=None, details=None):
    # --- FIX: Initialize boto3 inside the function ---
    if not LOG_TABLE_NAME:
        print("Log table name not configured, skipping log.")
        return
    try:
        log_table = boto3.resource('dynamodb').Table(LOG_TABLE_NAME)
        # --- END FIX ---
        
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

def add_to_savings_goal(event, context):
    
    # --- FIX: Initialize boto3 clients inside the handler ---
    dynamodb_client = boto3.client('dynamodb')
    dynamodb_resource = boto3.resource('dynamodb')
    savings_table = dynamodb_resource.Table(SAVINGS_TABLE_NAME) if SAVINGS_TABLE_NAME else None
    wallets_table = dynamodb_resource.Table(WALLETS_TABLE_NAME) if WALLETS_TABLE_NAME else None
    # --- END FIX ---

    # --- (CORS Preflight Check - no changes) ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }
    
    if not savings_table or not wallets_table or not LOG_TABLE_NAME: # Check LOG_TABLE_NAME
         print("FATAL: Environment variables not configured.")
         return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'POST':
        goal_name_for_log = 'Savings Goal'
        try:
            goal_id = unquote(event['pathParameters']['goal_id']).strip()
            body = json.loads(event.get('body', '{}'))
            wallet_id = body.get('wallet_id')
            amount_str = body.get('amount', '0.00')
            amount = Decimal(amount_str)

            if not wallet_id or amount <= 0:
                raise ValueError("Valid wallet_id and positive amount are required.")
            
            # --- (Wallet balance check - no changes) ---
            try:
                wallet_response = wallets_table.get_item(
                    Key={'wallet_id': wallet_id},
                    ConsistentRead=True 
                )
                wallet_item = wallet_response.get('Item')
                if not wallet_item:
                    raise ValueError("Wallet not found.")
                
                current_balance = wallet_item.get('balance', Decimal('0'))
                if current_balance < amount:
                    print(f"Insufficient funds: Wallet {wallet_id} has {current_balance}, needs {amount}")
                    return {
                        "statusCode": 400, "headers": POST_CORS_HEADERS,
                        "body": json.dumps({"message": "Insufficient funds."})
                    }
            except ClientError as ce:
                print(f"Error checking wallet balance: {ce}")
                raise ValueError("Could not verify wallet balance.")
                
            # --- (Fetch Goal Name - no changes) ---
            try:
                goal_response = savings_table.get_item(Key={'goal_id': goal_id})
                goal_item = goal_response.get('Item')
                if goal_item:
                    goal_name_for_log = goal_item.get('goal_name', 'Savings Goal')
                else:
                    print(f"Warning: Goal {goal_id} not found, transaction will likely fail.")
            except Exception as get_e:
                print(f"Warning: Could not fetch goal name for logging: {get_e}")

            print(f"Attempting transaction: Move {amount} from wallet {wallet_id} to goal '{goal_name_for_log}' ({goal_id})")

            # --- (Perform the transaction - no changes) ---
            dynamodb_client.transact_write_items(
                TransactItems=[
                    { # Debit wallet
                        'Update': {
                            'TableName': WALLETS_TABLE_NAME,
                            'Key': {'wallet_id': {'S': wallet_id}},
                            'UpdateExpression': 'SET balance = balance - :amount',
                            'ConditionExpression': 'balance >= :amount',
                            'ExpressionAttributeValues': {':amount': {'N': str(amount)}}
                        }
                    },
                    { # Credit savings goal
                        'Update': {
                            'TableName': SAVINGS_TABLE_NAME,
                            'Key': {'goal_id': {'S': goal_id}},
                            'UpdateExpression': 'SET current_amount = current_amount + :amount',
                            'ConditionExpression': 'attribute_exists(goal_id) AND wallet_id = :wallet_id_val',
                            'ExpressionAttributeValues': {
                                ':amount': {'N': str(amount)},
                                ':wallet_id_val': {'S': wallet_id}
                             }
                        }
                    }
                ]
            )
            print(f"Transaction successful for goal {goal_id}")
                
            # --- (Log Transaction - no changes) ---
            new_wallet_balance = current_balance - amount 
            log_transaction(
                wallet_id=wallet_id,
                tx_type="SAVINGS_ADD",
                amount=amount,
                new_balance=new_wallet_balance,
                related_id=goal_id,
                details={"goal_name": goal_name_for_log}
            )

            return { "statusCode": 200, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Successfully added {amount} to savings goal."}) }

        except ClientError as e:
            # ... (rest of error handling)
            error_code = e.response['Error']['Code']
            print(f"DynamoDB ClientError during transaction: {error_code}")
            if error_code == 'TransactionCanceledException':
                reasons = e.response.get('CancellationReasons', [])
                if any(r.get('Code') == 'ConditionalCheckFailed' for r in reasons):
                    print("Transaction failed: Goal ID mismatch/not found.")
                    return {
                        "statusCode": 400, "headers": POST_CORS_HEADERS,
                        "body": json.dumps({"message": "Transaction failed. Savings goal not found or wallet ID mismatch."})
                    }
            return {
                "statusCode": 500, "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": "Database error during transaction.", "error": str(e)})
            }
        except (ValueError, TypeError, InvalidOperation) as ve:
            print(f"Input Error: {ve}")
            return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Invalid input: {str(ve)}"}) }
        except Exception as e:
            print(f"Unexpected error: {e}")
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "An unexpected error occurred.", "error": str(e)}) }
    else:
         return { "statusCode": 405, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }