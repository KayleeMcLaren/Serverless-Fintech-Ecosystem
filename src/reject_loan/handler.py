import json
import os
import boto3
from urllib.parse import unquote
from botocore.exceptions import ClientError

# --- CORS Configuration ---
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")
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
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def reject_loan(event, context):
    """Updates loan status to 'REJECTED'. Handles OPTIONS."""

    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request for reject_loan")
        return {
            "statusCode": 200,
            "headers": OPTIONS_CORS_HEADERS,
            "body": ""
        }
    # --- End CORS Preflight Check ---

    # --- POST Logic ---
    if http_method == 'POST':
        print("Handling POST request for reject_loan")
        try:
            loan_id = unquote(event['pathParameters']['loan_id']).strip()
            print(f"Attempting to reject loan_id: {loan_id}")

            response = table.update_item(
                Key={'loan_id': loan_id},
                UpdateExpression="SET #status = :status",
                ConditionExpression="#status = :pending_status",
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'REJECTED',
                    ':pending_status': 'PENDING'
                },
                ReturnValues="UPDATED_NEW"
            )
            print(f"Loan {loan_id} updated to REJECTED.")

            return {
                "statusCode": 200,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": "Loan rejected", "attributes": response['Attributes']})
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            print(f"ClientError rejecting loan {loan_id}: {error_code}")
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
                    "body": json.dumps({"message": "Database error during rejection.", "error": str(e)})
                }
        except Exception as e:
            print(f"Error rejecting loan {loan_id}: {e}")
            return {
                "statusCode": 500,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": "Failed to reject loan.", "error": str(e)})
            }
    else:
        print(f"Unsupported method: {http_method}")
        return {
            "statusCode": 405,
            "headers": POST_CORS_HEADERS,
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }