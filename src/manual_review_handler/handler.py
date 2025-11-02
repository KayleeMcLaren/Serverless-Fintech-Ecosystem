import json
import os
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError
import logging

# Set up logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Environment Variables ---
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME')
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

def manual_review(event, context):
    """
    API: POST /onboarding/manual-review
    Handles the manual approval/rejection from an admin.
    Expects 'user_id' and 'decision' ('APPROVED'/'REJECTED') in the body.
    """
    
    # --- Initialize boto3 clients ---
    dynamodb = boto3.resource('dynamodb')
    sfn_client = boto3.client('stepfunctions')
    users_table = dynamodb.Table(USERS_TABLE_NAME) if USERS_TABLE_NAME else None
    
    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        logger.info("Handling OPTIONS preflight request for manual_review")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }
    
    if not users_table:
        log_message = {
            "status": "error",
            "action": "manual_review",
            "message": "FATAL: USERS_TABLE_NAME environment variable not set."
        }
        logger.error(json.dumps(log_message))
        return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'POST':
        log_context = {"action": "manual_review"}
        try:
            body = json.loads(event.get('body', '{}'))
            user_id = body.get('user_id')
            decision = body.get('decision')

            log_context.update({"user_id": user_id, "decision": decision})

            if not user_id or decision not in ['APPROVED', 'REJECTED']:
                raise ValueError("user_id and decision ('APPROVED'/'REJECTED') are required.")

            logger.info(json.dumps({**log_context, "status": "info", "message": "Processing manual review."}))

            # 1. Get the user record to find their TaskToken
            response = users_table.get_item(Key={'user_id': user_id})
            user_item = response.get('Item')

            if not user_item:
                logger.warn(json.dumps({**log_context, "status": "warn", "message": "User not found."}))
                return { "statusCode": 404, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "User not found."}) }
            
            task_token = user_item.get('sfn_task_token')
            if not task_token:
                 logger.warn(json.dumps({**log_context, "status": "warn", "message": "User is not awaiting manual review or token is missing."}))
                 return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "User is not awaiting manual review or token is missing."}) }

            # 2. Update user status in DynamoDB
            new_status = "PENDING_CREDIT_CHECK" if decision == "APPROVED" else "REJECTED_MANUAL"
            
            users_table.update_item(
                Key={'user_id': user_id},
                # Clear the task token so this can't be called twice
                UpdateExpression="SET onboarding_status = :status REMOVE sfn_task_token",
                ExpressionAttributeValues={':status': new_status}
            )
            
            # 3. Send success/failure signal back to the Step Function
            if decision == 'APPROVED':
                logger.info(json.dumps({**log_context, "status": "info", "message": "Sending TaskSuccess to Step Function."}))
                sfn_client.send_task_success(
                    taskToken=task_token,
                    output=json.dumps({"status": "APPROVED", "message": "Manual review approved."})
                )
            else: # 'REJECTED'
                logger.info(json.dumps({**log_context, "status": "info", "message": "Sending TaskFailure to Step Function."}))
                sfn_client.send_task_failure(
                    taskToken=task_token,
                    error="ManualReviewRejected",
                    cause="The user was rejected during manual review by an admin."
                )
                
            logger.info(json.dumps({**log_context, "status": "info", "message": "Successfully processed manual review."}))

            return {
                "statusCode": 200,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": f"Successfully processed manual {decision} for user {user_id}."})
            }

        except (ValueError, TypeError) as ve:
             logger.error(json.dumps({**log_context, "status": "error", "error_message": str(ve)}))
             return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Invalid input: {str(ve)}"}) }
        except ClientError as ce:
             log_context["error_code"] = ce.response['Error']['Code']
             if ce.response['Error']['Code'] == 'TaskTimedOut':
                 logger.warn(json.dumps({**log_context, "status": "warn", "message": "Task token has timed out."}))
                 return { "statusCode": 410, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "This task has timed out."}) }
             if ce.response['Error']['Code'] == 'TaskDoesNotExist':
                 logger.warn(json.dumps({**log_context, "status": "warn", "message": "Task token is invalid or already used."}))
                 return { "statusCode": 404, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "This task token is invalid or has already been used."}) }
             
             logger.error(json.dumps({**log_context, "status": "error", "error_message": str(ce)}))
             return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "AWS service error.", "error": str(ce)}) }
        except Exception as e:
            logger.error(json.dumps({**log_context, "status": "error", "error_message": str(e)}))
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "An unexpected error occurred.", "error": str(e)}) }
    else:
         return { "statusCode": 405, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }