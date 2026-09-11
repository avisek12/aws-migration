variable "audit_account_id" {
  description = "Account id delegated as the GuardDuty/Security Hub administrator for the organization."
  type        = string
}

variable "security_hub_standards" {
  description = "Security Hub standards ARNs (region-specific) to auto-subscribe the audit account to."
  type        = list(string)
  default = [
    "arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.4.0",
    "arn:aws:securityhub:us-east-1::standards/aws-foundational-security-best-practices/v/1.0.0",
  ]
}
