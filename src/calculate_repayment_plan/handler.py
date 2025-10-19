import json
import os
import boto3
from decimal import Decimal
import copy

# Get the table name from an environment variable
LOANS_TABLE_NAME = os.environ.get('LOANS_TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
loans_table = dynamodb.Table(LOANS_TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert a DynamoDB item to JSON."""
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def calculate_repayment_plan(event, context):
    """
    Calculates Debt Snowball and Avalanche repayment plans
    based on a user's approved loans and monthly budget.
    """
    try:
        body = json.loads(event.get('body', '{}'))
        wallet_id = body.get('wallet_id')
        monthly_budget = Decimal(body.get('monthly_budget'))

        if not wallet_id or not monthly_budget or monthly_budget <= 0:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "wallet_id and a positive monthly_budget are required."})
            }

        # 1. Fetch all 'APPROVED' loans for the wallet from the GSI
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
                "body": json.dumps({"message": "No approved loans found for this wallet."})
            }

        # 2. Check if budget covers minimum payments
        total_minimum_payment = sum(Decimal(loan['minimum_payment']) for loan in loans)
        if monthly_budget < total_minimum_payment:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "message": "Monthly budget is less than total minimum payments.",
                    "total_minimum_payment": total_minimum_payment,
                    "monthly_budget": monthly_budget
                }, cls=DecimalEncoder)
            }

        # 3. Run simulations
        avalanche_plan = simulate(copy.deepcopy(loans), monthly_budget, "avalanche")
        snowball_plan = simulate(copy.deepcopy(loans), monthly_budget, "snowball")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "summary": {
                    "total_loans": len(loans),
                    "monthly_budget": monthly_budget,
                    "total_minimum_payment": total_minimum_payment,
                    "extra_payment": monthly_budget - total_minimum_payment
                },
                "avalanche_plan": avalanche_plan,
                "snowball_plan": snowball_plan
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to calculate repayment plans.", "error": str(e)})
        }

def simulate(loans, monthly_budget, strategy):
    """Runs a single payoff simulation."""
    
    # Convert all necessary loan fields to Decimal
    for loan in loans:
        loan['remaining_balance'] = Decimal(loan['remaining_balance'])
        loan['interest_rate'] = Decimal(loan['interest_rate'])
        loan['minimum_payment'] = Decimal(loan['minimum_payment'])

    months = 0
    total_interest_paid = Decimal('0.00')
    total_minimum_payment = sum(l['minimum_payment'] for l in loans)
    
    payoff_log = [] # To track which loan was paid off when

    while loans:
        months += 1
        
        # 1. Calculate and add interest for the month
        monthly_interest = Decimal('0.00')
        for loan in loans:
            interest = (loan['remaining_balance'] * (loan['interest_rate'] / 100)) / 12
            loan['remaining_balance'] += interest
            total_interest_paid += interest
            monthly_interest += interest

        # 2. Determine extra payment amount
        available_payment = monthly_budget
        extra_payment = available_payment - total_minimum_payment
        
        # 3. Apply payments
        payment_log = {}
        
        # Apply minimums first
        for loan in loans:
            payment = min(loan['remaining_balance'], loan['minimum_payment'])
            loan['remaining_balance'] -= payment
            payment_log[loan['loan_id']] = payment
            available_payment -= payment
            
        # 4. Apply extra payment based on strategy
        if extra_payment > 0:
            # Re-sort the list each month to find the next target
            if strategy == 'avalanche':
                loans.sort(key=lambda x: x['interest_rate'], reverse=True)
            elif strategy == 'snowball':
                loans.sort(key=lambda x: x['remaining_balance'])

            # Target the first loan in the sorted list
            target_loan = loans[0]
            
            # Apply remaining extra payment (which is now just `available_payment`)
            payment = min(target_loan['remaining_balance'], available_payment)
            target_loan['remaining_balance'] -= payment
            payment_log[target_loan['loan_id']] += payment

        # 5. Remove paid-off loans
        paid_off_this_month = []
        for loan in list(loans): # Iterate over a copy
            if loan['remaining_balance'] <= 0:
                paid_off_this_month.append(loan['loan_id'])
                payoff_log.append(f"Month {months}: Paid off loan {loan['loan_id']} ({loan['goal_name'] if 'goal_name' in loan else ''}).")
                # Add its minimum payment to the "snowball"
                total_minimum_payment -= loan['minimum_payment']
                loans.remove(loan)

    return {
        "strategy": strategy,
        "months_to_payoff": months,
        "total_interest_paid": total_interest_paid
    }