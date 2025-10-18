import json
import os
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError

WALLET_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN') # This will be the payment_events topic

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
wallet_table = dynamodb.Table(WALLET_TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert a DynamoDB item to JSON."""
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def process_payment_request(event, context):
    """
    Subscribes to 'PAYMENT_REQUESTED' events.
    Attempts to debit the wallet.
    Publishes 'PAYMENT_SUCCESSFUL' or 'PAYMENT_FAILED' event.
    """
    print(f"Received event: {json.dumps(event)}")
    
    for record in event['Records']:
        sns_message = json.loads(record['Sns']['Message'])
        
        if sns_message.get('event_type') == 'PAYMENT_REQUESTED':
            transaction_details = sns_message.get('transaction_details', {})
            wallet_id = transaction_details.get('wallet_id')
            amount = Decimal(transaction_details.get('amount', '0.00'))
            
            if not wallet_id or amount <= 0:
                print(f"Invalid payment details in message: {transaction_details}")
                continue

            try:
                # 1. Attempt to debit the wallet (atomic, conditional update)
                wallet_table.update_item(
                    Key={'wallet_id': wallet_id},
                    UpdateExpression="SET balance = balance - :amount",
                    ConditionExpression="balance >= :amount", # Prevent overdraft
                    ExpressionAttributeValues={ ':amount': amount }
                )
                
                # 2. If successful, publish SUCCESS event
                print(f"Successfully debited wallet {wallet_id} for {amount}.")
                publish_event("PAYMENT_SUCCESSFUL", transaction_details)

            except ClientError as e:
                # 3. If debit failed (insufficient funds), publish FAILED event
                if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                    print(f"Insufficient funds in wallet {wallet_id} for {amount}.")
                    publish_event("PAYMENT_FAILED", transaction_details, "Insufficient funds.")
                else:
                    # Other error (e.g., wallet not found), publish FAILED
                    print(f"Error debiting wallet: {e}")
                    publish_event("PAYMENT_FAILED", transaction_details, str(e))
            except Exception as e:
                print(f"Unhandled error: {e}")
                publish_event("PAYMENT_FAILED", transaction_details, str(e))

    return {"statusCode": 200, "body": "Events processed."}


def publish_event(event_type, transaction_details, reason=None):
    """Helper function to publish the result event back to SNS."""
    message_body = {
        "event_type": event_type,
        "transaction_details": transaction_details
    }
    if reason:
        message_body['reason'] = reason

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=json.dumps(message_body, cls=DecimalEncoder),
        Subject=f"Payment Update: {transaction_details.get('transaction_id')}",
        MessageAttributes={
            'event_type': {
                'DataType': 'String',
                'StringValue': event_type # This passes 'PAYMENT_SUCCESSFUL' or 'PAYMENT_FAILED'
            }
        }
    )