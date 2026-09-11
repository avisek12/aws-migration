variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "allowed_regions" {
  type    = list(string)
  default = ["us-east-1", "us-east-2"]
}

variable "audit_account_id" {
  description = "Account id delegated as GuardDuty/Security Hub administrator."
  type        = string
}

variable "log_archive_account_id" {
  type = string
}

variable "log_archive_bucket_name" {
  description = "Output of the log-archive module, applied separately in the Log Archive account. Passed here so the org trail can point at it."
  type        = string
}

variable "log_archive_kms_key_arn" {
  type = string
}

variable "member_accounts" {
  description = "Optional accounts to vend directly through org-foundation. Leave empty if using Control Tower's Account Factory instead."
  type = map(object({
    email = string
    ou    = string
  }))
  default = {}
}
