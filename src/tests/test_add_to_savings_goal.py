import pytest
import boto3
import os
import json
from decimal import Decimal
from moto import mock_aws

# --- 1. Import the Lambda handler we want to test ---
# We must set the environment variables *before* importing the handler
# because the handler creates the Boto3 clients at the global level.
os.environ['SAVINGS_TABLE_NAME'] = 'test-savings-goals'
os.environ['WALLETS_TABLE_NAME'] = 'test-wallets'
os.environ['TRANSACTIONS_LOG_TABLE_NAME'] = 'test-transaction-logs'
os.environ['CORS_ORIGIN'] = '*'

from add_to_savings_goal.handler import add_to_savings_goal


# --- 2. Pytest Fixtures ---
# A "fixture" is a setup function that Pytest runs before a test.

@pytest.fixture
def mock_db():
    """Mocks all DynamoDB interactions."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create the mock tables
        dynamodb.create_table(
            TableName='test-wallets',
            KeySchema=[{'AttributeName': 'wallet_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'wallet_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        dynamodb.create_table(
            TableName='test-savings-goals',
            KeySchema=[{'AttributeName': 'goal_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'goal_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        dynamodb.create_table(
            TableName='test-transaction-logs',
            KeySchema=[{'AttributeName': 'transaction_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'transaction_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        yield dynamodb # Hand control over to the test

# --- 3. The Test Cases ---

def test_add_to_savings_goal_success(mock_db):
    """
    Tests the "happy path" where the user has enough funds.
    """
    # ARRANGE: Set up the database with our initial data
    wallets_table = mock_db.Table(os.environ['WALLETS_TABLE_NAME'])
    savings_table = mock_db.Table(os.environ['SAVINGS_TABLE_NAME'])
    log_table = mock_db.Table(os.environ['TRANSACTIONS_LOG_TABLE_NAME'])

    wallets_table.put_item(Item={
        'wallet_id': 'w_123',
        'balance': Decimal('100.00')
    })
    savings_table.put_item(Item={
        'goal_id': 'g_123',
        'wallet_id': 'w_123', # Must match wallet
        'goal_name': 'Vacation',
        'current_amount': Decimal('50.00'),
        'target_amount': Decimal('500.00')
    })

    # Create a mock API Gateway event
    event = {
        "httpMethod": "POST",
        "pathParameters": {
            "goal_id": "g_123"
        },
        "body": json.dumps({
            "wallet_id": "w_123",
            "amount": "25.50"
        })
    }

    # ACT: Run the Lambda handler
    response = add_to_savings_goal(event, {})

    # ASSERT: Check that everything is correct
    assert response['statusCode'] == 200
    assert "Successfully added" in response['body']

    # 1. Check that the wallet was debited
    wallet = wallets_table.get_item(Key={'wallet_id': 'w_123'})
    assert wallet['Item']['balance'] == Decimal('74.50') # 100.00 - 25.50

    # 2. Check that the savings goal was credited
    goal = savings_table.get_item(Key={'goal_id': 'g_123'})
    assert goal['Item']['current_amount'] == Decimal('75.50') # 50.00 + 25.50

    # 3. Check that the transaction was logged correctly
    logs = log_table.scan()['Items']
    assert len(logs) == 1
    assert logs[0]['type'] == 'SAVINGS_ADD'
    assert logs[0]['amount'] == Decimal('25.50')
    assert logs[0]['related_id'] == 'g_123'
    # This proves our ConsistentRead=True fix is working!
    assert logs[0]['balance_after'] == Decimal('74.50')


def test_add_to_savings_goal_insufficient_funds(mock_db):
    """
    Tests the failure path where the user does not have enough funds.
    """
    # ARRANGE: Set up the database, but with low funds
    wallets_table = mock_db.Table(os.environ['WALLETS_TABLE_NAME'])
    savings_table = mock_db.Table(os.environ['SAVINGS_TABLE_NAME'])
    log_table = mock_db.Table(os.environ['TRANSACTIONS_LOG_TABLE_NAME'])

    wallets_table.put_item(Item={
        'wallet_id': 'w_123',
        'balance': Decimal('10.00') # <-- Only $10
    })
    savings_table.put_item(Item={
        'goal_id': 'g_123',
        'wallet_id': 'w_123',
        'goal_name': 'Vacation',
        'current_amount': Decimal('50.00'),
        'target_amount': Decimal('500.00')
    })
    
    # Event tries to move $25, but wallet only has $10
    event = {
        "httpMethod": "POST",
        "pathParameters": { "goal_id": "g_123" },
        "body": json.dumps({ "wallet_id": "w_123", "amount": "25.00" })
    }

    # ACT: Run the Lambda handler
    response = add_to_savings_goal(event, {})

    # ASSERT: Check that it failed gracefully
    assert response['statusCode'] == 400
    assert "Insufficient funds." in response['body']

    # 1. Check that the wallet balance DID NOT change
    wallet = wallets_table.get_item(Key={'wallet_id': 'w_123'})
    assert wallet['Item']['balance'] == Decimal('10.00')

    # 2. Check that the savings goal balance DID NOT change
    goal = savings_table.get_item(Key={'goal_id': 'g_123'})
    assert goal['Item']['current_amount'] == Decimal('50.00')

    # 3. Check that NO transaction was logged
    logs = log_table.scan()['Items']
    assert len(logs) == 0