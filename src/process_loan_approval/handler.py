import json
import os
import boto3
from decimal import Decimal

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def process_loan_approval(event, context):
    """
    Processes 'LOAN_APPROVED' events from an SNS topic.
    Credits the specified wallet with the loan amount.
    """
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # SNS messages come in a list of 'Records'
        for record in event['Records']:
            sns_message = json.loads(record['Sns']['Message'])
            
            # Check if this is the event we care about
            if sns_message.get('event_type') == 'LOAN_APPROVED':
                loan_details = sns_message.get('loan_details', {})
                wallet_id = loan_details.get('wallet_id')
                amount = Decimal(loan_details.get('amount', '0.00'))

                if not wallet_id or amount <= 0:
                    print(f"Invalid loan details: {loan_details}")
                    continue # Skip this record

                print(f"Processing loan approval for wallet {wallet_id} with amount {amount}")

                # Use update_item to atomically add the amount to the balance
                table.update_item(
                    Key={'wallet_id': wallet_id},
                    UpdateExpression="SET balance = balance + :amount",
                    ExpressionAttributeValues={
                        ':amount': amount
                    },
                    # We can add a condition to ensure the wallet still exists
                    ConditionExpression="attribute_exists(wallet_id)" 
                )
                
                print(f"Successfully credited wallet {wallet_id} with {amount}.")
            
            else:
                print(f"Skipping event type: {sns_message.get('event_type')}")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Loan approvals processed successfully."})
        }
        
    except Exception as e:
        print(f"Error processing SNS event: {e}")
        # Re-raise the error to have SNS/Lambda retry the message
        raise e