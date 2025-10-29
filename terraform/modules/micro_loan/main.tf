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
  name               = "${var.project_name}-loan-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# --- IAM: DynamoDB Policy ---
data "aws_iam_policy_document" "dynamodb_loans_table_policy_doc" {
  statement {
    sid = "LoanTableAccess"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:UpdateItem"
    ]
    resources = [
      var.dynamodb_table_arn,
      "${var.dynamodb_table_arn}/index/*"
    ]
  }
  statement {
    sid       = "TransactionLogWriteAccess"
    actions   = ["dynamodb:PutItem"] # For logging repayments
    resources = [var.transactions_log_table_arn]
  }
}
resource "aws_iam_policy" "dynamodb_loans_table_policy" {
  name   = "${var.project_name}-loans-table-policy"
  policy = data.aws_iam_policy_document.dynamodb_loans_table_policy_doc.json
}
resource "aws_iam_role_policy_attachment" "dynamodb_loans_table_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.dynamodb_loans_table_policy.arn
}

# --- IAM: SNS Publish Policies ---
# Policy for loan_events topic
data "aws_iam_policy_document" "sns_loan_publish_policy_doc" {
  statement {
    actions   = ["sns:Publish"]
    resources = [var.sns_topic_arn] # loan_events topic
  }
}
resource "aws_iam_policy" "sns_loan_publish_policy" {
  name   = "${var.project_name}-sns-loan-publish-policy"
  policy = data.aws_iam_policy_document.sns_loan_publish_policy_doc.json
}
resource "aws_iam_role_policy_attachment" "sns_loan_publish_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.sns_loan_publish_policy.arn
}

# Policy for payment_events topic
data "aws_iam_policy_document" "sns_payment_publish_policy_doc" {
  statement {
    actions   = ["sns:Publish"]
    resources = [var.payment_sns_topic_arn] # payment_events topic
  }
}
resource "aws_iam_policy" "sns_payment_publish_policy" {
  name   = "${var.project_name}-loan-sns-payment-publish-policy" # Made name unique
  policy = data.aws_iam_policy_document.sns_payment_publish_policy_doc.json
}
resource "aws_iam_role_policy_attachment" "sns_payment_publish_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.sns_payment_publish_policy.arn
}

################################################################################
# --- LAMBDA FUNCTIONS (API) ---
################################################################################

# --- LAMBDA: APPLY FOR LOAN ---
data "archive_file" "apply_for_loan_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/apply_for_loan"
  output_path = "${path.module}/apply_for_loan.zip"
}
resource "aws_lambda_function" "apply_for_loan_lambda" {
  function_name    = "${var.project_name}-apply-for-loan"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.apply_for_loan_zip.output_path
  source_code_hash = data.archive_file.apply_for_loan_zip.output_base64sha256
  handler          = "handler.apply_for_loan"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME = var.dynamodb_table_name
      CORS_ORIGIN         = var.frontend_cors_origin
      REDEPLOY_TRIGGER = sha1(var.frontend_cors_origin)
    }
  }
}

# --- LAMBDA: GET LOAN ---
data "archive_file" "get_loan_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/get_loan"
  output_path = "${path.module}/get_loan.zip"
}
resource "aws_lambda_function" "get_loan_lambda" {
  function_name    = "${var.project_name}-get-loan"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.get_loan_zip.output_path
  source_code_hash = data.archive_file.get_loan_zip.output_base64sha256
  handler          = "handler.get_loan"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME = var.dynamodb_table_name
      CORS_ORIGIN         = var.frontend_cors_origin
      REDEPLOY_TRIGGER = sha1(var.frontend_cors_origin)
    }
  }
}

# --- LAMBDA: GET LOANS BY WALLET ---
data "archive_file" "get_loans_by_wallet_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/get_loans_by_wallet"
  output_path = "${path.module}/get_loans_by_wallet.zip"
}
resource "aws_lambda_function" "get_loans_by_wallet_lambda" {
  function_name    = "${var.project_name}-get-loans-by-wallet"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.get_loans_by_wallet_zip.output_path
  source_code_hash = data.archive_file.get_loans_by_wallet_zip.output_base64sha256
  handler          = "handler.get_loans_by_wallet"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME = var.dynamodb_table_name
      CORS_ORIGIN         = var.frontend_cors_origin
      REDEPLOY_TRIGGER = sha1(var.frontend_cors_origin)
    }
  }
}

