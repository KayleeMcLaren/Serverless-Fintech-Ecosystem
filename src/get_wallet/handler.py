import json
import os
import boto3
from decimal import Decimal
from urllib.parse import unquote

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

def get_wallet(event, context):
    """Retrieves a wallet by its ID."""
    try:
        # URL-decode the wallet ID to handle any URL-encoded characters like %0A
        wallet_id = unquote(event['pathParameters']['wallet_id'])

        # Strip any unwanted characters like leading/trailing spaces or newlines
        wallet_id = wallet_id.strip()

        print(f"Decoded and cleaned Wallet ID: {wallet_id}")  # Log cleaned wallet_id for debugging

        response = table.get_item(Key={'wallet_id': wallet_id})
        item = response.get('Item')

        if not item:
            return {
                "statusCode": 404,
                "body": json.dumps({"message": "Wallet not found."})
            }

        return {
            "statusCode": 200,
            "body": json.dumps(item, cls=DecimalEncoder)
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to retrieve wallet.", "error": str(e)})
        }
