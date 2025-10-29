variable "aws_region" {
  description = "The AWS region where resources will be created."
  type        = string
  default     = "us-east-1"
}

variable "frontend_cors_origin" {
  description = "The allowed CORS origin for the frontend (e.g., http://localhost:5173 or https://...)"
  type        = string
  default     = "http://localhost:5173"
}