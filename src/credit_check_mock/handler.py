import json
import os
import boto3
from decimal import Decimal

def credit_check(event, context):
    """
    MOCK: Simulates a 3rd-party credit check.
    This function is invoked by the Step Function.
    It ONLY returns a decision, it does not update DynamoDB.
    """
    print(f"Received event: {json.dumps(event)}")
    
    user_id = event.get('user_id')
    email = event.get('email')

    if not user_id:
        raise ValueError("user_id not found in event input.")

    # --- MOCK LOGIC ---
    decision = "APPROVED"
    message = "Credit check passed (Mock)."
    credit_score = 750

    if "lowscore@" in email:
        decision = "REJECTED"
        message = "Credit check failed: low score (Mock)."
        credit_score = 550
    
    print(f"Simulation result for user {user_id}: {decision}")
    # --- END MOCK LOGIC ---

    # --- DynamoDB update has been REMOVED ---
    
    # Return the result to the Step Function
    return {
        "status": decision,
        "message": message,
        "credit_score": credit_score
    }