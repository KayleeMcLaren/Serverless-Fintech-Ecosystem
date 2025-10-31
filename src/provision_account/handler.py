import json
import os
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError

# --- Environment Variables ---
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME')
CREATE_WALLET_LAMBDA_ARN = os.environ.get('CREATE_WALLET_LAMBDA_ARN') # The ARN of the wallet Lambda

# --- AWS Resources ---
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')
users_table = dynamodb.Table(USERS_TABLE_NAME) if USERS_TABLE_NAME else None

def provision_account(event, context):
    """
    Final step in the Step Function.
    1. Invokes the create_wallet Lambda.
    2. Updates the user's status to 'APPROVED' with their new wallet_id.
    """
    
    if not users_table or not CREATE_WALLET_LAMBDA_ARN:
        print("FATAL: Environment variables not set (USERS_TABLE_NAME or CREATE_WALLET_LAMBDA_ARN).")
        raise Exception("Server configuration error.")

    print(f"Received event: {json.dumps(event)}")
    
    user_id = event.get('user_id')
    email = event.get('email')

    if not user_id:
        raise ValueError("user_id not found in event input.")

    try:
        # --- 1. Invoke the create_wallet Lambda ---
        # We invoke it directly, passing an empty payload
        print(f"Invoking create_wallet Lambda for user {user_id}")
        invoke_response = lambda_client.invoke(
            FunctionName=CREATE_WALLET_LAMBDA_ARN,
            InvocationType='RequestResponse', # We need the response
            Payload=json.dumps({"httpMethod": "POST", "body": "{}"}) # Mock an API Gateway event
        )
        
        response_payload_str = invoke_response['Payload'].read().decode('utf-8')
        response_payload = json.loads(response_payload_str)
        
        # Check if the Lambda invocation itself failed
        if invoke_response.get('FunctionError'):
             print(f"create_wallet Lambda failed: {response_payload_str}")
             raise Exception(f"Wallet creation failed: {response_payload.get('errorMessage', 'Unknown error')}")

        # Check the statusCode from the Lambda's *return*
        if response_payload.get('statusCode') != 201:
            print(f"create_wallet Lambda returned non-201 status: {response_payload.get('body')}")
            raise Exception(f"Wallet creation returned error: {response_payload.get('body')}")

        # --- 2. Get the new wallet_id ---
        wallet_body = json.loads(response_payload.get('body', '{}'))
        new_wallet_id = wallet_body.get('wallet', {}).get('wallet_id')
        
        if not new_wallet_id:
            print(f"Could not parse wallet_id from response: {wallet_body}")
            raise Exception("Failed to parse wallet_id from create_wallet response.")
            
        print(f"Successfully created wallet {new_wallet_id} for user {user_id}")

        # --- 3. Update the user's status to APPROVED ---
        users_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression="SET onboarding_status = :status, wallet_id = :wallet_id",
            ExpressionAttributeValues={
                ':status': 'APPROVED',
                ':wallet_id': new_wallet_id
            }
        )
        
        # Return the final, complete user object to the Step Function
        return {
            "status": "APPROVED",
            "message": "User account provisioned and wallet created.",
            "user_id": user_id,
            "wallet_id": new_wallet_id
        }
        
    except ClientError as ce:
         print(f"DynamoDB or Lambda Error: {ce}")
         raise ce
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise e