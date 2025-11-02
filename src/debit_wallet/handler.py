import json
import os
import boto3
import uuid
import time
from decimal import Decimal, InvalidOperation
from botocore.exceptions import ClientError
import logging # <-- 1. Import logging

# --- 2. Set up logger ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# ---

# --- Environment Variables ---
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
LOG_TABLE_NAME = os.environ.get('TRANSACTIONS_LOG_TABLE_NAME')
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")

# --- (CORS Headers - no changes) ---
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
# ---

# --- (DecimalEncoder - no changes) ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)
# ---

# --- 3. Update log_transaction to use a logger ---
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
# ---

def debit_wallet(event, context):
    """
    Debits (subtracts) a specified amount from the wallet.
    Fails if funds are insufficient.
    """

    # --- 4. Initialize boto3 clients inside the handler ---
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME) if TABLE_NAME else None
    log_table = dynamodb.Table(LOG_TABLE_NAME) if LOG_TABLE_NAME else None
    # ---

    # --- (CORS Preflight Check - no changes) ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        logger.info("Handling OPTIONS preflight request for debit_wallet")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }

    if not table or not log_table:
        log_message = {
            "status": "error",
            "action": "debit_wallet",
            "message": "FATAL: Environment variables not set."
        }
        logger.error(json.dumps(log_message))
        return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'POST':
        wallet_id = "unknown"
        try:
            wallet_id = event['pathParameters']['wallet_id'].strip()
            body = json.loads(event.get('body', '{}'))
            amount = Decimal(body.get('amount', '0.00'))

            if amount <= 0:
                raise ValueError("Debit amount must be positive.")

            log_message = {
                "status": "info",
                "action": "debit_wallet",
                "wallet_id": wallet_id,
                "amount": str(amount)
            }
            logger.info(json.dumps(log_message))

            # Use a conditional expression to prevent overdraft
            response = table.update_item(
                Key={'wallet_id': wallet_id},
                UpdateExpression="SET balance = balance - :amount",
                ConditionExpression="attribute_exists(wallet_id) AND balance >= :amount",
                ExpressionAttributeValues={':amount': amount},
                ReturnValues="UPDATED_NEW"
            )
            
            new_balance = response.get('Attributes', {}).get('balance')
            
            # Log this transaction
            log_transaction(
                log_table=log_table,
                wallet_id=wallet_id,
                tx_type="DEBIT",
                amount=amount,
                new_balance=new_balance
            )

            return {
                "statusCode": 200,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": "Debit successful!", "balance": new_balance}, cls=DecimalEncoder)
            }

        except (ValueError, TypeError, InvalidOperation) as ve:
             log_message = {
                "status": "error",
                "action": "debit_wallet",
                "wallet_id": wallet_id,
                "error_message": str(ve)
             }
             logger.error(json.dumps(log_message))
             return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Invalid input: {str(ve)}"}) }
        except ClientError as e:
            log_message = {
                "status": "error",
                "action": "debit_wallet",
                "wallet_id": wallet_id,
                "error_code": e.response['Error']['Code'],
                "error_message": str(e)
            }
            logger.error(json.dumps(log_message))
            
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Insufficient funds."}) }
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Database error.", "error": str(e)}) }
        except Exception as e:
            log_message = {
                "status": "error",
                "action": "debit_wallet",
                "wallet_id": wallet_id,
                "error_message": str(e)
            }
            logger.error(json.dumps(log_message))
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "An unexpected error occurred.", "error": str(e)}) }
    else:
         return { "statusCode": 405, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }