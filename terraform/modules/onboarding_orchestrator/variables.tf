variable "project_name" {
  description = "The name of the overall project (e.g., fintech-ecosystem-prd)."
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

variable "users_table_arn" {
  description = "The ARN of the DynamoDB table for users."
  type        = string
}

variable "kyc_documents_bucket_arn" {
  description = "The ARN of the S3 bucket for KYC documents."
  type        = string
}

variable "create_wallet_lambda_arn" {
  description = "The ARN of the create_wallet Lambda function (which the Step Function will invoke)."
  type        = string
}

variable "frontend_cors_origin" {
  description = "The allowed CORS origin for the frontend."
  type        = string
}

variable "api_gateway_authorizer_id" {
  description = "The ID of the Cognito API Gateway Authorizer"
  type        = string
}