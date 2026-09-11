# GuardDuty and Security Hub for this account are configured remotely by
# the security-baseline module in environments/management (delegated
# administration) — nothing to duplicate here. This stack just gives the
# Audit account the same baseline every account gets.

module "account_baseline" {
  source = "../../modules/account-baseline"

  log_archive_bucket_name = var.log_archive_bucket_name
  log_archive_kms_key_arn = var.log_archive_kms_key_arn
}
