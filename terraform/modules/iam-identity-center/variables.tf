variable "permission_sets" {
  description = "Map of permission set name to config."
  type = map(object({
    description      = string
    session_duration = string # ISO-8601 duration, e.g. "PT4H"
    managed_policy_arns = list(string)
  }))
  default = {
    MigrationEngineer = {
      description         = "Runs MGN/DMS tooling, no IAM/Org access"
      session_duration    = "PT8H"
      managed_policy_arns = ["arn:aws:iam::aws:policy/AWSApplicationMigrationAgentPolicy"]
    }
    AppOwnerReadOnly = {
      description         = "Read-only visibility for app owners validating a migration"
      session_duration    = "PT4H"
      managed_policy_arns = ["arn:aws:iam::aws:policy/ReadOnlyAccess"]
    }
    SecurityAuditor = {
      description         = "Security/compliance review access"
      session_duration    = "PT4H"
      managed_policy_arns = ["arn:aws:iam::aws:policy/SecurityAudit"]
    }
  }
}
