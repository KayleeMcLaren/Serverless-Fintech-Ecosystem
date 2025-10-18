import json
import os
import boto3
import time

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def update_transaction_status(event, context):
    """
    Subscribes to 'PAYMENT_SUCCESSFUL' or 'PAYMENT_FAILED' events
    and updates the transaction status in the transactions_table.
    """
    print(f"Received event: {json.dumps(event)}")
    
    for record in event['Records']:
        sns_message = json.loads(record['Sns']['Message'])
        event_type = sns_message.get('event_type')
        
        if event_type in ["PAYMENT_SUCCESSFUL", "PAYMENT_FAILED"]:
            transaction_details = sns_message.get('transaction_details', {})
            transaction_id = transaction_details.get('transaction_id')
            
            if not transaction_id:
                print(f"Invalid message, no transaction_id: {transaction_details}")
                continue
                
            # Set the status based on the event type
            new_status = "SUCCESSFUL" if event_type == "PAYMENT_SUCCESSFUL" else "FAILED"
            
            print(f"Updating transaction {transaction_id} to {new_status}")

            try:
                # Update the transaction in the transactions_table
                table.update_item(
                    Key={'transaction_id': transaction_id},
                    UpdateExpression="SET #status = :status, updated_at = :updated_at",
                    ExpressionAttributeNames={ '#status': 'status' },
                    ExpressionAttributeValues={
                        ':status': new_status,
                        ':updated_at': int(time.time())
                    }
                )
                print(f"Successfully updated transaction {transaction_id}.")
                
            except Exception as e:
                print(f"Error updating transaction {transaction_id}: {e}")
                # Re-raise to have SNS retry
                raise e
        
    return {"statusCode": 200, "body": "Events processed."}