# Accept the Transit Gateway's RAM share before the first apply — either
# once by hand in the console/CLI, or by uncommenting this resource:
#
# resource "aws_ram_resource_share_accepter" "tgw" {
#   share_arn = var.tgw_ram_share_arn
# }

module "vpc" {
  source = "../../modules/workload-vpc"

  app_name           = var.app_name
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  azs                = var.azs
  transit_gateway_id = var.transit_gateway_id
  db_port            = var.db_port
  onprem_cidrs       = var.onprem_cidrs
}

module "account_baseline" {
  source = "../../modules/account-baseline"

  log_archive_bucket_name = var.log_archive_bucket_name
  log_archive_kms_key_arn = var.log_archive_kms_key_arn
}
