module "log_archive" {
  source = "../../modules/log-archive"

  organization_id = var.organization_id
  bucket_name     = var.bucket_name
}

# The Log Archive account is itself an account and needs the same baseline
# everything else gets — pointed at the bucket this very stack just created.
#
# depends_on is required here, not implied by the variable references above:
# account_baseline's Config delivery channel only depends on the bucket
# existing (via bucket_name/kms_key_arn), not on the bucket POLICY that
# actually grants Config permission to write to it — aws_s3_bucket_policy
# is a sibling resource inside log_archive with no output wired to it. Without
# this, Terraform can create the delivery channel and the bucket policy in
# parallel, and if the delivery channel's live write-access check runs before
# the policy is attached, it fails with an access-denied-style error. Forcing
# the whole log_archive module to finish first removes that race.
module "account_baseline" {
  source = "../../modules/account-baseline"

  log_archive_bucket_name = module.log_archive.bucket_name
  log_archive_kms_key_arn = module.log_archive.kms_key_arn

  depends_on = [module.log_archive]
}
