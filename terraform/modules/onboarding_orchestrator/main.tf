# --- FORCING A NEW SAVE ---

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
    "Access-Control-Allow-Methods" = "OPTIONS,GET,POST,DELETE",
    "Access-Control-Allow-Origin"  = var.frontend_cors_origin,
    "Access-Control-Allow-Credentials" = "true"
  }
}

# --- 1. IAM Role for the Lambdas ---
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
  name               = "${var.project_name}-onboarding-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# --- 2. IAM Policy for Lambdas ---
# We are removing the provisional 'data.aws_iam_policy_document.lambda_policy_doc'
# We are removing the provisional 'resource.aws_iam_policy.lambda_policy'
# We are removing the provisional 'resource.aws_iam_role_policy_attachment.lambda_policy_attachment'
# The single, final policy will be defined in section 6, which correctly depends on the Step Function.


# --- 3. IAM Role for the Step Function ---
data "aws_iam_policy_document" "step_function_assume_role_policy" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "step_function_role" {
  name               = "${var.project_name}-step-function-role"
  assume_role_policy = data.aws_iam_policy_document.step_function_assume_role_policy.json
  tags               = var.tags
}

# Policy for what the Step Function can do (Invoke Lambdas)
data "aws_iam_policy_document" "step_function_policy_doc" {
  statement {
    sid = "LambdaInvoke"
    actions = [
      "lambda:InvokeFunction"
    ]
    # Allow it to invoke *all* Lambdas created within this module
    resources = [
      aws_lambda_function.verify_id_mock_lambda.arn,
      aws_lambda_function.credit_check_mock_lambda.arn,
      aws_lambda_function.provision_account_lambda.arn
    ]
  }
  
  # --- ADDED PERMISSION for the DynamoDB.waitForTaskToken ---
  statement {
    sid = "DynamoDBUpdate"
    actions = [
        "dynamodb:UpdateItem"
    ]
    resources = [
        var.users_table_arn
    ]
  }
}

resource "aws_iam_policy" "step_function_policy" {
  name   = "${var.project_name}-step-function-policy"
  policy = data.aws_iam_policy_document.step_function_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "step_function_policy_attachment" {
  role       = aws_iam_role.step_function_role.name
  policy_arn = aws_iam_policy.step_function_policy.arn
}


################################################################################
# --- LAMBDA FUNCTIONS ---
################################################################################

# --- 4.1 LAMBDA: start_onboarding (API) ---
data "archive_file" "start_onboarding_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/start_onboarding"
  output_path = "${path.module}/start_onboarding.zip"
}
resource "aws_lambda_function" "start_onboarding_lambda" {
  function_name    = "${var.project_name}-start-onboarding"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.start_onboarding_zip.output_path
  source_code_hash = data.archive_file.start_onboarding_zip.output_base64sha256
  handler          = "handler.start_onboarding"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      USERS_TABLE_NAME  = split("/", var.users_table_arn)[1]
      STEP_FUNCTION_ARN = aws_sfn_state_machine.onboarding_sfn.arn # Use correct resource name
      CORS_ORIGIN       = var.frontend_cors_origin
    }
  }
}

# --- 4.2 LAMBDA: get_onboarding_status (API) ---
data "archive_file" "get_onboarding_status_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/get_onboarding_status"
  output_path = "${path.module}/get_onboarding_status.zip"
}
resource "aws_lambda_function" "get_onboarding_status_lambda" {
  function_name    = "${var.project_name}-get-onboarding-status"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.get_onboarding_status_zip.output_path
  source_code_hash = data.archive_file.get_onboarding_status_zip.output_base64sha256
  handler          = "handler.get_onboarding_status"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      USERS_TABLE_NAME = split("/", var.users_table_arn)[1]
      CORS_ORIGIN      = var.frontend_cors_origin
    }
  }
}

# --- 4.3 LAMBDA: manual_review_handler (API) ---
data "archive_file" "manual_review_handler_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/manual_review_handler"
  output_path = "${path.module}/manual_review_handler.zip"
}
resource "aws_lambda_function" "manual_review_handler_lambda" {
  function_name    = "${var.project_name}-manual-review-handler"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.manual_review_handler_zip.output_path
  source_code_hash = data.archive_file.manual_review_handler_zip.output_base64sha256
  handler          = "handler.manual_review"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      USERS_TABLE_NAME = split("/", var.users_table_arn)[1]
      CORS_ORIGIN      = var.frontend_cors_origin
    }
  }
}

