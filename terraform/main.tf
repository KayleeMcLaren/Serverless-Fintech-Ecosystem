terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0" 
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  project_name_prefix = "fintech-ecosystem"
  project_name        = "${local.project_name_prefix}-${terraform.workspace}"

  common_tags = {
    Project     = local.project_name_prefix
    Environment = terraform.workspace
  }
}

# --- SHARED RESOURCES ---

resource "aws_api_gateway_rest_api" "api" {
  name        = "${local.project_name}-api"
  description = "API for the Fintech Ecosystem"
  tags        = local.common_tags
}

resource "aws_dynamodb_table" "wallet_table" {
  name         = "${local.project_name}-wallets"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "wallet_id"
  attribute {
    name = "wallet_id"
    type = "S"
  }
  tags = local.common_tags
}

resource "aws_dynamodb_table" "loans_table" {
  name         = "${local.project_name}-loans"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "loan_id"

  attribute {
    name = "loan_id"
    type = "S"
  }
  attribute {
    name = "wallet_id"
    type = "S"
  }
  global_secondary_index {
    name            = "wallet_id-index"
    hash_key        = "wallet_id"
    projection_type = "ALL"
  }
  tags = local.common_tags
}

resource "aws_dynamodb_table" "transactions_table" {
  name         = "${local.project_name}-transactions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "transaction_id"

  attribute {
    name = "transaction_id"
    type = "S"
  }
  attribute {
    name = "wallet_id"
    type = "S"
  }
  global_secondary_index {
    name            = "wallet_id-index"
    hash_key        = "wallet_id"
    projection_type = "ALL"
  }
  tags = local.common_tags
}

resource "aws_dynamodb_table" "savings_goals_table" {
  name         = "${local.project_name}-savings-goals"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "goal_id"

  attribute {
    name = "goal_id"
    type = "S"
  }
  attribute {
    name = "wallet_id"
    type = "S"
  }
  global_secondary_index {
    name            = "wallet_id-index"
    hash_key        = "wallet_id"
    projection_type = "ALL"
  }
  tags = local.common_tags
}

resource "aws_dynamodb_table" "transactions_log_table" {
  name         = "${local.project_name}-transaction-logs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "transaction_id"

  attribute {
    name = "transaction_id"
    type = "S"
  }
  attribute {
    name = "wallet_id"
    type = "S"
  }
  attribute {
    name = "timestamp"
    type = "N"
  }
  attribute {
    name = "related_id"
    type = "S"
  }

  global_secondary_index {
    name            = "wallet_id-timestamp-index"
    hash_key        = "wallet_id"
    range_key       = "timestamp"
    projection_type = "ALL"
  }
  global_secondary_index {
    name            = "related_id-timestamp-index"
    hash_key        = "related_id"
    range_key       = "timestamp"
    projection_type = "ALL"
  }
  tags = local.common_tags
}

# The DynamoDB table for user onboarding status
resource "aws_dynamodb_table" "users_table" {
  name         = "${local.project_name}-users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id" # The main ID for the user

  attribute {
    name = "user_id"
    type = "S"
  }
  attribute {
    name = "email" # We'll index this to find users
    type = "S"
  }

  # This index lets us query by email to prevent duplicate signups
  global_secondary_index {
    name            = "email-index"
    hash_key        = "email"
    projection_type = "ALL"
  }

  tags = local.common_tags
}

resource "aws_api_gateway_deployment" "api_deployment" {
  rest_api_id = aws_api_gateway_rest_api.api.id

  triggers = {
    redeployment = sha1(
      "${module.digital_wallet.api_gateway_config_hash}${module.micro_loan.api_gateway_config_hash}${module.payment_processor.api_gateway_config_hash}${module.savings_goal.api_gateway_config_hash}${module.debt_optimiser.api_gateway_config_hash}${module.onboarding_orchestrator.api_gateway_config_hash}" # <-- ADD THIS NEW HASH
    )
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_authorizer.cognito_auth
  ]
}

resource "aws_api_gateway_stage" "api_stage" {
  deployment_id = aws_api_gateway_deployment.api_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.api.id
  stage_name    = "v1"
}

