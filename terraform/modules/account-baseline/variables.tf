variable "log_archive_bucket_name" {
  description = "Central log bucket name (from the log-archive module output), where this account's Config snapshots are delivered."
  type        = string
}

variable "log_archive_kms_key_arn" {
  type = string
}

variable "config_delivery_frequency" {
  description = "How often Config delivers a full configuration snapshot."
  type        = string
  default     = "TwentyFour_Hours"
}
