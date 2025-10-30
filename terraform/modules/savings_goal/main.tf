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
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_exec_role" {
  name               = "${var.project_name}-savings-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# --- IAM: DynamoDB Policy ---
data "aws_iam_policy_document" "dynamodb_savings_table_policy_doc" {
  # Statement 1: Permissions for the savings_goals_table
  statement {
    sid = "SavingsTableAccess"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:Query",
      "dynamodb:DeleteItem",
      "dynamodb:UpdateItem",
      "dynamodb:GetItem" # Added for fetching goal name
    ]
    resources = [
      var.dynamodb_table_arn,
      "${var.dynamodb_table_arn}/index/*"
    ]
  }
  # Statement 2: Permissions for the wallets_table (for transactions AND reading)
  statement {
    sid = "WalletsTableTxAccess"
    actions = [
      "dynamodb:UpdateItem", # For the transaction
      "dynamodb:GetItem"     # <-- ADD THIS LINE (for reading the new balance)
    ]
    resources = [var.wallets_table_arn]
  }
  # Statement 3: Permissions for writing to the transaction log table
  statement {
    sid       = "TransactionLogWriteAccess"
    actions   = ["dynamodb:PutItem"] # Permission to log
    resources = [var.transactions_log_table_arn]
  }
  # Statement 4: Permissions for reading the transaction log table GSI
  statement {
      sid = "TransactionLogReadGoalIndex"
      actions = ["dynamodb:Query"] # Permission to query GSI
      resources = [
          "${var.transactions_log_table_arn}/index/related_id-timestamp-index" # Specific index ARN
      ]
  }
}

resource "aws_iam_policy" "dynamodb_savings_table_policy" {
  name   = "${var.project_name}-savings-table-policy"
  policy = data.aws_iam_policy_document.dynamodb_savings_table_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "dynamodb_savings_table_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.dynamodb_savings_table_policy.arn
}

################################################################################
# --- LAMBDA FUNCTIONS (API) ---
################################################################################

# --- LAMBDA: CREATE SAVINGS GOAL ---
data "archive_file" "create_savings_goal_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/create_savings_goal"
  output_path = "${path.module}/create_savings_goal.zip"
}
resource "aws_lambda_function" "create_savings_goal_lambda" {
  function_name    = "${var.project_name}-create-savings-goal"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.create_savings_goal_zip.output_path
  source_code_hash = data.archive_file.create_savings_goal_zip.output_base64sha256
  handler          = "handler.create_savings_goal"
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

# --- LAMBDA: GET SAVINGS GOALS ---
data "archive_file" "get_savings_goals_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/get_savings_goals"
  output_path = "${path.module}/get_savings_goals.zip"
}
resource "aws_lambda_function" "get_savings_goals_lambda" {
  function_name    = "${var.project_name}-get-savings-goals"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.get_savings_goals_zip.output_path
  source_code_hash = data.archive_file.get_savings_goals_zip.output_base64sha256
  handler          = "handler.get_savings_goals"
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

# --- LAMBDA: DELETE SAVINGS GOAL ---
data "archive_file" "delete_savings_goal_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/delete_savings_goal"
  output_path = "${path.module}/delete_savings_goal.zip"
}
resource "aws_lambda_function" "delete_savings_goal_lambda" {
  function_name    = "${var.project_name}-delete-savings-goal"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.delete_savings_goal_zip.output_path
  source_code_hash = data.archive_file.delete_savings_goal_zip.output_base64sha256
  handler          = "handler.delete_savings_goal"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      DYNAMODB_TABLE_NAME = var.dynamodb_table_name
      WALLETS_TABLE_NAME          = var.wallets_table_name
      TRANSACTIONS_LOG_TABLE_NAME = var.transactions_log_table_name
      CORS_ORIGIN         = var.frontend_cors_origin
      REDEPLOY_TRIGGER = sha1(var.frontend_cors_origin)
      
    }
  }
}

# --- LAMBDA: ADD TO SAVINGS GOAL ---
data "archive_file" "add_to_savings_goal_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/add_to_savings_goal"
  output_path = "${path.module}/add_to_savings_goal.zip"
}
resource "aws_lambda_function" "add_to_savings_goal_lambda" {
  function_name    = "${var.project_name}-add-to-savings-goal"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.add_to_savings_goal_zip.output_path
  source_code_hash = data.archive_file.add_to_savings_goal_zip.output_base64sha256
  handler          = "handler.add_to_savings_goal"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      SAVINGS_TABLE_NAME          = var.dynamodb_table_name
      WALLETS_TABLE_NAME          = var.wallets_table_name
      TRANSACTIONS_LOG_TABLE_NAME = var.transactions_log_table_name
      CORS_ORIGIN                 = var.frontend_cors_origin
      REDEPLOY_TRIGGER = sha1(var.frontend_cors_origin)
    }
  }
}

