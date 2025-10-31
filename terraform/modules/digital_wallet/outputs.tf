output "api_gateway_config_hash" {
  description = "A hash of relevant API Gateway configurations to trigger deployment."
  value = sha1(jsonencode([
    # /wallet
    aws_api_gateway_resource.wallet_resource,

    # /wallet/{wallet_id}
    aws_api_gateway_resource.wallet_id_resource,
    aws_api_gateway_method.get_wallet_method,
    aws_api_gateway_integration.get_lambda_integration,
    aws_api_gateway_method.get_wallet_options_method,
    aws_api_gateway_integration.get_wallet_options_integration,
    aws_api_gateway_method_response.get_wallet_options_200,
    aws_api_gateway_integration_response.get_wallet_options_integration_response,

    # /wallet/{wallet_id}/credit
    aws_api_gateway_resource.credit_resource,
    aws_api_gateway_method.credit_wallet_method,
    aws_api_gateway_integration.credit_lambda_integration,
    aws_api_gateway_method.credit_options_method,
    aws_api_gateway_integration.credit_options_integration,
    aws_api_gateway_method_response.credit_options_200,
    aws_api_gateway_integration_response.credit_options_integration_response,

    # /wallet/{wallet_id}/debit
    aws_api_gateway_resource.debit_resource,
    aws_api_gateway_method.debit_wallet_method,
    aws_api_gateway_integration.debit_lambda_integration,
    aws_api_gateway_method.debit_options_method,
    aws_api_gateway_integration.debit_options_integration,
    aws_api_gateway_method_response.debit_options_200,
    aws_api_gateway_integration_response.debit_options_integration_response,

    # /wallet/{wallet_id}/transactions
    aws_api_gateway_resource.transactions_resource,
    aws_api_gateway_method.get_transactions_method,
    aws_api_gateway_integration.get_transactions_integration,
    aws_api_gateway_method.get_transactions_options_method,
    aws_api_gateway_integration.get_transactions_options_integration,
    aws_api_gateway_method_response.get_transactions_options_200,
    aws_api_gateway_integration_response.get_transactions_options_integration_response,
  ]))
}

# --- Wallet Table Outputs ---
output "wallet_table_name" {
  description = "The name of the digital wallet DynamoDB table"
  value       = var.dynamodb_table_name
}

output "wallet_table_arn" {
  description = "The ARN of the digital wallet DynamoDB table"
  value       = var.dynamodb_table_arn
}

output "create_wallet_lambda_arn" {
  description = "The ARN of the create_wallet Lambda function."
  value       = aws_lambda_function.create_wallet_lambda.arn
}