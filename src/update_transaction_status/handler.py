import json
import os
import boto3
import time
from decimal import Decimal, InvalidOperation
from botocore.exceptions import ClientError
import logging

# Set up logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Environment Variables ---
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME') 

def update_transaction_status(event, context):
    """
    SNS Subscriber for 'PAYMENT_SUCCESSFUL' / 'FAILED'
    Updates the transaction status in the transactions_table.
    """
    
    # --- Initialize boto3 inside the handler ---
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME) if TABLE_NAME else None

    if not table:
        log_message = {
            "status": "error",
            "action": "update_transaction_status",
            "message": "FATAL: DYNAMODB_TABLE_NAME environment variable not set."
        }
        logger.error(json.dumps(log_message))
        raise Exception("Server configuration error.")

    logger.info(f"Received event: {json.dumps(event)}")

    for record in event['Records']:
        message_id = record.get('Sns', {}).get('MessageId', 'Unknown')
        log_context = {"action": "update_transaction_status", "sns_message_id": message_id}
        
        try:
            sns_message_str = record.get('Sns', {}).get('Message')
            if not sns_message_str:
                logger.warn(json.dumps({**log_context, "status": "warn", "message": "Skipping record: Missing SNS message body."}))
                continue

            sns_message = json.loads(sns_message_str)
            event_type = sns_message.get('event_type')
            log_context["event_type"] = event_type
            
            event_details = sns_message.get('details') or sns_message.get('transaction_details') or {}
            
            transaction_id = event_details.get('transaction_id')
            log_context["transaction_id"] = transaction_id
            
            if not transaction_id:
                logger.warn(json.dumps({**log_context, "status": "warn", "message": "Invalid message, no transaction_id. Skipping."}))
                continue
                
            if event_type == "PAYMENT_SUCCESSFUL" or event_type == "PAYMENT_FAILED":
                new_status = "SUCCESSFUL" if event_type == "PAYMENT_SUCCESSFUL" else "FAILED"
                log_context["new_status"] = new_status
                
                logger.info(json.dumps({**log_context, "status": "info", "message": "Updating transaction status."}))

                try:
                    table.update_item(
                        Key={'transaction_id': transaction_id},
                        UpdateExpression="SET #status = :status, updated_at = :updated_at",
                        ConditionExpression="attribute_exists(transaction_id)", 
                        ExpressionAttributeNames={ '#status': 'status' },
                        ExpressionAttributeValues={
                            ':status': new_status,
                            ':updated_at': int(time.time())
                        }
                    )
                    logger.info(json.dumps({**log_context, "status": "info", "message": "Successfully updated transaction."}))
                
                except ClientError as ce:
                    log_context["error_code"] = ce.response['Error']['Code']
                    if ce.response['Error']['Code'] == 'ConditionalCheckFailedException':
                         logger.warn(json.dumps({**log_context, "status": "warn", "message": "Condition failed: Transaction not found."}))
                    else:
                         logger.error(json.dumps({**log_context, "status": "error", "message": f"DynamoDB error: {str(ce)}"}))
                         raise ce # Force SNS retry
            
            elif event_type in ["LOAN_REPAYMENT_SUCCESSFUL", "LOAN_REPAYMENT_FAILED"]:
                logger.info(json.dumps({**log_context, "status": "info", "message": "Skipping loan event, handled by another service."}))
                
            else:
                logger.warn(json.dumps({**log_context, "status": "warn", "message": "Skipping unhandled event type."}))

        except (ValueError, InvalidOperation, TypeError) as val_err:
             logger.error(json.dumps({**log_context, "status": "error", "message": f"Invalid data error: {str(val_err)}"}))
        except Exception as e:
            logger.error(json.dumps({**log_context, "status": "error", "message": f"Unexpected error: {str(e)}"}))
            raise e

    return {"statusCode": 200, "body": "Events processed."}