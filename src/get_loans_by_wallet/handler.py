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

def get_loans_by_wallet(event, context):
    """Retrieves all loans for a specific wallet_id using the GSI."""
    try:
        wallet_id = unquote(event['pathParameters']['wallet_id']).strip()

        # Query the Global Secondary Index (GSI)
        response = table.query(
            IndexName='wallet_id-index',
            KeyConditionExpression='wallet_id = :wallet_id',
            ExpressionAttributeValues={
                ':wallet_id': wallet_id
            }
        )
        
        items = response.get('Items', [])

        return {
            "statusCode": 200,
            "body": json.dumps(items, cls=DecimalEncoder)
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to retrieve loans.", "error": str(e)})
        }