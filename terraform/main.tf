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

# The deployment for the API Gateway
resource "aws_api_gateway_deployment" "api_deployment" {
  rest_api_id = aws_api_gateway_rest_api.api.id

  # --- THIS IS THE UPDATED BLOCK ---
  # It now listens to the output from the digital_wallet module.
  # If any API integration in that module changes, this trigger
  # will fire and create a new deployment.
  triggers = {
    redeployment = sha1(module.digital_wallet.api_integrations_json)
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
}