# --- LAMBDA: APPROVE LOAN ---
data "archive_file" "approve_loan_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/approve_loan"
  output_path = "${path.module}/approve_loan.zip"
}
resource "aws_lambda_function" "approve_loan_lambda" {
  function_name    = "${var.project_name}-approve-loan"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.approve_loan_zip.output_path
  source_code_hash = data.archive_file.approve_loan_zip.output_base64sha256
  handler          = "handler.approve_loan"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME = var.dynamodb_table_name
      SNS_TOPIC_ARN       = var.sns_topic_arn
      CORS_ORIGIN         = var.frontend_cors_origin
      REDEPLOY_TRIGGER = sha1(var.frontend_cors_origin)
    }
  }
}

# --- LAMBDA: REJECT LOAN ---
data "archive_file" "reject_loan_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/reject_loan"
  output_path = "${path.module}/reject_loan.zip"
}
resource "aws_lambda_function" "reject_loan_lambda" {
  function_name    = "${var.project_name}-reject-loan"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.reject_loan_zip.output_path
  source_code_hash = data.archive_file.reject_loan_zip.output_base64sha256
  handler          = "handler.reject_loan"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME = var.dynamodb_table_name
      CORS_ORIGIN         = var.frontend_cors_origin
      REDEPLOY_TRIGGER = sha1(var.frontend_cors_origin)
    }
  }
}

# --- LAMBDA: REPAY LOAN ---
data "archive_file" "repay_loan_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/repay_loan"
  output_path = "${path.module}/repay_loan.zip"
}
resource "aws_lambda_function" "repay_loan_lambda" {
  function_name    = "${var.project_name}-repay-loan"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.repay_loan_zip.output_path
  source_code_hash = data.archive_file.repay_loan_zip.output_base64sha256
  handler          = "handler.repay_loan"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME = var.dynamodb_table_name
      SNS_TOPIC_ARN       = var.payment_sns_topic_arn # Publishes to payment_events
      CORS_ORIGIN         = var.frontend_cors_origin
      REDEPLOY_TRIGGER = sha1(var.frontend_cors_origin)
    }
  }
}

################################################################################
# --- LAMBDA FUNCTIONS (EVENT) ---
################################################################################

# --- LAMBDA: UPDATE LOAN REPAYMENT STATUS ---
data "archive_file" "update_loan_repayment_status_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/update_loan_repayment_status"
  output_path = "${path.module}/update_loan_repayment_status.zip"
}
resource "aws_lambda_function" "update_loan_repayment_status_lambda" {
  function_name    = "${var.project_name}-update-loan-repayment-status"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.update_loan_repayment_status_zip.output_path
  source_code_hash = data.archive_file.update_loan_repayment_status_zip.output_base64sha256
  handler          = "handler.update_loan_repayment_status"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      LOANS_TABLE_NAME            = var.dynamodb_table_name
      TRANSACTIONS_LOG_TABLE_NAME = var.transactions_log_table_name
    }
  }
}

################################################################################
# --- API GATEWAY ---
################################################################################

# --- API: /loan ---
resource "aws_api_gateway_resource" "loan_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = var.api_gateway_root_resource_id
  path_part   = "loan"
}

# --- API: POST /loan (Apply) ---
resource "aws_api_gateway_method" "apply_for_loan_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.loan_resource.id
  http_method   = "POST"
  authorization = "NONE"
}
resource "aws_api_gateway_integration" "apply_for_loan_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.loan_resource.id
  http_method             = aws_api_gateway_method.apply_for_loan_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.apply_for_loan_lambda.invoke_arn
}

# --- API: OPTIONS /loan (CORS) ---
resource "aws_api_gateway_method" "apply_for_loan_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.loan_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}
resource "aws_api_gateway_method_response" "apply_for_loan_options_200" {
   rest_api_id   = var.api_gateway_id
   resource_id   = aws_api_gateway_resource.loan_resource.id
   http_method   = aws_api_gateway_method.apply_for_loan_options_method.http_method
   status_code   = "200"
   response_models = { "application/json" = "Empty" }
   response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => true }
}
resource "aws_api_gateway_integration" "apply_for_loan_options_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id           = aws_api_gateway_resource.loan_resource.id
  http_method             = aws_api_gateway_method.apply_for_loan_options_method.http_method
  type                    = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}
