variable "project_name" {
  description = "The name of the overall project."
  type        = string
}

variable "tags" {
  description = "A map of tags to apply to all resources."
  type        = map(string)
}

variable "api_gateway_id" {
  description = "The ID of the parent API Gateway REST API."
  type        = string
}

variable "api_gateway_root_resource_id" {
  description = "The ID of the root resource of the API Gateway."
  type        = string
}

variable "api_gateway_execution_arn" {
  description = "The execution ARN of the API Gateway."
  type        = string
}

variable "dynamodb_table_name" {
  description = "The name of the DynamoDB table for transactions."
  type        = string
}

variable "dynamodb_table_arn" {
  description = "The ARN of the DynamoDB table for transactions."
  type        = string
}

variable "sns_topic_arn" {
  description = "The ARN of the SNS topic for payment events"
  type        = string
}

variable "frontend_cors_origin" {
  description = "The allowed CORS origin for the frontend"
  type        = string
}

variable "api_gateway_authorizer_id" {
  description = "The ID of the Cognito API Gateway Authorizer"
  type        = string
}