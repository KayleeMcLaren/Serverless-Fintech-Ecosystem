import json
import os
import boto3
from decimal import Decimal
from urllib.parse import unquote
from botocore.exceptions import ClientError
import logging

# Set up logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Environment Variables ---
LOG_TABLE_NAME = os.environ.get('TRANSACTIONS_LOG_TABLE_NAME')
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "*")

# --- CORS Headers ---
OPTIONS_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Credentials": True
}
GET_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Credentials": True
}

# --- DecimalEncoder ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def get_goal_transactions(event, context):
    """
    API: GET /savings-goal/{goal_id}/transactions
    Retrieves all transactions for a specific savings goal using the GSI.
    """
    
    # --- Initialize boto3 inside the handler ---
    dynamodb = boto3.resource('dynamodb')
    log_table = dynamodb.Table(LOG_TABLE_NAME) if LOG_TABLE_NAME else None
    
    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        logger.info("Handling OPTIONS preflight request for get_goal_transactions")
        return { "statusCode": 200, "headers": OPTIONS_CORS_HEADERS, "body": "" }

    if not log_table:
        log_message = {
            "status": "error",
            "action": "get_goal_transactions",
            "message": "FATAL: TRANSACTIONS_LOG_TABLE_NAME environment variable not set."
        }
        logger.error(json.dumps(log_message))
        return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Server configuration error."}) }

    if http_method == 'GET':
        goal_id = "unknown"
        log_context = {"action": "get_goal_transactions"}
        try:
            goal_id = unquote(event['pathParameters']['goal_id']).strip()
            log_context["goal_id"] = goal_id
            
            logger.info(json.dumps({**log_context, "status": "info", "message": "Querying GSI for goal transactions."}))

            # Query the Global Secondary Index on the logs table
            response = log_table.query(
                IndexName='related_id-timestamp-index',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('related_id').eq(goal_id),
                # Only get savings-related transactions for this goal
                FilterExpression='#type IN (:add, :redeem, :refund)',
                ExpressionAttributeNames={'#type': 'type'},
                ExpressionAttributeValues={
                    ':add': 'SAVINGS_ADD',
                    ':redeem': 'SAVINGS_REDEEM',
                    ':refund': 'SAVINGS_REFUND'
                },
                ScanIndexForward=False  # Sort by timestamp descending
            )
            
            items = response.get('Items', [])

            return {
                "statusCode": 200,
                "headers": GET_CORS_HEADERS,
                "body": json.dumps(items, cls=DecimalEncoder)
            }
            
        except ClientError as ce:
             logger.error(json.dumps({**log_context, "status": "error", "error_code": ce.response['Error']['Code'], "error_message": str(ce)}))
             return { "statusCode": 500, "headers": GET_CORS_HEADERS, "body": json.dumps({"message": "Database error.", "error": str(ce)}) }
        except Exception as e:
            logger.error(json.dumps({**log_context, "status": "error", "error_message": str(e)}))
            return {
                "statusCode": 500,
                "headers": GET_CORS_HEADERS,
                "body": json.dumps({"message": "Failed to retrieve goal transactions.", "error": str(e)})
            }
    else:
         return {
            "statusCode": 405,
            "headers": GET_CORS_HEADERS,
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }