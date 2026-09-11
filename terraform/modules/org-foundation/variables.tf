variable "allowed_regions" {
  description = "Regions workloads are permitted to use. The region-restriction SCP denies everything else (global services excluded)."
  type        = list(string)
  default     = ["us-east-1", "us-east-2"]
}

variable "member_accounts" {
  description = "Optional: accounts to vend under this OU structure. Key is the account name. Leave empty to manage only OUs/SCPs and vend accounts another way (e.g. Control Tower Account Factory)."
  type = map(object({
    email = string
    ou    = string # one of: "Security", "Infrastructure", "Workloads/Prod", "Workloads/NonProd", "Sandbox"
  }))
  default = {}
}
