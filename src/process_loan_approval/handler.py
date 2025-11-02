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
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME') # Wallet table
LOG_TABLE_NAME = os.environ.get('TRANSACTIONS_LOG_TABLE_NAME') # Log Table Name

# --- (DecimalEncoder - no changes) ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

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

def process_loan_approval(event, context):
    """Processes 'LOAN_APPROVED' events, credits wallet, logs transaction."""
    
    # --- 4. Initialize boto3 clients inside the handler ---
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME) if TABLE_NAME else None
    log_table = dynamodb.Table(LOG_TABLE_NAME) if LOG_TABLE_NAME else None
    # ---

    if not table or not log_table:
        log_message = {
            "status": "error",
            "action": "process_loan_approval",
            "message": "FATAL: Environment variables not set."
        }
        logger.error(json.dumps(log_message))
        raise Exception("Server configuration error.") # Raise to force retry

    logger.info(f"Received event: {json.dumps(event)}")
    
    for record in event['Records']:
        message_id = record.get('Sns', {}).get('MessageId', 'Unknown')
        log_context = {"action": "process_loan_approval", "sns_message_id": message_id}
        
        try:
            sns_message_str = record.get('Sns', {}).get('Message')
            if not sns_message_str:
                logger.warn(json.dumps({**log_context, "status": "warn", "message": "Skipping record: Missing SNS message body."}))
                continue

            sns_message = json.loads(sns_message_str)
            event_type = sns_message.get('event_type')
            
            if event_type == 'LOAN_APPROVED':
                loan_details = sns_message.get('loan_details', {})
                wallet_id = loan_details.get('wallet_id')
                amount_str = loan_details.get('remaining_balance') or loan_details.get('amount')
                loan_id = loan_details.get('loan_id')

                # Update log context
                log_context['wallet_id'] = wallet_id
                log_context['loan_id'] = loan_id
                log_context['event_type'] = event_type

                if not wallet_id or not amount_str or not loan_id:
                    logger.error(json.dumps({**log_context, "status": "error", "message": "Invalid loan details in message."}))
                    continue

                amount = Decimal(amount_str)
                if amount <= 0:
                    logger.warn(json.dumps({**log_context, "status": "warn", "message": f"Loan amount is not positive: {amount}"}))
                    continue

                logger.info(json.dumps({**log_context, "status": "info", "amount": str(amount), "message": "Processing loan approval."}))

                # Credit the wallet
                response = table.update_item(
                    Key={'wallet_id': wallet_id},
                    UpdateExpression="SET balance = balance + :amount",
                    ExpressionAttributeValues={ ':amount': amount },
                    ConditionExpression="attribute_exists(wallet_id)",
                    ReturnValues="UPDATED_NEW"
                )
                
                new_balance = response.get('Attributes', {}).get('balance')
                logger.info(json.dumps({**log_context, "status": "info", "new_balance": str(new_balance), "message": "Successfully credited wallet."}))
                
                # Log Transaction
                log_transaction(
                    log_table=log_table,
                    wallet_id=wallet_id,
                    tx_type="LOAN_IN",
                    amount=amount,
                    new_balance=new_balance,
                    related_id=loan_id
                )
            else:
                logger.warn(json.dumps({**log_context, "status": "warn", "message": f"Skipping unhandled event type: {event_type}"}))

        except (ValueError, InvalidOperation, TypeError) as val_err:
             logger.error(json.dumps({**log_context, "status": "error", "message": f"Invalid data error: {str(val_err)}"}))
        except ClientError as ce:
             logger.error(json.dumps({**log_context, "status": "error", "error_code": ce.response['Error']['Code'], "message": f"DynamoDB error: {str(ce)}"}))
             raise ce # Re-raise to force SNS retry
        except Exception as inner_e:
             logger.error(json.dumps({**log_context, "status": "error", "message": f"Unexpected error processing record: {str(inner_e)}"}))
             raise inner_e # Re-raise to force SNS retry

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Loan approval processing complete."})
    }