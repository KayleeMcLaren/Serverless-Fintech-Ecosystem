output "api_integrations_json" {
  description = "A JSON string of all API integrations to trigger a new deployment."
  value = jsonencode([
    aws_api_gateway_integration.apply_for_loan_integration,
    aws_api_gateway_integration.get_loan_integration,
    aws_api_gateway_integration.get_loans_by_wallet_integration,
    aws_api_gateway_integration.approve_loan_integration,
    aws_api_gateway_integration.reject_loan_integration,
  ])
}