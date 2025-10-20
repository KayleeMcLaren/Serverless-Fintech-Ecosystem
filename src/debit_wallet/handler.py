import json
import os
import boto3
from decimal import Decimal
from urllib.parse import unquote
from botocore.exceptions import ClientError

# Get the table name from an environment variable
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

# Define allowed origin
ALLOWED_ORIGIN = "http://localhost:5173"

# Define CORS headers for OPTIONS response
OPTIONS_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token",
    "Access-Control-Allow-Credentials": True
}

# Define CORS headers for POST response
POST_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Credentials": True
}

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert a DynamoDB item to JSON."""
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def debit_wallet(event, context):
    """Debits a specified amount from a wallet's balance. Handles OPTIONS preflight."""

    # --- ADD THIS BLOCK ---
    # Handle CORS preflight (OPTIONS) request
    http_method = event.get('httpMethod', '').upper()
    if http_method == 'OPTIONS':
        print("Handling OPTIONS request")
        return {
            "statusCode": 200,
            "headers": OPTIONS_CORS_HEADERS,
            "body": "" # Empty body for OPTIONS
        }
    # ----------------------

    # If not OPTIONS, proceed with POST logic
    if http_method == 'POST':
      print("Handling POST request")
      try:
          # Get wallet_id from the URL path
          wallet_id = unquote(event['pathParameters']['wallet_id']).strip()

          # Get amount from the request body
          body = json.loads(event.get('body', '{}'))
          amount = Decimal(body.get('amount', '0.00'))

          if amount <= 0:
              return {
                  "statusCode": 400,
                  "headers": POST_CORS_HEADERS, # Use POST headers
                  "body": json.dumps({"message": "Amount must be positive."})
              }

          # Use update_item with a ConditionExpression to prevent overdrafts
          response = table.update_item(
              Key={'wallet_id': wallet_id},
              UpdateExpression="SET balance = balance - :amount",
              ConditionExpression="balance >= :amount", # Prevent overdraft
              ExpressionAttributeValues={
                  ':amount': amount
              },
              ReturnValues="UPDATED_NEW"
          )

          return {
              "statusCode": 200,
              "headers": POST_CORS_HEADERS, # Use POST headers
              "body": json.dumps(response['Attributes'], cls=DecimalEncoder)
          }

      except ClientError as e:
          # This error is raised if the ConditionExpression fails
          if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
              return {
                  "statusCode": 400, # Bad Request (client error - insufficient funds)
                  "headers": POST_CORS_HEADERS, # Use POST headers
                  "body": json.dumps({"message": "Insufficient funds."})
              }
          else:
              # Re-raise other DynamoDB client errors
              print(f"DynamoDB ClientError: {e}")
              return {
                  "statusCode": 500,
                  "headers": POST_CORS_HEADERS, # Use POST headers
                  "body": json.dumps({"message": "Failed to debit wallet due to database error.", "error": str(e)})
              }
      except Exception as e:
          # Handle other unexpected errors
          print(f"Unexpected Error: {e}")
          return {
              "statusCode": 500,
              "headers": POST_CORS_HEADERS, # Use POST headers
              "body": json.dumps({"message": "Failed to debit wallet.", "error": str(e)})
          }
    else:
        # Handle unsupported methods
        print(f"Unsupported method: {http_method}")
        return {
            "statusCode": 405, # Method Not Allowed
            "headers": POST_CORS_HEADERS, # Still include CORS for error
            "body": json.dumps({"message": f"Method {http_method} not allowed."})
        }