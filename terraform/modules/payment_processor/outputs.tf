output "api_gateway_config_hash" {
  description = "A hash of relevant API Gateway configurations to trigger deployment."
  value = sha1(jsonencode([
    # POST /payment
    aws_api_gateway_resource.payment_resource,
    aws_api_gateway_method.request_payment_method,
    aws_api_gateway_integration.request_payment_integration,

    # GET /payment/{transaction_id}
    aws_api_gateway_resource.transaction_id_resource,
    aws_api_gateway_method.get_transaction_status_method,
    aws_api_gateway_integration.get_transaction_status_integration,
  ]))
}