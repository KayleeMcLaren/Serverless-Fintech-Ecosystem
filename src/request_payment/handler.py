import json
import os
import uuid
import boto3
import time
from decimal import Decimal

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
table = dynamodb.Table(TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert a DynamoDB item to JSON."""
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def request_payment(event, context):
    """
    Creates a new 'PENDING' transaction and publishes a
    'PAYMENT_REQUESTED' event to SNS.
    """
    try:
        body = json.loads(event.get('body', '{}'))
        amount = Decimal(body.get('amount'))
        wallet_id = body.get('wallet_id')
        merchant_id = body.get('merchant_id') # Who the payment is for

        if not all([amount, wallet_id, merchant_id]) or amount <= 0:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Valid wallet_id, merchant_id, and positive amount are required."})
            }

        transaction_id = str(uuid.uuid4())
        item = {
            'transaction_id': transaction_id,
            'wallet_id': wallet_id,
            'merchant_id': merchant_id,
            'amount': amount,
            'status': 'PENDING',
            'created_at': int(time.time())
        }

        # 1. Save the PENDING transaction
        table.put_item(Item=item)

        # 2. Publish the event
        sns_message = {
            "event_type": "PAYMENT_REQUESTED",
            "transaction_details": item
        }
        
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=json.dumps(sns_message, cls=DecimalEncoder),
            Subject=f"Payment Requested: {transaction_id}"
        )

        response_body = {
            "message": "Payment request received and is processing.",
            "transaction": item
        }

        return {
            "statusCode": 202, # 202 Accepted (processing initiated)
            "body": json.dumps(response_body, cls=DecimalEncoder)
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to request payment.", "error": str(e)})
        }