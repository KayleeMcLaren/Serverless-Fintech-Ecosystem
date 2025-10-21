# --- IAM ---
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
  name               = "${var.project_name}-optimiser-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy for DynamoDB (Query only)
data "aws_iam_policy_document" "dynamodb_loans_table_policy_doc" {
  statement {
    actions = [ "dynamodb:Query" ] # Read-only permission
    resources = [
      var.loans_table_arn,
      "${var.loans_table_arn}/index/*" # Permission to query the GSI
    ]
  }
}

resource "aws_iam_policy" "dynamodb_loans_table_policy" {
  name   = "${var.project_name}-loans-table-query-policy"
  policy = data.aws_iam_policy_document.dynamodb_loans_table_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "dynamodb_loans_table_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.dynamodb_loans_table_policy.arn
}

# --- LAMBDA: CALCULATE REPAYMENT PLAN (API) ---
data "archive_file" "calculate_repayment_plan_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/calculate_repayment_plan"
  output_path = "${path.module}/calculate_repayment_plan.zip"
}

resource "aws_lambda_function" "calculate_repayment_plan_lambda" {
  function_name    = "${var.project_name}-calculate-repayment-plan"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.calculate_repayment_plan_zip.output_path
  source_code_hash = data.archive_file.calculate_repayment_plan_zip.output_base64sha256
  handler          = "handler.calculate_repayment_plan"
  runtime          = "python3.12"
  timeout          = 10 # Give it a bit more time for calculations
  tags             = var.tags
  environment {
    variables = {
      # The table name is passed in via the 'loans_table_arn' var,
      # but we need to extract just the name.
      LOANS_TABLE_NAME = split("/", var.loans_table_arn)[1]
    }
  }
}

# --- API GATEWAY: POST /debt-optimiser ---
resource "aws_api_gateway_resource" "debt_optimiser_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = var.api_gateway_root_resource_id
  path_part   = "debt-optimiser"
}

resource "aws_api_gateway_method" "calculate_repayment_plan_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.debt_optimiser_resource.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "calculate_repayment_plan_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.debt_optimiser_resource.id
  http_method             = aws_api_gateway_method.calculate_repayment_plan_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.calculate_repayment_plan_lambda.invoke_arn
}

# --- API: OPTIONS /debt-optimiser (CORS Preflight for POST) ---
resource "aws_api_gateway_method" "calculate_repayment_plan_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.debt_optimiser_resource.id # On the /debt-optimiser resource
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "calculate_repayment_plan_options_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id           = aws_api_gateway_resource.debt_optimiser_resource.id
  http_method             = aws_api_gateway_method.calculate_repayment_plan_options_method.http_method
  type                    = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "calculate_repayment_plan_options_200" {
   rest_api_id   = var.api_gateway_id
   resource_id   = aws_api_gateway_resource.debt_optimiser_resource.id
   http_method   = aws_api_gateway_method.calculate_repayment_plan_options_method.http_method
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

resource "aws_api_gateway_integration_response" "calculate_repayment_plan_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.debt_optimiser_resource.id
  http_method = aws_api_gateway_method.calculate_repayment_plan_options_method.http_method
  status_code = aws_api_gateway_method_response.calculate_repayment_plan_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'", # Allow POST and OPTIONS
    "method.response.header.Access-Control-Allow-Origin"  = "'*'", # Use '*' for dev
    "method.response.header.Access-Control-Allow-Credentials" = "'true'"
  }

  response_templates = {
    "application/json" = ""
  }
  depends_on = [aws_api_gateway_integration.calculate_repayment_plan_options_integration]
}

# --- API PERMISSION ---
resource "aws_lambda_permission" "api_gateway_calculate_plan_permission" {
  statement_id  = "AllowAPIGatewayToInvokeCalculatePlan"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.calculate_repayment_plan_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}