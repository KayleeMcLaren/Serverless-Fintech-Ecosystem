import json
import os
import boto3
import uuid
import time
from decimal import Decimal, InvalidOperation
from botocore.exceptions import ClientError

# --- Table Names & SNS Topic ---
WALLET_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
LOG_TABLE_NAME = os.environ.get('TRANSACTIONS_LOG_TABLE_NAME')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN') # Payment events topic

# --- REMOVE BOTO3 CLIENTS FROM GLOBAL SCOPE ---

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal): return str(o)
        return super(DecimalEncoder, self).default(o)

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
            'transaction_id': str(uuid.uuid4()), 'wallet_id': wallet_id,
            'timestamp': timestamp, 'type': tx_type, 'amount': amount,
            'balance_after': new_balance if new_balance is not None else Decimal('NaN'),
            'related_id': related_id if related_id else 'N/A',
            'details': details if details else {}
        }
        if isinstance(log_item['balance_after'], Decimal) and log_item['balance_after'].is_nan():
             log_item['balance_after'] = 'N/A'
        log_table.put_item(Item=log_item)
        print(f"Logged transaction: {log_item['transaction_id']}")
    except Exception as log_e:
        print(f"ERROR logging transaction: {log_e}")

# --- Event Publishing Helper ---
def publish_event(sns_client, event_type, event_details, reason=None): # Pass in sns_client
    message_body = {
        "event_type": event_type,
        "details": event_details
    }
    if reason:
        message_body['reason'] = reason
    try:
        sns_client.publish( # Use passed-in client
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
        print(f"Published {event_type} event")
    except Exception as pub_e:
         print(f"ERROR publishing {event_type} event: {pub_e}")
         raise pub_e

# --- Main Handler ---
def process_payment_request(event, context):
    """
    Subscribes to 'PAYMENT_REQUESTED' AND 'LOAN_REPAYMENT_REQUESTED'.
    Debits wallet, logs transaction, and publishes result.
    """
    
    # --- FIX: Initialize boto3 clients inside the handler ---
    dynamodb_resource = boto3.resource('dynamodb')
    sns_client = boto3.client('sns') # Use 'sns_client' to avoid name clash
    wallet_table = dynamodb_resource.Table(WALLET_TABLE_NAME) if WALLET_TABLE_NAME else None
    # --- END FIX ---

    print(f"Received event: {json.dumps(event)}")
    for record in event['Records']:
        message_id = record.get('Sns', {}).get('MessageId', 'Unknown')
        try:
            sns_message_str = record.get('Sns', {}).get('Message')
            if not sns_message_str:
                print(f"Skipping record {message_id}: Missing SNS message body.")
                continue

            sns_message = json.loads(sns_message_str)
            event_type = sns_message.get('event_type')
            
            event_details = sns_message.get('details') or sns_message.get('transaction_details') or {}
            
            wallet_id = event_details.get('wallet_id')
            amount_str = event_details.get('amount', '0.00')
            
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
                print(f"Skipping event type in message {message_id}: {event_type}")
                continue 

            if not wallet_id or not amount_str or not related_id:
                print(f"Invalid details in message {message_id}: {event_details}")
                publish_event(sns_client, fail_event, event_details, "Invalid message format received.")
                continue
            amount = Decimal(amount_str)
            if amount <= 0:
                 print(f"Invalid amount in message {message_id}: {amount}")
                 publish_event(sns_client, fail_event, event_details, "Invalid amount.")
                 continue

            print(f"Processing {event_type} for wallet {wallet_id}, amount {amount}")

            try:
                response = wallet_table.update_item(
                    Key={'wallet_id': wallet_id},
                    UpdateExpression="SET balance = balance - :amount",
                    ConditionExpression="balance >= :amount",
                    ExpressionAttributeValues={ ':amount': amount },
                    ReturnValues="UPDATED_NEW"
                )
                new_balance = response.get('Attributes', {}).get('balance')
                print(f"Successfully debited wallet {wallet_id}.")

                log_transaction(
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
                if error_code == 'ConditionalCheckFailedException':
                    print(f"Debit failed for wallet {wallet_id}: Insufficient funds.")
                    publish_event(sns_client, fail_event, event_details, "Insufficient funds.")
                else:
                    print(f"Debit failed: DynamoDB error: {e}")
                    publish_event(sns_client, fail_event, event_details, f"Wallet update error: {error_code}")
                    raise e
            except Exception as debit_e:
                 print(f"Debit failed: Unexpected error: {debit_e}")
                 publish_event(sns_client, fail_event, event_details, f"Processing error: {str(debit_e)}")
                 raise debit_e

        except Exception as record_e:
             print(f"ERROR processing individual record {message_id}: {record_e}.")
             raise record_e

    return {"statusCode": 200, "body": "Events processed."}