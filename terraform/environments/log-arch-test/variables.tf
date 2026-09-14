variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "organization_id" {
  type = string
}

variable "bucket_name" {
  description = "Must be globally unique across all of S3."
  type        = string
}
