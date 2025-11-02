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

# --- Table Names & SNS Topic ---
WALLET_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
LOG_TABLE_NAME = os.environ.get('TRANSACTIONS_LOG_TABLE_NAME')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')

# --- (DecimalEncoder - no changes) ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal): return str(o)
        return super(DecimalEncoder, self).default(o)

# --- 3. Update log_transaction to use a logger ---
def log_transaction(log_table, wallet_id, tx_type, amount, new_balance=None, related_id=None, details=None):
    if not log_table:
        logger.warning(json.dumps({"status": "warn", "action": "log_transaction", "message": "Log table not configured."}))
        return
    try:
        timestamp = int(time.time())
        log_item = {
            'transaction_id': str(uuid.uuid4()), 'wallet_id': wallet_id,
            'timestamp': timestamp, 'type': tx_type, 'amount': amount,
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

# --- 4. Update publish_event to use a logger ---
def publish_event(sns_client, event_type, event_details, reason=None):
    log_context = {
        "action": "publish_event",
        "event_type": event_type,
        "wallet_id": event_details.get('wallet_id'),
        "related_id": event_details.get('transaction_id') or event_details.get('loan_id')
    }
    
    message_body = {
        "event_type": event_type,
        "details": event_details
    }
    if reason:
        message_body['reason'] = reason
    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=json.dumps(message_body, cls=DecimalEncoder),
            Subject=f"Wallet Update: {event_type}",
            MessageAttributes={
                'event_type': {
                    'DataType': 'String',
                    'StringValue': event_type
                }
            }
        )
        logger.info(json.dumps({**log_context, "status": "info", "message": "Published SNS event."}))
    except Exception as pub_e:
         logger.error(json.dumps({**log_context, "status": "error", "error_message": str(pub_e)}))
         raise pub_e # Re-raise to fail the Lambda and force SNS retry
# ---

# --- Main Handler ---
def process_payment_request(event, context):
    """
    Subscribes to 'PAYMENT_REQUESTED' AND 'LOAN_REPAYMENT_REQUESTED'.
    Debits wallet, logs transaction, and publishes result.
    """
    
    # --- 5. Initialize boto3 clients inside the handler ---
    dynamodb_resource = boto3.resource('dynamodb')
    sns_client = boto3.client('sns')
    wallet_table = dynamodb_resource.Table(WALLET_TABLE_NAME) if WALLET_TABLE_NAME else None
    log_table = dynamodb_resource.Table(LOG_TABLE_NAME) if LOG_TABLE_NAME else None
    # ---
    
    if not wallet_table or not log_table or not SNS_TOPIC_ARN:
        log_message = {
            "status": "error",
            "action": "process_payment_request",
            "message": "FATAL: Environment variables not set."
        }
        logger.error(json.dumps(log_message))
        raise Exception("Server configuration error.")

    logger.info(f"Received event: {json.dumps(event)}")
    
    for record in event['Records']:
        message_id = record.get('Sns', {}).get('MessageId', 'Unknown')
        log_context = {"action": "process_payment_request", "sns_message_id": message_id}
        
        try:
            sns_message_str = record.get('Sns', {}).get('Message')
            if not sns_message_str:
                logger.warning(json.dumps({**log_context, "status": "warn", "message": "Skipping record: Missing SNS message body."}))
                continue

            sns_message = json.loads(sns_message_str)
            event_type = sns_message.get('event_type')
            log_context["event_type"] = event_type
            
            event_details = sns_message.get('details') or sns_message.get('transaction_details') or {}
            
            wallet_id = event_details.get('wallet_id')
            amount_str = event_details.get('amount', '0.00')
            log_context["wallet_id"] = wallet_id
            
            if event_type == 'PAYMENT_REQUESTED':
                log_type = 'PAYMENT_OUT'
                success_event = 'PAYMENT_SUCCESSFUL'
                fail_event = 'PAYMENT_FAILED'
                related_id = event_details.get('transaction_id')
                log_details = {"merchant": event_details.get('merchant_id')}
            elif event_type == 'LOAN_REPAYMENT_REQUESTED':
                log_type = 'LOAN_REPAYMENT'
                success_event = 'LOAN_REPAYMENT_SUCCESSFUL'
                fail_event = 'LOAN_REPAYMENT_FAILED'
                related_id = event_details.get('loan_id')
                log_details = {"loan_id": related_id}
            else:
                logger.warning(json.dumps({**log_context, "status": "warn", "message": "Skipping unhandled event type."}))
                continue 

            log_context["related_id"] = related_id

            if not wallet_id or not amount_str or not related_id:
                logger.error(json.dumps({**log_context, "status": "error", "message": "Invalid details in message."}))
                publish_event(sns_client, fail_event, event_details, "Invalid message format received.")
                continue
            
            amount = Decimal(amount_str)
            log_context["amount"] = str(amount)
            
            if amount <= 0:
                 logger.error(json.dumps({**log_context, "status": "error", "message": "Invalid amount."}))
                 publish_event(sns_client, fail_event, event_details, "Invalid amount.")
                 continue

            logger.info(json.dumps({**log_context, "status": "info", "message": "Processing payment/repayment."}))

            try:
                response = wallet_table.update_item(
                    Key={'wallet_id': wallet_id},
                    UpdateExpression="SET balance = balance - :amount",
                    ConditionExpression="balance >= :amount",
                    ExpressionAttributeValues={ ':amount': amount },
                    ReturnValues="UPDATED_NEW"
                )
                new_balance = response.get('Attributes', {}).get('balance')
                logger.info(json.dumps({**log_context, "status": "info", "new_balance": str(new_balance), "message": "Successfully debited wallet."}))

                log_transaction(
                    log_table=log_table,
                    wallet_id=wallet_id,
                    tx_type=log_type,
                    amount=amount,
                    new_balance=new_balance,
                    related_id=related_id,
                    details=log_details
                )
                
                publish_event(sns_client, success_event, event_details)

            except ClientError as e:
                error_code = e.response['Error']['Code']
                log_context["error_code"] = error_code
                
                if error_code == 'ConditionalCheckFailedException':
                    logger.warning(json.dumps({**log_context, "status": "warn", "message": "Insufficient funds."}))
                    publish_event(sns_client, fail_event, event_details, "Insufficient funds.")
                else:
                    logger.error(json.dumps({**log_context, "status": "error", "message": f"DynamoDB error: {str(e)}"}))
                    publish_event(sns_client, fail_event, event_details, f"Wallet update error: {error_code}")
                    raise e
            except Exception as debit_e:
                 logger.error(json.dumps({**log_context, "status": "error", "message": f"Unexpected debit error: {str(debit_e)}"}))
                 publish_event(sns_client, fail_event, event_details, f"Processing error: {str(debit_e)}")
                 raise debit_e

        except Exception as record_e:
             logger.error(json.dumps({**log_context, "status": "error", "message": f"FATAL error processing record: {str(record_e)}"}))
             raise record_e

    return {"statusCode": 200, "body": "Events processed."}