# --- 4.4 LAMBDA: verify_id_mock (Step Function Task) ---
data "archive_file" "verify_id_mock_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/verify_id_mock"
  output_path = "${path.module}/verify_id_mock.zip"
}
resource "aws_lambda_function" "verify_id_mock_lambda" {
  function_name    = "${var.project_name}-verify-id-mock"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.verify_id_mock_zip.output_path
  source_code_hash = data.archive_file.verify_id_mock_zip.output_base64sha256
  handler          = "handler.verify_id"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      USERS_TABLE_NAME = split("/", var.users_table_arn)[1]
    }
  }
}

# --- 4.5 LAMBDA: credit_check_mock (Step Function Task) ---
data "archive_file" "credit_check_mock_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/credit_check_mock"
  output_path = "${path.module}/credit_check_mock.zip"
}
resource "aws_lambda_function" "credit_check_mock_lambda" {
  function_name    = "${var.project_name}-credit-check-mock"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.credit_check_mock_zip.output_path
  source_code_hash = data.archive_file.credit_check_mock_zip.output_base64sha256
  handler          = "handler.credit_check"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      USERS_TABLE_NAME = split("/", var.users_table_arn)[1]
    }
  }
}

# --- 4.6 LAMBDA: provision_account (Step Function Task) ---
data "archive_file" "provision_account_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/provision_account"
  output_path = "${path.module}/provision_account.zip"
}
resource "aws_lambda_function" "provision_account_lambda" {
  function_name    = "${var.project_name}-provision-account"
  role             = aws_iam_role.lambda_exec_role.arn
  filename         = data.archive_file.provision_account_zip.output_path
  source_code_hash = data.archive_file.provision_account_zip.output_base64sha256
  handler          = "handler.provision_account"
  runtime          = "python3.12"
  tags             = var.tags
  environment {
    variables = {
      USERS_TABLE_NAME         = split("/", var.users_table_arn)[1]
      CREATE_WALLET_LAMBDA_ARN = var.create_wallet_lambda_arn
    }
  }
}


################################################################################
# --- 5. AWS STEP FUNCTION ---
################################################################################

# --- FIX: Use aws_sfn_state_machine AND type = "STANDARD" ---
resource "aws_sfn_state_machine" "onboarding_sfn" {
  name     = "${var.project_name}-onboarding-orchestrator"
  role_arn = aws_iam_role.step_function_role.arn
  type     = "STANDARD" # <-- You are correct, this is critical!

  definition = jsonencode({
    Comment = "User Onboarding and KYC Orchestrator"
    StartAt = "VerifyID"
    States = {
      VerifyID = {
        Type = "Task"
        Resource = aws_lambda_function.verify_id_mock_lambda.arn
        ResultPath = "$.VerificationResult"
        Next = "IDCheckDecision"
        Catch = [ {
          ErrorEquals = ["States.ALL"],
          Next = "FailState"
        } ]
      },
      IDCheckDecision = {
        Type = "Choice"
        Choices = [
          {
            Variable = "$.VerificationResult.status",
            StringEquals = "APPROVED",
            Next = "Wait_Before_CreditCheck" # <-- UPDATED
          },
          {
            Variable = "$.VerificationResult.status",
            StringEquals = "FLAGGED",
            Next = "WaitForManualReview"
          }
        ]
        Default = "FailState"
      },
      
      # --- NEW STATE ---
      Wait_Before_CreditCheck = {
        Type = "Wait",
        Seconds = 5, # Wait 5 seconds
        Next = "RunCreditCheck"
      },
      # --- END NEW STATE ---
      
      RunCreditCheck = {
        Type = "Task"
        Resource = aws_lambda_function.credit_check_mock_lambda.arn
        ResultPath = "$.CreditResult"
        Next = "CreditCheckDecision"
        Catch = [ {
          ErrorEquals = ["States.ALL"],
          Next = "FailState"
        } ]
      },
      CreditCheckDecision = {
        Type = "Choice"
        Choices = [
          {
            Variable = "$.CreditResult.status",
            StringEquals = "APPROVED",
            Next = "Wait_Before_Provisioning" # <-- UPDATED
          }
        ]
        Default = "FailState"
      },
      
      WaitForManualReview = {
        Type = "Task"
        Resource = "arn:aws:states:::aws-sdk:dynamodb:updateItem.waitForTaskToken"
        Parameters = {
          "TableName" = split("/", var.users_table_arn)[1],
          "Key" = {
            "user_id" = { "S.$" = "$.user_id" }
          },
          "UpdateExpression" = "SET onboarding_status = :status, sfn_task_token = :token",
          "ExpressionAttributeValues" = {
            ":status" = { "S" = "PENDING_MANUAL_REVIEW" },
            ":token"  = { "S.$" = "$$.Task.Token" }
          }
        }
        ResultPath = null
        Next = "Wait_Before_CreditCheck" # <-- UPDATED
        Catch = [ {
          ErrorEquals = ["States.ALL"],
          Next = "FailState"
        } ]
      },
      
      # --- NEW STATE ---
      Wait_Before_Provisioning = {
        Type = "Wait",
        Seconds = 5, # Wait 5 seconds
        Next = "ProvisionAccount"
      },
      # --- END NEW STATE ---

      ProvisionAccount = {
        Type = "Task"
        Resource = aws_lambda_function.provision_account_lambda.arn
        End = true
      },
      FailState = {
        Type = "Fail"
        Cause = "KYC/Credit check failed or task error"
      }
    }
  })

  tags = var.tags
}

