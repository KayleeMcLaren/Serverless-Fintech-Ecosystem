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
  name               = "${var.project_name}-payment-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy for DynamoDB (Put and Get)
data "aws_iam_policy_document" "dynamodb_transactions_table_policy_doc" {
  statement {
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:UpdateItem"
    ]
    resources = [
      var.dynamodb_table_arn,
      "${var.dynamodb_table_arn}/index/*"
    ]
  }
}

resource "aws_iam_policy" "dynamodb_transactions_table_policy" {
  name   = "${var.project_name}-transactions-table-policy"
  policy = data.aws_iam_policy_document.dynamodb_transactions_table_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "dynamodb_transactions_table_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.dynamodb_transactions_table_policy.arn
}

# Policy to allow publishing to the payment SNS topic
data "aws_iam_policy_document" "sns_publish_policy_doc" {
  statement {
    actions   = ["sns:Publish"]
    resources = [var.sns_topic_arn]
  }
}

resource "aws_iam_policy" "sns_publish_policy" {
  name   = "${var.project_name}-processor-payment-sns-publish-policy"
  policy = data.aws_iam_policy_document.sns_publish_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "sns_publish_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.sns_publish_policy.arn
}

# --- LAMBDA: REQUEST PAYMENT (API) ---
data "archive_file" "request_payment_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/request_payment"
  output_path = "${path.module}/request_payment.zip"
}

resource "aws_lambda_function" "request_payment_lambda" {
  function_name    = "${var.project_name}-request-payment"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.request_payment_zip.output_path
  source_code_hash = data.archive_file.request_payment_zip.output_base64sha256
  handler          = "handler.request_payment"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME = var.dynamodb_table_name
      SNS_TOPIC_ARN       = var.sns_topic_arn
    }
  }
}

# --- LAMBDA: GET TRANSACTION STATUS (API) ---
data "archive_file" "get_transaction_status_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/get_transaction_status"
  output_path = "${path.module}/get_transaction_status.zip"
}

resource "aws_lambda_function" "get_transaction_status_lambda" {
  function_name    = "${var.project_name}-get-transaction-status"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.get_transaction_status_zip.output_path
  source_code_hash = data.archive_file.get_transaction_status_zip.output_base64sha256
  handler          = "handler.get_transaction_status"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME = var.dynamodb_table_name
    }
  }
}

# --- API GATEWAY: POST /payment ---
resource "aws_api_gateway_resource" "payment_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = var.api_gateway_root_resource_id
  path_part   = "payment"
}

resource "aws_api_gateway_method" "request_payment_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.payment_resource.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "request_payment_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.payment_resource.id
  http_method             = aws_api_gateway_method.request_payment_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.request_payment_lambda.invoke_arn
}

# --- API: OPTIONS /payment (CORS Preflight for POST) ---
resource "aws_api_gateway_method" "request_payment_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.payment_resource.id # On the /payment resource
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "request_payment_options_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id           = aws_api_gateway_resource.payment_resource.id
  http_method             = aws_api_gateway_method.request_payment_options_method.http_method
  type                    = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "request_payment_options_200" {
   rest_api_id   = var.api_gateway_id
   resource_id   = aws_api_gateway_resource.payment_resource.id
   http_method   = aws_api_gateway_method.request_payment_options_method.http_method
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

resource "aws_api_gateway_integration_response" "request_payment_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.payment_resource.id
  http_method = aws_api_gateway_method.request_payment_options_method.http_method
  status_code = aws_api_gateway_method_response.request_payment_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'", # Allow POST and OPTIONS
    "method.response.header.Access-Control-Allow-Origin"  = "'*'", # Use '*' for dev
    "method.response.header.Access-Control-Allow-Credentials" = "'true'"
  }

  response_templates = {
    "application/json" = ""
  }
  depends_on = [aws_api_gateway_integration.request_payment_options_integration]
}

# --- API GATEWAY: GET /payment/{transaction_id} ---
resource "aws_api_gateway_resource" "transaction_id_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.payment_resource.id # Attaches to /payment
  path_part   = "{transaction_id}"
}

resource "aws_api_gateway_method" "get_transaction_status_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.transaction_id_resource.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "get_transaction_status_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.transaction_id_resource.id
  http_method             = aws_api_gateway_method.get_transaction_status_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.get_transaction_status_lambda.invoke_arn
}

# --- API: OPTIONS /payment/{transaction_id} (CORS Preflight for GET) ---
# Although simple GETs don't *usually* need preflight, adding it doesn't hurt
# and covers cases where custom headers might be added later.
resource "aws_api_gateway_method" "get_transaction_status_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.transaction_id_resource.id # On the /{transaction_id} resource
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "get_transaction_status_options_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id           = aws_api_gateway_resource.transaction_id_resource.id
  http_method             = aws_api_gateway_method.get_transaction_status_options_method.http_method
  type                    = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "get_transaction_status_options_200" {
   rest_api_id   = var.api_gateway_id
   resource_id   = aws_api_gateway_resource.transaction_id_resource.id
   http_method   = aws_api_gateway_method.get_transaction_status_options_method.http_method
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

resource "aws_api_gateway_integration_response" "get_transaction_status_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.transaction_id_resource.id
  http_method = aws_api_gateway_method.get_transaction_status_options_method.http_method
  status_code = aws_api_gateway_method_response.get_transaction_status_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'", # Allow GET and OPTIONS
    "method.response.header.Access-Control-Allow-Origin"  = "'*'",
    "method.response.header.Access-Control-Allow-Credentials" = "'true'"
  }

  response_templates = {
    "application/json" = ""
  }
  depends_on = [aws_api_gateway_integration.get_transaction_status_options_integration]
}

# --- API PERMISSIONS ---
resource "aws_lambda_permission" "api_gateway_request_payment_permission" {
  statement_id  = "AllowAPIGatewayToInvokeRequestPayment"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.request_payment_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_get_transaction_permission" {
  statement_id  = "AllowAPIGatewayToInvokeGetTransaction"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_transaction_status_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

# --- LAMBDA: UPDATE TRANSACTION STATUS (SNS SUBSCRIBER) ---
data "archive_file" "update_transaction_status_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/update_transaction_status"
  output_path = "${path.module}/update_transaction_status.zip"
}

resource "aws_lambda_function" "update_transaction_status_lambda" {
  function_name    = "${var.project_name}-update-transaction-status"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.update_transaction_status_zip.output_path
  source_code_hash = data.archive_file.update_transaction_status_zip.output_base64sha256
  handler          = "handler.update_transaction_status"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME = var.dynamodb_table_name
    }
  }
}

# --- SNS SUBSCRIPTION & PERMISSION (PAYMENT RESULTS) ---
resource "aws_sns_topic_subscription" "payment_result_subscription" {
  topic_arn = var.sns_topic_arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.update_transaction_status_lambda.arn
  # Add a filter policy so this Lambda only gets 'RESULT' events
  filter_policy = jsonencode({
    "event_type": ["PAYMENT_SUCCESSFUL", "PAYMENT_FAILED"]
  })
}

resource "aws_lambda_permission" "sns_payment_result_invoke_permission" {
  statement_id  = "AllowSNSPaymentResultInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.update_transaction_status_lambda.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = var.sns_topic_arn
}