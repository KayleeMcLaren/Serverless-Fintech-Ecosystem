output "api_gateway_config_hash" {
  description = "A hash of relevant API Gateway configurations to trigger deployment."
  value = sha1(jsonencode([
    # POST /loan
    aws_api_gateway_resource.loan_resource,
    aws_api_gateway_method.apply_for_loan_method,
    aws_api_gateway_integration.apply_for_loan_integration,
    aws_api_gateway_method.apply_for_loan_options_method,
    aws_api_gateway_integration.apply_for_loan_options_integration,
    aws_api_gateway_method_response.apply_for_loan_options_200,
    aws_api_gateway_integration_response.apply_for_loan_options_integration_response,

    # GET /loan/{loan_id}
    aws_api_gateway_resource.loan_id_resource,
    aws_api_gateway_method.get_loan_method,
    aws_api_gateway_integration.get_loan_integration,

    # GET /loan/by-wallet/{wallet_id}
    aws_api_gateway_resource.loan_by_wallet_resource,
    aws_api_gateway_resource.loan_by_wallet_id_resource,
    aws_api_gateway_method.get_loans_by_wallet_method,
    aws_api_gateway_integration.get_loans_by_wallet_integration,

    # POST /loan/{loan_id}/approve
    aws_api_gateway_resource.approve_loan_resource,
    aws_api_gateway_method.approve_loan_method,
    aws_api_gateway_integration.approve_loan_integration,
    aws_api_gateway_method.approve_loan_options_method,
    aws_api_gateway_integration.approve_loan_options_integration,
    aws_api_gateway_method_response.approve_loan_options_200,
    aws_api_gateway_integration_response.approve_loan_options_integration_response,

    # POST /loan/{loan_id}/reject
    aws_api_gateway_resource.reject_loan_resource,
    aws_api_gateway_method.reject_loan_method,
    aws_api_gateway_integration.reject_loan_integration,
    aws_api_gateway_method.reject_loan_options_method,
    aws_api_gateway_integration.reject_loan_options_integration,
    aws_api_gateway_method_response.reject_loan_options_200,
    aws_api_gateway_integration_response.reject_loan_options_integration_response,

    # POST /loan/{loan_id}/repay
    aws_api_gateway_resource.repay_loan_resource,
    aws_api_gateway_method.repay_loan_method,
    aws_api_gateway_integration.repay_loan_integration,
    
    # OPTIONS for /loan/{loan_id}/repay
    aws_api_gateway_method.repay_loan_options_method,
    aws_api_gateway_method_response.repay_loan_options_200,
    aws_api_gateway_integration.repay_loan_options_integration,
    aws_api_gateway_integration_response.repay_loan_options_integration_response,
  ]))
}

output "loans_table_arn" {
  description = "The ARN of the micro-loans DynamoDB table"
  value       = var.dynamodb_table_arn
}