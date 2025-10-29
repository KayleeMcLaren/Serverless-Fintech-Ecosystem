import json
import os
import uuid
import boto3
import time
from decimal import Decimal
from botocore.exceptions import ClientError # Import ClientError

# --- CORS Configuration ---
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")
OPTIONS_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS", # Allow POST
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Credentials": True
}
POST_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Credentials": True
}
# --- End CORS Configuration ---

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
table = dynamodb.Table(TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def request_payment(event, context):
    """
    Creates a 'PENDING' transaction and publishes 'PAYMENT_REQUESTED'.
    Handles OPTIONS preflight.
    """
    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request for request_payment")
        return {
            "statusCode": 200,
            "headers": OPTIONS_CORS_HEADERS,
            "body": ""
        }
    # --- End CORS Preflight Check ---

    # --- POST Logic ---
    if http_method == 'POST':
        print("Handling POST request for request_payment")
        try:
            body = json.loads(event.get('body', '{}'))
            amount_str = body.get('amount')
            wallet_id = body.get('wallet_id')
            merchant_id = body.get('merchant_id')

            # Validate before converting
            if not all([amount_str, wallet_id, merchant_id]):
                 raise ValueError("wallet_id, merchant_id, and amount are required.")
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be positive.")

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
            print(f"Saved PENDING transaction: {transaction_id}")

            # 2. Publish the event with MessageAttributes for filtering
            sns_message = {
                "event_type": "PAYMENT_REQUESTED",
                "transaction_details": item
            }
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Message=json.dumps(sns_message, cls=DecimalEncoder),
                Subject=f"Payment Requested: {transaction_id}",
                MessageAttributes={
                    'event_type': {
                        'DataType': 'String',
                        'StringValue': 'PAYMENT_REQUESTED'
                    }
                }
            )
            print(f"Published PAYMENT_REQUESTED event for {transaction_id}")

            response_body = {
                "message": "Payment request received and is processing.",
                "transaction": item
            }

            return {
                "statusCode": 202, # Accepted
                "headers": POST_CORS_HEADERS,
                "body": json.dumps(response_body, cls=DecimalEncoder)
            }
        except (ValueError, TypeError) as ve:
            print(f"Input Error requesting payment: {ve}")
            return {
                "statusCode": 400,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": f"Invalid input: {ve}"})
            }
        except Exception as e:
            print(f"Error requesting payment: {e}")
            return {
                "statusCode": 500,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": "Failed to request payment.", "error": str(e)})
            }
    else:
        print(f"Unsupported method: {http_method}")
        return {
            "statusCode": 405,
            "headers": POST_CORS_HEADERS,
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }