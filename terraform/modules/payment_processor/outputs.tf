output "api_integrations_json" {
  description = "A JSON string of all API integrations to trigger a new deployment."
  value = jsonencode([
    aws_api_gateway_integration.request_payment_integration,
    aws_api_gateway_integration.get_transaction_status_integration,
  ])
}