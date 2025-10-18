import json
import os
import boto3
from urllib.parse import unquote
from botocore.exceptions import ClientError
from decimal import Decimal

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN') # New environment variable

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
table = dynamodb.Table(TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert a DynamoDB item to JSON."""
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def approve_loan(event, context):
    """Updates a loan's status to 'APPROVED' and publishes to SNS."""
    try:
        loan_id = unquote(event['pathParameters']['loan_id']).strip()

        # Update the item and set status to APPROVED
        # Use ConditionExpression to ensure it's PENDING
        # Use ReturnValues="ALL_NEW" to get the full loan item
        response = table.update_item(
            Key={'loan_id': loan_id},
            UpdateExpression="SET #status = :status",
            ConditionExpression="#status = :pending_status",
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': 'APPROVED',
                ':pending_status': 'PENDING'
            },
            ReturnValues="ALL_NEW" # Get the full item to send to SNS
        )
        
        loan_item = response['Attributes']

        # --- Publish to SNS ---
        # We send the full loan details so the subscriber
        # knows which wallet to credit and how much.
        sns_message = {
            "event_type": "LOAN_APPROVED",
            "loan_details": loan_item
        }
        
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=json.dumps(sns_message, cls=DecimalEncoder),
            Subject=f"Loan Approved: {loan_id}"
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Loan approved and event published.", "loan": loan_item}, cls=DecimalEncoder)
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
            "body": json.dumps({"message": "Failed to approve loan.", "error": str(e)})
        }