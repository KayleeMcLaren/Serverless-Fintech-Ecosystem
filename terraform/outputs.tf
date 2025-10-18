output "api_endpoint_url" {
  description = "The base URL for the API Gateway stage."
  value       = "${aws_api_gateway_stage.api_stage.invoke_url}"
}