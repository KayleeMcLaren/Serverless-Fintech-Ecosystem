import json
import os
import boto3
from decimal import Decimal
from urllib.parse import unquote
from botocore.exceptions import ClientError

# Get BOTH table names from environment variables
SAVINGS_TABLE_NAME = os.environ.get('SAVINGS_TABLE_NAME')
WALLETS_TABLE_NAME = os.environ.get('WALLETS_TABLE_NAME')

dynamodb = boto3.client('dynamodb') # Use the client for transactions

def add_to_savings_goal(event, context):
    """
    Atomically moves funds from a wallet to a savings goal
    using a DynamoDB transaction.
    """
    try:
        goal_id = unquote(event['pathParameters']['goal_id']).strip()
        
        body = json.loads(event.get('body', '{}'))
        wallet_id = body.get('wallet_id')
        amount = Decimal(body.get('amount', '0.00'))

        if not wallet_id or amount <= 0:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Valid wallet_id and positive amount are required."})
            }

        print(f"Attempting transaction: Move {amount} from wallet {wallet_id} to goal {goal_id}")

        # This is the DynamoDB transaction
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
        
        return {
            "statusCode": 200,
            "body": json.dumps({"message": f"Successfully added {amount} to savings goal."})
        }

    except ClientError as e:
        # Check if the transaction failed due to a condition check (e.g., insufficient funds)
        if e.response['Error']['Code'] == 'TransactionCanceledException':
            if 'ConditionalCheckFailed' in [r.get('Code') for r in e.response.get('CancellationReasons', [])]:
                print("Transaction failed: Insufficient funds or goal not found.")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"message": "Transaction failed. Check wallet balance or savings goal ID."})
                }
        
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to update savings goal.", "error": str(e)})
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "An unexpected error occurred.", "error": str(e)})
        }