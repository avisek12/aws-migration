variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "state_bucket_name" {
  description = "Globally-unique S3 bucket name for THIS account's Terraform state, e.g. \"acme-tfstate-management\", \"acme-tfstate-log-archive\"."
  type        = string
}

variable "lock_table_name" {
  type    = string
  default = "terraform-locks"
}
