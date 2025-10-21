output "api_gateway_config_hash" {
  description = "A hash of relevant API Gateway configurations to trigger deployment."
  value = sha1(jsonencode([
    # POST /loan
    aws_api_gateway_resource.loan_resource,
    aws_api_gateway_method.apply_for_loan_method,
    aws_api_gateway_integration.apply_for_loan_integration,
    aws_api_gateway_method.apply_for_loan_options_method,          # OPTIONS
    aws_api_gateway_integration.apply_for_loan_options_integration, # OPTIONS
    aws_api_gateway_method_response.apply_for_loan_options_200,   # OPTIONS

    # GET /loan/{loan_id}
    aws_api_gateway_resource.loan_id_resource,
    aws_api_gateway_method.get_loan_method,
    aws_api_gateway_integration.get_loan_integration,
    # (No OPTIONS needed for simple GET)

    # GET /loan/by-wallet/{wallet_id}
    aws_api_gateway_resource.loan_by_wallet_resource,
    aws_api_gateway_resource.loan_by_wallet_id_resource,
    aws_api_gateway_method.get_loans_by_wallet_method,
    aws_api_gateway_integration.get_loans_by_wallet_integration,
    # (No OPTIONS needed for simple GET)

    # POST /loan/{loan_id}/approve
    aws_api_gateway_resource.approve_loan_resource,
    aws_api_gateway_method.approve_loan_method,
    aws_api_gateway_integration.approve_loan_integration,
    aws_api_gateway_method.approve_loan_options_method,          # OPTIONS
    aws_api_gateway_integration.approve_loan_options_integration, # OPTIONS
    aws_api_gateway_method_response.approve_loan_options_200,   # OPTIONS

    # POST /loan/{loan_id}/reject
    aws_api_gateway_resource.reject_loan_resource,
    aws_api_gateway_method.reject_loan_method,
    aws_api_gateway_integration.reject_loan_integration,
    aws_api_gateway_method.reject_loan_options_method,          # OPTIONS
    aws_api_gateway_integration.reject_loan_options_integration, # OPTIONS
    aws_api_gateway_method_response.reject_loan_options_200,   # OPTIONS
  ]))
}

# Keep this output as well, since the debt_optimiser module uses it
output "loans_table_arn" {
  description = "The ARN of the micro-loans DynamoDB table"
  value       = var.dynamodb_table_arn
}