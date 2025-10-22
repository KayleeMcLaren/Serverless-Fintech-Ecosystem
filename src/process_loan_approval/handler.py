import json
import os
import boto3
import uuid # For transaction ID
import time # For timestamp
from decimal import Decimal, InvalidOperation # Import InvalidOperation
from botocore.exceptions import ClientError

# --- Table Names ---
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME') # Wallet table
LOG_TABLE_NAME = os.environ.get('TRANSACTIONS_LOG_TABLE_NAME') # Log Table Name

# --- DynamoDB Resources ---
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)
log_table = dynamodb.Table(LOG_TABLE_NAME) if LOG_TABLE_NAME else None

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


def process_loan_approval(event, context):
    """Processes 'LOAN_APPROVED' events, credits wallet, logs transaction."""
    print(f"Received event: {json.dumps(event)}")

    processed_record_ids = []

    try:
        for record in event['Records']:
            message_id = record.get('Sns', {}).get('MessageId', 'Unknown')
            try:
                sns_message_str = record.get('Sns', {}).get('Message')
                if not sns_message_str:
                    print(f"Skipping record {message_id}: Missing SNS message body.")
                    continue

                sns_message = json.loads(sns_message_str)

                if sns_message.get('event_type') == 'LOAN_APPROVED':
                    loan_details = sns_message.get('loan_details', {})
                    wallet_id = loan_details.get('wallet_id')
                    # Use remaining_balance or amount as the value credited
                    amount_str = loan_details.get('remaining_balance') or loan_details.get('amount')
                    loan_id = loan_details.get('loan_id')

                    if not wallet_id or not amount_str or not loan_id:
                        print(f"Invalid loan details in message {message_id}: {loan_details}")
                        continue

                    amount = Decimal(amount_str)
                    if amount <= 0:
                        print(f"Loan amount is not positive in message {message_id}: {amount}")
                        continue

                    print(f"Processing loan approval for wallet {wallet_id}, loan {loan_id}, amount {amount}")

                    # Credit the wallet
                    response = table.update_item(
                        Key={'wallet_id': wallet_id},
                        UpdateExpression="SET balance = balance + :amount",
                        ExpressionAttributeValues={ ':amount': amount },
                        ConditionExpression="attribute_exists(wallet_id)",
                        ReturnValues="UPDATED_NEW" # Get updated balance
                    )
                    print(f"Successfully credited wallet {wallet_id} for loan {loan_id}.")
                    new_balance = response.get('Attributes', {}).get('balance') # Get new balance

                    # --- Log Transaction ---
                    log_transaction(
                        wallet_id=wallet_id,
                        tx_type="LOAN_IN",
                        amount=amount,
                        new_balance=new_balance, # Pass the balance
                        related_id=loan_id
                    )
                    # --- End Log ---

                    processed_record_ids.append(message_id)

                else:
                    print(f"Skipping event type in message {message_id}: {sns_message.get('event_type')}")
                    processed_record_ids.append(message_id)

            except (ValueError, InvalidOperation, TypeError) as val_err:
                 print(f"ERROR processing record {message_id} due to invalid data: {val_err}")
            except ClientError as ce:
                 print(f"ERROR: DynamoDB error processing record {message_id}: {ce}")
                 # raise ce # Uncomment to force retry of the whole batch
            except Exception as inner_e:
                 print(f"ERROR: Unexpected error processing record {message_id}: {inner_e}")
                 # raise inner_e # Uncomment to force retry of the whole batch

        return {
            "statusCode": 200,
            "body": json.dumps({"message": f"Processed {len(processed_record_ids)} records."})
        }

    except Exception as e:
        print(f"FATAL Error processing SNS event batch: {e}")
        raise e