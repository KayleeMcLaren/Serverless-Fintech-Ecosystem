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
  name               = "${var.project_name}-wallet-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "dynamodb_wallet_table_policy_doc" {
  statement {
    actions   = ["dynamodb:PutItem", "dynamodb:GetItem"]
    resources = [var.dynamodb_table_arn]
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

# --- LAMBDA FUNCTIONS ---
data "archive_file" "create_wallet_zip" {
  type        = "zip"
  source_dir  = "/home/kaylee-dev/Desktop/Serverless-Fintech-Ecosystem/src/create_wallet"  # Correct path from terraform/modules
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

data "archive_file" "get_wallet_zip" {
  type        = "zip"
  source_dir  = "/home/kaylee-dev/Desktop/Serverless-Fintech-Ecosystem/src/get_wallet"  # Correct path from terraform/modules
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

# --- API GATEWAY ---
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

# --- PERMISSIONS ---
resource "aws_lambda_permission" "api_gateway_create_permission" {
  statement_id  = "AllowAPIGatewayToInvokeCreate"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.create_wallet_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_get_permission" {
  statement_id  = "AllowAPIGatewayToInvokeGet"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_wallet_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}