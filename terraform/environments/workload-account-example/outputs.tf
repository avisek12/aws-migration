output "vpc_id" {
  value = module.vpc.vpc_id
}

output "alb_security_group_id" {
  value = module.vpc.alb_security_group_id
}

output "app_security_group_id" {
  value = module.vpc.app_security_group_id
}

output "data_security_group_id" {
  value = module.vpc.data_security_group_id
}

output "kms_key_arn" {
  value = module.vpc.kms_key_arn
}
