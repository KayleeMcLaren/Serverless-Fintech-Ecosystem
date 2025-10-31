output "api_gateway_config_hash" {
  description = "A hash of relevant API Gateway configurations to trigger deployment."
  value = sha1(jsonencode([
    # POST /onboarding/start
    aws_api_gateway_resource.onboarding_resource,
    aws_api_gateway_resource.start_resource,
    aws_api_gateway_method.start_method,
    aws_api_gateway_integration.start_integration,
    aws_api_gateway_method.start_options_method,
    aws_api_gateway_integration.start_options_integration,
    aws_api_gateway_method_response.start_options_200,
    aws_api_gateway_integration_response.start_options_integration_response,

    # GET /onboarding/{id}/status
    aws_api_gateway_resource.status_id_resource,
    aws_api_gateway_resource.status_resource,
    aws_api_gateway_method.status_method,
    aws_api_gateway_integration.status_integration,
    aws_api_gateway_method.status_options_method,
    aws_api_gateway_integration.status_options_integration,
    aws_api_gateway_method_response.status_options_200,
    aws_api_gateway_integration_response.status_options_integration_response,
    
    # POST /onboarding/manual-review
    aws_api_gateway_resource.review_resource,
    aws_api_gateway_method.review_method,
    aws_api_gateway_integration.review_integration,
    aws_api_gateway_method.review_options_method,
    aws_api_gateway_integration.review_options_integration,
    aws_api_gateway_method_response.review_options_200,
    aws_api_gateway_integration_response.review_options_integration_response,
  ]))
}

output "step_function_arn" {
  description = "The ARN of the onboarding Step Function"
  value       = aws_sfn_state_machine.onboarding_sfn.arn
}