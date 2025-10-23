import json
import os
import boto3
import time
from decimal import Decimal, InvalidOperation
from botocore.exceptions import ClientError

# --- Table Names ---
LOANS_TABLE_NAME = os.environ.get('LOANS_TABLE_NAME') # This is actually the TRANSACTIONS table
LOG_TABLE_NAME = os.environ.get('TRANSACTIONS_LOG_TABLE_NAME') # This is not used here

# --- Self-Correction: Fix Environment Variable Name ---
# The Terraform for this Lambda passes DYNAMODB_TABLE_NAME, not LOANS_TABLE_NAME
# Let's check the Terraform block:
# resource "aws_lambda_function" "update_transaction_status_lambda" {
#   ...
#   environment {
#     variables = {
#       DYNAMODB_TABLE_NAME = var.dynamodb_table_name
#     }
#   }
# }
# OK, the code should be reading DYNAMODB_TABLE_NAME
# Let's fix the handler to read the correct variable.

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME') # Correct variable name

# --- DynamoDB Resources ---
dynamodb = boto3.resource('dynamodb')

if not TABLE_NAME:
    print("ERROR: DYNAMODB_TABLE_NAME environment variable not set.")
    table = None # Changed from loans_table to table
else:
    table = dynamodb.Table(TABLE_NAME) # Changed from loans_table to table

def update_transaction_status(event, context):
    """
    Subscribes to 'PAYMENT_SUCCESSFUL' / 'FAILED'
    and updates the transaction status in the transactions_table.
    """
    print(f"Received event: {json.dumps(event)}")
    
    if not table: # Changed from loans_table
        print("FATAL: table is not configured. Aborting.")
        raise Exception("Server configuration error: DYNAMODB_TABLE_NAME not set.")

    for record in event['Records']:
        message_id = record.get('Sns', {}).get('MessageId', 'Unknown')
        try:
            sns_message_str = record.get('Sns', {}).get('Message')
            if not sns_message_str:
                print(f"Skipping record {message_id}: Missing SNS message body.")
                continue

            sns_message = json.loads(sns_message_str)
            event_type = sns_message.get('event_type')
            
            # --- FIX: Check for both keys ---
            event_details = sns_message.get('details') or sns_message.get('transaction_details') or {}
            
            transaction_id = event_details.get('transaction_id') # Get from event_details
            # --- END FIX ---
            
            if not transaction_id:
                print(f"Invalid message, no transaction_id: {event_details}")
                continue # Move to next record
                
            if event_type == "PAYMENT_SUCCESSFUL" or event_type == "PAYMENT_FAILED":
                new_status = "SUCCESSFUL" if event_type == "PAYMENT_SUCCESSFUL" else "FAILED"
                print(f"Updating transaction {transaction_id} to {new_status}")

                try:
                    # Update the transaction in the transactions_table
                    table.update_item(
                        Key={'transaction_id': transaction_id},
                        UpdateExpression="SET #status = :status, updated_at = :updated_at",
                        ConditionExpression="attribute_exists(transaction_id)", # Ensure it exists
                        ExpressionAttributeNames={ '#status': 'status' },
                        ExpressionAttributeValues={
                            ':status': new_status,
                            ':updated_at': int(time.time())
                        }
                    )
                    print(f"Successfully updated transaction {transaction_id}.")
                
                except ClientError as ce:
                    if ce.response['Error']['Code'] == 'ConditionalCheckFailedException':
                         print(f"Skipping update for {transaction_id}: Transaction not found.")
                    else:
                         print(f"ERROR: DynamoDB error updating transaction {transaction_id}: {ce}")
                         raise ce # Force SNS retry
            
            elif event_type in ["LOAN_REPAYMENT_SUCCESSFUL", "LOAN_REPAYMENT_FAILED"]:
                # This Lambda (update_transaction_status) does not handle loan repayments.
                # That is handled by update_loan_repayment_status.
                # We can just ignore these events.
                print(f"Skipping event type {event_type}, handled by another service.")
                
            else:
                print(f"Skipping unhandled event type: {event_type}")

        except (ValueError, InvalidOperation, TypeError) as val_err:
             print(f"ERROR processing record {message_id} due to invalid data: {val_err}")
        except Exception as e:
            print(f"ERROR: Unexpected error processing record {message_id}: {e}")
            raise e # Force SNS to retry

    return {"statusCode": 200, "body": "Events processed."}