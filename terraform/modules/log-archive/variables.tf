variable "organization_id" {
  description = "AWS Organizations id (e.g. o-xxxxxxxxxx) — scopes the bucket policy to only this org's accounts."
  type        = string
}

variable "bucket_name" {
  description = "Globally-unique name for the central log bucket."
  type        = string
}

variable "log_retention_days" {
  description = "Days before objects expire entirely. Set to null to retain forever (common for CloudTrail in regulated environments)."
  type        = number
  default     = 2555 # ~7 years
}

variable "transition_to_ia_days" {
  type    = number
  default = 30
}

variable "transition_to_glacier_days" {
  type    = number
  default = 90
}
