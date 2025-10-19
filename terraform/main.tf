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


# The deployment for the API Gateway
resource "aws_api_gateway_deployment" "api_deployment" {
  rest_api_id = aws_api_gateway_rest_api.api.id

  # --- THIS IS THE UPDATED BLOCK ---
  # We now combine the outputs from ALL FOUR modules.
  triggers = {
    redeployment = sha1(
      "${module.digital_wallet.api_integrations_json}${module.micro_loan.api_integrations_json}${module.payment_processor.api_integrations_json}${module.savings_goal.api_integrations_json}"
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
}