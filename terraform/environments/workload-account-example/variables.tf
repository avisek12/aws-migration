variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "app_name" {
  type = string
}

variable "environment" {
  type = string # "prod" | "nonprod"
}

variable "vpc_cidr" {
  description = "A /24 works cleanly with this module's subnetting math (3 tiers x up to 2 AZs = 6x /27)."
  type        = string
}

variable "azs" {
  type    = list(string)
  default = ["us-east-1a", "us-east-1b"]
}

variable "transit_gateway_id" {
  description = "Shared TGW id, output by environments/network-hub-account — accept the RAM share invitation in this account first (aws ram get-resource-share-invitations / accept-resource-share-invitation), or Terraform's aws_ram_resource_share_accepter."
  type        = string
}

variable "db_port" {
  type    = number
  default = 5432
}

variable "onprem_cidrs" {
  type    = list(string)
  default = []
}

variable "log_archive_bucket_name" {
  type = string
}

variable "log_archive_kms_key_arn" {
  type = string
}
