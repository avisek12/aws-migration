# Run this module from the AWS Organizations management account.
#
# If an organization already exists (it almost always does — every AWS
# account is born into one), import it instead of letting Terraform try to
# create a second one:
#   terraform import aws_organizations_organization.this <organization-id>

resource "aws_organizations_organization" "this" {
  aws_service_access_principals = [
    "cloudtrail.amazonaws.com",
    "config.amazonaws.com",
    "guardduty.amazonaws.com",
    "securityhub.amazonaws.com",
    "sso.amazonaws.com",
    "ram.amazonaws.com",
    "account.amazonaws.com",
  ]
  feature_set          = "ALL"
  enabled_policy_types = ["SERVICE_CONTROL_POLICY", "TAG_POLICY"]
}

locals {
  root_id = aws_organizations_organization.this.roots[0].id
}

# ---------------------------------------------------------------------------
# Organizational Units — mirrors docs/04-hld-landing-zone.md §1
# ---------------------------------------------------------------------------

resource "aws_organizations_organizational_unit" "security" {
  name      = "Security"
  parent_id = local.root_id
}

resource "aws_organizations_organizational_unit" "infrastructure" {
  name      = "Infrastructure"
  parent_id = local.root_id
}

resource "aws_organizations_organizational_unit" "workloads" {
  name      = "Workloads"
  parent_id = local.root_id
}

resource "aws_organizations_organizational_unit" "workloads_prod" {
  name      = "Prod"
  parent_id = aws_organizations_organizational_unit.workloads.id
}

resource "aws_organizations_organizational_unit" "workloads_nonprod" {
  name      = "NonProd"
  parent_id = aws_organizations_organizational_unit.workloads.id
}

resource "aws_organizations_organizational_unit" "sandbox" {
  name      = "Sandbox"
  parent_id = local.root_id
}

locals {
  ou_id_by_name = {
    "Security"          = aws_organizations_organizational_unit.security.id
    "Infrastructure"     = aws_organizations_organizational_unit.infrastructure.id
    "Workloads/Prod"     = aws_organizations_organizational_unit.workloads_prod.id
    "Workloads/NonProd"  = aws_organizations_organizational_unit.workloads_nonprod.id
    "Sandbox"            = aws_organizations_organizational_unit.sandbox.id
  }
}

# ---------------------------------------------------------------------------
# Service Control Policies — preventive guardrails, docs/04 §4
# ---------------------------------------------------------------------------

resource "aws_organizations_policy" "deny_leave_org" {
  name        = "deny-leave-organization"
  description = "Prevents any account from removing itself from the organization."
  type        = "SERVICE_CONTROL_POLICY"
  content     = file("${path.module}/scps/deny-leave-organization.json")
}

resource "aws_organizations_policy" "deny_root_user" {
  name        = "deny-root-user-actions"
  description = "Blocks the root user from taking any action at all — break-glass access should use a dedicated IAM Identity Center permission set instead."
  type        = "SERVICE_CONTROL_POLICY"
  content     = file("${path.module}/scps/deny-root-user.json")
}

resource "aws_organizations_policy" "require_imdsv2" {
  name        = "require-imdsv2"
  description = "Blocks launching EC2 instances that allow IMDSv1."
  type        = "SERVICE_CONTROL_POLICY"
  content     = file("${path.module}/scps/require-imdsv2.json")
}

resource "aws_organizations_policy" "region_restriction" {
  name        = "region-restriction"
  description = "Denies service actions outside the approved region list, excluding global services."
  type        = "SERVICE_CONTROL_POLICY"
  content = templatefile("${path.module}/scps/region-restriction.json.tpl", {
    allowed_regions = jsonencode(var.allowed_regions)
  })
}

# Attach org-wide guardrails at the root so they apply to every OU.
resource "aws_organizations_policy_attachment" "deny_leave_org_root" {
  policy_id = aws_organizations_policy.deny_leave_org.id
  target_id = local.root_id
}

resource "aws_organizations_policy_attachment" "deny_root_user_root" {
  policy_id = aws_organizations_policy.deny_root_user.id
  target_id = local.root_id
}

# Workload-specific guardrails — attach only where they belong so Security/
# Infrastructure accounts retain the flexibility to run global tooling.
resource "aws_organizations_policy_attachment" "require_imdsv2_workloads" {
  policy_id = aws_organizations_policy.require_imdsv2.id
  target_id = aws_organizations_organizational_unit.workloads.id
}

resource "aws_organizations_policy_attachment" "region_restriction_workloads" {
  policy_id = aws_organizations_policy.region_restriction.id
  target_id = aws_organizations_organizational_unit.workloads.id
}

# ---------------------------------------------------------------------------
# Optional: vend member accounts directly (skip this if you're using
# Control Tower's Account Factory instead — the two approaches shouldn't
# both manage the same account).
# ---------------------------------------------------------------------------

resource "aws_organizations_account" "member" {
  for_each  = var.member_accounts
  name      = each.key
  email     = each.value.email
  parent_id = local.ou_id_by_name[each.value.ou]

  close_on_deletion = false

  # The account's default OrganizationAccountAccessRole name/trust policy
  # is set at creation time and shouldn't be churned by later applies.
  lifecycle {
    ignore_changes = [role_name]
  }
}
