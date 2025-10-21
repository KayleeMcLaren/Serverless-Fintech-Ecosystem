# --- IAM ---
# New, separate IAM Role for the Loan service.
# It only has permission to write to the loans table.

data "aws_iam_policy_document" "lambda_assume_role_policy" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
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

# Policy to allow writing to the new loans table
data "aws_iam_policy_document" "dynamodb_loans_table_policy_doc" {
  statement {
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem", 
      "dynamodb:Query",
      "dynamodb:UpdateItem"    
    ]
    resources = [
      var.dynamodb_table_arn,
      "${var.dynamodb_table_arn}/index/*" # Add this line to allow querying the GSI
    ]
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

# Policy to allow publishing to the SNS topic
data "aws_iam_policy_document" "sns_publish_policy_doc" {
  statement {
    actions   = ["sns:Publish"]
    resources = [var.sns_topic_arn]
  }
}

resource "aws_iam_policy" "sns_publish_policy" {
  name   = "${var.project_name}-sns-publish-policy"
  policy = data.aws_iam_policy_document.sns_publish_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "sns_publish_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.sns_publish_policy.arn
}

# --- LAMBDA: APPLY FOR LOAN ---
data "archive_file" "apply_for_loan_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/apply_for_loan" # Up 3 levels to root
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
    }
  }
}

# --- API GATEWAY: POST /loan ---
resource "aws_api_gateway_resource" "loan_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = var.api_gateway_root_resource_id
  path_part   = "loan"
}

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

# --- LAMBDA PERMISSION ---
resource "aws_lambda_permission" "api_gateway_apply_loan_permission" {
  statement_id  = "AllowAPIGatewayToInvokeApplyLoan"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.apply_for_loan_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

# --- LAMBDA: GET LOAN ---
data "archive_file" "get_loan_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/get_loan" # Up 3 levels
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
    }
  }
}

# --- LAMBDA: GET LOANS BY WALLET ---
data "archive_file" "get_loans_by_wallet_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/get_loans_by_wallet" # Up 3 levels
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
    }
  }
}

# --- API GATEWAY: GET /loan/{loan_id} ---
resource "aws_api_gateway_resource" "loan_id_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.loan_resource.id # Attaches to /loan
  path_part   = "{loan_id}"
}

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

# --- API: OPTIONS /loan (CORS Preflight for POST) ---
resource "aws_api_gateway_method" "apply_for_loan_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.loan_resource.id # On the /loan resource
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "apply_for_loan_options_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id           = aws_api_gateway_resource.loan_resource.id
  http_method             = aws_api_gateway_method.apply_for_loan_options_method.http_method
  type                    = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "apply_for_loan_options_200" {
   rest_api_id   = var.api_gateway_id
   resource_id   = aws_api_gateway_resource.loan_resource.id
   http_method   = aws_api_gateway_method.apply_for_loan_options_method.http_method
   status_code   = "200"
   response_models = {
     "application/json" = "Empty"
   }
   response_parameters = {
     "method.response.header.Access-Control-Allow-Headers" = true,
     "method.response.header.Access-Control-Allow-Methods" = true,
     "method.response.header.Access-Control-Allow-Origin" = true,
     "method.response.header.Access-Control-Allow-Credentials" = true
   }
}

resource "aws_api_gateway_integration_response" "apply_for_loan_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.loan_resource.id
  http_method = aws_api_gateway_method.apply_for_loan_options_method.http_method
  status_code = aws_api_gateway_method_response.apply_for_loan_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'", # Allow POST and OPTIONS
    "method.response.header.Access-Control-Allow-Origin"  = "'*'", # Use '*' for dev
    "method.response.header.Access-Control-Allow-Credentials" = "'true'"
  }

  response_templates = {
    "application/json" = ""
  }
  depends_on = [aws_api_gateway_integration.apply_for_loan_options_integration]
}

# --- API GATEWAY: GET /loan/by-wallet/{wallet_id} ---
resource "aws_api_gateway_resource" "loan_by_wallet_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.loan_resource.id # Attaches to /loan
  path_part   = "by-wallet"
}

