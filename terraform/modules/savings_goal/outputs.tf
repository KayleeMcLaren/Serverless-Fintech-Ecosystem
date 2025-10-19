output "api_integrations_json" {
  description = "A JSON string of all API integrations to trigger a new deployment."
  value = jsonencode([
    aws_api_gateway_integration.create_savings_goal_integration,
    aws_api_gateway_integration.get_savings_goals_integration,
    aws_api_gateway_integration.delete_savings_goal_integration,
  ])
}