import json
import os
import boto3
import uuid
import time
from decimal import Decimal, InvalidOperation
from botocore.exceptions import ClientError
import logging

# Set up logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Environment Variables ---
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
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

def create_savings_goal(event, context):
    """
    API: POST /savings-goal
    Creates a new savings goal for a given wallet.
    """
    
    # --- Initialize boto3 inside the handler ---
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME) if TABLE_NAME else None
    
    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        logger.info("Handling OPTIONS preflight request for create_savings_goal")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }

    if not table:
        log_message = {
            "status": "error",
            "action": "create_savings_goal",
            "message": "FATAL: DYNAMODB_TABLE_NAME environment variable not set."
        }
        logger.error(json.dumps(log_message))
        return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'POST':
        log_context = {"action": "create_savings_goal"}
        try:
            body = json.loads(event.get('body', '{}'))
            wallet_id = body.get('wallet_id')
            goal_name = body.get('goal_name')
            target_amount_str = body.get('target_amount')

            log_context["wallet_id"] = wallet_id

            if not wallet_id or not goal_name or not target_amount_str:
                raise ValueError("wallet_id, goal_name, and target_amount are required.")
            
            target_amount = Decimal(target_amount_str)
            if target_amount <= 0:
                raise ValueError("Target amount must be positive.")

            goal_id = str(uuid.uuid4())
            timestamp = int(time.time())
            
            log_context.update({
                "goal_id": goal_id,
                "goal_name": goal_name,
                "target_amount": str(target_amount)
            })
            logger.info(json.dumps({**log_context, "status": "info", "message": "Creating new savings goal."}))

            item = {
                'goal_id': goal_id,
                'wallet_id': wallet_id,
                'goal_name': goal_name,
                'target_amount': target_amount,
                'current_amount': Decimal('0.00'), # Start at 0
                'created_at': timestamp,
            }
            
            table.put_item(Item=item)
            
            logger.info(json.dumps({**log_context, "status": "info", "message": "Savings goal created successfully."}))

            return {
                "statusCode": 201, # Created
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": "Savings goal created!", "goal": item}, cls=DecimalEncoder)
            }
            
        except (ValueError, TypeError, InvalidOperation) as ve:
             logger.error(json.dumps({**log_context, "status": "error", "error_message": str(ve)}))
             return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Invalid input: {str(ve)}"}) }
        except ClientError as ce:
             logger.error(json.dumps({**log_context, "status": "error", "error_code": ce.response['Error']['Code'], "error_message": str(ce)}))
             return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Database error.", "error": str(ce)}) }
        except Exception as e:
            logger.error(json.dumps({**log_context, "status": "error", "error_message": str(e)}))
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "An unexpected error occurred.", "error": str(e)}) }
    else:
         return { "statusCode": 405, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }