import json
import os
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError
import logging
from copy import deepcopy

# --- 1. Set up logger ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# ---

# --- Environment Variables ---
LOANS_TABLE_NAME = os.environ.get('LOANS_TABLE_NAME')
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

# --- (Simulation Logic - no changes, but moved here) ---
def simulate_plan(loans_list, total_monthly_payment, strategy):
    """
    Simulates a repayment plan.
    strategy='avalanche' (highest interest) or 'snowball' (lowest balance)
    """
    loans = deepcopy(loans_list) # Don't modify the original list
    total_interest_paid = Decimal('0.0')
    months = 0
    payoff_log = []
    
    # Sort loans based on strategy
    if strategy == 'avalanche':
        # Highest interest rate first
        loans.sort(key=lambda x: x['interest_rate'], reverse=True)
        first_target_loan = loans[0] if loans else None
    elif strategy == 'snowball':
        # Lowest remaining balance first
        loans.sort(key=lambda x: x['remaining_balance'])
        first_target_loan = loans[0] if loans else None
    else:
        first_target_loan = None # Min payment plan

    while any(l['remaining_balance'] > 0 for l in loans):
        months += 1
        if months > 1200: # Max 100 years, prevent infinite loop
            raise Exception("Repayment plan exceeds 100 years.")
            
        payment_remaining = total_monthly_payment
        
        # 1. Pay minimums on all loans
        total_minimums_due = Decimal('0.0')
        for loan in loans:
            if loan['remaining_balance'] > 0:
                min_payment = min(loan['minimum_payment'], loan['remaining_balance'])
                total_minimums_due += min_payment
        
        # This check is now handled in the main handler, but good to have
        if payment_remaining < total_minimums_due:
             raise Exception(f"Monthly budget {total_monthly_payment} is less than total minimums {total_minimums_due}")
        
        # Apply minimum payments and calculate interest
        for loan in loans:
            if loan['remaining_balance'] > 0:
                interest_this_month = (loan['remaining_balance'] * (loan['interest_rate'] / 100)) / 12
                total_interest_paid += interest_this_month
                
                # Pay minimum (or less if balance is lower)
                payment = min(loan['minimum_payment'], loan['remaining_balance'] + interest_this_month)
                
                # Check if this payment is more than what's left after interest
                principal_payment = payment - interest_this_month
                if principal_payment < 0: 
                    # Interest is more than min payment (negative amortization)
                    loan['remaining_balance'] -= principal_payment # Balance goes up
                else:
                    loan['remaining_balance'] -= principal_payment
                    
                payment_remaining -= payment

        # 2. Apply extra payment ("avalanche" or "snowball")
        extra_payment = payment_remaining
        
        # The 'loans' list is already sorted by the chosen strategy
        for loan in loans:
            if extra_payment <= 0:
                break # No more extra money to apply
                
            if loan['remaining_balance'] > 0:
                payment = min(extra_payment, loan['remaining_balance'])
                loan['remaining_balance'] -= payment
                extra_payment -= payment
                
                if loan['remaining_balance'] <= 0:
                    payoff_log.append(f"Month {months}: Paid off '{loan.get('name', 'Loan')}'!")

    return {
        'months_to_payoff': months,
        'total_interest_paid': total_interest_paid.quantize(Decimal('0.01')),
        'first_target': first_target_loan,
        'payoff_log': payoff_log
    }
# ---

def calculate_repayment_plan(event, context):
    """
    API: POST /debt-optimiser
    Calculates Avalanche and Snowball debt repayment plans.
    """
    
    # --- 3. Initialize boto3 inside the handler ---
    dynamodb = boto3.resource('dynamodb')
    loans_table = dynamodb.Table(LOANS_TABLE_NAME) if LOANS_TABLE_NAME else None
    # ---

    # --- (CORS Preflight Check - no changes) ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        logger.info("Handling OPTIONS preflight request for calculate_repayment_plan")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }

    if not loans_table:
        log_message = {
            "status": "error",
            "action": "calculate_repayment_plan",
            "message": "FATAL: LOANS_TABLE_NAME environment variable not set."
        }
        logger.error(json.dumps(log_message))
        return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'POST':
        log_context = {"action": "calculate_repayment_plan"}
        try:
            body = json.loads(event.get('body', '{}'))
            wallet_id = body.get('wallet_id')
            monthly_budget_str = body.get('monthly_budget')
            
            log_context["wallet_id"] = wallet_id

            if not wallet_id or not monthly_budget_str:
                raise ValueError("wallet_id and monthly_budget are required.")
            
            monthly_budget = Decimal(monthly_budget_str)
            log_context["monthly_budget"] = str(monthly_budget)

            logger.info(json.dumps({**log_context, "status": "info", "message": "Fetching approved loans."}))
            
            # 1. Get all APPROVED loans for the wallet
            response = loans_table.query(
                IndexName='wallet_id-index',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('wallet_id').eq(wallet_id),
                FilterExpression='#status = :status_val',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status_val': 'APPROVED'}
            )
            loans = response.get('Items', [])

            if not loans:
                logger.warning(json.dumps({**log_context, "status": "warn", "message": "No approved loans found."}))
                return { "statusCode": 404, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "No approved loans found for this wallet."}) }

            # 2. Check if budget is sufficient
            total_minimum_payment = sum(l.get('minimum_payment', Decimal('0')) for l in loans)
            if monthly_budget < total_minimum_payment:
                logger.warning(json.dumps({**log_context, "status": "warn", "total_minimum_payment": str(total_minimum_payment), "message": "Budget is less than total minimum payments."}))
                return {
                    "statusCode": 400,
                    "headers": POST_CORS_HEADERS,
                    "body": json.dumps({
                        "message": "Monthly budget is less than the total minimum payment.",
                        "total_minimum_payment": total_minimum_payment
                    }, cls=DecimalEncoder)
                }
            
            extra_payment = monthly_budget - total_minimum_payment
            log_context["extra_payment"] = str(extra_payment)
            
            # 3. Run simulations
            logger.info(json.dumps({**log_context, "status": "info", "message": "Running simulations."}))
            
            # Add 'name' to loans for better logging
            for i, loan in enumerate(loans):
                loan['name'] = f"Loan {i+1} ({loan['loan_id'][:4]}...)"

            avalanche_plan = simulate_plan(loans, monthly_budget, 'avalanche')
            snowball_plan = simulate_plan(loans, monthly_budget, 'snowball')
            
            logger.info(json.dumps({**log_context, "status": "info", "message": "Simulations complete."}))

            return {
                "statusCode": 200,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({
                    "summary": {
                        "total_loans": len(loans),
                        "monthly_budget": monthly_budget,
                        "total_minimum_payment": total_minimum_payment.quantize(Decimal('0.01')),
                        "extra_payment": extra_payment.quantize(Decimal('0.01'))
                    },
                    "avalanche_plan": avalanche_plan,
                    "snowball_plan": snowball_plan
                }, cls=DecimalEncoder)
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
         return {
            "statusCode": 405,
            "headers": POST_CORS_HEADERS,
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }