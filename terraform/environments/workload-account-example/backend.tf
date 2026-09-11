# Copy this whole environments/workload-account-example/ directory per app
# account (e.g. environments/ordermgmt-prod/) and give each its own backend
# key so state never collides across apps.
#
# terraform {
#   backend "s3" {
#     bucket         = "your-org-tfstate-workloads"
#     key            = "landing-zone/ordermgmt-prod/terraform.tfstate"
#     region         = "us-east-1"
#     dynamodb_table = "your-org-tfstate-locks"
#     encrypt        = true
#   }
# }
