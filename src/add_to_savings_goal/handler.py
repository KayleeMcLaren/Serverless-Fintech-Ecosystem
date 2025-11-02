import json
import os
import boto3
import uuid 
import time 
from decimal import Decimal, InvalidOperation
from urllib.parse import unquote
from botocore.exceptions import ClientError
import logging

# --- 1. Set up logger ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# ---

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
LOG_TABLE_NAME = os.environ.get('TRANSACTIONS_LOG_TABLE_NAME') 

# --- Transaction Logging Helper ---
def log_transaction(log_table, wallet_id, tx_type, amount, new_balance=None, related_id=None, details=None):
    if not log_table:
        logger.warning(json.dumps({"status": "warn", "action": "log_transaction", "message": "Log table not configured."}))
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
        
        log_message = {
            "status": "info",
            "action": "log_transaction",
            "wallet_id": wallet_id,
            "transaction_id": log_item['transaction_id']
        }
        logger.info(json.dumps(log_message))

    except Exception as log_e:
        log_message = {
            "status": "error",
            "action": "log_transaction",
            "wallet_id": wallet_id,
            "error_message": str(log_e)
        }
        logger.error(json.dumps(log_message))
# --- End Helper ---

def add_to_savings_goal(event, context):
    """
    Atomically moves funds using a DynamoDB transaction and logs it.
    Handles OPTIONS preflight.
    """
    
    # --- 2. Initialize boto3 clients inside the handler ---
    dynamodb_client = boto3.client('dynamodb')
    dynamodb_resource = boto3.resource('dynamodb')
    savings_table = dynamodb_resource.Table(SAVINGS_TABLE_NAME) if SAVINGS_TABLE_NAME else None
    wallets_table = dynamodb_resource.Table(WALLETS_TABLE_NAME) if WALLETS_TABLE_NAME else None
    log_table = dynamodb_resource.Table(LOG_TABLE_NAME) if LOG_TABLE_NAME else None
    # ---
    
    # --- (CORS Preflight Check - no changes) ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        logger.info("Handling OPTIONS preflight request for add_to_savings_goal")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }
    
    if not savings_table or not wallets_table or not log_table:
         log_message = {
            "status": "error",
            "action": "add_to_savings_goal",
            "message": "FATAL: Environment variables not configured."
         }
         logger.error(json.dumps(log_message))
         return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'POST':
        goal_name_for_log = 'Savings Goal'
        log_context = {"action": "add_to_savings_goal"}
        wallet_id = "unknown"
        goal_id = "unknown"
        
        try:
            goal_id = unquote(event['pathParameters']['goal_id']).strip()
            body = json.loads(event.get('body', '{}'))
            wallet_id = body.get('wallet_id')
            amount_str = body.get('amount', '0.00')
            amount = Decimal(amount_str)

            log_context.update({"wallet_id": wallet_id, "goal_id": goal_id})

            if not wallet_id or amount <= 0:
                raise ValueError("Valid wallet_id and positive amount are required.")
            
            log_context["amount"] = str(amount)

            # 1. Get the wallet *first* to check the balance
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
                    logger.warning(json.dumps({**log_context, "status": "warn", "current_balance": str(current_balance), "message": "Insufficient funds."}))
                    return {
                        "statusCode": 400, "headers": POST_CORS_HEADERS,
                        "body": json.dumps({"message": "Insufficient funds."})
                    }
            except ClientError as ce:
                logger.error(json.dumps({**log_context, "status": "error", "error_code": ce.response['Error']['Code'], "message": f"Error checking wallet balance: {str(ce)}"}))
                raise ValueError("Could not verify wallet balance.")
                
            # 2. Fetch Goal Name (for logging)
            try:
                goal_response = savings_table.get_item(Key={'goal_id': goal_id})
                goal_item = goal_response.get('Item')
                if goal_item:
                    goal_name_for_log = goal_item.get('goal_name', 'Savings Goal')
                else:
                    logger.warning(json.dumps({**log_context, "status": "warn", "message": "Goal not found, transaction will likely fail."}))
            except Exception as get_e:
                logger.warning(json.dumps({**log_context, "status": "warn", "message": f"Could not fetch goal name for logging: {str(get_e)}"}))

            logger.info(json.dumps({**log_context, "status": "info", "message": "Attempting transaction."}))

            # 3. Perform the transaction
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
            logger.info(json.dumps({**log_context, "status": "info", "message": "Transaction successful."}))
                
            # 4. Log Transaction
            new_wallet_balance = current_balance - amount 
            
            log_transaction(
                log_table=log_table,
                wallet_id=wallet_id,
                tx_type="SAVINGS_ADD",
                amount=amount,
                new_balance=new_wallet_balance,
                related_id=goal_id,
                details={"goal_name": goal_name_for_log}
            )

            return { "statusCode": 200, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Successfully added {amount} to savings goal."}) }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            log_context["error_code"] = error_code
            logger.error(json.dumps({**log_context, "status": "error", "message": f"DynamoDB ClientError: {str(e)}"}))
            
            if error_code == 'TransactionCanceledException':
                reasons = e.response.get('CancellationReasons', [])
                if any(r.get('Code') == 'ConditionalCheckFailed' for r in reasons):
                    logger.warning(json.dumps({**log_context, "status": "warn", "message": "Transaction failed: ConditionalCheckFailed."}))
                    return {
                        "statusCode": 400, "headers": POST_CORS_HEADERS,
                        "body": json.dumps({"message": "Transaction failed. Savings goal not found or wallet ID mismatch."})
                    }
            return {
                "statusCode": 500, "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": "Database error during transaction.", "error": str(e)})
            }
        except (ValueError, TypeError, InvalidOperation) as ve:
             logger.error(json.dumps({**log_context, "status": "error", "error_message": str(ve)}))
             return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Invalid input: {str(ve)}"}) }
        except Exception as e:
            logger.error(json.dumps({**log_context, "status": "error", "error_message": str(e)}))
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "An unexpected error occurred.", "error": str(e)}) }
    else:
         return { "statusCode": 405, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }