# Copy this whole environments/workload-account-example/ directory per app
# account (e.g. environments/ordermgmt-prod/, or automatically via the
# Landing Zone UI's "New Workload Account" page) — give each copy its own
# backend key below so state never collides across apps.
#
# By default (the block below left commented out) Terraform uses LOCAL
# state — a terraform.tfstate file in this directory. Fine for a first
# look, but it lives only on this machine: no backup, no locking against
# two concurrent applies, and it's exactly what you'd need if you ever
# have to `terraform destroy` this app's infrastructure for real. Before
# applying anything you intend to keep, switch to remote state:
#
#   1. Bootstrap THIS APP'S AWS account's S3 bucket + DynamoDB lock table
#      once via ../../bootstrap-backend/ (see its README).
#   2. Copy backend.hcl.example -> backend.hcl in this copied directory,
#      set `key` to this app's own path (e.g.
#      "landing-zone/ordermgmt-prod/terraform.tfstate"), and fill in the
#      other values bootstrap-backend printed as outputs.
#   3. Uncomment the block below, then run:
#        terraform init -backend-config=backend.hcl
#
# terraform {
#   backend "s3" {}
# }