resource "aws_api_gateway_integration_response" "apply_for_loan_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.loan_resource.id
  http_method = aws_api_gateway_method.apply_for_loan_options_method.http_method
  status_code = aws_api_gateway_method_response.apply_for_loan_options_200.status_code
  response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => "'${v}'" }
  response_templates = { "application/json" = "" }
  depends_on = [aws_api_gateway_integration.apply_for_loan_options_integration]
}

# --- API: /loan/by-wallet/{wallet_id} ---
resource "aws_api_gateway_resource" "loan_by_wallet_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.loan_resource.id
  path_part   = "by-wallet"
}
resource "aws_api_gateway_resource" "loan_by_wallet_id_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.loan_by_wallet_resource.id
  path_part   = "{wallet_id}"
}

# --- API: GET /loan/by-wallet/{wallet_id} ---
resource "aws_api_gateway_method" "get_loans_by_wallet_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.loan_by_wallet_id_resource.id
  http_method   = "GET"
  authorization = "NONE"
}
resource "aws_api_gateway_integration" "get_loans_by_wallet_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.loan_by_wallet_id_resource.id
  http_method             = aws_api_gateway_method.get_loans_by_wallet_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.get_loans_by_wallet_lambda.invoke_arn
}
# (Skipping OPTIONS for simple GET)

# --- API: /loan/{loan_id} ---
resource "aws_api_gateway_resource" "loan_id_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.loan_resource.id
  path_part   = "{loan_id}"
}

# --- API: GET /loan/{loan_id} ---
resource "aws_api_gateway_method" "get_loan_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.loan_id_resource.id
  http_method   = "GET"
  authorization = "NONE"
}
resource "aws_api_gateway_integration" "get_loan_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.loan_id_resource.id
  http_method             = aws_api_gateway_method.get_loan_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.get_loan_lambda.invoke_arn
}
# (Skipping OPTIONS for simple GET)

# --- API: /loan/{loan_id}/approve ---
resource "aws_api_gateway_resource" "approve_loan_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.loan_id_resource.id
  path_part   = "approve"
}

# --- API: POST /loan/{loan_id}/approve ---
resource "aws_api_gateway_method" "approve_loan_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.approve_loan_resource.id
  http_method   = "POST"
  authorization = "NONE"
}
resource "aws_api_gateway_integration" "approve_loan_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.approve_loan_resource.id
  http_method             = aws_api_gateway_method.approve_loan_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.approve_loan_lambda.invoke_arn
}

# --- API: OPTIONS /loan/{loan_id}/approve (CORS) ---
resource "aws_api_gateway_method" "approve_loan_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.approve_loan_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}
resource "aws_api_gateway_method_response" "approve_loan_options_200" {
   rest_api_id   = var.api_gateway_id
   resource_id   = aws_api_gateway_resource.approve_loan_resource.id
   http_method   = aws_api_gateway_method.approve_loan_options_method.http_method
   status_code   = "200"
   response_models = { "application/json" = "Empty" }
   response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => true }
}
resource "aws_api_gateway_integration" "approve_loan_options_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id           = aws_api_gateway_resource.approve_loan_resource.id
  http_method             = aws_api_gateway_method.approve_loan_options_method.http_method
  type                    = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}
resource "aws_api_gateway_integration_response" "approve_loan_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.approve_loan_resource.id
  http_method = aws_api_gateway_method.approve_loan_options_method.http_method
  status_code = aws_api_gateway_method_response.approve_loan_options_200.status_code
  response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => "'${v}'" }
  response_templates = { "application/json" = "" }
  depends_on = [aws_api_gateway_integration.approve_loan_options_integration]
}

# --- API: /loan/{loan_id}/reject ---
resource "aws_api_gateway_resource" "reject_loan_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.loan_id_resource.id
  path_part   = "reject"
}

# --- API: POST /loan/{loan_id}/reject ---
resource "aws_api_gateway_method" "reject_loan_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.reject_loan_resource.id
  http_method   = "POST"
  authorization = "NONE"
}
resource "aws_api_gateway_integration" "reject_loan_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.reject_loan_resource.id
  http_method             = aws_api_gateway_method.reject_loan_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.reject_loan_lambda.invoke_arn
}

