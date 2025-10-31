import json
import os
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError

# --- Environment Variables ---
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME')
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

def manual_review(event, context):
    """
    Handles the manual approval/rejection from an admin.
    Expects 'user_id' and 'decision' ('APPROVED'/'REJECTED') in the body.
    """
    
    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }
    
    if not users_table:
        print("FATAL: USERS_TABLE_NAME environment variable not set.")
        return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'POST':
        try:
            body = json.loads(event.get('body', '{}'))
            user_id = body.get('user_id')
            decision = body.get('decision')

            if not user_id or decision not in ['APPROVED', 'REJECTED']:
                raise ValueError("user_id and decision ('APPROVED'/'REJECTED') are required.")

            print(f"Processing manual review for user {user_id} with decision {decision}")

            # 1. Get the user record to find their TaskToken
            response = users_table.get_item(Key={'user_id': user_id})
            user_item = response.get('Item')

            if not user_item:
                return { "statusCode": 404, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "User not found."}) }
            
            task_token = user_item.get('sfn_task_token')
            if not task_token:
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
                sfn_client.send_task_success(
                    taskToken=task_token,
                    output=json.dumps({"status": "APPROVED", "message": "Manual review approved."})
                )
            else: # 'REJECTED'
                sfn_client.send_task_failure(
                    taskToken=task_token,
                    error="ManualReviewRejected",
                    cause="The user was rejected during manual review by an admin."
                )
                
            print(f"Successfully processed manual {decision} for user {user_id}")

            return {
                "statusCode": 200,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": f"Successfully processed manual {decision} for user {user_id}."})
            }

        except (ValueError, TypeError) as ve:
            return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Invalid input: {str(ve)}"}) }
        except ClientError as ce:
             if ce.response['Error']['Code'] == 'TaskTimedOut':
                 return { "statusCode": 410, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "This task has timed out."}) }
             if ce.response['Error']['Code'] == 'TaskDoesNotExist':
                 return { "statusCode": 404, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "This task token is invalid or has already been used."}) }
             return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "AWS service error.", "error": str(ce)}) }
        except Exception as e:
            print(f"Unexpected error: {e}")
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "An unexpected error occurred.", "error": str(e)}) }
    else:
         return { "statusCode": 405, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }