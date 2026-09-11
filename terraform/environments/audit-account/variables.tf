variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "log_archive_bucket_name" {
  type = string
}

variable "log_archive_kms_key_arn" {
  type = string
}
