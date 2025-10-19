import json
import os
import boto3
from urllib.parse import unquote

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def delete_savings_goal(event, context):
    """Deletes a specific savings goal by its goal_id."""
    try:
        goal_id = unquote(event['pathParameters']['goal_id']).strip()

        # Delete the item from the table
        table.delete_item(
            Key={'goal_id': goal_id}
        )
        
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Savings goal deleted successfully."})
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to delete savings goal.", "error": str(e)})
        }