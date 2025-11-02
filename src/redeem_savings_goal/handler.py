import json
import os
import boto3
import uuid
import time
from decimal import Decimal
from urllib.parse import unquote
from botocore.exceptions import ClientError
import logging

# Set up logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Table Names & CORS ---
SAVINGS_TABLE_NAME = os.environ.get('SAVINGS_TABLE_NAME')
WALLETS_TABLE_NAME = os.environ.get('WALLETS_TABLE_NAME')
LOG_TABLE_NAME = os.environ.get('TRANSACTIONS_LOG_TABLE_NAME')
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")

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

# --- DecimalEncoder ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

# --- Transaction Logging Helper ---
def log_transaction(log_table, wallet_id, tx_type, amount, new_balance=None, related_id=None, details=None):
    if not log_table:
        logger.warn(json.dumps({"status": "warn", "action": "log_transaction", "message": "Log table not configured."}))
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
            "transaction_id": log_item['transaction_id'],
            "type": tx_type
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
# ---

def redeem_savings_goal(event, context):
    """
    API: POST /savings-goal/{goal_id}/redeem
    Redeems a completed goal, atomically moving funds back to the wallet.
    """
    
    # --- Initialize boto3 clients inside the handler ---
    dynamodb_resource = boto3.resource('dynamodb')
    dynamodb_client = boto3.client('dynamodb')
    savings_table = dynamodb_resource.Table(SAVINGS_TABLE_NAME) if SAVINGS_TABLE_NAME else None
    wallets_table = dynamodb_resource.Table(WALLETS_TABLE_NAME) if WALLETS_TABLE_NAME else None
    log_table = dynamodb_resource.Table(LOG_TABLE_NAME) if LOG_TABLE_NAME else None
    
    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        logger.info("Handling OPTIONS preflight request for redeem_savings_goal")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }

    if not savings_table or not wallets_table or not log_table:
        log_message = {
            "status": "error",
            "action": "redeem_savings_goal",
            "message": "FATAL: Environment variables not configured."
        }
        logger.error(json.dumps(log_message))
        return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'POST':
        goal_id = "unknown"
        log_context = {"action": "redeem_savings_goal"}
        try:
            goal_id = unquote(event['pathParameters']['goal_id']).strip()
            log_context["goal_id"] = goal_id
            
            logger.info(json.dumps({**log_context, "status": "info", "message": "Attempting to redeem goal."}))

            # 1. Get the goal to verify it's complete
            response = savings_table.get_item(Key={'goal_id': goal_id})
            goal_item = response.get('Item')

            if not goal_item:
                logger.warn(json.dumps({**log_context, "status": "warn", "message": "Savings goal not found."}))
                return { "statusCode": 404, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Savings goal not found."}) }

            current_amount = goal_item.get('current_amount', Decimal('0'))
            target_amount = goal_item.get('target_amount', Decimal('0'))
            wallet_id = goal_item.get('wallet_id')
            goal_name = goal_item.get('goal_name', 'Redeemed Goal')

            log_context.update({
                "wallet_id": wallet_id,
                "current_amount": str(current_amount),
                "target_amount": str(target_amount)
            })

            # 2. Check if goal is actually complete
            if current_amount < target_amount:
                logger.warn(json.dumps({**log_context, "status": "warn", "message": "Goal not yet complete. Cannot redeem."}))
                return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Goal is not yet complete. Cannot redeem."}) }
            
            if not wallet_id:
                 logger.error(json.dumps({**log_context, "status": "error", "message": "Goal item is corrupt, missing wallet_id."}))
                 return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Goal item is corrupt, missing wallet_id."}) }

            # 3. Perform atomic transaction
            logger.info(json.dumps({**log_context, "status": "info", "message": "Goal is complete. Refunding to wallet."}))
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
                wallet_response = wallets_table.get_item(Key={'wallet_id': wallet_id}, ConsistentRead=True)
                new_wallet_balance = wallet_response.get('Item', {}).get('balance', 'N/A')
            except Exception as log_get_e:
                logger.error(json.dumps({**log_context, "status": "error", "message": f"Could not fetch new balance for logging: {str(log_get_e)}"}))

            # 5. Log the redemption
            log_transaction(
                log_table=log_table,
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
            log_context["error_code"] = e.response['Error']['Code']
            if e.response['Error']['Code'] == 'TransactionCanceledException':
                 logger.error(json.dumps({**log_context, "status": "error", "message": f"Transaction failed: {e.response['CancellationReasons']}"}))
                 return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Transaction failed. Could not refund to wallet.", "error": str(e)}) }
            
            logger.error(json.dumps({**log_context, "status": "error", "error_message": str(e)}))
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Database error.", "error": str(e)}) }
        except Exception as e:
            logger.error(json.dumps({**log_context, "status": "error", "error_message": str(e)}))
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "An unexpected error occurred.", "error": str(e)}) }
    else:
        return { "statusCode": 405, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }