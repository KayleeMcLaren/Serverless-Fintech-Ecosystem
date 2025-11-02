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

def credit_check(event, context):
    """
    MOCK: Simulates a 3rd-party credit check.
    This function is invoked by the Step Function.
    
    It returns a decision, it does not update DynamoDB.
    """
    
    # --- Initialize boto3 inside the handler ---
    # We only need this to check the env var, but it's good practice
    dynamodb = boto3.resource('dynamodb')
    users_table = dynamodb.Table(USERS_TABLE_NAME) if USERS_TABLE_NAME else None

    if not users_table:
        log_message = {
            "status": "error",
            "action": "credit_check_mock",
            "message": "FATAL: USERS_TABLE_NAME environment variable not set."
        }
        logger.error(json.dumps(log_message))
        raise Exception("Server configuration error: USERS_TABLE_NAME not set.")

    logger.info(f"Received event: {json.dumps(event)}")
    
    user_id = event.get('user_id')
    email = event.get('email')
    log_context = {"action": "credit_check_mock", "user_id": user_id, "email": email}

    if not user_id:
        logger.error(json.dumps({**log_context, "status": "error", "message": "user_id not found in event input."}))
        raise ValueError("user_id not found in event input.")

    # --- MOCK LOGIC ---
    decision = "APPROVED"
    message = "Credit check passed (Mock)."
    credit_score = 750

    if "lowscore@" in email:
        decision = "REJECTED"
        message = "Credit check failed: low score (Mock)."
        credit_score = 550
    
    logger.info(json.dumps({**log_context, "status": "info", "decision": decision, "credit_score": credit_score, "message": "Simulation complete."}))
    # --- END MOCK LOGIC ---

    try:
        # --- This function NO LONGER updates DynamoDB ---
        # The Step Function is now responsible for updating the status
        
        # Return the result to the Step Function
        return {
            "status": decision,
            "message": message,
            "credit_score": credit_score
        }
        
    except Exception as e:
        logger.error(json.dumps({**log_context, "status": "error", "error_message": str(e)}))
        raise e