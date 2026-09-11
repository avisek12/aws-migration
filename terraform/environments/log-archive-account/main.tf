module "log_archive" {
  source = "../../modules/log-archive"

  organization_id = var.organization_id
  bucket_name     = var.bucket_name
}

# The Log Archive account is itself an account and needs the same baseline
# everything else gets — pointed at the bucket this very stack just created.
module "account_baseline" {
  source = "../../modules/account-baseline"

  log_archive_bucket_name = module.log_archive.bucket_name
  log_archive_kms_key_arn = module.log_archive.kms_key_arn
}
