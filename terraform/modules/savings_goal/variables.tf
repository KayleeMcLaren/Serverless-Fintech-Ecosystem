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
  description = "The name of the DynamoDB table for savings goals."
  type        = string
}

variable "dynamodb_table_arn" {
  description = "The ARN of the DynamoDB table for savings goals."
  type        = string
}

variable "wallets_table_name" {
  description = "The name of the wallets DynamoDB table."
  type        = string
}

variable "wallets_table_arn" {
  description = "The ARN of the wallets DynamoDB table."
  type        = string
}

variable "transactions_log_table_name" {
  description = "The name of the transaction logs DynamoDB table"
  type        = string
}

variable "transactions_log_table_arn" {
  description = "The ARN of the transaction logs DynamoDB table"
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