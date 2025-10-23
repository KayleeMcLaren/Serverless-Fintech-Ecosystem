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

# --- AWS Resources ---
dynamodb_resource = boto3.resource('dynamodb')
sns = boto3.client('sns')
wallet_table = dynamodb_resource.Table(WALLET_TABLE_NAME)
log_table = dynamodb_resource.Table(LOG_TABLE_NAME) if LOG_TABLE_NAME else None

class DecimalEncoder(json.JSONEncoder):
    # ... (keep as is)
    def default(self, o):
        if isinstance(o, Decimal): return str(o)
        return super(DecimalEncoder, self).default(o)

# --- Transaction Logging Helper ---
def log_transaction(wallet_id, tx_type, amount, new_balance=None, related_id=None, details=None):
    # ... (keep as is)
    if not log_table:
        print("Log table name not configured, skipping log.")
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
        print(f"Logged transaction: {log_item['transaction_id']}")
    except Exception as log_e:
        print(f"ERROR logging transaction: {log_e}")

# --- Event Publishing Helper ---
def publish_event(event_type, event_details, reason=None): # Renamed var
    message_body = {
        "event_type": event_type,
        "details": event_details # Use a generic 'details' key
    }
    if reason:
        message_body['reason'] = reason
    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=json.dumps(message_body, cls=DecimalEncoder),
            Subject=f"Wallet Update: {event_type}",
            MessageAttributes={
                'event_type': {
                    'DataType': 'String',
                    'StringValue': event_type # Critical for filtering
                }
            }
        )
        print(f"Published {event_type} event")
    except Exception as pub_e:
         print(f"ERROR publishing {event_type} event: {pub_e}")
         raise pub_e # Re-raise to fail the Lambda and force SNS retry

# --- Main Handler ---
def process_payment_request(event, context):
    """
    Subscribes to 'PAYMENT_REQUESTED' AND 'LOAN_REPAYMENT_REQUESTED'.
    Debits wallet, logs transaction, and publishes result.
    """
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
            
            # Use 'details' key which holds the original payload
            event_details = sns_message.get('details', {}) 
            
            wallet_id = event_details.get('wallet_id')
            amount_str = event_details.get('amount', '0.00')
            
            # Determine logging and response types based on incoming event
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
                continue # Not an event we handle

            # --- Validation ---
            if not wallet_id or not amount_str or not related_id:
                print(f"Invalid details in message {message_id}: {event_details}")
                publish_event(fail_event, event_details, "Invalid message format received.")
                continue
            amount = Decimal(amount_str)
            if amount <= 0:
                 print(f"Invalid amount in message {message_id}: {amount}")
                 publish_event(fail_event, event_details, "Invalid amount.")
                 continue

            print(f"Processing {event_type} for wallet {wallet_id}, amount {amount}")

            # --- 1. Attempt to debit the wallet ---
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

                # --- 2. Log Transaction ---
                log_transaction(
                    wallet_id=wallet_id,
                    tx_type=log_type,
                    amount=amount,
                    new_balance=new_balance,
                    related_id=related_id,
                    details=log_details
                )

                # --- 3. Publish SUCCESS event ---
                publish_event(success_event, event_details)

            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ConditionalCheckFailedException':
                    print(f"Debit failed for wallet {wallet_id}: Insufficient funds.")
                    publish_event(fail_event, event_details, "Insufficient funds.")
                else:
                    print(f"Debit failed: DynamoDB error: {e}")
                    publish_event(fail_event, event_details, f"Wallet update error: {error_code}")
                    raise e # Force retry for non-conditional errors
            except Exception as debit_e:
                 print(f"Debit failed: Unexpected error: {debit_e}")
                 publish_event(fail_event, event_details, f"Processing error: {str(debit_e)}")
                 raise debit_e # Force retry

        except Exception as record_e:
             print(f"ERROR processing individual record {message_id}: {record_e}.")
             raise record_e # Raise exception to make SNS retry this batch

    return {"statusCode": 200, "body": "Events processed."}