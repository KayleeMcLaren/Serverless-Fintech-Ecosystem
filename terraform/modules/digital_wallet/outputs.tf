output "api_gateway_config_hash" {
  description = "A hash of relevant API Gateway configurations to trigger deployment."
  value = sha1(jsonencode([
    # List all resources, methods, integrations, and method responses
    aws_api_gateway_resource.wallet_resource,
    aws_api_gateway_method.create_wallet_method,
    aws_api_gateway_integration.create_lambda_integration,
    # Add method responses if you define them explicitly, e.g., aws_api_gateway_method_response.create_wallet_201

    aws_api_gateway_resource.wallet_id_resource,
    aws_api_gateway_method.get_wallet_method,
    aws_api_gateway_integration.get_lambda_integration,

    aws_api_gateway_resource.credit_resource,
    aws_api_gateway_method.credit_wallet_method,
    aws_api_gateway_integration.credit_lambda_integration,
    aws_api_gateway_method.credit_options_method,          # Add OPTIONS method
    aws_api_gateway_integration.credit_options_integration, # Add OPTIONS integration
    aws_api_gateway_method_response.credit_options_200,   # Add OPTIONS response

    aws_api_gateway_resource.debit_resource,
    aws_api_gateway_method.debit_wallet_method,
    aws_api_gateway_integration.debit_lambda_integration,
    aws_api_gateway_method.debit_options_method,           # Add OPTIONS method
    aws_api_gateway_integration.debit_options_integration,  # Add OPTIONS integration
    aws_api_gateway_method_response.debit_options_200,    # Add OPTIONS response
  ]))
}

# --- ADD THESE IF THEY ARE MISSING ---
output "wallet_table_name" {
  description = "The name of the digital wallet DynamoDB table"
  value       = var.dynamodb_table_name # Reads from the input variable
}

output "wallet_table_arn" {
  description = "The ARN of the digital wallet DynamoDB table"
  value       = var.dynamodb_table_arn # Reads from the input variable
}
# ---