# --- LAMBDA: GET GOAL TRANSACTIONS ---
data "archive_file" "get_goal_transactions_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/get_goal_transactions"
  output_path = "${path.module}/get_goal_transactions.zip"
}
resource "aws_lambda_function" "get_goal_transactions_lambda" {
  function_name    = "${var.project_name}-get-goal-transactions"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.get_goal_transactions_zip.output_path
  source_code_hash = data.archive_file.get_goal_transactions_zip.output_base64sha256
  handler          = "handler.get_goal_transactions"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      TRANSACTIONS_LOG_TABLE_NAME = var.transactions_log_table_name
      CORS_ORIGIN                 = var.frontend_cors_origin
      REDEPLOY_TRIGGER = sha1(var.frontend_cors_origin)
    }
  }
}

################################################################################
# --- API GATEWAY ---
################################################################################

# --- API: /savings-goal ---
resource "aws_api_gateway_resource" "savings_goal_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = var.api_gateway_root_resource_id
  path_part   = "savings-goal"
}

# --- API: POST /savings-goal (CREATE) ---
resource "aws_api_gateway_method" "create_savings_goal_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.savings_goal_resource.id
  http_method   = "POST"
  authorization = "NONE"
}
resource "aws_api_gateway_integration" "create_savings_goal_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.savings_goal_resource.id
  http_method             = aws_api_gateway_method.create_savings_goal_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.create_savings_goal_lambda.invoke_arn
}

# --- API: OPTIONS /savings-goal (CORS Preflight for POST) ---
resource "aws_api_gateway_method" "create_savings_goal_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.savings_goal_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}
resource "aws_api_gateway_method_response" "create_savings_goal_options_200" {
   rest_api_id   = var.api_gateway_id
   resource_id   = aws_api_gateway_resource.savings_goal_resource.id
   http_method   = aws_api_gateway_method.create_savings_goal_options_method.http_method
   status_code   = "200"
   response_models = { "application/json" = "Empty" }
   response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => true }
}
resource "aws_api_gateway_integration" "create_savings_goal_options_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id           = aws_api_gateway_resource.savings_goal_resource.id
  http_method             = aws_api_gateway_method.create_savings_goal_options_method.http_method
  type                    = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}
resource "aws_api_gateway_integration_response" "create_savings_goal_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.savings_goal_resource.id
  http_method = aws_api_gateway_method.create_savings_goal_options_method.http_method
  status_code = aws_api_gateway_method_response.create_savings_goal_options_200.status_code
  response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => "'${v}'" }
  response_templates = { "application/json" = "" }
  depends_on = [aws_api_gateway_integration.create_savings_goal_options_integration]
}

# --- API: /savings-goal/by-wallet/{wallet_id} ---
resource "aws_api_gateway_resource" "savings_by_wallet_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.savings_goal_resource.id
  path_part   = "by-wallet"
}
resource "aws_api_gateway_resource" "savings_by_wallet_id_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.savings_by_wallet_resource.id
  path_part   = "{wallet_id}"
}

# --- API: GET /savings-goal/by-wallet/{wallet_id} ---
resource "aws_api_gateway_method" "get_savings_goals_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.savings_by_wallet_id_resource.id
  http_method   = "GET"
  authorization = "NONE"
}
resource "aws_api_gateway_integration" "get_savings_goals_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.savings_by_wallet_id_resource.id
  http_method             = aws_api_gateway_method.get_savings_goals_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.get_savings_goals_lambda.invoke_arn
}
# (Skipping OPTIONS for simple GET)

# --- API: /savings-goal/{goal_id} ---
resource "aws_api_gateway_resource" "savings_goal_id_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.savings_goal_resource.id
  path_part   = "{goal_id}"
}

# --- API: DELETE /savings-goal/{goal_id} ---
resource "aws_api_gateway_method" "delete_savings_goal_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.savings_goal_id_resource.id
  http_method   = "DELETE"
  authorization = "NONE"
}
resource "aws_api_gateway_integration" "delete_savings_goal_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.savings_goal_id_resource.id
  http_method             = aws_api_gateway_method.delete_savings_goal_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.delete_savings_goal_lambda.invoke_arn
}

# --- API: OPTIONS /savings-goal/{goal_id} (CORS Preflight for DELETE) ---
resource "aws_api_gateway_method" "delete_savings_goal_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.savings_goal_id_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}
resource "aws_api_gateway_method_response" "delete_savings_goal_options_200" {
   rest_api_id   = var.api_gateway_id
   resource_id   = aws_api_gateway_resource.savings_goal_id_resource.id
   http_method   = aws_api_gateway_method.delete_savings_goal_options_method.http_method
   status_code   = "200"
   response_models = { "application/json" = "Empty" }
   response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => true }
}
resource "aws_api_gateway_integration" "delete_savings_goal_options_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id           = aws_api_gateway_resource.savings_goal_id_resource.id
  http_method             = aws_api_gateway_method.delete_savings_goal_options_method.http_method
  type                    = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}
