import json
import os
import boto3
import uuid
import time
from decimal import Decimal
from botocore.exceptions import ClientError

# --- Environment Variables ---
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME')
STEP_FUNCTION_ARN = os.environ.get('STEP_FUNCTION_ARN')
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")

# --- AWS Resources ---
dynamodb = boto3.resource('dynamodb')
sfn_client = boto3.client('stepfunctions')
users_table = dynamodb.Table(USERS_TABLE_NAME) if USERS_TABLE_NAME else None

# --- CORS Headers ---
OPTIONS_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Credentials": True
}
POST_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Credentials": True
}

# --- DecimalEncoder ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def start_onboarding(event, context):
    """
    Starts the user onboarding Step Function.
    Expects an 'email' in the body.
    """
    
    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }
    
    if not users_table or not STEP_FUNCTION_ARN:
        print("FATAL: Environment variables not set.")
        return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'POST':
        try:
            body = json.loads(event.get('body', '{}'))
            email = body.get('email')
            if not email:
                raise ValueError("Email is required.")

            # 1. Check if user already exists (using the email GSI)
            response = users_table.query(
                IndexName='email-index',
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={':email': email}
            )
            if response.get('Items'):
                return {
                    "statusCode": 409, # Conflict
                    "headers": POST_CORS_HEADERS,
                    "body": json.dumps({"message": "A user with this email already exists."})
                }

            # 2. Create a new user ID
            user_id = str(uuid.uuid4())
            sfn_execution_name = f"{user_id}-{int(time.time())}" # Unique name for SFN
            
            sfn_input = {
                'user_id': user_id,
                'email': email
            }

            # 3. Start the Step Function execution
            sfn_response = sfn_client.start_execution(
                stateMachineArn=STEP_FUNCTION_ARN,
                name=sfn_execution_name,
                input=json.dumps(sfn_input)
            )
            
            # 4. Create the PENDING user record in DynamoDB
            user_item = {
                'user_id': user_id,
                'email': email,
                'onboarding_status': 'PENDING_ID_VERIFICATION',
                'created_at': int(time.time()),
                'step_function_arn': sfn_response['executionArn']
            }
            users_table.put_item(Item=user_item)

            print(f"Started onboarding for user {user_id} with email {email}")

            return {
                "statusCode": 202, # Accepted
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({
                    "message": "Onboarding process started.",
                    "user_id": user_id,
                    "status": "PENDING_ID_VERIFICATION"
                })
            }

        except (ValueError, TypeError) as ve:
            return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Invalid input: {str(ve)}"}) }
        except ClientError as ce:
             return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "AWS service error.", "error": str(ce)}) }
        except Exception as e:
            print(f"Unexpected error: {e}")
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "An unexpected error occurred.", "error": str(e)}) }
    else:
         return { "statusCode": 405, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }