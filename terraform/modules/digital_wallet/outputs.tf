output "api_integrations_json" {
  description = "A JSON string of all API integrations to trigger a new deployment."
  value = jsonencode([
    aws_api_gateway_integration.create_lambda_integration,
    aws_api_gateway_integration.get_lambda_integration,
    aws_api_gateway_integration.credit_lambda_integration,
    aws_api_gateway_integration.debit_lambda_integration,
  ])
}

output "wallet_table_name" {
  description = "The name of the digital wallet DynamoDB table"
  value       = var.dynamodb_table_name
}

output "wallet_table_arn" {
  description = "The ARN of the digital wallet DynamoDB table"
  value       = var.dynamodb_table_arn
}