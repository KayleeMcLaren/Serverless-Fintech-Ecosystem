import json
import os
import boto3
from decimal import Decimal
from urllib.parse import unquote

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert a DynamoDB item to JSON."""
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def get_loan(event, context):
    """Retrieves a specific loan by its loan_id."""
    try:
        loan_id = unquote(event['pathParameters']['loan_id']).strip()

        response = table.get_item(Key={'loan_id': loan_id})
        item = response.get('Item')

        if not item:
            return {
                "statusCode": 404,
                "body": json.dumps({"message": "Loan not found."})
            }

        return {
            "statusCode": 200,
            "body": json.dumps(item, cls=DecimalEncoder)
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to retrieve loan.", "error": str(e)})
        }