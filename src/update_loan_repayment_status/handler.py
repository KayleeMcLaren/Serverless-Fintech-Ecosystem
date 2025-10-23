import json
import os
import boto3
from decimal import Decimal, InvalidOperation
from botocore.exceptions import ClientError

# --- Table Name ---
LOANS_TABLE_NAME = os.environ.get('LOANS_TABLE_NAME')

# --- DynamoDB Resources ---
dynamodb = boto3.resource('dynamodb')

if not LOANS_TABLE_NAME:
    print("ERROR: LOANS_TABLE_NAME environment variable not set.")
    loans_table = None
else:
    loans_table = dynamodb.Table(LOANS_TABLE_NAME)


def update_loan_repayment_status(event, context):
    """
    Subscribes to 'LOAN_REPAYMENT_SUCCESSFUL' or 'FAILED'
    Updates the loan's remaining_balance in the loans_table.
    """
    print(f"Received event: {json.dumps(event)}")
    
    if not loans_table:
        print("FATAL: loans_table is not configured. Aborting.")
        # Raise error to force SNS retry if the env var is missing
        raise Exception("Server configuration error: LOANS_TABLE_NAME not set.")

    for record in event['Records']:
        message_id = record.get('Sns', {}).get('MessageId', 'Unknown')
        try:
            sns_message_str = record.get('Sns', {}).get('Message')
            if not sns_message_str:
                print(f"Skipping record {message_id}: Missing SNS message body.")
                continue

            sns_message = json.loads(sns_message_str)
            event_type = sns_message.get('event_type')
            event_details = sns_message.get('details', {})
            
            loan_id = event_details.get('loan_id')
            wallet_id = event_details.get('wallet_id')
            amount_str = event_details.get('amount')
            
            if not loan_id or not wallet_id or not amount_str:
                print(f"Skipping record {message_id}: Invalid details {event_details}")
                continue

            amount = Decimal(amount_str)

            if event_type == 'LOAN_REPAYMENT_SUCCESSFUL':
                print(f"Processing successful repayment for loan {loan_id}, amount {amount}")
                
                # Decrease the remaining_balance on the loan
                response = loans_table.update_item(
                    Key={'loan_id': loan_id},
                    UpdateExpression="SET remaining_balance = remaining_balance - :amount",
                    # Ensure the loan is still approved and not already paid off
                    ConditionExpression="attribute_exists(loan_id) AND #status = :status_approved",
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={ 
                        ':amount': amount,
                        ':status_approved': 'APPROVED'
                    },
                    ReturnValues="UPDATED_NEW"
                )
                
                new_remaining_balance = response.get('Attributes', {}).get('remaining_balance')
                print(f"Loan {loan_id} new remaining balance: {new_remaining_balance}")
                
                # If loan is paid off, update status to 'PAID'
                if new_remaining_balance is not None and new_remaining_balance <= 0:
                    print(f"Loan {loan_id} has been fully paid off. Setting status to PAID.")
                    loans_table.update_item(
                         Key={'loan_id': loan_id},
                         UpdateExpression="SET #status = :status_paid",
                         ExpressionAttributeNames={'#status': 'status'},
                         ExpressionAttributeValues={':status_paid': 'PAID'}
                    )
                    print(f"Set loan {loan_id} status to PAID.")

            elif event_type == 'LOAN_REPAYMENT_FAILED':
                reason = sns_message.get('reason', 'Unknown')
                print(f"Processing FAILED repayment for loan {loan_id}. Reason: {reason}. No action taken on loan balance.")
                # No action needed on the loan balance, just log.
            
            else:
                print(f"Skipping event type: {event_type}")

        except (ValueError, InvalidOperation, TypeError) as val_err:
             print(f"ERROR processing record {message_id} due to invalid data: {val_err}")
             # Don't re-raise, move to next record
        except ClientError as ce:
             # Handle conditional check failure (e.g., loan not 'APPROVED')
             if ce.response['Error']['Code'] == 'ConditionalCheckFailedException':
                 print(f"Skipping repayment for {loan_id}: Condition failed (likely not in APPROVED state).")
             else:
                 print(f"ERROR: DynamoDB error processing record {message_id}: {ce}")
                 raise ce # Force SNS to retry the batch
        except Exception as e:
            print(f"ERROR: Unexpected error processing record {message_id}: {e}")
            raise e # Force SNS to retry the batch

    return {"statusCode": 200, "body": "Events processed."}