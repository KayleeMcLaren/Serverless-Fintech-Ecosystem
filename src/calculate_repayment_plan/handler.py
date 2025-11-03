import json
import os
import boto3
from decimal import Decimal, InvalidOperation
from botocore.exceptions import ClientError
import logging
from copy import deepcopy
from boto3.dynamodb.types import TypeDeserializer
import math # <-- Import math for logs/power

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
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Credentials": True
}
POST_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Credentials": True
}
# ---

# --- DecimalEncoder ---
class DecimalEncoder(json.JSONEncoder):
    # This ensures that Decimal objects are serialized as strings for JSON output
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)
# ---


# --- NEW STABLE CALCULATION LOGIC ---
def calculate_amortization(loans_list, monthly_payment):
    """
    Calculates total payoff time and interest for a fixed monthly payment,
    based on the total principal and weighted average interest rate.
    """
    # 1. Calculate weighted average interest rate (for simplification)
    total_principal = sum(l.get('remaining_balance', Decimal('0')) for l in loans_list)
    if total_principal == 0:
        return { 'months': 0, 'interest_paid': Decimal('0.00') }
        
    weighted_rate_num = sum(l.get('remaining_balance', Decimal('0')) * l.get('interest_rate', Decimal('0')) for l in loans_list)
    weighted_rate_annual = weighted_rate_num / total_principal / 100
    weighted_rate_monthly = weighted_rate_annual / 12

    # 2. Check if payment covers interest
    total_monthly_interest = total_principal * weighted_rate_monthly
    if monthly_payment <= total_monthly_interest:
        return { 'months': 999, 'interest_paid': Decimal('999999.00') }
    
    P = total_principal
    i = weighted_rate_monthly
    PMT = monthly_payment
    
    # 3. Amortization formula to calculate number of periods (N):
    # N = -log(1 - (i * P) / PMT) / log(1 + i)
    try:
        numerator = Decimal('1') - (i * P) / PMT
        
        # Use Python's math.log (natural log) for calculation stability
        months_decimal = -(Decimal(math.log(float(numerator))) / Decimal(math.log(float(Decimal('1') + i))))
        
        months = max(1, math.ceil(float(months_decimal))) # Ensure minimum is 1 month
        
        # 4. Total Interest = (Monthly Payment * Total Months) - Principal
        total_interest_paid = (PMT * Decimal(str(months))) - P
        
        return {
            'months': months,
            'interest_paid': total_interest_paid.quantize(Decimal('0.01')),
        }
    except Exception as e:
        logger.error(json.dumps({"action": "amortization_math_error", "error": str(e)}))
        return { 'months': 999, 'interest_paid': Decimal('999999.00') }
    
    
# --- Utility to unpack the raw client response ---
def unpack_dynamodb_items(items):
    deserializer = TypeDeserializer()
    loans = [deserializer.deserialize({'M': item}) for item in items]
    
    for loan in loans:
        for key in ['amount', 'remaining_balance', 'interest_rate', 'minimum_payment', 'loan_term_months', 'created_at', 'updated_at']:
            value = loan.get(key)
            if value is not None and not isinstance(value, Decimal):
                try:
                    loan[key] = Decimal(str(value)) # Force conversion to Decimal
                except Exception:
                    pass
    return loans
# ---


# --- Main Handler (calculate_repayment_plan) ---
def calculate_repayment_plan(event, context):
    
    log_context = {"action": "calculate_repayment_plan"}
    dynamodb_client = boto3.client('dynamodb')
    loans_table_name = LOANS_TABLE_NAME 

    # (CORS check remains the same)
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        logger.info(json.dumps({"action": "calculate_repayment_plan", "message": "Handling OPTIONS preflight request."}))
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }

    if not LOANS_TABLE_NAME:
        logger.error(json.dumps({"status": "error", "action": "calculate_repayment_plan", "message": "FATAL: LOANS_TABLE_NAME not set."}))
        return { "statusCode": 500, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'POST':
        try:
            body = json.loads(event.get('body', '{}'))
            wallet_id = body.get('wallet_id')
            monthly_budget_str = body.get('monthly_budget')
            
            log_context["wallet_id"] = wallet_id

            if not wallet_id or not monthly_budget_str:
                raise ValueError("wallet_id and monthly_budget are required.")
            
            monthly_budget = Decimal(monthly_budget_str)
            
            # 1. Fetch and process loans
            client_response = dynamodb_client.query(
                TableName=loans_table_name,
                IndexName='wallet_id-index',
                KeyConditionExpression='wallet_id = :wid',
                FilterExpression='#status = :status_val',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':wid': {'S': wallet_id},
                    ':status_val': {'S': 'APPROVED'}
                }
            )
            loans = unpack_dynamodb_items(client_response.get('Items', []))

            if not loans:
                logger.warning(json.dumps({**log_context, "status": "warn", "message": "No approved loans found."}))
                return { "statusCode": 404, "headers": POST_CORS_HEADERS, "body": json.dumps({"message": "No approved loans found for this wallet."}) }

            # 2. Calculate minimum and check budget
            total_minimum_payment = sum(l.get('minimum_payment', Decimal('0')) for l in loans)
            if monthly_budget < total_minimum_payment:
                # ... (error logging)
                return {
                    "statusCode": 400, "headers": POST_CORS_HEADERS,
                    "body": json.dumps({"message": "Monthly budget is less than the total minimum payment.", "total_minimum_payment": total_minimum_payment}, cls=DecimalEncoder)
                }
            
            extra_payment = monthly_budget - total_minimum_payment
            
            # 3. Run Projections (Using fixed monthly payment)
            logger.info(json.dumps({**log_context, "status": "info", "message": "Running stable projections."}))
            
            min_only_result = calculate_amortization(loans, total_minimum_payment)
            accelerated_result = calculate_amortization(loans, monthly_budget)
            
            # 4. Calculate final metrics
            interest_saved = accelerated_result['interest_paid'] - min_only_result['interest_paid']
            months_saved = min_only_result['months'] - accelerated_result['months']
            total_principal = sum(l.get('amount', Decimal('0')) for l in loans)


            # 5. Return structured response
            return {
                "statusCode": 200,
                "headers": POST_CORS_HEADERS,
                "body": json.dumps({
                    "summary": {
                        "total_loans": len(loans),
                        "total_minimum_payment": total_minimum_payment.quantize(Decimal('0.01')),
                        "extra_payment": extra_payment.quantize(Decimal('0.01')),
                        "total_balance": total_principal.quantize(Decimal('0.01'))
                    },
                    "projection_min": min_only_result,
                    "projection_accel": accelerated_result,
                    "interest_saved": interest_saved.quantize(Decimal('0.01')),
                    "months_saved": months_saved
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