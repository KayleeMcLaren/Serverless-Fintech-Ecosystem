variable "project_name" {
  description = "The name of the project"
  type        = string
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
}

variable "api_gateway_id" {
  description = "The ID of the shared API Gateway"
  type        = string
}

variable "api_gateway_root_resource_id" {
  description = "The ID of the API Gateway's root resource"
  type        = string
}

variable "api_gateway_execution_arn" {
  description = "The execution ARN of the API Gateway"
  type        = string
}

variable "dynamodb_table_name" {
  description = "The name of the savings goals DynamoDB table"
  type        = string
}

variable "dynamodb_table_arn" {
  description = "The ARN of the savings goals DynamoDB table"
  type        = string
}

variable "wallets_table_name" {
  description = "The name of the wallets DynamoDB table"
  type        = string
}

variable "wallets_table_arn" {
  description = "The ARN of the wallets DynamoDB table"
  type        = string
}