# --- 6. Update Lambda Policy with Step Function ARN ---
# This is now the one-and-only policy for the Lambda role
data "aws_iam_policy_document" "lambda_policy_doc" {
  # (Copy all statements from 'lambda_policy_doc' above)
  statement {
    sid = "DynamoDBUsersTable"
    actions = [
      "dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem", "dynamodb:Query"
    ]
    resources = [
      var.users_table_arn,
      "${var.users_table_arn}/index/*"
    ]
  }
  statement {
    sid       = "ResumeStepFunction"
    actions   = ["states:SendTaskSuccess", "states:SendTaskFailure"]
    resources = ["*"]
  }
  statement {
    sid       = "InvokeCreateWalletLambda"
    actions   = ["lambda:InvokeFunction"]
    resources = [var.create_wallet_lambda_arn]
  }

  # --- This statement is the only one that changes ---
  statement {
    sid       = "StartStepFunction"
    actions   = ["states:StartExecution"]
    resources = [aws_sfn_state_machine.onboarding_sfn.arn]
  }
}

# Renamed from lambda_policy_final to lambda_policy
resource "aws_iam_policy" "lambda_policy" {
  name   = "${var.project_name}-onboarding-lambda-policy"
  policy = data.aws_iam_policy_document.lambda_policy_doc.json

  # The lifecycle block is no longer needed and has been removed
}

# Renamed from lambda_policy_attachment_final to lambda_policy_attachment
resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn

  # The 'depends_on' is no longer needed as Terraform infers the dependency
}


################################################################################
# --- 7. API GATEWAY ---
################################################################################

# --- API: /onboarding ---
resource "aws_api_gateway_resource" "onboarding_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = var.api_gateway_root_resource_id
  path_part   = "onboarding"
}

# --- API: POST /onboarding/start ---
resource "aws_api_gateway_resource" "start_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.onboarding_resource.id
  path_part   = "start"
}
resource "aws_api_gateway_method" "start_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.start_resource.id
  http_method   = "POST"
  authorization = "NONE"
}
resource "aws_api_gateway_integration" "start_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.start_resource.id
  http_method             = aws_api_gateway_method.start_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.start_onboarding_lambda.invoke_arn
}
# (OPTIONS for /start)
resource "aws_api_gateway_method" "start_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.start_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}
resource "aws_api_gateway_method_response" "start_options_200" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.start_resource.id
  http_method = aws_api_gateway_method.start_options_method.http_method
  status_code = "200"
  response_models = { "application/json" = "Empty" }
  response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => true }
}
resource "aws_api_gateway_integration" "start_options_integration" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.start_resource.id
  http_method = aws_api_gateway_method.start_options_method.http_method
  type        = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}
