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
        
        # Get all required fields
        wallet_id = body.get('wallet_id')
        amount = Decimal(body.get('amount'))
        interest_rate = Decimal(body.get('interest_rate'))     # NEW
        minimum_payment = Decimal(body.get('minimum_payment')) # NEW

        if not all([wallet_id, amount, interest_rate, minimum_payment]) or amount <= 0:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "wallet_id, amount, interest_rate, and minimum_payment are required."})
            }
        
        loan_id = str(uuid.uuid4())
        item = {
            'loan_id': loan_id,
            'wallet_id': wallet_id,
            'amount': amount,
            'status': 'PENDING',
            'created_at': int(time.time()),
            'interest_rate': interest_rate,         
            'minimum_payment': minimum_payment,   
            'remaining_balance': amount           
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