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

def verify_id(event, context):
    """
    MOCK: Simulates an ID verification step (like AWS Rekognition).
    This function is invoked by the Step Function.
    
    It updates the user's status and returns the result.
    """
    
    # --- Initialize boto3 inside the handler ---
    dynamodb = boto3.resource('dynamodb')
    users_table = dynamodb.Table(USERS_TABLE_NAME) if USERS_TABLE_NAME else None

    if not users_table:
        log_message = {
            "status": "error",
            "action": "verify_id_mock",
            "message": "FATAL: USERS_TABLE_NAME environment variable not set."
        }
        logger.error(json.dumps(log_message))
        raise Exception("Server configuration error: USERS_TABLE_NAME not set.")

    logger.info(f"Received event: {json.dumps(event)}")
    
    user_id = event.get('user_id')
    email = event.get('email')
    log_context = {"action": "verify_id_mock", "user_id": user_id, "email": email}

    if not user_id:
        logger.error(json.dumps({**log_context, "status": "error", "message": "user_id not found in event input."}))
        raise ValueError("user_id not found in event input.")

    # --- MOCK LOGIC ---
    decision = "APPROVED"
    message = "ID Verification successful (Mock)."

    if "flag@" in email:
        decision = "FLAGGED"
        message = "ID ambiguous, flagging for manual review (Mock)."
    elif "reject@" in email:
        decision = "REJECTED"
        message = "ID Verification failed (Mock)."
    
    logger.info(json.dumps({**log_context, "status": "info", "decision": decision, "message": "Simulation complete."}))
    # --- END MOCK LOGIC ---

    try:
        # --- THIS FUNCTION NO LONGER UPDATES DYNAMODB ---
        # The Step Function is now responsible for updating the status
        # based on the 'decision' we return.
        
        # Return the result to the Step Function
        return {
            "status": decision,
            "message": message
        }
        
    except Exception as e:
        logger.error(json.dumps({**log_context, "status": "error", "error_message": str(e)}))
        raise e