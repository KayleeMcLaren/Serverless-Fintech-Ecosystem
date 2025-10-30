import json
import os
import boto3
import time # <--- THIS WAS MISSING
from decimal import Decimal, InvalidOperation
from urllib.parse import unquote
from botocore.exceptions import ClientError

# --- (Keep CORS Configuration as is) ---
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")
OPTIONS_CORS_HEADERS = { "Access-Control-Allow-Origin": ALLOWED_ORIGIN, "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type, Authorization", "Access-Control-Allow-Credentials": True }
POST_CORS_HEADERS = { "Access-Control-Allow-Origin": ALLOWED_ORIGIN, "Access-Control-Allow-Credentials": True }
# --- End CORS Configuration ---

# --- (Keep Table Names & AWS Resources as is) ---
LOANS_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN') # Payment events topic
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
loans_table = dynamodb.Table(LOANS_TABLE_NAME) if LOANS_TABLE_NAME else None

# --- (Keep DecimalEncoder as is) ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal): return str(o)
        return super(DecimalEncoder, self).default(o)
    

def repay_loan(event, context):
    """Initiates a loan repayment by publishing an event."""

    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }
    # --- End CORS Preflight Check ---

    if not loans_table:
        print("ERROR: Loans table resource is not initialized.")
        return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error: Table not found."}) }

    if http_method == 'POST':
        print("Handling POST request") # Added print statement
        try:
            loan_id = unquote(event['pathParameters']['loan_id']).strip()
            body = json.loads(event.get('body', '{}'))
            amount_str = body.get('amount')

            if not amount_str:
                raise ValueError("Amount is required.")
            
            amount = Decimal(amount_str)
            if amount <= 0:
                 raise ValueError("Amount must be positive.")
            
            print(f"Fetching loan {loan_id} to get wallet_id")
            # 1. Get the loan to find the wallet_id and check status
            response = loans_table.get_item(Key={'loan_id': loan_id})
            loan_item = response.get('Item')

            # 1. Get the loan to find the wallet_id and remaining_balance
            response = loans_table.get_item(Key={'loan_id': loan_id})
            loan_item = response.get('Item')

            if not loan_item:
                print(f"Loan not found: {loan_id}")
                return { "statusCode": 404, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Loan not found."}) }
            if loan_item.get('status') != 'APPROVED':
                 print(f"Loan {loan_id} is not in APPROVED state.")
                 return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Loan is not in 'APPROVED' state."}) }
            
            wallet_id = loan_item.get('wallet_id')
            if not wallet_id:
                 print(f"ERROR: Loan {loan_id} is missing wallet_id.")
                 return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Loan item is missing wallet_id."}) }

            # --- 2. NEW: Compare Amount to Balance ---
            remaining_balance = Decimal(loan_item.get('remaining_balance', '0'))
            amount_to_pay = amount # Assume full amount initially

            if amount > remaining_balance:
                print(f"Payment amount {amount} exceeds balance {remaining_balance}. Adjusting.")
                amount_to_pay = remaining_balance # Cap payment at the remaining balance
            # --- END NEW LOGIC ---

            # 3. Publish the repayment request event
            event_details = {
                'loan_id': loan_id,
                'wallet_id': wallet_id,
                'amount': amount_to_pay, # <-- Use the (potentially adjusted) amount
                'repayment_time': int(time.time())
            }
            
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Message=json.dumps({"event_type": "LOAN_REPAYMENT_REQUESTED", "details": event_details}, cls=DecimalEncoder),
                Subject=f"Loan Repayment Requested: {loan_id}",
                MessageAttributes={
                    'event_type': { 'DataType': 'String', 'StringValue': 'LOAN_REPAYMENT_REQUESTED' }
                }
            )

            #--- 4. UPDATE: Return the actual amount processed ---
            return {
                "statusCode": 202, # Accepted
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({
                    "message": "Repayment request received and is processing.",
                    "amount_processed": amount_to_pay # Return the adjusted amount
                }, cls=DecimalEncoder)
            }
            
        except (ValueError, TypeError, InvalidOperation) as ve:
            print(f"Input Error: {ve}")
            return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Invalid input: {ve}"}) }
        except ClientError as ce:
            print(f"DynamoDB Error: {ce}")
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Database error.", "error": str(ce)}) }
        except Exception as e:
            print(f"Unexpected Error: {e}")
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Failed to request repayment.", "error": str(e)}) }
    else:
        print(f"Unsupported method: {http_method}")
        return { "statusCode": 405, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }