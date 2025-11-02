terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

locals {
  # Reusable CORS headers for MOCK integrations
  cors_headers = {
    "Access-Control-Allow-Headers" = "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods" = "OPTIONS,GET,POST,DELETE", # General list
    "Access-Control-Allow-Origin"  = var.frontend_cors_origin, # Use variable
    "Access-Control-Allow-Credentials" = "true"
  }
}

# --- IAM ---
data "aws_iam_policy_document" "lambda_assume_role_policy" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com", "sns.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_exec_role" {
  name               = "${var.project_name}-wallet-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# --- IAM: DynamoDB Policy ---
data "aws_iam_policy_document" "dynamodb_wallet_table_policy_doc" {
  # Statement 1: Permissions for wallet_table
  statement {
    sid = "WalletTableAccess"
    actions   = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem"]
    resources = [var.dynamodb_table_arn]
  }
  # Statement 2: Permissions for transaction_logs_table
  statement {
    sid = "TransactionLogAccess"
    actions = [
      "dynamodb:PutItem", # For logging new transactions
      "dynamodb:Query"    # For getting history
    ]
    resources = [
      var.transactions_log_table_arn,
      "${var.transactions_log_table_arn}/index/*" # Access the GSIs
    ]
  }
}

resource "aws_iam_policy" "dynamodb_wallet_table_policy" {
  name   = "${var.project_name}-wallet-table-policy"
  policy = data.aws_iam_policy_document.dynamodb_wallet_table_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "dynamodb_wallet_table_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.dynamodb_wallet_table_policy.arn
}

# --- IAM: SNS PUBLISH POLICY (PAYMENTS) ---
data "aws_iam_policy_document" "sns_payment_publish_policy_doc" {
  statement {
    actions   = ["sns:Publish"]
    resources = [var.payment_sns_topic_arn]
  }
}

resource "aws_iam_policy" "sns_payment_publish_policy" {
  name   = "${var.project_name}-wallet-payment-sns-publish-policy"
  policy = data.aws_iam_policy_document.sns_payment_publish_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "sns_payment_publish_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.sns_payment_publish_policy.arn
}

################################################################################
# --- LAMBDA FUNCTIONS (API) ---
################################################################################

# --- LAMBDA: CREATE WALLET ---
# This Lambda is now private, only invoked by the Step Function
# No archive_file or aws_lambda_function resource is needed here anymore
# We will create it in the digital_wallet module as it's still a core part of it.
data "archive_file" "create_wallet_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/create_wallet"
  output_path = "${path.module}/create_wallet.zip"
}
resource "aws_lambda_function" "create_wallet_lambda" {
  function_name    = "${var.project_name}-create-wallet"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.create_wallet_zip.output_path
  source_code_hash = data.archive_file.create_wallet_zip.output_base64sha256
  handler          = "handler.create_wallet"
  runtime          = "python3.12"
  timeout          = 10
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME           = var.dynamodb_table_name
      TRANSACTIONS_LOG_TABLE_NAME = var.transactions_log_table_name
      CORS_ORIGIN                   = var.frontend_cors_origin
    }
  }
}

# --- LAMBDA: GET WALLET ---
data "archive_file" "get_wallet_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/get_wallet"
  output_path = "${path.module}/get_wallet.zip"
}
resource "aws_lambda_function" "get_wallet_lambda" {
  function_name    = "${var.project_name}-get-wallet"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.get_wallet_zip.output_path
  source_code_hash = data.archive_file.get_wallet_zip.output_base64sha256
  handler          = "handler.get_wallet"
  runtime          = "python3.12"
  timeout          = 10
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME = var.dynamodb_table_name
      CORS_ORIGIN         = var.frontend_cors_origin
      REDEPLOY_TRIGGER    = sha1(var.frontend_cors_origin)
    }
  }
}

# --- LAMBDA: CREDIT WALLET ---
data "archive_file" "credit_wallet_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/credit_wallet"
  output_path = "${path.module}/credit_wallet.zip"
}
resource "aws_lambda_function" "credit_wallet_lambda" {
  function_name    = "${var.project_name}-credit-wallet"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.credit_wallet_zip.output_path
  source_code_hash = data.archive_file.credit_wallet_zip.output_base64sha256
  handler          = "handler.credit_wallet"
  runtime          = "python3.12"
  timeout          = 10
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME           = var.dynamodb_table_name
      TRANSACTIONS_LOG_TABLE_NAME = var.transactions_log_table_name
      CORS_ORIGIN                   = var.frontend_cors_origin
    }
  }
}

# --- LAMBDA: DEBIT WALLET ---
data "archive_file" "debit_wallet_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/debit_wallet"
  output_path = "${path.module}/debit_wallet.zip"
}
resource "aws_lambda_function" "debit_wallet_lambda" {
  function_name    = "${var.project_name}-debit-wallet"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.debit_wallet_zip.output_path
  source_code_hash = data.archive_file.debit_wallet_zip.output_base64sha256
  handler          = "handler.debit_wallet"
  runtime          = "python3.12"
  timeout          = 10
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME           = var.dynamodb_table_name
      TRANSACTIONS_LOG_TABLE_NAME = var.transactions_log_table_name
      CORS_ORIGIN                   = var.frontend_cors_origin
    }
  }
}

# --- LAMBDA: GET WALLET TRANSACTIONS ---
data "archive_file" "get_wallet_transactions_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/get_wallet_transactions"
  output_path = "${path.module}/get_wallet_transactions.zip"
}
resource "aws_lambda_function" "get_wallet_transactions_lambda" {
  function_name    = "${var.project_name}-get-wallet-transactions"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.get_wallet_transactions_zip.output_path
  source_code_hash = data.archive_file.get_wallet_transactions_zip.output_base64sha256
  handler          = "handler.get_wallet_transactions"
  runtime          = "python3.12"
  timeout          = 10
  tags             = var.tags
  environment {
    variables = {
      TRANSACTIONS_LOG_TABLE_NAME = var.transactions_log_table_name
      CORS_ORIGIN                   = var.frontend_cors_origin
      REDEPLOY_TRIGGER    = sha1(var.frontend_cors_origin)
    }
  }
}

################################################################################
# --- LAMBDA FUNCTIONS (EVENT) ---
################################################################################

# --- LAMBDA: PROCESS LOAN APPROVAL (SNS SUBSCRIBER) ---
data "archive_file" "process_loan_approval_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/process_loan_approval"
  output_path = "${path.module}/process_loan_approval.zip"
}
resource "aws_lambda_function" "process_loan_approval_lambda" {
  function_name    = "${var.project_name}-process-loan-approval"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.process_loan_approval_zip.output_path
  source_code_hash = data.archive_file.process_loan_approval_zip.output_base64sha256
  handler          = "handler.process_loan_approval"
  runtime          = "python3.12"
  timeout          = 10
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME           = var.dynamodb_table_name
      TRANSACTIONS_LOG_TABLE_NAME = var.transactions_log_table_name
    }
  }
}

# --- LAMBDA: PROCESS PAYMENT REQUEST (SNS SUBSCRIBER) ---
data "archive_file" "process_payment_request_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/process_payment_request"
  output_path = "${path.module}/process_payment_request.zip"
}
resource "aws_lambda_function" "process_payment_request_lambda" {
  function_name    = "${var.project_name}-process-payment-request"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.process_payment_request_zip.output_path
  source_code_hash = data.archive_file.process_payment_request_zip.output_base64sha256
  handler          = "handler.process_payment_request"
  runtime          = "python3.12"
  timeout          = 10
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME           = var.dynamodb_table_name
      TRANSACTIONS_LOG_TABLE_NAME = var.transactions_log_table_name
      SNS_TOPIC_ARN                 = var.payment_sns_topic_arn
    }
  }
}

################################################################################
# --- API GATEWAY ---
################################################################################

# --- API: /wallet ---
resource "aws_api_gateway_resource" "wallet_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = var.api_gateway_root_resource_id
  path_part   = "wallet"
}

# Note: The POST /wallet (Create) endpoint has been removed.
# It is now only invoked by the Step Function.

# --- API: /wallet/{wallet_id} ---
resource "aws_api_gateway_resource" "wallet_id_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.wallet_resource.id
  path_part   = "{wallet_id}"
}

