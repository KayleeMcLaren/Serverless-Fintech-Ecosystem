import json
import os
import boto3
import uuid
import time
from decimal import Decimal
from botocore.exceptions import ClientError
import logging

# Set up logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Environment Variables ---
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME')
STEP_FUNCTION_ARN = os.environ.get('STEP_FUNCTION_ARN')
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")

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
    API: POST /onboarding/start
    Starts the user onboarding Step Function.
    """
    
    # --- Initialize boto3 clients ---
    dynamodb = boto3.resource('dynamodb')
    sfn_client = boto3.client('stepfunctions')
    users_table = dynamodb.Table(USERS_TABLE_NAME) if USERS_TABLE_NAME else None
    
    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        logger.info("Handling OPTIONS preflight request for start_onboarding")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }
    
    if not users_table or not STEP_FUNCTION_ARN:
        log_message = {
            "status": "error",
            "action": "start_onboarding",
            "message": "FATAL: Environment variables not set."
        }
        logger.error(json.dumps(log_message))
        return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'POST':
        log_context = {"action": "start_onboarding"}
        try:
            body = json.loads(event.get('body', '{}'))
            email = body.get('email')
            if not email:
                raise ValueError("Email is required.")

            log_context["email"] = email
            
            # Note: We removed the "email already exists" check for demo purposes

            # 2. Create a new user ID
            user_id = str(uuid.uuid4())
            sfn_execution_name = f"{user_id}-{int(time.time())}"
            
            sfn_input = {
                'user_id': user_id,
                'email': email
            }
            
            log_context["user_id"] = user_id

            # 3. Start the Step Function execution
            logger.info(json.dumps({**log_context, "status": "info", "message": "Starting Step Function execution."}))
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
            
            logger.info(json.dumps({**log_context, "status": "info", "sfn_arn": sfn_response['executionArn'], "message": "Onboarding process started."}))

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
             logger.error(json.dumps({**log_context, "status": "error", "error_message": str(ve)}))
             return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Invalid input: {str(ve)}"}) }
        except ClientError as ce:
             logger.error(json.dumps({**log_context, "status": "error", "error_code": ce.response['Error']['Code'], "error_message": str(ce)}))
             return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "AWS service error.", "error": str(ce)}) }
        except Exception as e:
            logger.error(json.dumps({**log_context, "status": "error", "error_message": str(e)}))
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "An unexpected error occurred.", "error": str(e)}) }
    else:
         return { "statusCode": 405, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }