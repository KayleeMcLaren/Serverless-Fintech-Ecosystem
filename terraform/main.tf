provider "aws" {
  region = var.aws_region
}

locals {
  project_name = "fintech-ecosystem"
  common_tags = {
    Project = local.project_name
  }
}

# --- SHARED RESOURCES ---

# The main API Gateway for all services
resource "aws_api_gateway_rest_api" "api" {
  name        = "${local.project_name}-api"
  description = "API for the Fintech Ecosystem"
  tags        = local.common_tags
}

# The DynamoDB table for wallets
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

# The DynamoDB table for loans
resource "aws_dynamodb_table" "loans_table" {
  name         = "${local.project_name}-loans"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "loan_id" # The main ID for the loan

  attribute {
    name = "loan_id"
    type = "S"
  }
  attribute {
    name = "wallet_id" # We'll index this
    type = "S"
  }

  # This index lets us query all loans by a user's wallet_id
  global_secondary_index {
    name            = "wallet_id-index"
    hash_key        = "wallet_id"
    projection_type = "ALL" # Lets us get all loan data when querying the index
  }

  tags = local.common_tags
}

# The DynamoDB table for all transactions
resource "aws_dynamodb_table" "transactions_table" {
  name         = "${local.project_name}-transactions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "transaction_id"

  attribute {
    name = "transaction_id"
    type = "S"
  }
  attribute {
    name = "wallet_id" # We'll index this
    type = "S"
  }

  # This index lets us query all transactions by a user's wallet_id
  global_secondary_index {
    name            = "wallet_id-index"
    hash_key        = "wallet_id"
    projection_type = "ALL"
  }

  tags = local.common_tags
}

# The DynamoDB table for savings goals
resource "aws_dynamodb_table" "savings_goals_table" {
  name         = "${local.project_name}-savings-goals"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "goal_id" # The main ID for the goal

  attribute {
    name = "goal_id"
    type = "S"
  }
  attribute {
    name = "wallet_id" # We'll index this
    type = "S"
  }

  # This index lets us query all goals by a user's wallet_id
  global_secondary_index {
    name            = "wallet_id-index"
    hash_key        = "wallet_id"
    projection_type = "ALL" # Get all goal data when querying
  }

  tags = local.common_tags
}

# The DynamoDB table for transaction history logs
resource "aws_dynamodb_table" "transactions_log_table" {
  name         = "${local.project_name}-transaction-logs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "transaction_id" # Unique ID for each log entry

  attribute {
    name = "transaction_id"
    type = "S"
  }
  attribute {
    name = "wallet_id" # We'll index this to query by wallet
    type = "S"
  }
  attribute {
    name = "timestamp" # Index this for sorting by time
    type = "N" # Store as Unix timestamp (number)
  }
  attribute { 
    name = "related_id" 
    type = "S" 
    }

  # GSI to query transactions by wallet, sorted by time
  global_secondary_index {
    name            = "wallet_id-timestamp-index"
    hash_key        = "wallet_id"
    range_key       = "timestamp" # Sort key
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "related_id-timestamp-index" # New index name
    hash_key        = "related_id"                 # Query by goal_id (stored in related_id)
    range_key       = "timestamp"                  # Sort by time
    projection_type = "ALL"                        # Get all transaction data
  }

  tags = local.common_tags
}