# Allow the Onboarding Step Function to invoke the Create Wallet Lambda
resource "aws_lambda_permission" "sfn_can_invoke_create_wallet" {
  statement_id  = "AllowStepFunctionToInvokeCreateWallet"
  action        = "lambda:InvokeFunction"
  function_name = module.digital_wallet.create_wallet_lambda_arn
  principal     = "states.amazonaws.com"

  # This links it to our specific Step Function execution
  source_arn    = module.onboarding_orchestrator.step_function_arn
}

resource "aws_sns_topic" "payment_events" {
  name = "${local.project_name}-payment-events"
  tags = local.common_tags
}

resource "aws_sns_topic" "loan_events" {
  name = "${local.project_name}-loan-events"
  tags = local.common_tags
}

# --- AWS Cognito User Pool ---
resource "aws_cognito_user_pool" "user_pool" {
  name = "${local.project_name}-user-pool"
  
  # Use email as the username
  username_attributes = ["email"]
  
  # Configure email as a required attribute
  schema {
    name                     = "email"
    attribute_data_type      = "String"
    mutable                  = true
    required                 = true
    string_attribute_constraints {
      min_length = 1
      max_length = 2048
    }
  }

  # Set a simple password policy for the demo
  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
    require_uppercase = true
  }

  # Allow users to sign themselves up
  admin_create_user_config {
    allow_admin_create_user_only = false
  }

  # We will auto-verify emails for this demo to skip email loops
  auto_verified_attributes = ["email"]

  lambda_config {
    pre_sign_up = aws_lambda_function.pre_signup_trigger_lambda.arn
  }

  tags = local.common_tags
}

# --- Cognito User Pool Client ---
# This is what the frontend app uses to interface with Cognito
resource "aws_cognito_user_pool_client" "user_pool_client" {
  name = "${local.project_name}-app-client"
  user_pool_id = aws_cognito_user_pool.user_pool.id

  # CRITICAL: This must be false for public web/mobile clients
  generate_secret = false

  # Allow the standard username/password flow
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]

  # Allow Cognito to remember devices
  enable_token_revocation = true
}

# --- API Gateway Authorizer ---
# This connects our API to our new Cognito User Pool
resource "aws_api_gateway_authorizer" "cognito_auth" {
  name                   = "${local.project_name}-cognito-authorizer"
  rest_api_id            = aws_api_gateway_rest_api.api.id
  type                   = "COGNITO_USER_POOLS"
  identity_source        = "method.request.header.Authorization" # Looks for the JWT token here
  provider_arns = [aws_cognito_user_pool.user_pool.arn]
  depends_on = [
    aws_cognito_user_pool.user_pool
  ]
}

# The S3 bucket for storing KYC documents (e.g., ID photos)
resource "aws_s3_bucket" "kyc_documents_bucket" {
  bucket = "${local.project_name}-kyc-documents-${random_id.bucket_suffix.hex}"
  tags   = local.common_tags
}

# Block all public access to the KYC bucket
resource "aws_s3_bucket_public_access_block" "kyc_bucket_pab" {
  bucket = aws_s3_bucket.kyc_documents_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- Lambda Function for Cognito Pre-Sign-Up Trigger ---

# (We need a simple IAM role for this Lambda)
data "aws_iam_policy_document" "cognito_trigger_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "cognito_trigger_role" {
  name               = "${local.project_name}-cognito-trigger-role"
  assume_role_policy = data.aws_iam_policy_document.cognito_trigger_assume_role.json
  tags               = local.common_tags
}

