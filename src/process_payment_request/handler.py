import json
import os
import boto3
import uuid # For transaction ID
import time # For timestamp
from decimal import Decimal, InvalidOperation # Import InvalidOperation
from botocore.exceptions import ClientError

# --- Table Names & SNS Topic ---
WALLET_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
LOG_TABLE_NAME = os.environ.get('TRANSACTIONS_LOG_TABLE_NAME')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')

# --- AWS Resources ---
dynamodb_resource = boto3.resource('dynamodb')
sns = boto3.client('sns')
wallet_table = dynamodb_resource.Table(WALLET_TABLE_NAME)
log_table = dynamodb_resource.Table(LOG_TABLE_NAME) if LOG_TABLE_NAME else None

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

# --- Transaction Logging Helper ---
def log_transaction(wallet_id, tx_type, amount, new_balance=None, related_id=None, details=None):
    if not log_table:
        print("Log table name not configured, skipping log.")
        return
    try:
        timestamp = int(time.time()) # Ensure timestamp is integer
        log_item = {
            'transaction_id': str(uuid.uuid4()),
            'wallet_id': wallet_id,
            'timestamp': timestamp, # Save timestamp as Number (N)
            'type': tx_type,
            'amount': amount,
            'balance_after': new_balance if new_balance is not None else Decimal('NaN'),
            'related_id': related_id if related_id else 'N/A',
            'details': details if details else {}
        }
        # Handle NaN specifically for DynamoDB put_item
        if isinstance(log_item['balance_after'], Decimal) and log_item['balance_after'].is_nan():
             log_item['balance_after'] = 'N/A' # Store as string 'N/A'
        # Boto3 handles Decimal conversion for valid numbers

        log_table.put_item(Item=log_item)
        print(f"Logged transaction: {log_item['transaction_id']} for wallet {wallet_id}")
    except Exception as log_e:
        print(f"ERROR logging transaction: {log_e}")
# --- End Helper ---

# --- Event Publishing Helper ---
def publish_event(event_type, transaction_details, reason=None):
    message_body = {
        "event_type": event_type,
        "transaction_details": transaction_details
    }
    if reason:
        message_body['reason'] = reason
    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=json.dumps(message_body, cls=DecimalEncoder),
            Subject=f"Payment Update: {transaction_details.get('transaction_id')}",
            MessageAttributes={
                'event_type': {
                    'DataType': 'String',
                    'StringValue': event_type
                }
            }
        )
        print(f"Published {event_type} event for transaction {transaction_details.get('transaction_id')}")
    except Exception as pub_e:
         print(f"ERROR publishing {event_type} event: {pub_e}")
         # raise pub_e
# --- End Helper ---


def process_payment_request(event, context):
    """
    Subscribes to 'PAYMENT_REQUESTED', debits wallet, logs transaction,
    and publishes result event.
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

            if sns_message.get('event_type') == 'PAYMENT_REQUESTED':
                transaction_details = sns_message.get('transaction_details', {})
                wallet_id = transaction_details.get('wallet_id')
                amount_str = transaction_details.get('amount', '0.00')
                transaction_id = transaction_details.get('transaction_id')
                merchant_id = transaction_details.get('merchant_id')

                if not wallet_id or not amount_str or not transaction_id:
                    print(f"Invalid payment details in message {message_id}: {transaction_details}")
                    publish_event("PAYMENT_FAILED", transaction_details, "Invalid message format received.")
                    continue

                amount = Decimal(amount_str)
                if amount <= 0:
                     print(f"Invalid amount in message {message_id}: {amount}")
                     publish_event("PAYMENT_FAILED", transaction_details, "Invalid amount.")
                     continue

                print(f"Processing payment request for tx {transaction_id}, wallet {wallet_id}, amount {amount}")

                try:
                    # 1. Attempt to debit the wallet
                    response = wallet_table.update_item(
                        Key={'wallet_id': wallet_id},
                        UpdateExpression="SET balance = balance - :amount",
                        ConditionExpression="balance >= :amount",
                        ExpressionAttributeValues={ ':amount': amount },
                        ReturnValues="UPDATED_NEW" # Get updated balance
                    )
                    print(f"Successfully debited wallet {wallet_id} for tx {transaction_id}.")
                    new_balance = response.get('Attributes', {}).get('balance') # Get new balance

                    # --- 2. Log Transaction ---
                    log_transaction(
                        wallet_id=wallet_id,
                        tx_type="PAYMENT_OUT",
                        amount=amount,
                        new_balance=new_balance, # Pass the balance
                        related_id=transaction_id,
                        details={"merchant": merchant_id}
                    )
                    # --- End Log ---

                    # 3. Publish SUCCESS event
                    publish_event("PAYMENT_SUCCESSFUL", transaction_details)

                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code == 'ConditionalCheckFailedException':
                        print(f"Payment failed for tx {transaction_id}: Insufficient funds in wallet {wallet_id}.")
                        publish_event("PAYMENT_FAILED", transaction_details, "Insufficient funds.")
                    else:
                        print(f"Payment failed for tx {transaction_id}: DynamoDB error debiting wallet: {e}")
                        publish_event("PAYMENT_FAILED", transaction_details, f"Wallet update error: {error_code}")
                        # raise e # Consider retry for non-conditional errors
                except Exception as debit_e:
                     print(f"Payment failed for tx {transaction_id}: Unexpected error during debit: {debit_e}")
                     publish_event("PAYMENT_FAILED", transaction_details, f"Processing error: {str(debit_e)}")
                     # raise debit_e # Consider retry

            else:
                print(f"Skipping event type in message {message_id}: {sns_message.get('event_type')}")

        except (ValueError, InvalidOperation, TypeError) as val_err:
             print(f"ERROR processing record {message_id} due to invalid data: {val_err}")
        except Exception as record_e:
             print(f"ERROR processing individual record {message_id}: {record_e}.")
             # raise record_e # Consider retry for the whole batch

    return {"statusCode": 200, "body": "Events processed."}