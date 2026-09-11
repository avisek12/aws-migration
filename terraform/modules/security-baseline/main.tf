# This module needs TWO provider configurations: the default `aws` provider
# authenticated to the MANAGEMENT account (delegation is a management-account
# -only action), and `aws.audit` authenticated to the Audit account (where
# GuardDuty/Security Hub actually run once delegated). Call it like:
#
#   module "security_baseline" {
#     source = "../../modules/security-baseline"
#     providers = {
#       aws       = aws
#       aws.audit = aws.audit
#     }
#     audit_account_id = "111111111111"
#   }

terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      configuration_aliases = [aws.audit]
    }
  }
}

# ---------------------------------------------------------------------------
# Delegate administration to the Audit account (run as management account)
# ---------------------------------------------------------------------------

resource "aws_guardduty_organization_admin_account" "this" {
  admin_account_id = var.audit_account_id
}

resource "aws_securityhub_organization_admin_account" "this" {
  admin_account_id = var.audit_account_id
}

# ---------------------------------------------------------------------------
# Configure the delegated services (run as the Audit account)
# ---------------------------------------------------------------------------

resource "aws_guardduty_detector" "audit" {
  provider = aws.audit
  enable   = true

  depends_on = [aws_guardduty_organization_admin_account.this]
}

# The old `datasources` block on aws_guardduty_detector was deprecated in
# AWS provider v5 and removed in v6 — each data source is now its own
# aws_guardduty_detector_feature resource.
resource "aws_guardduty_detector_feature" "s3_logs" {
  provider    = aws.audit
  detector_id = aws_guardduty_detector.audit.id
  name        = "S3_DATA_EVENTS"
  status      = "ENABLED"
}

resource "aws_guardduty_detector_feature" "eks_audit_logs" {
  provider    = aws.audit
  detector_id = aws_guardduty_detector.audit.id
  name        = "EKS_AUDIT_LOGS"
  status      = "ENABLED"
}

resource "aws_guardduty_detector_feature" "ebs_malware_protection" {
  provider    = aws.audit
  detector_id = aws_guardduty_detector.audit.id
  name        = "EBS_MALWARE_PROTECTION"
  status      = "ENABLED"
}

resource "aws_guardduty_organization_configuration" "audit" {
  provider                         = aws.audit
  detector_id                      = aws_guardduty_detector.audit.id
  auto_enable_organization_members = "ALL"
}

resource "aws_securityhub_account" "audit" {
  provider                 = aws.audit
  enable_default_standards = false
  depends_on                = [aws_securityhub_organization_admin_account.this]
}

resource "aws_securityhub_organization_configuration" "audit" {
  provider    = aws.audit
  auto_enable = true
  depends_on  = [aws_securityhub_account.audit]
}

resource "aws_securityhub_standards_subscription" "audit" {
  provider      = aws.audit
  for_each      = toset(var.security_hub_standards)
  standards_arn = each.value
  depends_on    = [aws_securityhub_account.audit]
}
