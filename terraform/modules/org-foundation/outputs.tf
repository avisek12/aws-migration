output "organization_id" {
  value = aws_organizations_organization.this.id
}

output "root_id" {
  value = local.root_id
}

output "ou_ids" {
  description = "Map of OU name to OU id, for referencing from other stacks (e.g. SCP attachments, account moves)."
  value       = local.ou_id_by_name
}

output "member_account_ids" {
  description = "Map of account name to account id, for accounts vended by this module."
  value       = { for name, acct in aws_organizations_account.member : name => acct.id }
}
