import json
import os
import uuid
import boto3
import time
from decimal import Decimal, ROUND_HALF_UP
from botocore.exceptions import ClientError

# --- CORS Configuration (Keep as is) ---
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")
OPTIONS_CORS_HEADERS = { "Access-Control-Allow-Origin": ALLOWED_ORIGIN, "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type, Authorization", "Access-Control-Allow-Credentials": True }
POST_CORS_HEADERS = { "Access-Control-Allow-Origin": ALLOWED_ORIGIN, "Access-Control-Allow-Credentials": True }
# --- End CORS Configuration ---

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal): return str(o)
        return super(DecimalEncoder, self).default(o)

# --- NEW: Interest rate based ONLY on term ---
def calculate_interest_rate(term_months):
    """Calculates interest rate based on loan term."""
    term = int(term_months)
    if term <= 12:
        return Decimal('8.0') # Short term
    elif term <= 24:
        return Decimal('12.0') # Medium term
    else:
        return Decimal('15.0') # Long term
# ---

# --- NEW: Amortization Formula for Minimum Payment ---
def calculate_minimum_payment(amount, annual_rate, term_months):
    """Calculates the monthly payment (PMT) for a loan."""
    if annual_rate <= 0 or term_months <= 0:
        return (amount / (term_months if term_months > 0 else 1)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    monthly_rate = (annual_rate / Decimal('100')) / Decimal('12') # i
    n = term_months # n
    P = amount # P
    
    if monthly_rate == 0:
        return (P / n).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    try:
        numerator = monthly_rate * ((Decimal('1') + monthly_rate) ** n)
        denominator = ((Decimal('1') + monthly_rate) ** n) - Decimal('1')
        monthly_payment = P * (numerator / denominator)
        
        return monthly_payment.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except Exception as e:
        print(f"Error in amortization calculation: {e}")
        # Fallback to simple interest + principal
        return (amount / n + (amount * (annual_rate / 100) / 12)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
# ---

def apply_for_loan(event, context):
    """Creates a new loan application, calculating rate/min_payment from amount/term."""

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
            term_months_str = body.get('loan_term_months')

            if not all([wallet_id, amount_str, term_months_str]):
                raise ValueError("wallet_id, amount, and loan_term_months are required.")

            amount = Decimal(amount_str)
            term_months = int(term_months_str)
            
            if not (Decimal('50') <= amount <= Decimal('10000')):
                 raise ValueError("Loan amount must be between $50 and $10,000.")
            if term_months not in [12, 24, 36]:
                 raise ValueError("Loan term must be 12, 24, or 36 months.")

            # --- Calculate Loan Terms ---
            interest_rate = calculate_interest_rate(term_months) # Use new logic
            minimum_payment = calculate_minimum_payment(amount, interest_rate, term_months)
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
                'loan_term_months': term_months
            }

            table.put_item(Item=item)
            response_body = { "message": "Loan application received!", "loan": item }

            return {
                "statusCode": 201,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps(response_body, cls=DecimalEncoder)
            }
        
        except (ValueError, TypeError, InvalidOperation) as ve:
            print(f"Input Error applying for loan: {ve}")
            return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Invalid input: {str(ve)}"}) }
        except Exception as e:
            print(f"Error applying for loan: {e}")
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Failed to apply for loan.", "error": str(e)}) }
    else:
         return { "statusCode": 405, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }