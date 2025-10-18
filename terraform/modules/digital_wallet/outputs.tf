output "api_integrations" {
  description = "A list of API gateway integrations created by this module."
  value = [
    aws_api_gateway_integration.create_lambda_integration,
    aws_api_gateway_integration.get_lambda_integration
  ]
}