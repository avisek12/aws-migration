# State for the management account stack. The S3 bucket + DynamoDB lock
# table referenced here must exist before `terraform init` — bootstrap them
# by hand (or with a tiny separate one-off stack) since Terraform can't
# create the backend it's about to store its own state in.
#
# terraform {
#   backend "s3" {
#     bucket         = "your-org-tfstate-management"
#     key            = "landing-zone/management/terraform.tfstate"
#     region         = "us-east-1"
#     dynamodb_table = "your-org-tfstate-locks"
#     encrypt        = true
#   }
# }