# (It also needs basic CloudWatch logging permissions)
resource "aws_iam_role_policy_attachment" "cognito_trigger_basic_execution" {
  role       = aws_iam_role.cognito_trigger_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# (Zip up the new code)
data "archive_file" "pre_signup_trigger_zip" {
  type        = "zip"
  source_dir  = "../src/pre_signup_trigger"
  output_path = "pre_signup_trigger.zip"
}

# (Create the Lambda function)
resource "aws_lambda_function" "pre_signup_trigger_lambda" {
  function_name    = "${local.project_name}-pre-signup-trigger"
  role             = aws_iam_role.cognito_trigger_role.arn
  filename         = data.archive_file.pre_signup_trigger_zip.output_path
  source_code_hash = data.archive_file.pre_signup_trigger_zip.output_base64sha256
  handler          = "handler.auto_confirm_user"
  runtime          = "python3.12"
  tags             = local.common_tags
}

# (Allow Cognito to invoke this Lambda)
resource "aws_lambda_permission" "cognito_allow_invoke_pre_signup" {
  statement_id  = "AllowCognitoToInvokePreSignup"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pre_signup_trigger_lambda.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.user_pool.arn
}

# --- SERVICE MODULES ---

# --- THIS IS THE CORRECT DIGITAL_WALLET BLOCK ---
module "digital_wallet" {
  source = "./modules/digital_wallet"
  providers = {
    aws = aws
  }

  project_name                 = local.project_name
  tags                         = local.common_tags
  api_gateway_id               = aws_api_gateway_rest_api.api.id
  api_gateway_root_resource_id = aws_api_gateway_rest_api.api.root_resource_id
  api_gateway_execution_arn    = aws_api_gateway_rest_api.api.execution_arn
  dynamodb_table_name          = aws_dynamodb_table.wallet_table.name
  dynamodb_table_arn           = aws_dynamodb_table.wallet_table.arn
  sns_topic_arn                = aws_sns_topic.loan_events.arn
  payment_sns_topic_arn        = aws_sns_topic.payment_events.arn
  transactions_log_table_name  = aws_dynamodb_table.transactions_log_table.name
  transactions_log_table_arn   = aws_dynamodb_table.transactions_log_table.arn
  frontend_cors_origin         = var.frontend_cors_origin
  api_gateway_authorizer_id    = aws_api_gateway_authorizer.cognito_auth.id
}
# --- END CORRECTION ---

module "micro_loan" {
  source = "./modules/micro_loan"
  providers = {
    aws = aws
  }

  project_name                 = local.project_name
  tags                         = local.common_tags
  api_gateway_id               = aws_api_gateway_rest_api.api.id
  api_gateway_root_resource_id = aws_api_gateway_rest_api.api.root_resource_id
  api_gateway_execution_arn    = aws_api_gateway_rest_api.api.execution_arn
  dynamodb_table_name          = aws_dynamodb_table.loans_table.name
  dynamodb_table_arn           = aws_dynamodb_table.loans_table.arn
  sns_topic_arn                = aws_sns_topic.loan_events.arn
  payment_sns_topic_arn        = aws_sns_topic.payment_events.arn
  transactions_log_table_name  = aws_dynamodb_table.transactions_log_table.name
  transactions_log_table_arn   = aws_dynamodb_table.transactions_log_table.arn
  frontend_cors_origin         = var.frontend_cors_origin
  api_gateway_authorizer_id    = aws_api_gateway_authorizer.cognito_auth.id
}

module "payment_processor" {
  source = "./modules/payment_processor"
  providers = {
    aws = aws
  }

  project_name                 = local.project_name
  tags                         = local.common_tags
  api_gateway_id               = aws_api_gateway_rest_api.api.id
  api_gateway_root_resource_id = aws_api_gateway_rest_api.api.root_resource_id
  api_gateway_execution_arn    = aws_api_gateway_rest_api.api.execution_arn
  dynamodb_table_name          = aws_dynamodb_table.transactions_table.name
  dynamodb_table_arn           = aws_dynamodb_table.transactions_table.arn
  sns_topic_arn                = aws_sns_topic.payment_events.arn
  frontend_cors_origin         = var.frontend_cors_origin
  api_gateway_authorizer_id    = aws_api_gateway_authorizer.cognito_auth.id
}

module "savings_goal" {
  source = "./modules/savings_goal"
  providers = {
    aws = aws
  }

  project_name                 = local.project_name
  tags                         = local.common_tags
  api_gateway_id               = aws_api_gateway_rest_api.api.id
  api_gateway_root_resource_id = aws_api_gateway_rest_api.api.root_resource_id
  api_gateway_execution_arn    = aws_api_gateway_rest_api.api.execution_arn
  dynamodb_table_name          = aws_dynamodb_table.savings_goals_table.name
  dynamodb_table_arn           = aws_dynamodb_table.savings_goals_table.arn
  wallets_table_name           = module.digital_wallet.wallet_table_name
  wallets_table_arn            = module.digital_wallet.wallet_table_arn
  transactions_log_table_name  = aws_dynamodb_table.transactions_log_table.name
  transactions_log_table_arn   = aws_dynamodb_table.transactions_log_table.arn
  frontend_cors_origin         = var.frontend_cors_origin
  api_gateway_authorizer_id    = aws_api_gateway_authorizer.cognito_auth.id
}

module "debt_optimiser" {
  source = "./modules/debt_optimiser"
  providers = {
    aws = aws
  }

  project_name                 = local.project_name
  tags                         = local.common_tags
  api_gateway_id               = aws_api_gateway_rest_api.api.id
  api_gateway_root_resource_id = aws_api_gateway_rest_api.api.root_resource_id
  api_gateway_execution_arn    = aws_api_gateway_rest_api.api.execution_arn
  loans_table_arn              = module.micro_loan.loans_table_arn
  frontend_cors_origin         = var.frontend_cors_origin
  api_gateway_authorizer_id    = aws_api_gateway_authorizer.cognito_auth.id
}

module "onboarding_orchestrator" {
  source = "./modules/onboarding_orchestrator"
  providers = {
    aws = aws
  }

  project_name                 = local.project_name
  tags                         = local.common_tags
  api_gateway_id               = aws_api_gateway_rest_api.api.id
  api_gateway_root_resource_id = aws_api_gateway_rest_api.api.root_resource_id
  api_gateway_execution_arn    = aws_api_gateway_rest_api.api.execution_arn
  
  users_table_arn              = aws_dynamodb_table.users_table.arn
  kyc_documents_bucket_arn     = aws_s3_bucket.kyc_documents_bucket.arn
  
  # We need to get the ARN from the digital_wallet module.
  # This requires adding an output to that module first.
  create_wallet_lambda_arn   = module.digital_wallet.create_wallet_lambda_arn 
  
  frontend_cors_origin         = var.frontend_cors_origin
  api_gateway_authorizer_id    = aws_api_gateway_authorizer.cognito_auth.id
}

# --- FRONTEND DEPLOYMENT (S3 & CloudFront) ---

resource "aws_s3_bucket" "frontend_bucket" {
  bucket = "${local.project_name}-frontend-bucket-${random_id.bucket_suffix.hex}"
  tags   = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "frontend_bucket_pab" {
  bucket = aws_s3_bucket.frontend_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_website_configuration" "frontend_website_config" {
  bucket = aws_s3_bucket.frontend_bucket.id

  index_document {
    suffix = "index.html"
  }
  error_document {
    key = "index.html"
  }
}

resource "random_id" "bucket_suffix" {
  byte_length = 8
}

# --- CloudFront Distribution ---
resource "aws_cloudfront_origin_access_control" "frontend_oac" {
  name                        = "${local.project_name}-frontend-oac"
  description                 = "OAC for frontend bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior            = "always"
  signing_protocol            = "sigv4"
}

resource "aws_cloudfront_distribution" "frontend_distribution" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${local.project_name} Frontend Distribution"
  default_root_object = "index.html"

  origin {
    domain_name              = aws_s3_bucket.frontend_bucket.bucket_regional_domain_name
    origin_id                = "S3-${aws_s3_bucket.frontend_bucket.id}"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend_oac.id
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.frontend_bucket.id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
    compress               = true
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  custom_error_response {
    error_caching_min_ttl = 10
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
  }
  custom_error_response {
    error_caching_min_ttl = 10
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  tags = local.common_tags
}

# --- S3 Bucket Policy to Allow CloudFront Access via OAC ---
data "aws_iam_policy_document" "frontend_bucket_policy_doc" {
  statement {
    actions   = ["s3:GetObject"]
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    resources = ["${aws_s3_bucket.frontend_bucket.arn}/*"]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.frontend_distribution.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "frontend_bucket_policy" {
  bucket = aws_s3_bucket.frontend_bucket.id
  policy = data.aws_iam_policy_document.frontend_bucket_policy_doc.json
}