# --- API: OPTIONS /loan/{loan_id}/reject (CORS) ---
resource "aws_api_gateway_method" "reject_loan_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.reject_loan_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}
resource "aws_api_gateway_method_response" "reject_loan_options_200" {
   rest_api_id   = var.api_gateway_id
   resource_id   = aws_api_gateway_resource.reject_loan_resource.id
   http_method   = aws_api_gateway_method.reject_loan_options_method.http_method
   status_code   = "200"
   response_models = { "application/json" = "Empty" }
   response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => true }
}
resource "aws_api_gateway_integration" "reject_loan_options_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id           = aws_api_gateway_resource.reject_loan_resource.id
  http_method             = aws_api_gateway_method.reject_loan_options_method.http_method
  type                    = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}
resource "aws_api_gateway_integration_response" "reject_loan_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.reject_loan_resource.id
  http_method = aws_api_gateway_method.reject_loan_options_method.http_method
  status_code = aws_api_gateway_method_response.reject_loan_options_200.status_code
  response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => "'${v}'" }
  response_templates = { "application/json" = "" }
  depends_on = [aws_api_gateway_integration.reject_loan_options_integration]
}

# --- API: /loan/{loan_id}/repay ---
resource "aws_api_gateway_resource" "repay_loan_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.loan_id_resource.id
  path_part   = "repay"
}

# --- API: POST /loan/{loan_id}/repay ---
resource "aws_api_gateway_method" "repay_loan_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.repay_loan_resource.id
  http_method   = "POST"
  authorization = "NONE"
}
resource "aws_api_gateway_integration" "repay_loan_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.repay_loan_resource.id
  http_method             = aws_api_gateway_method.repay_loan_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.repay_loan_lambda.invoke_arn
}

# --- API: OPTIONS /loan/{loan_id}/repay (CORS) ---
resource "aws_api_gateway_method" "repay_loan_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.repay_loan_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}
resource "aws_api_gateway_method_response" "repay_loan_options_200" {
   rest_api_id   = var.api_gateway_id
   resource_id   = aws_api_gateway_resource.repay_loan_resource.id
   http_method   = aws_api_gateway_method.repay_loan_options_method.http_method
   status_code   = "200"
   response_models = { "application/json" = "Empty" }
   response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => true }
}
resource "aws_api_gateway_integration" "repay_loan_options_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id           = aws_api_gateway_resource.repay_loan_resource.id
  http_method             = aws_api_gateway_method.repay_loan_options_method.http_method
  type                    = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}
resource "aws_api_gateway_integration_response" "repay_loan_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.repay_loan_resource.id
  http_method = aws_api_gateway_method.repay_loan_options_method.http_method
  status_code = aws_api_gateway_method_response.repay_loan_options_200.status_code
  response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => "'${v}'" }
  response_templates = { "application/json" = "" }
  depends_on = [aws_api_gateway_integration.repay_loan_options_integration]
}


################################################################################
# --- LAMBDA PERMISSIONS ---
################################################################################

resource "aws_lambda_permission" "api_gateway_apply_loan_permission" {
  statement_id  = "AllowAPIGatewayToInvokeApplyLoan"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.apply_for_loan_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_get_loan_permission" {
  statement_id  = "AllowAPIGatewayToInvokeGetLoan"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_loan_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_get_loans_by_wallet_permission" {
  statement_id  = "AllowAPIGatewayToInvokeGetLoansByWallet"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_loans_by_wallet_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_approve_loan_permission" {
  statement_id  = "AllowAPIGatewayToInvokeApproveLoan"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.approve_loan_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_reject_loan_permission" {
  statement_id  = "AllowAPIGatewayToInvokeRejectLoan"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.reject_loan_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_repay_loan_permission" {
  statement_id  = "AllowAPIGatewayToInvokeRepayLoan"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.repay_loan_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}


################################################################################
# --- SNS SUBSCRIPTIONS & PERMISSIONS ---
################################################################################

resource "aws_sns_topic_subscription" "loan_repayment_subscription" {
  topic_arn = var.payment_sns_topic_arn # Subscribes to PAYMENT topic
  protocol  = "lambda"
  endpoint  = aws_lambda_function.update_loan_repayment_status_lambda.arn
  filter_policy = jsonencode({
    "event_type": ["LOAN_REPAYMENT_SUCCESSFUL", "LOAN_REPAYMENT_FAILED"]
  })
}

resource "aws_lambda_permission" "sns_loan_repayment_invoke_permission" {
  statement_id  = "AllowSNSToInvokeLoanRepayment"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.update_loan_repayment_status_lambda.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = var.payment_sns_topic_arn
}