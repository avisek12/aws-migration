# terraform {
#   backend "s3" {
#     bucket         = "your-org-tfstate-network-hub"
#     key            = "landing-zone/network-hub/terraform.tfstate"
#     region         = "us-east-1"
#     dynamodb_table = "your-org-tfstate-locks"
#     encrypt        = true
#   }
# }
