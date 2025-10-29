import json
import os
import boto3
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import copy
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

# --- (Keep CORS Configuration as is) ---
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")
OPTIONS_CORS_HEADERS = { "Access-Control-Allow-Origin": ALLOWED_ORIGIN, "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type, Authorization", "Access-Control-Allow-Credentials": True }
POST_CORS_HEADERS = { "Access-Control-Allow-Origin": ALLOWED_ORIGIN, "Access-Control-Allow-Credentials": True }

# --- (Keep Table/DynamoDB setup as is) ---
LOANS_TABLE_NAME = os.environ.get('LOANS_TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
loans_table = dynamodb.Table(LOANS_TABLE_NAME) if LOANS_TABLE_NAME else None

# --- (Keep DecimalEncoder as is) ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            if not o.is_finite(): return 'N/A'
            return "{:.2f}".format(o)
        return super(DecimalEncoder, self).default(o)

# --- (Keep calculate_interest_rate and calculate_minimum_payment as is) ---
def calculate_interest_rate(term_months):
    term = int(term_months)
    if term <= 12: return Decimal('8.0')
    elif term <= 24: return Decimal('12.0')
    else: return Decimal('15.0')

def calculate_minimum_payment(amount, annual_rate, term_months):
    # ... (Amortization logic) ...
    if annual_rate <= 0 or term_months <= 0: return (amount / (term_months if term_months > 0 else 1)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    monthly_rate = (annual_rate / Decimal('100')) / Decimal('12')
    n = term_months
    P = amount
    if monthly_rate == 0: return (P / n).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    try:
        numerator = monthly_rate * ((Decimal('1') + monthly_rate) ** n)
        denominator = ((Decimal('1') + monthly_rate) ** n) - Decimal('1')
        monthly_payment = P * (numerator / denominator)
        return monthly_payment.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except Exception as e:
        print(f"Error in amortization calculation: {e}")
        return (amount / n + (amount * (annual_rate / 100) / 12)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


# --- Simulation Logic (MODIFIED) ---
def simulate(loans, monthly_budget, strategy):
    """Runs a single payoff simulation and returns the first target loan AND the payoff log."""
    
    first_target_details = None
    if loans:
        # Sort to find the first target *before* simulating
        if strategy == 'avalanche':
            # Sort by interest rate (desc), then balance (asc) as tie-breaker
            sorted_loans = sorted(loans, key=lambda x: (-x['interest_rate'], x['remaining_balance']))
        elif strategy == 'snowball':
            # Sort by balance (asc), then interest rate (desc) as tie-breaker
            sorted_loans = sorted(loans, key=lambda x: (x['remaining_balance'], -x['interest_rate']))
        
        if sorted_loans:
            first_target = sorted_loans[0]
            first_target_details = {
                'loan_id': first_target.get('loan_id'),
                'name': f"Loan ({first_target.get('loan_id', 'N/A')[:8]}...)", 
                'remaining_balance': first_target['remaining_balance'],
                'interest_rate': first_target['interest_rate']
            }

    months = 0
    total_interest_paid = Decimal('0.00')
    payoff_log = [] # <-- We already had this!

    while loans:
        months += 1
        if months > 1000:
             print("ERROR: Simulation exceeded 1000 months.")
             return {"error": "Simulation exceeded maximum duration."}

        # ... (1. Calculate interest - no changes) ...
        for loan in loans:
            if loan['remaining_balance'] > 0:
                interest = (loan['remaining_balance'] * (loan['interest_rate'] / 100)) / 12
                interest = interest.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                loan['remaining_balance'] += interest
                total_interest_paid += interest

        # ... (2. Determine payment allocation - no changes) ...
        current_total_minimum = sum(l['minimum_payment'] for l in loans if l['remaining_balance'] > 0)
        available_payment = monthly_budget
        extra_payment = available_payment - current_total_minimum
        if extra_payment < 0: extra_payment = Decimal('0.00')
        
        # ... (3. Apply minimum payments - no changes) ...
        paid_minimums = Decimal('0.00')
        for loan in loans:
            if loan['remaining_balance'] > 0:
                payment = min(loan['remaining_balance'], loan['minimum_payment'])
                loan['remaining_balance'] -= payment
                paid_minimums += payment

        available_extra = monthly_budget - paid_minimums
        if available_extra < 0: available_extra = Decimal('0.00')

        # ... (4. Apply extra payment - no changes) ...
        if available_extra > 0:
            active_loans = [l for l in loans if l['remaining_balance'] > 0]
            if not active_loans: break

            if strategy == 'avalanche':
                active_loans.sort(key=lambda x: (-x['interest_rate'], x['remaining_balance']))
            elif strategy == 'snowball':
                active_loans.sort(key=lambda x: (x['remaining_balance'], -x['interest_rate']))

            if active_loans:
                target_loan = active_loans[0]
                payment = min(target_loan['remaining_balance'], available_extra)
                target_loan['remaining_balance'] -= payment

        # 5. Remove paid-off loans and LOG them
        next_loans = []
        for loan in loans:
            if loan['remaining_balance'] > Decimal('0.00'):
                next_loans.append(loan)
            else:
                # --- UPDATE: Make the log message cleaner ---
                loan_name = f"Loan ({loan.get('loan_id', 'N/A')[:8]}...)"
                payoff_log.append(f"Month {months}: Paid off {loan_name}!")
                # ---
        loans = next_loans
    
    return {
        "strategy": strategy,
        "months_to_payoff": months,
        "total_interest_paid": total_interest_paid.quantize(Decimal('0.01')),
        "first_target": first_target_details,
        "payoff_log": payoff_log # --- ADD THIS LINE ---
    }
# --- End Simulation Logic ---

# --- Main Lambda Handler ---
def calculate_repayment_plan(event, context):
    """Main handler function"""
    
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }
    
    if not loans_table:
        print("ERROR: loans_table resource is not initialized.")
        return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error: Table not found."}) }

    if http_method == 'POST':
        try:
            body = json.loads(event.get('body', '{}'))
            wallet_id = body.get('wallet_id')
            monthly_budget_str = body.get('monthly_budget')
            if not wallet_id or not monthly_budget_str: raise ValueError("wallet_id and monthly_budget are required.")
            monthly_budget = Decimal(monthly_budget_str)
            if monthly_budget <= 0: raise ValueError("Monthly budget must be positive.")

            # 1. Fetch loans
            response = loans_table.query(
                IndexName='wallet_id-index', KeyConditionExpression=Key('wallet_id').eq(wallet_id),
                FilterExpression='#status = :status_approved',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={ ':status_approved': 'APPROVED' } # <-- CORRECT
            )
            loans = response.get('Items', [])
            if not loans:
                return { "statusCode": 404, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "No approved loans found for this wallet."}) }

            processed_loans = []
            for loan in loans:
                try:
                    loan['remaining_balance'] = Decimal(loan['remaining_balance'])
                    loan['interest_rate'] = Decimal(loan['interest_rate'])
                    loan['minimum_payment'] = Decimal(loan['minimum_payment'])
                    processed_loans.append(loan)
                except (KeyError, InvalidOperation, TypeError) as data_err:
                     print(f"Skipping loan {loan.get('loan_id', 'Unknown')} due to missing/invalid data: {data_err}")

            if not processed_loans:
                 return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "No valid loans found with required data (balance, rate, min payment)."}) }

            # 2. Check budget
            total_minimum_payment = sum(loan['minimum_payment'] for loan in processed_loans)
            if monthly_budget < total_minimum_payment:
                return {
                    "statusCode": 400, "headers": POST_CORS_HEADERS,
                    "body": json.dumps({
                        "message": "Monthly budget is less than total minimum payments.",
                        "total_minimum_payment": total_minimum_payment,
                        "monthly_budget": monthly_budget
                    }, cls=DecimalEncoder)
                }

            # 3. Run simulations
            avalanche_plan = simulate(copy.deepcopy(processed_loans), monthly_budget, "avalanche")
            snowball_plan = simulate(copy.deepcopy(processed_loans), monthly_budget, "snowball")

            return {
                "statusCode": 200, "headers": POST_CORS_HEADERS,
                "body": json.dumps({
                    "summary": {
                        "total_loans": len(processed_loans),
                        "monthly_budget": monthly_budget,
                        "total_minimum_payment": total_minimum_payment,
                        "extra_payment": monthly_budget - total_minimum_payment
                    },
                    "avalanche_plan": avalanche_plan,
                    "snowball_plan": snowball_plan
                }, cls=DecimalEncoder)
            }
        
        except (ValueError, InvalidOperation, TypeError) as ve:
            return { "statusCode": 400, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Invalid input: {str(ve)}"}) }
        except ClientError as ce:
             return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Database error.", "error": str(ce)}) }
        except Exception as e:
            print(f"Error calculating plan: {e}")
            return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Failed to calculate repayment plans.", "error": str(e)}) }
    else:
         return { "statusCode": 405, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": f"Method {http_method} not allowed."}) }