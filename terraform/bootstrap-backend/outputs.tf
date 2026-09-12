output "state_bucket_name" {
  value = aws_s3_bucket.tfstate.id
}

output "lock_table_name" {
  value = aws_dynamodb_table.locks.name
}

output "backend_hcl" {
  description = "Paste this into backend.hcl in whichever environments/*/ stack(s) run in this account."
  value = join("\n", [
    "bucket         = \"${aws_s3_bucket.tfstate.id}\"",
    "dynamodb_table = \"${aws_dynamodb_table.locks.name}\"",
    "region         = \"${var.aws_region}\"",
    "encrypt        = true",
  ])
}
