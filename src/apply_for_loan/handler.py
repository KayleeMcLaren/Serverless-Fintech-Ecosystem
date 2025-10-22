import json
import os
import uuid
import boto3
import time
from decimal import Decimal, ROUND_HALF_UP
from botocore.exceptions import ClientError

# --- CORS Configuration (Keep as is) ---
ALLOWED_ORIGIN = "*"
OPTIONS_CORS_HEADERS = { #...
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Credentials": True
}
POST_CORS_HEADERS = { #...
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Credentials": True
}
# --- End CORS Configuration ---

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

# --- Define Loan Parameters ---
# Removed DEFAULT_INTEREST_RATE
MIN_PAYMENT_PERCENTAGE = Decimal('0.05')
MIN_PAYMENT_FLOOR = Decimal('20.00')
DEFAULT_LOAN_TERM_MONTHS = 12 # Example: Fixed 12-month term

class DecimalEncoder(json.JSONEncoder):
    # ... (Keep as is)
     def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


# --- NEW: Function to Calculate Interest Rate based on Amount ---
def calculate_interest_rate(amount):
    """Calculates interest rate based on loan amount (example logic)."""
    if amount < 500:
        return Decimal('25.0') # Higher rate for smaller loans
    elif amount < 2000:
        return Decimal('18.5')
    elif amount < 5000:
        return Decimal('15.0')
    else:
        return Decimal('12.5') # Lower rate for larger loans
# --- End Interest Rate Function ---


def apply_for_loan(event, context):
    """Creates a new loan application, calculating rate, min payment, and term."""

    # --- CORS Preflight Check (Keep as is) ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }
    # --- End CORS Preflight Check ---

    if http_method == 'POST':
        try:
            body = json.loads(event.get('body', '{}'))
            wallet_id = body.get('wallet_id')
            amount_str = body.get('amount')

            if not wallet_id or not amount_str:
                raise ValueError("wallet_id and amount are required.")

            amount = Decimal(amount_str)
            if amount <= 0:
                 raise ValueError("Amount must be positive.")
            # Basic validation for loan amount range (example: $50 to $10000)
            if not (Decimal('50') <= amount <= Decimal('10000')):
                 raise ValueError("Loan amount must be between $50 and $10,000.")


            # --- Calculate Loan Terms ---
            interest_rate = calculate_interest_rate(amount) # Use the function
            calculated_min = (amount * MIN_PAYMENT_PERCENTAGE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            minimum_payment = max(calculated_min, MIN_PAYMENT_FLOOR)
            loan_term = DEFAULT_LOAN_TERM_MONTHS # Assign fixed term
            # --- End Calculation ---

            loan_id = str(uuid.uuid4())
            item = {
                'loan_id': loan_id,
                'wallet_id': wallet_id,
                'amount': amount,
                'status': 'PENDING',
                'created_at': int(time.time()),
                'interest_rate': interest_rate,
                'minimum_payment': minimum_payment,
                'remaining_balance': amount,
                'loan_term_months': loan_term # Add loan term
            }

            table.put_item(Item=item)

            response_body = {
                "message": "Loan application received successfully!",
                "loan": item # Return the full item including calculated terms
            }

            return {
                "statusCode": 201,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps(response_body, cls=DecimalEncoder)
            }
        # --- Keep existing exception handling ---
        except (ValueError, TypeError, InvalidOperation) as ve:
            print(f"Input Error applying for loan: {ve}")
            return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Invalid input: {ve}"}) }
        except Exception as e:
            print(f"Error applying for loan: {e}")
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Failed to apply for loan.", "error": str(e)}) }
    else:
        # --- Keep unsupported method handling ---
         return { "statusCode": 405, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }