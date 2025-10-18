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

def credit_wallet(event, context):
    """Adds a specified amount to a wallet's balance."""
    try:
        # Get wallet_id from the URL path
        wallet_id = unquote(event['pathParameters']['wallet_id']).strip()
        
        # Get amount from the request body
        body = json.loads(event.get('body', '{}'))
        amount = Decimal(body.get('amount', '0.00'))

        if amount <= 0:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Amount must be positive."})
            }

        # Use update_item to atomically add the amount to the balance
        # 'ReturnValues="UPDATED_NEW"' tells DynamoDB to return the new values
        response = table.update_item(
            Key={'wallet_id': wallet_id},
            UpdateExpression="SET balance = balance + :amount",
            ExpressionAttributeValues={
                ':amount': amount
            },
            ReturnValues="UPDATED_NEW"
        )
        
        return {
            "statusCode": 200,
            "body": json.dumps(response['Attributes'], cls=DecimalEncoder)
        }
        
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to credit wallet.", "error": str(e)})
        }