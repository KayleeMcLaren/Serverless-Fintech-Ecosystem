import json
import os
import uuid
import boto3
import time
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

def apply_for_loan(event, context):
    """Creates a new loan application with a 'PENDING' status."""
    try:
        body = json.loads(event.get('body', '{}'))
        amount = Decimal(body.get('amount'))
        wallet_id = body.get('wallet_id')

        if not amount or amount <= 0:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Valid positive amount is required."})
            }
        
        if not wallet_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "wallet_id is required."})
            }

        loan_id = str(uuid.uuid4())
        item = {
            'loan_id': loan_id,
            'wallet_id': wallet_id,
            'amount': amount,
            'status': 'PENDING', # New loans are pending approval
            'created_at': int(time.time())
        }

        table.put_item(Item=item)

        response_body = {
            "message": "Loan application received successfully!",
            "loan": item
        }

        return {
            "statusCode": 201,
            "body": json.dumps(response_body, cls=DecimalEncoder)
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to apply for loan.", "error": str(e)})
        }