resource "aws_api_gateway_integration_response" "start_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.start_resource.id
  http_method = aws_api_gateway_method.start_options_method.http_method
  status_code = aws_api_gateway_method_response.start_options_200.status_code
  response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => "'${v}'" }
  response_templates = { "application/json" = "" }
  depends_on = [aws_api_gateway_integration.start_options_integration]
}


# --- API: GET /onboarding/{id}/status ---
resource "aws_api_gateway_resource" "status_id_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.onboarding_resource.id
  path_part   = "{user_id}"
}
resource "aws_api_gateway_resource" "status_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.status_id_resource.id
  path_part   = "status"
}
resource "aws_api_gateway_method" "status_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.status_resource.id
  http_method   = "GET"
  authorization = "NONE"
}
resource "aws_api_gateway_integration" "status_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.status_resource.id
  http_method             = aws_api_gateway_method.status_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.get_onboarding_status_lambda.invoke_arn
}
# (OPTIONS for GET /status)
resource "aws_api_gateway_method" "status_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.status_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}
resource "aws_api_gateway_method_response" "status_options_200" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.status_resource.id
  http_method = aws_api_gateway_method.status_options_method.http_method
  status_code = "200"
  response_models = { "application/json" = "Empty" }
  response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => true }
}
resource "aws_api_gateway_integration" "status_options_integration" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.status_resource.id
  http_method = aws_api_gateway_method.status_options_method.http_method
  type        = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}
resource "aws_api_gateway_integration_response" "status_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.status_resource.id
  http_method = aws_api_gateway_method.status_options_method.http_method
  status_code = aws_api_gateway_method_response.status_options_200.status_code
  response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => "'${v}'" }
  response_templates = { "application/json" = "" }
  depends_on = [aws_api_gateway_integration.status_options_integration]
}

# --- API: POST /onboarding/manual-review (Admin) ---
resource "aws_api_gateway_resource" "review_resource" {
  rest_api_id = var.api_gateway_id
  parent_id   = aws_api_gateway_resource.onboarding_resource.id
  path_part   = "manual-review"
}
resource "aws_api_gateway_method" "review_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.review_resource.id
  http_method   = "POST"
  authorization = "NONE"
}
resource "aws_api_gateway_integration" "review_integration" {
  rest_api_id             = var.api_gateway_id
  resource_id             = aws_api_gateway_resource.review_resource.id
  http_method             = aws_api_gateway_method.review_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.manual_review_handler_lambda.invoke_arn
}
# (OPTIONS for /manual-review)
resource "aws_api_gateway_method" "review_options_method" {
  rest_api_id   = var.api_gateway_id
  resource_id   = aws_api_gateway_resource.review_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}
resource "aws_api_gateway_method_response" "review_options_200" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.review_resource.id
  http_method = aws_api_gateway_method.review_options_method.http_method
  status_code = "200"
  response_models = { "application/json" = "Empty" }
  response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => true }
}
resource "aws_api_gateway_integration" "review_options_integration" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.review_resource.id
  http_method = aws_api_gateway_method.review_options_method.http_method
  type        = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}
resource "aws_api_gateway_integration_response" "review_options_integration_response" {
  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_resource.review_resource.id
  http_method = aws_api_gateway_method.review_options_method.http_method
  status_code = aws_api_gateway_method_response.review_options_200.status_code
  response_parameters = { for k, v in local.cors_headers : "method.response.header.${k}" => "'${v}'" }
  response_templates = { "application/json" = "" }
  depends_on = [aws_api_gateway_integration.review_options_integration]
}


################################################################################
# --- 8. LAMBDA PERMISSIONS ---
################################################################################

resource "aws_lambda_permission" "api_gateway_start_onboarding" {
  statement_id  = "AllowAPIGatewayToInvokeStartOnboarding"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.start_onboarding_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}
resource "aws_lambda_permission" "api_gateway_get_onboarding_status" {
  statement_id  = "AllowAPIGatewayToInvokeGetOnboardingStatus"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_onboarding_status_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}
resource "aws_lambda_permission" "api_gateway_manual_review" {
  statement_id  = "AllowAPIGatewayToInvokeManualReview"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.manual_review_handler_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}



