module "org_foundation" {
  source = "../../modules/org-foundation"

  allowed_regions = var.allowed_regions
  member_accounts = var.member_accounts
}

module "security_baseline" {
  source = "../../modules/security-baseline"
  providers = {
    aws       = aws
    aws.audit = aws.audit
  }

  audit_account_id = var.audit_account_id
}

module "identity_center" {
  source = "../../modules/iam-identity-center"
}

# Organization-wide CloudTrail trail. Must be created from the management
# account; points at the bucket the log-archive module built in the Log
# Archive account (applied separately — see environments/log-archive-account).
resource "aws_cloudtrail" "organization" {
  name                          = "org-trail"
  s3_bucket_name                = var.log_archive_bucket_name
  is_organization_trail         = true
  is_multi_region_trail         = true
  enable_log_file_validation    = true
  kms_key_id                    = var.log_archive_kms_key_arn

  event_selector {
    read_write_type           = "All"
    include_management_events = true
  }

  depends_on = [module.org_foundation]
}
