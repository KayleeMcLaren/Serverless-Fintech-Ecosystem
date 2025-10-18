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
  description = "The name of the DynamoDB table for wallets."
  type        = string
}

variable "dynamodb_table_arn" {
  description = "The ARN of the DynamoDB table for wallets."
  type        = string
}