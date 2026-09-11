# terraform {
#   backend "s3" {
#     bucket         = "your-org-tfstate-log-archive"
#     key            = "landing-zone/log-archive/terraform.tfstate"
#     region         = "us-east-1"
#     dynamodb_table = "your-org-tfstate-locks"
#     encrypt        = true
#   }
# }
