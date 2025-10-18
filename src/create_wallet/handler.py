import json
import os
import uuid
import boto3
from decimal import Decimal

# Get the table name from an environment variable
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert a DynamoDB item to JSON."""
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def create_wallet(event, context):
    """Creates a new digital wallet with a zero balance."""
    try:
        wallet_id = str(uuid.uuid4())
        item = {
            'wallet_id': wallet_id,
            'balance': Decimal('0.00'),
            'currency': 'USD'
        }

        table.put_item(Item=item)

        response_body = {
            "message": "Wallet created successfully!",
            "wallet": item
        }

        return {
            "statusCode": 201,
            "body": json.dumps(response_body, cls=DecimalEncoder)
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to create wallet.", "error": str(e)})
        }