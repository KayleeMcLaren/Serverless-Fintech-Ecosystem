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
