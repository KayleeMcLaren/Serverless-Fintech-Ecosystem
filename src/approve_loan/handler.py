import json
import os
import boto3
from urllib.parse import unquote
from botocore.exceptions import ClientError
from decimal import Decimal

# --- CORS Configuration ---
ALLOWED_ORIGIN = "*" # Use "*" for dev, replace with CloudFront URL for prod
OPTIONS_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS", # Allow POST
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Credentials": True
}
POST_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Credentials": True
}
# --- End CORS Configuration ---

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
table = dynamodb.Table(TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def approve_loan(event, context):
    """Updates loan status to 'APPROVED' and publishes to SNS. Handles OPTIONS."""

    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request for approve_loan")
        return {
            "statusCode": 200,
            "headers": OPTIONS_CORS_HEADERS,
            "body": ""
        }
    # --- End CORS Preflight Check ---

    # --- POST Logic ---
    if http_method == 'POST':
        print("Handling POST request for approve_loan")
        try:
            loan_id = unquote(event['pathParameters']['loan_id']).strip()
            print(f"Attempting to approve loan_id: {loan_id}")

            response = table.update_item(
                Key={'loan_id': loan_id},
                UpdateExpression="SET #status = :status",
                ConditionExpression="#status = :pending_status",
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'APPROVED',
                    ':pending_status': 'PENDING'
                },
                ReturnValues="ALL_NEW" # Get the full item to send to SNS
            )

            loan_item = response['Attributes']
            print(f"Loan {loan_id} updated to APPROVED.")

            # --- Publish to SNS ---
            sns_message = {
                "event_type": "LOAN_APPROVED",
                "loan_details": loan_item
            }

            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Message=json.dumps(sns_message, cls=DecimalEncoder),
                Subject=f"Loan Approved: {loan_id}"
                # No MessageAttributes needed here if subscriber doesn't filter
            )
            print(f"Published LOAN_APPROVED event for {loan_id}")

            return {
                "statusCode": 200,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": "Loan approved and event published.", "loan": loan_item}, cls=DecimalEncoder)
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            print(f"ClientError approving loan {loan_id}: {error_code}")
            if error_code == 'ConditionalCheckFailedException':
                return {
                    "statusCode": 409, # Conflict
                    "headers": POST_CORS_HEADERS,
                    "body": json.dumps({"message": "Loan is not in a PENDING state."})
                }
            else:
                 return {
                    "statusCode": 500,
                    "headers": POST_CORS_HEADERS,
                    "body": json.dumps({"message": "Database error during approval.", "error": str(e)})
                }
        except Exception as e:
            print(f"Error approving loan {loan_id}: {e}")
            return {
                "statusCode": 500,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": "Failed to approve loan.", "error": str(e)})
            }
    else:
        print(f"Unsupported method: {http_method}")
        return {
            "statusCode": 405,
            "headers": POST_CORS_HEADERS,
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }