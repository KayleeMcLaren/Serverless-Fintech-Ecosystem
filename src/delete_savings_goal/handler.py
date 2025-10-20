import json
import os
import boto3
from urllib.parse import unquote
from botocore.exceptions import ClientError # Import ClientError

# --- CORS Configuration ---
ALLOWED_ORIGIN = "http://localhost:5173"
OPTIONS_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "DELETE, OPTIONS", # Allow DELETE
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Credentials": True
}
DELETE_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Credentials": True
}
# --- End CORS Configuration ---

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def delete_savings_goal(event, context):
    """Deletes a savings goal. Handles OPTIONS preflight."""

    # --- CORS Preflight Check ---
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request for delete_savings_goal")
        return {
            "statusCode": 200,
            "headers": OPTIONS_CORS_HEADERS,
            "body": ""
        }
    # --- End CORS Preflight Check ---

    # --- DELETE Logic ---
    if http_method == 'DELETE':
        print("Handling DELETE request for delete_savings_goal")
        try:
            goal_id = unquote(event['pathParameters']['goal_id']).strip()
            print(f"Attempting to delete goal_id: {goal_id}")

            # Optional: Add a condition to ensure the item exists before deleting
            # response = table.delete_item(
            #     Key={'goal_id': goal_id},
            #     ConditionExpression="attribute_exists(goal_id)"
            # )
            # If the condition fails, it raises a ClientError

            table.delete_item(
                Key={'goal_id': goal_id}
            )
            print(f"Successfully deleted goal_id: {goal_id}")

            return {
                "statusCode": 200,
                "headers": DELETE_CORS_HEADERS,
                "body": json.dumps({"message": "Savings goal deleted successfully."})
            }
        except ClientError as ce:
             # Handle potential ConditionCheckFailedException if you added the condition
             print(f"DynamoDB ClientError deleting goal: {ce}")
             status_code = 404 if ce.response['Error']['Code'] == 'ConditionalCheckFailedException' else 500
             error_message = "Goal not found." if status_code == 404 else "Database error during deletion."
             return {
                "statusCode": status_code,
                "headers": DELETE_CORS_HEADERS,
                "body": json.dumps({"message": error_message, "error": str(ce)})
            }
        except Exception as e:
            print(f"Error deleting savings goal: {e}")
            return {
                "statusCode": 500,
                "headers": DELETE_CORS_HEADERS,
                "body": json.dumps({"message": "Failed to delete savings goal.", "error": str(e)})
            }
    else:
        # Handle unsupported methods
        print(f"Unsupported method: {http_method}")
        return {
            "statusCode": 405, # Method Not Allowed
            "headers": DELETE_CORS_HEADERS,
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }