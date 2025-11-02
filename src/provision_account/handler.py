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
CREATE_WALLET_LAMBDA_ARN = os.environ.get('CREATE_WALLET_LAMBDA_ARN') # The ARN of the wallet Lambda

def provision_account(event, context):
    """
    Final step in the Step Function.
    1. Invokes the create_wallet Lambda.
    2. Updates the user's status to 'APPROVED' with their new wallet_id.
    """
    
    # --- Initialize boto3 clients ---
    dynamodb = boto3.resource('dynamodb')
    lambda_client = boto3.client('lambda')
    users_table = dynamodb.Table(USERS_TABLE_NAME) if USERS_TABLE_NAME else None

    if not users_table or not CREATE_WALLET_LAMBDA_ARN:
        log_message = {
            "status": "error",
            "action": "provision_account",
            "message": "FATAL: Environment variables not set (USERS_TABLE_NAME or CREATE_WALLET_LAMBDA_ARN)."
        }
        logger.error(json.dumps(log_message))
        raise Exception("Server configuration error.")

    logger.info(f"Received event: {json.dumps(event)}")
    
    user_id = event.get('user_id')
    log_context = {"action": "provision_account", "user_id": user_id}

    if not user_id:
        logger.error(json.dumps({**log_context, "status": "error", "message": "user_id not found in event input."}))
        raise ValueError("user_id not found in event input.")

    try:
        # --- 1. Invoke the create_wallet Lambda ---
        logger.info(json.dumps({**log_context, "status": "info", "message": "Invoking create_wallet Lambda."}))
        
        # We pass an empty event because the create_wallet handler
        # doesn't need any info, it just creates a wallet and returns the ID.
        # We mock a minimal 'httpMethod' to bypass its API Gateway checks.
        invoke_payload = json.dumps({"httpMethod": "POST", "body": "{}"}) 
        
        invoke_response = lambda_client.invoke(
            FunctionName=CREATE_WALLET_LAMBDA_ARN,
            InvocationType='RequestResponse', # We need the response
            Payload=invoke_payload
        )
        
        response_payload_str = invoke_response['Payload'].read().decode('utf-8')
        
        # Check for Lambda invocation error
        if invoke_response.get('FunctionError'):
             log_message = {
                 **log_context,
                 "status": "error",
                 "message": "create_wallet Lambda invocation failed.",
                 "lambda_error": response_payload_str
             }
             logger.error(json.dumps(log_message))
             raise Exception(f"Wallet creation failed: {response_payload_str}")

        response_payload = json.loads(response_payload_str)

        # Check the statusCode from the Lambda's *return*
        if response_payload.get('statusCode') != 201:
            log_message = {
                 **log_context,
                 "status": "error",
                 "message": "create_wallet Lambda returned non-201 status.",
                 "lambda_response": response_payload.get('body')
             }
            logger.error(json.dumps(log_message))
            raise Exception(f"Wallet creation returned error: {response_payload.get('body')}")

        # --- 2. Get the new wallet_id ---
        wallet_body = json.loads(response_payload.get('body', '{}'))
        new_wallet_id = wallet_body.get('wallet', {}).get('wallet_id')
        
        if not new_wallet_id:
            log_message = {
                 **log_context,
                 "status": "error",
                 "message": "Could not parse wallet_id from create_wallet response.",
                 "lambda_response_body": wallet_body
             }
            logger.error(json.dumps(log_message))
            raise Exception("Failed to parse wallet_id from create_wallet response.")
            
        log_context["wallet_id"] = new_wallet_id
        logger.info(json.dumps({**log_context, "status": "info", "message": "Successfully created wallet."}))

        # --- 3. Update the user's status to APPROVED ---
        users_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression="SET onboarding_status = :status, wallet_id = :wallet_id",
            ExpressionAttributeValues={
                ':status': 'APPROVED',
                ':wallet_id': new_wallet_id
            }
        )
        
        logger.info(json.dumps({**log_context, "status": "info", "message": "User status set to APPROVED."}))
        
        # Return the final, complete user object to the Step Function
        return {
            "status": "APPROVED",
            "message": "User account provisioned and wallet created.",
            "user_id": user_id,
            "wallet_id": new_wallet_id
        }
        
    except ClientError as ce:
         logger.error(json.dumps({**log_context, "status": "error", "error_code": ce.response['Error']['Code'], "error_message": str(ce)}))
         raise ce
    except Exception as e:
        logger.error(json.dumps({**log_context, "status": "error", "error_message": str(e)}))
        raise e