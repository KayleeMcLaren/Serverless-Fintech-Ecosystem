import json

def auto_confirm_user(event, context):
    """
    This trigger is run by Cognito before user sign-up.
    It automatically confirms the user and verifies their email
    to skip the email verification code step for the demo.
    """
    
    print(f"Received pre-sign-up event: {json.dumps(event)}")
    
    # Tell Cognito to auto-confirm the user
    event['response']['autoConfirmUser'] = True
    
    # Tell Cognito to auto-verify the email attribute
    event['response']['autoVerifyEmail'] = True
    
    # Return the modified event to Cognito
    return event