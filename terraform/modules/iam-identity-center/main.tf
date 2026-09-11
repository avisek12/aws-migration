# IAM Identity Center itself must be enabled once, by hand, in the AWS
# Console (Settings > Enable) before Terraform can manage anything under it —
# there's no API to turn it on from a cold start. Once enabled, this module
# manages the permission sets on top of it. Run from the management account
# (or the account delegated as the Identity Center administrator).

data "aws_ssoadmin_instances" "this" {}

locals {
  sso_instance_arn = tolist(data.aws_ssoadmin_instances.this.arns)[0]
}

resource "aws_ssoadmin_permission_set" "this" {
  for_each         = var.permission_sets
  name             = each.key
  description      = each.value.description
  instance_arn     = local.sso_instance_arn
  session_duration = each.value.session_duration
}

resource "aws_ssoadmin_managed_policy_attachment" "this" {
  for_each = { for pair in flatten([
    for name, cfg in var.permission_sets : [
      for policy_arn in cfg.managed_policy_arns : {
        key         = "${name}-${policy_arn}"
        name        = name
        policy_arn  = policy_arn
      }
    ]
  ]) : pair.key => pair }

  instance_arn       = local.sso_instance_arn
  permission_set_arn = aws_ssoadmin_permission_set.this[each.value.name].arn
  managed_policy_arn = each.value.policy_arn
}
