output "api_endpoint_url" {
  description = "The base URL for the API Gateway stage."
  value       = "${aws_api_gateway_stage.api_stage.invoke_url}"
}

output "cloudfront_domain_name" {
  description = "The domain name of the CloudFront distribution for the frontend"
  value       = aws_cloudfront_distribution.frontend_distribution.domain_name
}