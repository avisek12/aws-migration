output "transit_gateway_id" {
  value = aws_ec2_transit_gateway.this.id
}

output "transit_gateway_route_table_id" {
  value = aws_ec2_transit_gateway.this.association_default_route_table_id
}

output "egress_vpc_id" {
  value = aws_vpc.egress.id
}

output "ram_share_arn" {
  value = length(var.workload_account_ids) > 0 ? aws_ram_resource_share.tgw[0].arn : null
}
