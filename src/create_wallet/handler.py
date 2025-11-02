import json
import os
import boto3
import uuid
import time
from decimal import Decimal
from botocore.exceptions import ClientError
import logging

# --- Set up logger ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# ---

# --- Environment Variables ---
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
LOG_TABLE_NAME = os.environ.get('TRANSACTIONS_LOG_TABLE_NAME')
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*") # Not used by this Lambda, but good practice

# --- CORS Headers ---
# Note: This Lambda is now private and not called by API Gateway,
# but we'll keep the headers for potential future debugging.
POST_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Credentials": True
}
# ---

# --- DecimalEncoder ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)
# ---

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

# --- THIS IS THE CORRECT FUNCTION ---
def create_wallet(event, context):
    """
    Creates a new digital wallet with a zero balance.
    This handler is invoked by the Step Function, not API Gateway.
    """
    
    # --- Initialize boto3 clients inside the handler ---
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME) if TABLE_NAME else None
    log_table = dynamodb.Table(LOG_TABLE_NAME) if LOG_TABLE_NAME else None
    
    log_context = {"action": "create_wallet"}
    
    if not table or not log_table:
        log_message = {
            **log_context,
            "status": "error",
            "message": "FATAL: Environment variables not set."
        }
        logger.error(json.dumps(log_message))
        # This error will be returned to the Step Function
        raise Exception("Server configuration error.")

    try:
        wallet_id = str(uuid.uuid4())
        timestamp = int(time.time())
        new_balance = Decimal('0.00')
        
        log_context["wallet_id"] = wallet_id
        
        item = {
            'wallet_id': wallet_id,
            'balance': new_balance,
            'currency': 'USD',
            'created_at': timestamp,
            'updated_at': timestamp
        }
        
        table.put_item(Item=item)
        
        logger.info(json.dumps({**log_context, "status": "info", "message": "New wallet created in DynamoDB."}))

        # Log this as the first transaction
        log_transaction(
            log_table=log_table,
            wallet_id=wallet_id,
            tx_type="WALLET_CREATED",
            amount=Decimal('0.00'),
            new_balance=new_balance,
            related_id=wallet_id
        )
        
        # Return a 201 response so the Step Function knows it succeeded
        return {
            "statusCode": 201,
            "headers": POST_CORS_HEADERS,
            "body": json.dumps({"message": "Wallet created successfully!", "wallet": item}, cls=DecimalEncoder)
        }

    except ClientError as e:
        log_message = {
            **log_context,
            "status": "error",
            "error_code": e.response['Error']['Code'],
            "error_message": str(e)
        }
        logger.error(json.dumps(log_message))
        raise e # Re-raise to fail the Step Function task
    except Exception as e:
        log_message = {
            **log_context,
            "status": "error",
            "error_message": str(e)
        }
        logger.error(json.dumps(log_message))
        raise e # Re-raise to fail the Step Function task