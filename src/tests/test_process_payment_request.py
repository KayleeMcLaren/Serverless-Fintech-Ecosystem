import pytest
import boto3
import os
import json
from decimal import Decimal
from botocore.exceptions import ClientError

# --- 1. Import the universal @mock_aws decorator ---
from moto import mock_aws

# --- 2. Set Environment Variables BEFORE importing the handler ---
MOCK_SNS_ARN = 'arn:aws:sns:us-east-1:123456789012:test-payment-events'
os.environ['DYNAMODB_TABLE_NAME'] = 'test-wallets'
os.environ['TRANSACTIONS_LOG_TABLE_NAME'] = 'test-transaction-logs'
os.environ['SNS_TOPIC_ARN'] = MOCK_SNS_ARN

# Import the handler *after* setting env vars
from process_payment_request.handler import process_payment_request


# --- 3. Mock Fixtures ---

@pytest.fixture(autouse=True) # This fixture sets credentials for ALL tests
def set_mock_aws_credentials(monkeypatch):
    """Mocks AWS credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

@pytest.fixture
def mock_aws_clients():
    with mock_aws():
        """Mocks all AWS clients (DynamoDB and SNS)."""
        # This code now runs *inside* the mock_aws context
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        sns = boto3.client('sns', region_name='us-east-1')

        # Create the mock tables
        dynamodb.create_table(
            TableName=os.environ['DYNAMODB_TABLE_NAME'],
            KeySchema=[{'AttributeName': 'wallet_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'wallet_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        dynamodb.create_table(
            TableName=os.environ['TRANSACTIONS_LOG_TABLE_NAME'],
            KeySchema=[{'AttributeName': 'transaction_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'transaction_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        # Create the mock SNS topic
        sns.create_topic(Name=os.environ['SNS_TOPIC_ARN'].split(':')[-1])

        # The test will run here
        yield dynamodb, sns

        # The mock automatically stops here
    # --- END FIX ----

@pytest.fixture
def mock_sns_event():
    with mock_aws():
        """Creates a mock SNS event payload."""
        def _create_event(event_type, details):
            sns_message_body = {
                "event_type": event_type,
                "details": details if event_type == 'LOAN_REPAYMENT_REQUESTED' else None,
                "transaction_details": details if event_type == 'PAYMENT_REQUESTED' else None
            }
        
            return {
                'Records': [
                    {
                        'Sns': { # The record key is 'Sns', not 'body'
                        'Message': json.dumps(sns_message_body, cls=DecimalEncoder),
                        'MessageAttributes': {
                            'event_type': {
                                'DataType': 'String',
                                'StringValue': event_type
                            }
                        }
                    }
                }
            ]
        }
    return _create_event

# Helper class for Decimal
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal): return str(o)
        return super(DecimalEncoder, self).default(o)


# --- 5. The Test Cases (no changes needed) ---

def test_payment_success(mock_aws_clients, mock_sns_event):
    """
    Tests a successful payment:
    1. Wallet is debited.
    2. A 'PAYMENT_SUCCESSFUL' event is published.
    3. A transaction is logged.
    """
    dynamodb, sns = mock_aws_clients
    
    # ARRANGE
    wallets_table = dynamodb.Table(os.environ['DYNAMODB_TABLE_NAME'])
    log_table = dynamodb.Table(os.environ['TRANSACTIONS_LOG_TABLE_NAME'])
    
    wallets_table.put_item(Item={'wallet_id': 'w_123', 'balance': Decimal('100.00')})
    
    payment_details = {
        'transaction_id': 't_payment_1',
        'wallet_id': 'w_123',
        'merchant_id': 'm_starbucks',
        'amount': Decimal('40.00')
    }
    event = mock_sns_event('PAYMENT_REQUESTED', payment_details)

    # ACT
    response = process_payment_request(event, {})

    # ASSERT
    assert response['statusCode'] == 200
    
    wallet = wallets_table.get_item(Key={'wallet_id': 'w_123'})
    assert wallet['Item']['balance'] == Decimal('60.00') 

    logs = log_table.scan()['Items']
    assert len(logs) == 1
    assert logs[0]['type'] == 'PAYMENT_OUT'
    assert logs[0]['amount'] == Decimal('40.00')
    assert logs[0]['balance_after'] == Decimal('60.00')


def test_payment_insufficient_funds(mock_aws_clients, mock_sns_event):
    """
    Tests a failed payment:
    1. Wallet is NOT debited.
    2. A 'PAYMENT_FAILED' event is published.
    3. NO transaction is logged.
    """
    dynamodb, sns = mock_aws_clients
    
    # ARRANGE
    wallets_table = dynamodb.Table(os.environ['DYNAMODB_TABLE_NAME'])
    log_table = dynamodb.Table(os.environ['TRANSACTIONS_LOG_TABLE_NAME'])
    
    wallets_table.put_item(Item={'wallet_id': 'w_123', 'balance': Decimal('10.00')})
    
    payment_details = {
        'transaction_id': 't_payment_2',
        'wallet_id': 'w_123',
        'merchant_id': 'm_starbucks',
        'amount': Decimal('40.00')
    }
    event = mock_sns_event('PAYMENT_REQUESTED', payment_details)

    # ACT
    response = process_payment_request(event, {})

    # ASSERT
    assert response['statusCode'] == 200
    
    wallet = wallets_table.get_item(Key={'wallet_id': 'w_123'})
    assert wallet['Item']['balance'] == Decimal('10.00') # Unchanged

    logs = log_table.scan()['Items']
    assert len(logs) == 0


def test_loan_repayment_success(mock_aws_clients, mock_sns_event):
    """
    Tests that a 'LOAN_REPAYMENT_REQUESTED' event also works.
    1. Wallet is debited.
    2. A 'LOAN_REPAYMENT_SUCCESSFUL' event is published.
    3. A 'LOAN_REPAYMENT' transaction is logged.
    """
    dynamodb, sns = mock_aws_clients
    
    # ARRANGE
    wallets_table = dynamodb.Table(os.environ['DYNAMODB_TABLE_NAME'])
    log_table = dynamodb.Table(os.environ['TRANSACTIONS_LOG_TABLE_NAME'])
    
    wallets_table.put_item(Item={'wallet_id': 'w_123', 'balance': Decimal('100.00')})
    
    repayment_details = {
        'loan_id': 'l_abc',
        'wallet_id': 'w_123',
        'amount': Decimal('30.00')
    }
    event = mock_sns_event('LOAN_REPAYMENT_REQUESTED', repayment_details)

    # ACT
    response = process_payment_request(event, {})

    # ASSERT
    assert response['statusCode'] == 200
    
    wallet = wallets_table.get_item(Key={'wallet_id': 'w_123'})
    assert wallet['Item']['balance'] == Decimal('70.00') 

    logs = log_table.scan()['Items']
    assert len(logs) == 1
    assert logs[0]['type'] == 'LOAN_REPAYMENT'
    assert logs[0]['amount'] == Decimal('30.00')
    assert logs[0]['balance_after'] == Decimal('70.00')
    assert logs[0]['related_id'] == 'l_abc'