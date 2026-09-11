terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Default provider — run with credentials for the Organizations MANAGEMENT
# account (e.g. `aws sso login --profile mgmt` then AWS_PROFILE=mgmt).
provider "aws" {
  region = var.aws_region
}

# Aliased provider for the Audit account, used only by the security-baseline
# module to configure GuardDuty/Security Hub once delegated to it.
provider "aws" {
  alias  = "audit"
  region = var.aws_region

  assume_role {
    role_arn = "arn:aws:iam::${var.audit_account_id}:role/OrganizationAccountAccessRole"
  }
}
