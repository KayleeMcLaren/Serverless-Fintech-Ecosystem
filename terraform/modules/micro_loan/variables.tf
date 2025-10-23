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
  description = "The name of the loans DynamoDB table"
  type        = string
}

variable "dynamodb_table_arn" {
  description = "The ARN of the loans DynamoDB table"
  type        = string
}

variable "sns_topic_arn" {
  description = "The ARN of the SNS topic for loan events"
  type        = string
}

variable "payment_sns_topic_arn" { # This is for PAYMENT_EVENTS
  description = "The ARN of the SNS topic for payment events"
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