resource "aws_api_gateway_resource" "loan_by_wallet_id_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.loan_by_wallet_resource.id # Attaches to /loan/by-wallet
  path_part   = "{wallet_id}"
}

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
      SNS_TOPIC_ARN       = var.sns_topic_arn # Pass ARN to handler
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
    }
  }
}

# --- API GATEWAY: POST /loan/{loan_id}/approve ---
resource "aws_api_gateway_resource" "approve_loan_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.loan_id_resource.id # Attaches to /loan/{loan_id}
  path_part   = "approve"
}

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

# --- API: OPTIONS /loan/{loan_id}/approve (CORS Preflight for POST) ---
resource "aws_api_gateway_method" "approve_loan_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.approve_loan_resource.id # On the /approve resource
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "approve_loan_options_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id           = aws_api_gateway_resource.approve_loan_resource.id
  http_method             = aws_api_gateway_method.approve_loan_options_method.http_method
  type                    = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "approve_loan_options_200" {
   rest_api_id   = var.api_gateway_id
   resource_id   = aws_api_gateway_resource.approve_loan_resource.id
   http_method   = aws_api_gateway_method.approve_loan_options_method.http_method
   status_code   = "200"
   response_models = {
     "application/json" = "Empty"
   }
   response_parameters = {
     "method.response.header.Access-Control-Allow-Headers" = true,
     "method.response.header.Access-Control-Allow-Methods" = true,
     "method.response.header.Access-Control-Allow-Origin" = true,
     "method.response.header.Access-Control-Allow-Credentials" = true
   }
}

resource "aws_api_gateway_integration_response" "approve_loan_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.approve_loan_resource.id
  http_method = aws_api_gateway_method.approve_loan_options_method.http_method
  status_code = aws_api_gateway_method_response.approve_loan_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'",
    "method.response.header.Access-Control-Allow-Origin"  = "'*'",
    "method.response.header.Access-Control-Allow-Credentials" = "'true'"
  }

  response_templates = {
    "application/json" = ""
  }
  depends_on = [aws_api_gateway_integration.approve_loan_options_integration]
}

# --- API GATEWAY: POST /loan/{loan_id}/reject ---
resource "aws_api_gateway_resource" "reject_loan_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.loan_id_resource.id # Attaches to /loan/{loan_id}
  path_part   = "reject"
}

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

# --- API: OPTIONS /loan/{loan_id}/reject (CORS Preflight for POST) ---
resource "aws_api_gateway_method" "reject_loan_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.reject_loan_resource.id # On the /reject resource
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "reject_loan_options_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id           = aws_api_gateway_resource.reject_loan_resource.id
  http_method             = aws_api_gateway_method.reject_loan_options_method.http_method
  type                    = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "reject_loan_options_200" {
   rest_api_id   = var.api_gateway_id
   resource_id   = aws_api_gateway_resource.reject_loan_resource.id
   http_method   = aws_api_gateway_method.reject_loan_options_method.http_method
   status_code   = "200"
   response_models = {
     "application/json" = "Empty"
   }
   response_parameters = {
     "method.response.header.Access-Control-Allow-Headers" = true,
     "method.response.header.Access-Control-Allow-Methods" = true,
     "method.response.header.Access-Control-Allow-Origin" = true,
     "method.response.header.Access-Control-Allow-Credentials" = true
   }
}

resource "aws_api_gateway_integration_response" "reject_loan_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.reject_loan_resource.id
  http_method = aws_api_gateway_method.reject_loan_options_method.http_method
  status_code = aws_api_gateway_method_response.reject_loan_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'",
    "method.response.header.Access-Control-Allow-Origin"  = "'*'",
    "method.response.header.Access-Control-Allow-Credentials" = "'true'"
  }

  response_templates = {
    "application/json" = ""
  }
  depends_on = [aws_api_gateway_integration.reject_loan_options_integration]
}

# --- LAMBDA PERMISSIONS (GET) ---
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

# --- LAMBDA PERMISSIONS (Approve/Reject) ---
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