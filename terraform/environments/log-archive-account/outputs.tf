output "bucket_name" {
  value = module.log_archive.bucket_name
}

output "bucket_arn" {
  value = module.log_archive.bucket_arn
}

output "kms_key_arn" {
  value = module.log_archive.kms_key_arn
}
