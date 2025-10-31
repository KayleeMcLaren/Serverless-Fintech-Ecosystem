import json
import os
import boto3

def verify_id(event, context):
    """
    MOCK: Simulates an ID verification step.
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
    message = "ID Verification successful (Mock)."

    if "flag@" in email:
        decision = "FLAGGED"
        message = "ID ambiguous, flagging for manual review (Mock)."
    elif "reject@" in email:
        decision = "REJECTED"
        message = "ID Verification failed (Mock)."
    
    print(f"Simulation result for user {user_id}: {decision}")
    # --- END MOCK LOGIC ---

    # --- DynamoDB update has been REMOVED ---
    
    # Return the result to the Step Function
    return {
        "status": decision,
        "message": message
    }