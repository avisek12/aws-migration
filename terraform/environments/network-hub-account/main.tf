module "network_hub" {
  source = "../../modules/network-hub"

  azs                       = var.azs
  egress_vpc_cidr           = var.egress_vpc_cidr
  enable_direct_connect     = var.enable_direct_connect
  direct_connect_gateway_id = var.direct_connect_gateway_id
  enable_vpn_backup         = var.enable_vpn_backup
  customer_gateway_ip       = var.customer_gateway_ip
  workload_account_ids      = var.workload_account_ids
}

module "account_baseline" {
  source = "../../modules/account-baseline"

  log_archive_bucket_name = var.log_archive_bucket_name
  log_archive_kms_key_arn = var.log_archive_kms_key_arn
}