# The deployment for the API Gateway
resource "aws_api_gateway_deployment" "api_deployment" {
  rest_api_id = aws_api_gateway_rest_api.api.id

  # --- THIS IS THE UPDATED BLOCK ---
  # We now combine the outputs from ALL FIVE modules.
  triggers = {
    redeployment = sha1(
      "${module.digital_wallet.api_gateway_config_hash}${module.micro_loan.api_gateway_config_hash}${module.payment_processor.api_gateway_config_hash}${module.savings_goal.api_gateway_config_hash}${module.debt_optimiser.api_gateway_config_hash}"
      # NOTE: You will need to rename the output in other modules too!
    )
  }
  # ---------------------------------

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "api_stage" {
  deployment_id = aws_api_gateway_deployment.api_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.api.id
  stage_name    = "v1"
}

# SNS Topic for payment processing events
resource "aws_sns_topic" "payment_events" {
  name = "${local.project_name}-payment-events"
  tags = local.common_tags
}

# SNS Topic for loan status updates (e.g., approval)
resource "aws_sns_topic" "loan_events" {
  name = "${local.project_name}-loan-events"
  tags = local.common_tags
}


# --- SERVICE MODULES ---

module "digital_wallet" {
  source = "./modules/digital_wallet"

  project_name                 = local.project_name
  tags                         = local.common_tags
  api_gateway_id               = aws_api_gateway_rest_api.api.id
  api_gateway_root_resource_id = aws_api_gateway_rest_api.api.root_resource_id
  api_gateway_execution_arn    = aws_api_gateway_rest_api.api.execution_arn
  dynamodb_table_name          = aws_dynamodb_table.wallet_table.name
  dynamodb_table_arn           = aws_dynamodb_table.wallet_table.arn
  sns_topic_arn                = aws_sns_topic.loan_events.arn
  payment_sns_topic_arn        = aws_sns_topic.payment_events.arn
  transactions_log_table_name = aws_dynamodb_table.transactions_log_table.name
  transactions_log_table_arn  = aws_dynamodb_table.transactions_log_table.arn
}

module "micro_loan" {
  source = "./modules/micro_loan"

  project_name                 = local.project_name
  tags                         = local.common_tags
  api_gateway_id               = aws_api_gateway_rest_api.api.id
  api_gateway_root_resource_id = aws_api_gateway_rest_api.api.root_resource_id
  api_gateway_execution_arn    = aws_api_gateway_rest_api.api.execution_arn
  dynamodb_table_name          = aws_dynamodb_table.loans_table.name
  dynamodb_table_arn           = aws_dynamodb_table.loans_table.arn
  sns_topic_arn                = aws_sns_topic.loan_events.arn
}

module "payment_processor" {
  source = "./modules/payment_processor"

  project_name                 = local.project_name
  tags                         = local.common_tags
  api_gateway_id               = aws_api_gateway_rest_api.api.id
  api_gateway_root_resource_id = aws_api_gateway_rest_api.api.root_resource_id
  api_gateway_execution_arn    = aws_api_gateway_rest_api.api.execution_arn
  dynamodb_table_name          = aws_dynamodb_table.transactions_table.name
  dynamodb_table_arn           = aws_dynamodb_table.transactions_table.arn
  sns_topic_arn                = aws_sns_topic.payment_events.arn
}

module "savings_goal" {
  source = "./modules/savings_goal"

  project_name                 = local.project_name
  tags                         = local.common_tags
  api_gateway_id               = aws_api_gateway_rest_api.api.id
  api_gateway_root_resource_id = aws_api_gateway_rest_api.api.root_resource_id
  api_gateway_execution_arn    = aws_api_gateway_rest_api.api.execution_arn
  dynamodb_table_name          = aws_dynamodb_table.savings_goals_table.name
  dynamodb_table_arn           = aws_dynamodb_table.savings_goals_table.arn
  wallets_table_name           = module.digital_wallet.wallet_table_name
  wallets_table_arn            = module.digital_wallet.wallet_table_arn
  transactions_log_table_name = aws_dynamodb_table.transactions_log_table.name
  transactions_log_table_arn  = aws_dynamodb_table.transactions_log_table.arn
}

module "debt_optimiser" {
  source = "./modules/debt_optimiser"

  project_name                 = local.project_name
  tags                         = local.common_tags
  api_gateway_id               = aws_api_gateway_rest_api.api.id
  api_gateway_root_resource_id = aws_api_gateway_rest_api.api.root_resource_id
  api_gateway_execution_arn    = aws_api_gateway_rest_api.api.execution_arn
  loans_table_arn              = module.micro_loan.loans_table_arn
}

# --- FRONTEND DEPLOYMENT (S3 & CloudFront) ---

# --- S3 Bucket for Frontend Static Files ---
resource "aws_s3_bucket" "frontend_bucket" {
  bucket = "${local.project_name}-frontend-bucket-${random_id.bucket_suffix.hex}" # Unique bucket name

  tags = local.common_tags
}

# Block public access as CloudFront will handle access via OAC
resource "aws_s3_bucket_public_access_block" "frontend_bucket_pab" {
  bucket = aws_s3_bucket.frontend_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable website hosting configuration (even though access is restricted to CloudFront)
# CloudFront uses this to know the index document.
resource "aws_s3_bucket_website_configuration" "frontend_website_config" {
  bucket = aws_s3_bucket.frontend_bucket.id

  index_document {
    suffix = "index.html"
  }
  error_document {
    key = "index.html" # Redirect errors back to the single-page app
  }
}

# Add a random suffix to bucket name for global uniqueness
resource "random_id" "bucket_suffix" {
  byte_length = 8
}

# --- CloudFront Distribution ---
resource "aws_cloudfront_origin_access_control" "frontend_oac" {
  name                              = "${local.project_name}-frontend-oac"
  description                       = "OAC for frontend bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
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
    default_ttl            = 3600 # Cache objects for 1 hour by default
    max_ttl                = 86400 # Cache objects for 1 day maximum
    compress               = true
  }

  # Redirect HTTP to HTTPS
  viewer_certificate {
    cloudfront_default_certificate = true
  }

  # Handle single-page app routing for 403/404 errors
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
      restriction_type = "none" # Allow access from anywhere
    }
  }

  tags = local.common_tags
}

# --- S3 Bucket Policy to Allow CloudFront Access via OAC ---
data "aws_iam_policy_document" "frontend_bucket_policy_doc" {
  statement {
    actions    = ["s3:GetObject"]
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    resources = ["${aws_s3_bucket.frontend_bucket.arn}/*"] # Grant access to objects in the bucket

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

# --- Output the CloudFront Domain Name ---
output "cloudfront_domain_name" {
  description = "The domain name of the CloudFront distribution for the frontend"
  value       = aws_cloudfront_distribution.frontend_distribution.domain_name
}