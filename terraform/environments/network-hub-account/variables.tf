variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "azs" {
  type    = list(string)
  default = ["us-east-1a", "us-east-1b"]
}

variable "egress_vpc_cidr" {
  type    = string
  default = "10.0.0.0/24"
}

variable "enable_direct_connect" {
  type    = bool
  default = false
}

variable "direct_connect_gateway_id" {
  type    = string
  default = null
}

variable "enable_vpn_backup" {
  type    = bool
  default = false
}

variable "customer_gateway_ip" {
  type    = string
  default = null
}

variable "workload_account_ids" {
  description = "Every workload/shared-services account id that needs to attach a VPC to this Transit Gateway."
  type        = list(string)
  default     = []
}

variable "log_archive_bucket_name" {
  type = string
}

variable "log_archive_kms_key_arn" {
  type = string
}
