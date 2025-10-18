import json
import os
import boto3
from urllib.parse import unquote
from botocore.exceptions import ClientError

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def reject_loan(event, context):
    """Updates a loan's status to 'REJECTED'."""
    try:
        loan_id = unquote(event['pathParameters']['loan_id']).strip()

        # Update the item and set status to REJECTED
        # Use ConditionExpression to ensure the loan is still PENDING
        response = table.update_item(
            Key={'loan_id': loan_id},
            UpdateExpression="SET #status = :status",
            ConditionExpression="#status = :pending_status",
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': 'REJECTED',
                ':pending_status': 'PENDING'
            },
            ReturnValues="UPDATED_NEW"
        )
        
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Loan rejected", "attributes": response['Attributes']})
        }
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {
                "statusCode": 409, # Conflict
                "body": json.dumps({"message": "Loan is not in a PENDING state."})
            }
        else:
            raise
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to reject loan.", "error": str(e)})
        }