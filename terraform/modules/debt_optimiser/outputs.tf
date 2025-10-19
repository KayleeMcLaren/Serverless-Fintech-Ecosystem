output "api_integrations_json" {
  description = "A JSON string of all API integrations to trigger a new deployment."
  value = jsonencode([
    aws_api_gateway_integration.calculate_repayment_plan_integration,
  ])
}