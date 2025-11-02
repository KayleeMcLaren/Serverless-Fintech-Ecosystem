import json
import os
import logging

# Set up logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def verify_id(event, context):
    """
    MOCK: Simulates an ID verification step (like AWS Rekognition).
    This function is invoked by the Step Function.
    
    It ONLY returns a decision.
    """
    
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

    # Return the result to the Step Function
    return {
        "status": decision,
        "message": message
    }