import json
import os
import uuid
import boto3
import time
from decimal import Decimal

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert a DynamoDB item to JSON."""
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def create_savings_goal(event, context):
    """Creates a new savings goal for a specific wallet."""
    try:
        body = json.loads(event.get('body', '{}'))
        
        wallet_id = body.get('wallet_id')
        goal_name = body.get('goal_name')
        target_amount = Decimal(body.get('target_amount'))

        if not all([wallet_id, goal_name, target_amount]) or target_amount <= 0:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Valid wallet_id, goal_name, and positive target_amount are required."})
            }

        goal_id = str(uuid.uuid4())
        item = {
            'goal_id': goal_id,
            'wallet_id': wallet_id,
            'goal_name': goal_name,
            'target_amount': target_amount,
            'current_amount': Decimal('0.00'), # All new goals start at 0
            'created_at': int(time.time())
        }

        table.put_item(Item=item)

        response_body = {
            "message": "Savings goal created successfully!",
            "goal": item
        }

        return {
            "statusCode": 201,
            "body": json.dumps(response_body, cls=DecimalEncoder)
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to create savings goal.", "error": str(e)})
        }