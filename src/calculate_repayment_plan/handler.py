import json
import os
import boto3
from decimal import Decimal, InvalidOperation # Import InvalidOperation
import copy
from botocore.exceptions import ClientError # Import ClientError

# --- CORS Configuration ---
ALLOWED_ORIGIN = "*" # Use "*" for dev, replace with CloudFront URL for prod
OPTIONS_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS", # Allow POST
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Credentials": True
}
POST_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Credentials": True
}
# --- End CORS Configuration ---

# Get the table name from an environment variable
LOANS_TABLE_NAME = os.environ.get('LOANS_TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
loans_table = dynamodb.Table(LOANS_TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert a DynamoDB item to JSON."""
    def default(self, o):
        if isinstance(o, Decimal):
            # Format to 2 decimal places for currency consistency
            return "{:.2f}".format(o)
        return super(DecimalEncoder, self).default(o)

def calculate_repayment_plan(event, context):
    """
    Calculates Debt Snowball and Avalanche repayment plans.
    Handles OPTIONS preflight.
    """
    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request for calculate_repayment_plan")
        return {
            "statusCode": 200,
            "headers": OPTIONS_CORS_HEADERS,
            "body": ""
        }
    # --- End CORS Preflight Check ---

    # --- POST Logic ---
    if http_method == 'POST':
        print("Handling POST request for calculate_repayment_plan")
        try:
            body = json.loads(event.get('body', '{}'))
            wallet_id = body.get('wallet_id')
            monthly_budget_str = body.get('monthly_budget')

            if not wallet_id or not monthly_budget_str:
                 raise ValueError("wallet_id and monthly_budget are required.")

            monthly_budget = Decimal(monthly_budget_str)
            if monthly_budget <= 0:
                raise ValueError("Monthly budget must be positive.")

            # 1. Fetch all 'APPROVED' loans
            response = loans_table.query(
                IndexName='wallet_id-index',
                KeyConditionExpression='wallet_id = :wallet_id',
                FilterExpression='#status = :status_approved',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':wallet_id': wallet_id,
                    ':status_approved': 'APPROVED'
                }
            )

            loans = response.get('Items', [])
            if not loans:
                return {
                    "statusCode": 404,
                    "headers": POST_CORS_HEADERS, # Add headers
                    "body": json.dumps({"message": "No approved loans found for this wallet."})
                }

            # Pre-process loans, ensuring required fields exist and are Decimals
            processed_loans = []
            for loan in loans:
                try:
                    loan['remaining_balance'] = Decimal(loan['remaining_balance'])
                    loan['interest_rate'] = Decimal(loan['interest_rate'])
                    loan['minimum_payment'] = Decimal(loan['minimum_payment'])
                    processed_loans.append(loan)
                except (KeyError, InvalidOperation) as data_err:
                     print(f"Skipping loan {loan.get('loan_id', 'Unknown')} due to missing/invalid data: {data_err}")
                     # Optionally inform the user about skipped loans

            if not processed_loans:
                 return {
                    "statusCode": 400,
                    "headers": POST_CORS_HEADERS,
                    "body": json.dumps({"message": "No valid loans found with required data (balance, rate, min payment)."})
                }


            # 2. Check if budget covers minimum payments
            total_minimum_payment = sum(loan['minimum_payment'] for loan in processed_loans)
            if monthly_budget < total_minimum_payment:
                return {
                    "statusCode": 400,
                    "headers": POST_CORS_HEADERS, # Add headers
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
                "statusCode": 200,
                "headers": POST_CORS_HEADERS, # Add headers
                "body": json.dumps({
                    "summary": {
                        "total_loans": len(processed_loans), # Use count of processed loans
                        "monthly_budget": monthly_budget,
                        "total_minimum_payment": total_minimum_payment,
                        "extra_payment": monthly_budget - total_minimum_payment
                    },
                    "avalanche_plan": avalanche_plan,
                    "snowball_plan": snowball_plan
                }, cls=DecimalEncoder)
            }
        except (ValueError, InvalidOperation, TypeError) as ve: # Catch validation/conversion errors
            print(f"Input Error calculating plan: {ve}")
            return {
                "statusCode": 400,
                "headers": POST_CORS_HEADERS, # Add headers
                "body": json.dumps({"message": f"Invalid input: {ve}"})
            }
        except ClientError as ce:
             print(f"DynamoDB ClientError calculating plan: {ce}")
             return {
                "statusCode": 500,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({"message": "Database error retrieving loans.", "error": str(ce)})
            }
        except Exception as e:
            print(f"Error calculating plan: {e}")
            return {
                "statusCode": 500,
                "headers": POST_CORS_HEADERS, # Add headers
                "body": json.dumps({"message": "Failed to calculate repayment plans.", "error": str(e)})
            }
    else:
        print(f"Unsupported method: {http_method}")
        return {
            "statusCode": 405,
            "headers": POST_CORS_HEADERS,
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }


# --- Simulation Logic ---
# (Keep the simulate function exactly as it was)
def simulate(loans, monthly_budget, strategy):
    """Runs a single payoff simulation."""

    # Assuming loans passed in already have Decimal types from pre-processing
    months = 0
    total_interest_paid = Decimal('0.00')
    # Recalculate minimum based on currently active loans
    current_total_minimum = sum(l['minimum_payment'] for l in loans)

    payoff_log = [] # To track which loan was paid off when

    while loans:
        months += 1
        if months > 1000: # Safety break for potential infinite loops
             print("ERROR: Simulation exceeded 1000 months, breaking.")
             return {"error": "Simulation exceeded maximum duration."}

        # 1. Calculate and add interest for the month
        monthly_interest = Decimal('0.00')
        for loan in loans:
            # Ensure remaining_balance is positive before calculating interest
            if loan['remaining_balance'] > 0:
                interest = (loan['remaining_balance'] * (loan['interest_rate'] / 100)) / 12
                # Round interest to avoid potential floating point issues over many months
                interest = interest.quantize(Decimal('0.01'))
                loan['remaining_balance'] += interest
                total_interest_paid += interest
                monthly_interest += interest

        # 2. Determine payment allocation
        available_payment = monthly_budget
        current_total_minimum = sum(l['minimum_payment'] for l in loans) # Update each month
        extra_payment = available_payment - current_total_minimum
        if extra_payment < 0: extra_payment = Decimal('0.00') # Budget might just cover minimums

        payment_details_this_month = {} # Track payment per loan

        # 3. Apply minimum payments first
        paid_minimums = Decimal('0.00')
        for loan in loans:
            # Only pay if there's a balance
            if loan['remaining_balance'] > 0:
                payment = min(loan['remaining_balance'], loan['minimum_payment'])
                loan['remaining_balance'] -= payment
                payment_details_this_month[loan['loan_id']] = payment
                paid_minimums += payment
            else:
                 payment_details_this_month[loan['loan_id']] = Decimal('0.00')

        available_extra = monthly_budget - paid_minimums
        if available_extra < 0: available_extra = Decimal('0.00')


        # 4. Apply extra payment based on strategy
        if available_extra > 0 and loans: # Check if there are still loans
            # Re-sort the list each month to find the next target
            active_loans = [l for l in loans if l['remaining_balance'] > 0]
            if not active_loans: break # All paid off

            if strategy == 'avalanche':
                active_loans.sort(key=lambda x: x['interest_rate'], reverse=True)
            elif strategy == 'snowball':
                active_loans.sort(key=lambda x: x['remaining_balance'])

            # Target the first loan in the sorted list that still has a balance
            target_loan = active_loans[0]

            payment = min(target_loan['remaining_balance'], available_extra)
            target_loan['remaining_balance'] -= payment
            payment_details_this_month[target_loan['loan_id']] += payment # Add extra to minimum paid


        # 5. Remove paid-off loans *after* all payments for the month
        paid_off_this_month_ids = []
        next_loans = []
        for loan in loans:
            if loan['remaining_balance'] <= Decimal('0.00'): # Check against zero Decimal
                paid_off_this_month_ids.append(loan['loan_id'])
                # Don't add to next_loans
            else:
                next_loans.append(loan)

        loans = next_loans # Update the list for the next iteration

        if paid_off_this_month_ids:
             print(f"Month {months}: Paid off loans {paid_off_this_month_ids}")


    return {
        "strategy": strategy,
        "months_to_payoff": months,
        # Round final interest for cleaner output
        "total_interest_paid": total_interest_paid.quantize(Decimal('0.01'))
    }