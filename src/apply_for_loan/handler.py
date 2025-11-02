import json
import os
import boto3
import uuid
import time
from decimal import Decimal, InvalidOperation
from botocore.exceptions import ClientError
import logging # <-- 1. Import logging

# --- 2. Set up logger ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# ---

# --- Environment Variables ---
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")

# --- (CORS Headers - no changes) ---
OPTIONS_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Credentials": True
}
POST_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Credentials": True
}
# ---

# --- (DecimalEncoder - no changes) ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)
# ---

def apply_for_loan(event, context):
    """
    API: POST /loan
    Applies for a new loan. Creates a 'PENDING' loan entry in DynamoDB.
    """
    
    # --- 3. Initialize boto3 inside the handler ---
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME) if TABLE_NAME else None
    # ---
    
    # --- (CORS Preflight Check - no changes) ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        logger.info("Handling OPTIONS preflight request for apply_for_loan")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }

    if not table:
        log_message = {
            "status": "error",
            "action": "apply_for_loan",
            "message": "FATAL: DYNAMODB_TABLE_NAME environment variable not set."
        }
        logger.error(json.dumps(log_message))
        return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'POST':
        log_context = {"action": "apply_for_loan"}
        try:
            body = json.loads(event.get('body', '{}'))
            wallet_id = body.get('wallet_id')
            amount_str = body.get('amount')
            term_months_str = body.get('loan_term_months')

            log_context["wallet_id"] = wallet_id

            if not wallet_id or not amount_str or not term_months_str:
                raise ValueError("wallet_id, amount, and loan_term_months are required.")
            
            amount = Decimal(amount_str)
            term_months = int(term_months_str)
            
            if amount <= 0 or term_months <= 0:
                raise ValueError("Amount and term must be positive.")

            log_context.update({"amount": str(amount), "term_months": term_months})
            logger.info(json.dumps({**log_context, "status": "info", "message": "Processing new loan application."}))

            # --- Business Logic for Loan ---
            loan_id = str(uuid.uuid4())
            timestamp = int(time.time())
            
            # Determine interest rate
            if term_months <= 12:
                interest_rate = Decimal('8.0')
            elif term_months <= 24:
                interest_rate = Decimal('12.0')
            else:
                interest_rate = Decimal('15.0')
                
            # Calculate minimum monthly payment
            if interest_rate > 0:
                monthly_rate = (interest_rate / 100) / 12
                P = amount
                n = term_months
                numerator = monthly_rate * ((1 + monthly_rate) ** n)
                denominator = ((1 + monthly_rate) ** n) - 1
                minimum_payment = P * (numerator / denominator)
            else:
                minimum_payment = amount / term_months # Simple interest-free

            item = {
                'loan_id': loan_id,
                'wallet_id': wallet_id,
                'amount': amount,
                'remaining_balance': amount, # Initially, remaining balance is the full amount
                'interest_rate': interest_rate,
                'loan_term_months': term_months,
                'minimum_payment': minimum_payment.quantize(Decimal('0.01')),
                'status': 'PENDING', # New loans start as PENDING
                'created_at': timestamp,
                'updated_at': timestamp
            }
            
            # 1. Create the loan item
            table.put_item(Item=item)
            
            logger.info(json.dumps({**log_context, "loan_id": loan_id, "status": "info", "message": "Loan application created successfully."}))

            return {
                "statusCode": 201, # Created
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": "Loan application received!", "loan": item}, cls=DecimalEncoder)
            }
            
        except (ValueError, TypeError, InvalidOperation) as ve:
             logger.error(json.dumps({**log_context, "status": "error", "error_message": str(ve)}))
             return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Invalid input: {str(ve)}"}) }
        except ClientError as ce:
             logger.error(json.dumps({**log_context, "status": "error", "error_code": ce.response['Error']['Code'], "error_message": str(ce)}))
             return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Database error.", "error": str(ce)}) }
        except Exception as e:
            logger.error(json.dumps({**log_context, "status": "error", "error_message": str(e)}))
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "An unexpected error occurred.", "error": str(e)}) }
    else:
         return { "statusCode": 405, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }