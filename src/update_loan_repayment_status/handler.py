import json
import os
import boto3
from decimal import Decimal, InvalidOperation
from botocore.exceptions import ClientError
import logging # <-- 1. Import logging

# --- 2. Set up logger ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# ---

# --- Environment Variables ---
LOANS_TABLE_NAME = os.environ.get('LOANS_TABLE_NAME')
# (This Lambda doesn't log to the transactions table, so it doesn't need LOG_TABLE_NAME)

def update_loan_repayment_status(event, context):
    """
    SNS Subscriber for 'LOAN_REPAYMENT_SUCCESSFUL' / 'FAILED'
    Updates the loan's remaining_balance in the loans_table.
    """
    
    # --- 3. Initialize boto3 inside the handler ---
    dynamodb = boto3.resource('dynamodb')
    loans_table = dynamodb.Table(LOANS_TABLE_NAME) if LOANS_TABLE_NAME else None
    # ---
    
    if not loans_table:
        log_message = {
            "status": "error",
            "action": "update_loan_repayment_status",
            "message": "FATAL: LOANS_TABLE_NAME environment variable not set."
        }
        logger.error(json.dumps(log_message))
        raise Exception("Server configuration error.")

    logger.info(f"Received event: {json.dumps(event)}")

    for record in event['Records']:
        message_id = record.get('Sns', {}).get('MessageId', 'Unknown')
        log_context = {"action": "update_loan_repayment_status", "sns_message_id": message_id}
        
        try:
            sns_message_str = record.get('Sns', {}).get('Message')
            if not sns_message_str:
                logger.warn(json.dumps({**log_context, "status": "warn", "message": "Skipping record: Missing SNS message body."}))
                continue

            sns_message = json.loads(sns_message_str)
            event_type = sns_message.get('event_type')
            event_details = sns_message.get('details', {})
            
            log_context["event_type"] = event_type
            
            loan_id = event_details.get('loan_id')
            wallet_id = event_details.get('wallet_id')
            amount_str = event_details.get('amount')
            
            log_context.update({"loan_id": loan_id, "wallet_id": wallet_id})

            if not loan_id or not wallet_id or not amount_str:
                logger.error(json.dumps({**log_context, "status": "error", "message": "Invalid event details."}))
                continue

            amount = Decimal(amount_str)
            log_context["amount"] = str(amount)

            if event_type == 'LOAN_REPAYMENT_SUCCESSFUL':
                logger.info(json.dumps({**log_context, "status": "info", "message": "Processing successful repayment."}))
                
                # Decrease the remaining_balance on the loan
                response = loans_table.update_item(
                    Key={'loan_id': loan_id},
                    UpdateExpression="SET remaining_balance = remaining_balance - :amount",
                    ConditionExpression="attribute_exists(loan_id) AND #status = :status_approved",
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={ 
                        ':amount': amount,
                        ':status_approved': 'APPROVED'
                    },
                    ReturnValues="UPDATED_NEW"
                )
                
                new_remaining_balance = response.get('Attributes', {}).get('remaining_balance')
                log_context["new_remaining_balance"] = str(new_remaining_balance)
                logger.info(json.dumps({**log_context, "status": "info", "message": "Loan balance updated."}))
                
                # If loan is paid off, update status to 'PAID'
                if new_remaining_balance is not None and new_remaining_balance <= 0:
                    logger.info(json.dumps({**log_context, "status": "info", "message": "Loan fully paid off. Setting status to PAID."}))
                    loans_table.update_item(
                         Key={'loan_id': loan_id},
                         UpdateExpression="SET #status = :status_paid",
                         ExpressionAttributeNames={'#status': 'status'},
                         ExpressionAttributeValues={':status_paid': 'PAID'}
                    )
                    logger.info(json.dumps({**log_context, "status": "info", "message": "Loan status set to PAID."}))

            elif event_type == 'LOAN_REPAYMENT_FAILED':
                reason = sns_message.get('reason', 'Unknown')
                log_context["reason"] = reason
                logger.warn(json.dumps({**log_context, "status": "warn", "message": "Processing FAILED repayment. No action taken."}))
            
            else:
                logger.warn(json.dumps({**log_context, "status": "warn", "message": "Skipping unhandled event type."}))

        except (ValueError, InvalidOperation, TypeError) as val_err:
             logger.error(json.dumps({**log_context, "status": "error", "message": f"Invalid data error: {str(val_err)}"}))
        except ClientError as ce:
             log_context["error_code"] = ce.response['Error']['Code']
             if ce.response['Error']['Code'] == 'ConditionalCheckFailedException':
                 logger.warn(json.dumps({**log_context, "status": "warn", "message": "Condition failed (loan likely not in APPROVED state)."}))
             else:
                 logger.error(json.dumps({**log_context, "status": "error", "message": f"DynamoDB error: {str(ce)}"}))
                 raise ce # Force SNS to retry
        except Exception as e:
            logger.error(json.dumps({**log_context, "status": "error", "message": f"Unexpected error: {str(e)}"}))
            raise e # Force SNS to retry

    return {"statusCode": 200, "body": "Events processed."}