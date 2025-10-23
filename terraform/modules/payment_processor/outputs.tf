output "api_gateway_config_hash" {
  description = "A hash of relevant API Gateway configurations to trigger deployment."
  value = sha1(jsonencode([
    # POST /payment
    aws_api_gateway_resource.payment_resource,
    aws_api_gateway_method.request_payment_method,
    aws_api_gateway_integration.request_payment_integration,
    aws_api_gateway_method.request_payment_options_method,
    aws_api_gateway_integration.request_payment_options_integration,
    aws_api_gateway_method_response.request_payment_options_200,

    # GET /payment/{transaction_id}
    aws_api_gateway_resource.transaction_id_resource,
    aws_api_gateway_method.get_transaction_status_method,
    aws_api_gateway_integration.get_transaction_status_integration,
    aws_api_gateway_method.get_transaction_status_options_method,
    aws_api_gateway_integration.get_transaction_status_options_integration,
    aws_api_gateway_method_response.get_transaction_status_options_200,

    # GET /payment/by-wallet/{wallet_id}
    aws_api_gateway_resource.payment_by_wallet_resource,
    aws_api_gateway_resource.payment_by_wallet_id_resource,
    aws_api_gateway_method.get_payments_by_wallet_method,
    aws_api_gateway_integration.get_payments_by_wallet_integration,
    aws_api_gateway_method.get_payments_by_wallet_options_method,
    aws_api_gateway_integration.get_payments_by_wallet_options_integration,
    aws_api_gateway_method_response.get_payments_by_wallet_options_200,
  ]))
}