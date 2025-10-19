# --- IAM ---
# This section defines all permissions for our Lambda functions.

# --- IAM: LAMBDA EXECUTION ROLE ---
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

# --- IAM: DYNAMODB POLICY ---
data "aws_iam_policy_document" "dynamodb_savings_table_policy_doc" {
  # Statement 1: Permissions for the savings_goals_table
  statement {
    actions = [
      "dynamodb:PutItem",
      "dynamodb:Query",
      "dynamodb:DeleteItem",
      "dynamodb:UpdateItem" # Add UpdateItem
    ]
    resources = [
      var.dynamodb_table_arn,
      "${var.dynamodb_table_arn}/index/*"
    ]
  }
  # Statement 2: Permissions for the wallets_table
  statement {
    actions   = ["dynamodb:UpdateItem"] # Only needs UpdateItem
    resources = [var.wallets_table_arn]
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
# --- LAMBDA FUNCTIONS ---
# This section defines the three serverless functions for our API.
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
      SAVINGS_TABLE_NAME = var.dynamodb_table_name
      WALLETS_TABLE_NAME = var.wallets_table_name
    }
  }
}

################################################################################
# --- API GATEWAY ---
# This section defines the HTTP endpoints that trigger our Lambda functions.
################################################################################

# --- API: POST /savings-goal (CREATE) ---
resource "aws_api_gateway_resource" "savings_goal_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = var.api_gateway_root_resource_id
  path_part   = "savings-goal"
}

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

# --- API: GET /savings-goal/by-wallet/{wallet_id} ---
resource "aws_api_gateway_resource" "savings_by_wallet_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.savings_goal_resource.id # Attaches to /savings-goal
  path_part   = "by-wallet"
}

resource "aws_api_gateway_resource" "savings_by_wallet_id_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.savings_by_wallet_resource.id # Attaches to /savings-goal/by-wallet
  path_part   = "{wallet_id}"
}

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

# --- API: DELETE /savings-goal/{goal_id} ---
resource "aws_api_gateway_resource" "savings_goal_id_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.savings_goal_resource.id # Attaches to /savings-goal
  path_part   = "{goal_id}"
}

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

# --- API: POST /savings-goal/{goal_id}/add ---
resource "aws_api_gateway_resource" "add_to_goal_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.savings_goal_id_resource.id # Attaches to /savings-goal/{goal_id}
  path_part   = "add"
}

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

################################################################################
# --- LAMBDA PERMISSIONS ---
# This section grants API Gateway permission to invoke our Lambda functions.
################################################################################

# --- PERMISSION: CREATE SAVINGS GOAL ---
resource "aws_lambda_permission" "api_gateway_create_savings_goal_permission" {
  statement_id  = "AllowAPIGatewayToInvokeCreateSavingsGoal"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.create_savings_goal_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

# --- PERMISSION: GET SAVINGS GOALS ---
resource "aws_lambda_permission" "api_gateway_get_savings_goals_permission" {
  statement_id  = "AllowAPIGatewayToInvokeGetSavingsGoals"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_savings_goals_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

# --- PERMISSION: DELETE SAVINGS GOAL ---
resource "aws_lambda_permission" "api_gateway_delete_savings_goal_permission" {
  statement_id  = "AllowAPIGatewayToInvokeDeleteSavingsGoal"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.delete_savings_goal_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

# --- PERMISSION: ADD TO SAVINGS GOAL ---
resource "aws_lambda_permission" "api_gateway_add_to_goal_permission" {
  statement_id  = "AllowAPIGatewayToInvokeAddToGoal"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.add_to_savings_goal_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}