# terraform {
#   backend "s3" {
#     bucket         = "your-org-tfstate-audit"
#     key            = "landing-zone/audit/terraform.tfstate"
#     region         = "us-east-1"
#     dynamodb_table = "your-org-tfstate-locks"
#     encrypt        = true
#   }
# }