resource "aws_api_gateway_integration_response" "delete_savings_goal_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.savings_goal_id_resource.id
  http_method = aws_api_gateway_method.delete_savings_goal_options_method.http_method
  status_code = aws_api_gateway_method_response.delete_savings_goal_options_200.status_code
  response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => "'${v}'" }
  response_templates = { "application/json" = "" }
  depends_on = [aws_api_gateway_integration.delete_savings_goal_options_integration]
}

# --- API: /savings-goal/{goal_id}/add ---
resource "aws_api_gateway_resource" "add_to_goal_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.savings_goal_id_resource.id
  path_part   = "add"
}

# --- API: POST /savings-goal/{goal_id}/add ---
resource "aws_api_gateway_method" "add_to_goal_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.add_to_goal_resource.id
  http_method   = "POST"
  authorization = "NONE"
}
resource "aws_api_gateway_integration" "add_to_goal_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.add_to_goal_resource.id
  http_method             = aws_api_gateway_method.add_to_goal_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.add_to_savings_goal_lambda.invoke_arn
}

# --- API: OPTIONS /savings-goal/{goal_id}/add (CORS Preflight) ---
resource "aws_api_gateway_method" "add_to_goal_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.add_to_goal_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}
resource "aws_api_gateway_method_response" "add_to_goal_options_200" {
   rest_api_id   = var.api_gateway_id
   resource_id   = aws_api_gateway_resource.add_to_goal_resource.id
   http_method   = aws_api_gateway_method.add_to_goal_options_method.http_method
   status_code   = "200"
   response_models = { "application/json" = "Empty" }
   response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => true }
}
resource "aws_api_gateway_integration" "add_to_goal_options_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id           = aws_api_gateway_resource.add_to_goal_resource.id
  http_method             = aws_api_gateway_method.add_to_goal_options_method.http_method
  type                    = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}
resource "aws_api_gateway_integration_response" "add_to_goal_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.add_to_goal_resource.id
  http_method = aws_api_gateway_method.add_to_goal_options_method.http_method
  status_code = aws_api_gateway_method_response.add_to_goal_options_200.status_code
  response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => "'${v}'" }
  response_templates = { "application/json" = "" }
  depends_on = [aws_api_gateway_integration.add_to_goal_options_integration]
}

# --- API: /savings-goal/{goal_id}/transactions ---
resource "aws_api_gateway_resource" "goal_transactions_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.savings_goal_id_resource.id
  path_part   = "transactions"
}

# --- API: GET /savings-goal/{goal_id}/transactions ---
resource "aws_api_gateway_method" "get_goal_transactions_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.goal_transactions_resource.id
  http_method   = "GET"
  authorization = "NONE"
}
resource "aws_api_gateway_integration" "get_goal_transactions_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.goal_transactions_resource.id
  http_method             = aws_api_gateway_method.get_goal_transactions_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.get_goal_transactions_lambda.invoke_arn
}

# --- API: OPTIONS /savings-goal/{goal_id}/transactions (CORS) ---
resource "aws_api_gateway_method" "get_goal_transactions_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.goal_transactions_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}
resource "aws_api_gateway_method_response" "get_goal_transactions_options_200" {
   rest_api_id   = var.api_gateway_id
   resource_id   = aws_api_gateway_resource.goal_transactions_resource.id
   http_method   = aws_api_gateway_method.get_goal_transactions_options_method.http_method
   status_code   = "200"
   response_models = { "application/json" = "Empty" }
   response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => true }
}
resource "aws_api_gateway_integration" "get_goal_transactions_options_integration" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.goal_transactions_resource.id
  http_method   = aws_api_gateway_method.get_goal_transactions_options_method.http_method
  type          = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}
resource "aws_api_gateway_integration_response" "get_goal_transactions_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.goal_transactions_resource.id
  http_method = aws_api_gateway_method.get_goal_transactions_options_method.http_method
  status_code = aws_api_gateway_method_response.get_goal_transactions_options_200.status_code
  response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => "'${v}'" }
  response_templates = { "application/json" = "" }
  depends_on = [aws_api_gateway_integration.get_goal_transactions_options_integration]
}

################################################################################
# --- LAMBDA PERMISSIONS ---
################################################################################

resource "aws_lambda_permission" "api_gateway_create_savings_goal_permission" {
  statement_id  = "AllowAPIGatewayToInvokeCreateSavingsGoal"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.create_savings_goal_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_get_savings_goals_permission" {
  statement_id  = "AllowAPIGatewayToInvokeGetSavingsGoals"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_savings_goals_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_delete_savings_goal_permission" {
  statement_id  = "AllowAPIGatewayToInvokeDeleteSavingsGoal"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.delete_savings_goal_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_add_to_goal_permission" {
  statement_id  = "AllowAPIGatewayToInvokeAddToGoal"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.add_to_savings_goal_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_get_goal_transactions_permission" {
  statement_id  = "AllowAPIGatewayToInvokeGetGoalTx"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_goal_transactions_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}