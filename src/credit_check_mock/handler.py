import json
import os
import logging

# Set up logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def credit_check(event, context):
    """
    MOCK: Simulates a 3rd-party credit check.
    This function is invoked by the Step Function.
    
    It returns a decision.
    """
    
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

    # Return the result to the Step Function
    return {
        "status": decision,
        "message": message,
        "credit_score": credit_score
    }