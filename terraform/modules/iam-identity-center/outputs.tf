output "permission_set_arns" {
  value = { for name, ps in aws_ssoadmin_permission_set.this : name => ps.arn }
}
