# --- IAM ---
# This section defines all permissions for our Lambda functions.

# --- IAM: LAMBDA EXECUTION ROLE ---
# This is the basic role our Lambda functions will "assume" (use) to run.
# It trusts the Lambda service to use it.
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

# This attaches the basic AWS-managed policy that allows Lambda
# to write logs to CloudWatch.
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# --- IAM: DYNAMODB POLICY ---
# This defines a custom policy that allows our Lambda functions
# to read, write, and update items in our wallet table.
data "aws_iam_policy_document" "dynamodb_wallet_table_policy_doc" {
  statement {
    actions   = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem"]
    resources = [var.dynamodb_table_arn]
  }
}

resource "aws_iam_policy" "dynamodb_wallet_table_policy" {
  name   = "${var.project_name}-wallet-table-policy"
  policy = data.aws_iam_policy_document.dynamodb_wallet_table_policy_doc.json
}

# This attaches our new DynamoDB policy to our main Lambda role.
resource "aws_iam_role_policy_attachment" "dynamodb_wallet_table_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.dynamodb_wallet_table_policy.arn
}

################################################################################
# --- LAMBDA FUNCTIONS (API) ---
# This section defines the serverless functions for our wallet API.
################################################################################

# --- LAMBDA: CREATE WALLET ---
data "archive_file" "create_wallet_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/create_wallet" # Corrected path
  output_path = "${path.module}/create_wallet.zip"
}

resource "aws_lambda_function" "create_wallet_lambda" {
  function_name    = "${var.project_name}-create-wallet"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.create_wallet_zip.output_path
  source_code_hash = data.archive_file.create_wallet_zip.output_base64sha256
  handler          = "handler.create_wallet"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME = var.dynamodb_table_name
    }
  }
}

# --- LAMBDA: GET WALLET ---
data "archive_file" "get_wallet_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/get_wallet" # Corrected path
  output_path = "${path.module}/get_wallet.zip"
}

resource "aws_lambda_function" "get_wallet_lambda" {
  function_name    = "${var.project_name}-get-wallet"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.get_wallet_zip.output_path
  source_code_hash = data.archive_file.get_wallet_zip.output_base64sha256
  handler          = "handler.get_wallet"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME = var.dynamodb_table_name
    }
  }
}

# --- LAMBDA: CREDIT WALLET ---
data "archive_file" "credit_wallet_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/credit_wallet" # FIXED PATH!
  output_path = "${path.module}/credit_wallet.zip"
}

resource "aws_lambda_function" "credit_wallet_lambda" {
  function_name    = "${var.project_name}-credit-wallet"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.credit_wallet_zip.output_path
  source_code_hash = data.archive_file.credit_wallet_zip.output_base64sha256
  handler          = "handler.credit_wallet"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME = var.dynamodb_table_name
    }
  }
}

# --- LAMBDA: DEBIT WALLET ---
data "archive_file" "debit_wallet_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/debit_wallet" # FIXED PATH!
  output_path = "${path.module}/debit_wallet.zip"
}

resource "aws_lambda_function" "debit_wallet_lambda" {
  function_name    = "${var.project_name}-debit-wallet"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.debit_wallet_zip.output_path
  source_code_hash = data.archive_file.debit_wallet_zip.output_base64sha256
  handler          = "handler.debit_wallet"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME = var.dynamodb_table_name
    }
  }
}

################################################################################
# --- LAMBDA FUNCTIONS (EVENT) ---
# This section defines functions triggered by events (e.g., SNS).
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
  tags             = var.tags
  environment {
    variables = {
      # This function updates the wallet table, so it needs the table name
      DYNAMODB_TABLE_NAME = var.dynamodb_table_name
    }
  }
}

# --- SNS SUBSCRIPTION & PERMISSION ---
# We co-locate these with the Lambda they are tied to.
resource "aws_sns_topic_subscription" "loan_approval_subscription" {
  topic_arn = var.sns_topic_arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.process_loan_approval_lambda.arn
}

resource "aws_lambda_permission" "sns_invoke_permission" {
  statement_id  = "AllowSNSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.process_loan_approval_lambda.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = var.sns_topic_arn
}

################################################################################
# --- API GATEWAY ---
# This section defines the HTTP endpoints that trigger our Lambda functions.
################################################################################

# --- API: POST /wallet (CREATE) ---
resource "aws_api_gateway_resource" "wallet_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = var.api_gateway_root_resource_id
  path_part   = "wallet"
}

resource "aws_api_gateway_method" "create_wallet_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.wallet_resource.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "create_lambda_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.wallet_resource.id
  http_method             = aws_api_gateway_method.create_wallet_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.create_wallet_lambda.invoke_arn
}

# --- API: GET /wallet/{wallet_id} (GET) ---
resource "aws_api_gateway_resource" "wallet_id_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.wallet_resource.id
  path_part   = "{wallet_id}"
}

resource "aws_api_gateway_method" "get_wallet_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.wallet_id_resource.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "get_lambda_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.wallet_id_resource.id
  http_method             = aws_api_gateway_method.get_wallet_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.get_wallet_lambda.invoke_arn
}

# --- API: POST /wallet/{wallet_id}/credit (CREDIT) ---
resource "aws_api_gateway_resource" "credit_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.wallet_id_resource.id
  path_part   = "credit"
}

resource "aws_api_gateway_method" "credit_wallet_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.credit_resource.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "credit_lambda_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.credit_resource.id
  http_method             = aws_api_gateway_method.credit_wallet_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.credit_wallet_lambda.invoke_arn
}

# --- API: POST /wallet/{wallet_id}/debit (DEBIT) ---
resource "aws_api_gateway_resource" "debit_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.wallet_id_resource.id
  path_part   = "debit"
}

resource "aws_api_gateway_method" "debit_wallet_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.debit_resource.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "debit_lambda_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.debit_resource.id
  http_method             = aws_api_gateway_method.debit_wallet_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.debit_wallet_lambda.invoke_arn
}


################################################################################
# --- API GATEWAY PERMISSIONS ---
# This section grants API Gateway permission to invoke our API-backed Lambdas.
################################################################################

# --- PERMISSION: CREATE WALLET ---
resource "aws_lambda_permission" "api_gateway_create_permission" {
  statement_id  = "AllowAPIGatewayToInvokeCreate"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.create_wallet_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

# --- PERMISSION: GET WALLET ---
resource "aws_lambda_permission" "api_gateway_get_permission" {
  statement_id  = "AllowAPIGatewayToInvokeGet"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_wallet_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

# --- PERMISSION: CREDIT WALLET ---
resource "aws_lambda_permission" "api_gateway_credit_permission" {
  statement_id  = "AllowAPIGatewayToInvokeCredit"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.credit_wallet_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

# --- PERMISSION: DEBIT WALLET ---
resource "aws_lambda_permission" "api_gateway_debit_permission" {
  statement_id  = "AllowAPIGatewayToInvokeDebit"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.debit_wallet_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}