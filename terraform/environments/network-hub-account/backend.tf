# State for the Network Hub account stack.
#
# By default (the block below left commented out) Terraform uses LOCAL
# state — a terraform.tfstate file in this directory. Fine for a first
# look, but it lives only on this machine: no backup, no locking against
# two concurrent applies, and it's exactly what you'd need if you ever
# have to `terraform destroy` this stack for real. Before applying
# anything you intend to keep, switch to remote state:
#
#   1. Bootstrap this account's S3 bucket + DynamoDB lock table once via
#      ../../bootstrap-backend/ (see its README).
#   2. Copy backend.hcl.example -> backend.hcl here and fill in the
#      values bootstrap-backend printed as outputs.
#   3. Uncomment the block below, then run:
#        terraform init -backend-config=backend.hcl
#
# terraform {
#   backend "s3" {}
# }