# --- API: GET /wallet/{wallet_id} ---
resource "aws_api_gateway_method" "get_wallet_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.wallet_id_resource.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = var.api_gateway_authorizer_id
}
resource "aws_api_gateway_integration" "get_lambda_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.wallet_id_resource.id
  http_method             = aws_api_gateway_method.get_wallet_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.get_wallet_lambda.invoke_arn
}

# --- NEW: (OPTIONS for GET /wallet/{id}) ---
resource "aws_api_gateway_method" "get_wallet_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.wallet_id_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}
resource "aws_api_gateway_method_response" "get_wallet_options_200" {
   rest_api_id   = var.api_gateway_id
   resource_id   = aws_api_gateway_resource.wallet_id_resource.id
   http_method   = aws_api_gateway_method.get_wallet_options_method.http_method
   status_code   = "200"
   response_models = { "application/json" = "Empty" }
   response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => true }
}
resource "aws_api_gateway_integration" "get_wallet_options_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id           = aws_api_gateway_resource.wallet_id_resource.id
  http_method             = aws_api_gateway_method.get_wallet_options_method.http_method
  type                    = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}
resource "aws_api_gateway_integration_response" "get_wallet_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.wallet_id_resource.id
  http_method = aws_api_gateway_method.get_wallet_options_method.http_method
  status_code = aws_api_gateway_method_response.get_wallet_options_200.status_code
  response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => "'${v}'" }
  response_templates = { "application/json" = "" }
  depends_on = [aws_api_gateway_integration.get_wallet_options_integration]
}
# --- END NEW BLOCK ---

# --- API: /wallet/{wallet_id}/credit ---
resource "aws_api_gateway_resource" "credit_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.wallet_id_resource.id
  path_part   = "credit"
}

# --- API: POST /wallet/{wallet_id}/credit ---
resource "aws_api_gateway_method" "credit_wallet_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.credit_resource.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = var.api_gateway_authorizer_id
}
resource "aws_api_gateway_integration" "credit_lambda_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.credit_resource.id
  http_method             = aws_api_gateway_method.credit_wallet_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.credit_wallet_lambda.invoke_arn
}

# --- API: OPTIONS /wallet/{wallet_id}/credit (CORS) ---
resource "aws_api_gateway_method" "credit_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.credit_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}
resource "aws_api_gateway_method_response" "credit_options_200" {
   rest_api_id   = var.api_gateway_id
   resource_id   = aws_api_gateway_resource.credit_resource.id
   http_method   = aws_api_gateway_method.credit_options_method.http_method
   status_code   = "200"
   response_models = { "application/json" = "Empty" }
   response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => true }
}
resource "aws_api_gateway_integration" "credit_options_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id           = aws_api_gateway_resource.credit_resource.id
  http_method             = aws_api_gateway_method.credit_options_method.http_method
  type                    = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}
resource "aws_api_gateway_integration_response" "credit_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.credit_resource.id
  http_method = aws_api_gateway_method.credit_options_method.http_method
  status_code = aws_api_gateway_method_response.credit_options_200.status_code
  response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => "'${v}'" }
  response_templates = { "application/json" = "" }
  depends_on = [aws_api_gateway_integration.credit_options_integration]
}


# --- API: /wallet/{wallet_id}/debit ---
resource "aws_api_gateway_resource" "debit_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.wallet_id_resource.id
  path_part   = "debit"
}

# --- API: POST /wallet/{wallet_id}/debit ---
resource "aws_api_gateway_method" "debit_wallet_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.debit_resource.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = var.api_gateway_authorizer_id
}
resource "aws_api_gateway_integration" "debit_lambda_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.debit_resource.id
  http_method             = aws_api_gateway_method.debit_wallet_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.debit_wallet_lambda.invoke_arn
}

# --- API: OPTIONS /wallet/{wallet_id}/debit (CORS) ---
resource "aws_api_gateway_method" "debit_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.debit_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}
resource "aws_api_gateway_method_response" "debit_options_200" {
   rest_api_id   = var.api_gateway_id
   resource_id   = aws_api_gateway_resource.debit_resource.id
   http_method   = aws_api_gateway_method.debit_options_method.http_method
   status_code   = "200"
   response_models = { "application/json" = "Empty" }
   response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => true }
}
resource "aws_api_gateway_integration" "debit_options_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id           = aws_api_gateway_resource.debit_resource.id
  http_method             = aws_api_gateway_method.debit_options_method.http_method
  type                    = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}
resource "aws_api_gateway_integration_response" "debit_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.debit_resource.id
  http_method = aws_api_gateway_method.debit_options_method.http_method
  status_code = aws_api_gateway_method_response.debit_options_200.status_code
  response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => "'${v}'" }
  response_templates = { "application/json" = "" }
  depends_on = [aws_api_gateway_integration.debit_options_integration]
}


# --- API: /wallet/{wallet_id}/transactions ---
resource "aws_api_gateway_resource" "transactions_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.wallet_id_resource.id
  path_part   = "transactions"
}

# --- API: GET /wallet/{wallet_id}/transactions ---
resource "aws_api_gateway_method" "get_transactions_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.transactions_resource.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = var.api_gateway_authorizer_id
}
resource "aws_api_gateway_integration" "get_transactions_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.transactions_resource.id
  http_method             = aws_api_gateway_method.get_transactions_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.get_wallet_transactions_lambda.invoke_arn
}

# --- NEW: (OPTIONS for GET /wallet/{id}/transactions) ---
resource "aws_api_gateway_method" "get_transactions_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.transactions_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}
resource "aws_api_gateway_method_response" "get_transactions_options_200" {
   rest_api_id   = var.api_gateway_id
   resource_id   = aws_api_gateway_resource.transactions_resource.id
   http_method   = aws_api_gateway_method.get_transactions_options_method.http_method
   status_code   = "200"
   response_models = { "application/json" = "Empty" }
   response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => true }
}
resource "aws_api_gateway_integration" "get_transactions_options_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id           = aws_api_gateway_resource.transactions_resource.id
  http_method             = aws_api_gateway_method.get_transactions_options_method.http_method
  type                    = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}
resource "aws_api_gateway_integration_response" "get_transactions_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.transactions_resource.id
  http_method = aws_api_gateway_method.get_transactions_options_method.http_method
  status_code = aws_api_gateway_method_response.get_transactions_options_200.status_code
  response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => "'${v}'" }
  response_templates = { "application/json" = "" }
  depends_on = [aws_api_gateway_integration.get_transactions_options_integration]
}
# --- END NEW BLOCK ---


################################################################################
# --- LAMBDA PERMISSIONS (API Gateway) ---
################################################################################

# (api_gateway_create_permission was removed)

resource "aws_lambda_permission" "api_gateway_get_permission" {
  statement_id  = "AllowAPIGatewayToInvokeGet"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_wallet_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_credit_permission" {
  statement_id  = "AllowAPIGatewayToInvokeCredit"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.credit_wallet_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_debit_permission" {
  statement_id  = "AllowAPIGatewayToInvokeDebit"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.debit_wallet_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_get_transactions_permission" {
  statement_id  = "AllowAPIGatewayToInvokeGetTransactions"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_wallet_transactions_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

################################################################################
# --- SNS SUBSCRIPTIONS & PERMISSIONS ---
################################################################################

# --- SNS: LOAN APPROVAL (Subscriber) ---
resource "aws_sns_topic_subscription" "loan_approval_subscription" {
  topic_arn = var.sns_topic_arn # loan_events topic
  protocol  = "lambda"
  endpoint  = aws_lambda_function.process_loan_approval_lambda.arn
}
resource "aws_lambda_permission" "sns_invoke_permission" {
  statement_id  = "AllowSNSInvokeLoanApproval"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.process_loan_approval_lambda.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = var.sns_topic_arn
}

# --- SNS: PAYMENT REQUEST (Subscriber) ---
resource "aws_sns_topic_subscription" "payment_request_subscription" {
  topic_arn = var.payment_sns_topic_arn # payment_events topic
  protocol  = "lambda"
  endpoint  = aws_lambda_function.process_payment_request_lambda.arn
  filter_policy = jsonencode({
    "event_type": ["PAYMENT_REQUESTED", "LOAN_REPAYMENT_REQUESTED"]
  })
}
resource "aws_lambda_permission" "sns_payment_invoke_permission" {
  statement_id  = "AllowSNSPaymentInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.process_payment_request_lambda.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = var.payment_sns_topic_arn
}