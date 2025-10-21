import json
import os
import boto3
from decimal import Decimal
from urllib.parse import unquote
from botocore.exceptions import ClientError

# --- CORS Configuration ---
ALLOWED_ORIGIN = "*" # Use "*" for now, replace with CloudFront URL for production
OPTIONS_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS", # Allow POST for adding funds
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Credentials": True
}
POST_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Credentials": True
}
# --- End CORS Configuration ---

# Get BOTH table names from environment variables
SAVINGS_TABLE_NAME = os.environ.get('SAVINGS_TABLE_NAME')
WALLETS_TABLE_NAME = os.environ.get('WALLETS_TABLE_NAME')

dynamodb = boto3.client('dynamodb') # Use the client for transactions

def add_to_savings_goal(event, context):
    """
    Atomically moves funds from a wallet to a savings goal
    using a DynamoDB transaction. Handles OPTIONS preflight.
    """

    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request for add_to_savings_goal")
        return {
            "statusCode": 200,
            "headers": OPTIONS_CORS_HEADERS,
            "body": ""
        }
    # --- End CORS Preflight Check ---

    # --- POST Logic ---
    if http_method == 'POST':
        print("Handling POST request for add_to_savings_goal")
        try:
            goal_id = unquote(event['pathParameters']['goal_id']).strip()

            body = json.loads(event.get('body', '{}'))
            wallet_id = body.get('wallet_id')
            amount_str = body.get('amount', '0.00') # Get as string
            amount = Decimal(amount_str) # Convert

            if not wallet_id or amount <= 0:
                print("Validation failed: Missing wallet_id or non-positive amount.")
                return {
                    "statusCode": 400,
                    "headers": POST_CORS_HEADERS, # Add Headers
                    "body": json.dumps({"message": "Valid wallet_id and positive amount are required."})
                }

            print(f"Attempting transaction: Move {amount} from wallet {wallet_id} to goal {goal_id}")

            # DynamoDB transaction
            dynamodb.transact_write_items(
                TransactItems=[
                    {
                        # 1. Debit the main wallet
                        'Update': {
                            'TableName': WALLETS_TABLE_NAME,
                            'Key': {
                                'wallet_id': {'S': wallet_id}
                            },
                            'UpdateExpression': 'SET balance = balance - :amount',
                            'ConditionExpression': 'balance >= :amount', # Check for funds
                            'ExpressionAttributeValues': {
                                ':amount': {'N': str(amount)}
                            }
                        }
                    },
                    {
                        # 2. Credit the savings goal
                        'Update': {
                            'TableName': SAVINGS_TABLE_NAME,
                            'Key': {
                                'goal_id': {'S': goal_id}
                            },
                            'UpdateExpression': 'SET current_amount = current_amount + :amount',
                            'ConditionExpression': 'attribute_exists(goal_id)', # Ensure goal exists
                            'ExpressionAttributeValues': {
                                ':amount': {'N': str(amount)}
                            }
                        }
                    }
                ]
            )

            print(f"Transaction successful for goal {goal_id}")
            return {
                "statusCode": 200,
                "headers": POST_CORS_HEADERS, # Add Headers
                "body": json.dumps({"message": f"Successfully added {amount} to savings goal."})
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            print(f"DynamoDB ClientError during transaction: {error_code}")
            # Check if the transaction failed due to a condition check
            if error_code == 'TransactionCanceledException':
                reasons = e.response.get('CancellationReasons', [])
                if any(r.get('Code') == 'ConditionalCheckFailed' for r in reasons):
                    print("Transaction failed: Insufficient funds or goal/wallet not found.")
                    return {
                        "statusCode": 400, # Bad Request (likely insufficient funds)
                        "headers": POST_CORS_HEADERS, # Add Headers
                        "body": json.dumps({"message": "Transaction failed. Check wallet balance or savings goal ID."})
                    }

            # Other DynamoDB errors
            return {
                "statusCode": 500,
                "headers": POST_CORS_HEADERS, # Add Headers
                "body": json.dumps({"message": "Database error during transaction.", "error": str(e)})
            }
        except (ValueError, TypeError) as ve: # Catch Decimal conversion errors
            print(f"Input Error: {ve}")
            return {
                "statusCode": 400,
                "headers": POST_CORS_HEADERS, # Add Headers
                "body": json.dumps({"message": f"Invalid amount format: {ve}"})
            }
        except Exception as e:
            print(f"Unexpected error: {e}")
            return {
                "statusCode": 500,
                "headers": POST_CORS_HEADERS, # Add Headers
                "body": json.dumps({"message": "An unexpected error occurred.", "error": str(e)})
            }
    else:
        # Handle unsupported methods
        print(f"Unsupported method: {http_method}")
        return {
            "statusCode": 405, # Method Not Allowed
            "headers": POST_CORS_HEADERS,
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }