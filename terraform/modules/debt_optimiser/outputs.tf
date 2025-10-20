output "api_gateway_config_hash" {
  description = "A hash of relevant API Gateway configurations to trigger deployment."
  value = sha1(jsonencode([
    # POST /debt-optimiser
    aws_api_gateway_resource.debt_optimiser_resource,
    aws_api_gateway_method.calculate_repayment_plan_method,
    aws_api_gateway_integration.calculate_repayment_plan_integration,
  ]))
}