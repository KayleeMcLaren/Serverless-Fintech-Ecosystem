import json
import logging

# --- 1. Set up logger ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# ---

def auto_confirm_user(event, context):
    """
    This trigger is run by Cognito before user sign-up.
    It automatically confirms the user and verifies their email
    to skip the email verification code step for the demo.
    """
    
    # --- 2. Log using structured JSON ---
    log_context = {
        "status": "info",
        "action": "auto_confirm_user",
        "user_email": event.get('userName'),
        "user_attributes": event.get('request', {}).get('userAttributes', {})
    }
    logger.info(json.dumps({**log_context, "message": "Auto-confirming user and verifying email for demo."}))
    # ---
    
    # Tell Cognito to auto-confirm the user
    event['response']['autoConfirmUser'] = True
    
    # Tell Cognito to auto-verify the email attribute
    event['response']['autoVerifyEmail'] = True
    
    # Return the modified event to Cognito
    return event