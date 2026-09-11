# Run this module from the Network Hub account (docs/04-hld-landing-zone.md
# §1-2). It builds the Transit Gateway, a centralized egress VPC (NAT lives
# here, not in every workload account), and optionally attaches Direct
# Connect and/or a Site-to-Site VPN backup directly to the TGW.
#
# Segmentation note: this module ships with a SINGLE shared Transit Gateway
# route table (default association/propagation = enable) — good enough for
# an initial landing zone. As the estate grows, switch
# default_route_table_association/propagation to "disable" and create
# explicit aws_ec2_transit_gateway_route_table resources per segment
# (prod / non-prod / shared-services) so prod cannot route to non-prod by
# default, per the HLD's intent.

resource "aws_ec2_transit_gateway" "this" {
  description                    = "${var.name_prefix}-tgw"
  amazon_side_asn                = var.amazon_side_asn
  auto_accept_shared_attachments = "enable"
  dns_support                    = "enable"
  vpn_ecmp_support                = "enable"

  tags = { Name = "${var.name_prefix}-tgw" }
}

# ---------------------------------------------------------------------------
# Share the Transit Gateway with workload accounts via AWS RAM so their VPCs
# can create their own attachments without the TGW needing to move accounts.
# ---------------------------------------------------------------------------

resource "aws_ram_resource_share" "tgw" {
  count                     = length(var.workload_account_ids) > 0 ? 1 : 0
  name                      = "${var.name_prefix}-tgw-share"
  allow_external_principals = false
}

resource "aws_ram_resource_association" "tgw" {
  count              = length(var.workload_account_ids) > 0 ? 1 : 0
  resource_arn       = aws_ec2_transit_gateway.this.arn
  resource_share_arn = aws_ram_resource_share.tgw[0].arn
}

resource "aws_ram_principal_association" "tgw" {
  for_each           = toset(var.workload_account_ids)
  principal          = each.value
  resource_share_arn = aws_ram_resource_share.tgw[0].arn
}

# ---------------------------------------------------------------------------
# Centralized egress VPC
# ---------------------------------------------------------------------------

resource "aws_vpc" "egress" {
  cidr_block           = var.egress_vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${var.name_prefix}-egress-vpc" }
}

resource "aws_internet_gateway" "egress" {
  vpc_id = aws_vpc.egress.id
  tags   = { Name = "${var.name_prefix}-egress-igw" }
}

# One NAT subnet + one TGW-attachment subnet per AZ.
resource "aws_subnet" "nat" {
  for_each                = { for idx, az in var.azs : az => idx }
  vpc_id                  = aws_vpc.egress.id
  availability_zone       = each.key
  cidr_block              = cidrsubnet(var.egress_vpc_cidr, 2, each.value)
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.name_prefix}-nat-${each.key}" }
}

resource "aws_subnet" "tgw_attach" {
  for_each          = { for idx, az in var.azs : az => idx }
  vpc_id            = aws_vpc.egress.id
  availability_zone = each.key
  cidr_block        = cidrsubnet(var.egress_vpc_cidr, 2, each.value + length(var.azs))
  tags              = { Name = "${var.name_prefix}-tgw-attach-${each.key}" }
}

resource "aws_eip" "nat" {
  for_each = aws_subnet.nat
  domain   = "vpc"
  tags     = { Name = "${var.name_prefix}-nat-eip-${each.key}" }
}

resource "aws_nat_gateway" "this" {
  for_each      = aws_subnet.nat
  allocation_id = aws_eip.nat[each.key].id
  subnet_id     = each.value.id
  tags          = { Name = "${var.name_prefix}-nat-${each.key}" }
  depends_on    = [aws_internet_gateway.egress]
}

resource "aws_route_table" "nat" {
  vpc_id = aws_vpc.egress.id
  tags   = { Name = "${var.name_prefix}-nat-rt" }
}

resource "aws_route" "nat_to_igw" {
  route_table_id         = aws_route_table.nat.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id              = aws_internet_gateway.egress.id
}

resource "aws_route_table_association" "nat" {
  for_each       = aws_subnet.nat
  subnet_id      = each.value.id
  route_table_id = aws_route_table.nat.id
}

# Traffic arriving over the Transit Gateway routes out through NAT in the
# same AZ (keeps egress traffic from crossing AZs unnecessarily).
resource "aws_route_table" "tgw_attach" {
  for_each = aws_subnet.tgw_attach
  vpc_id   = aws_vpc.egress.id
  tags     = { Name = "${var.name_prefix}-tgw-attach-rt-${each.key}" }
}

resource "aws_route" "tgw_attach_to_nat" {
  for_each               = aws_route_table.tgw_attach
  route_table_id         = each.value.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id          = aws_nat_gateway.this[each.key].id
}

resource "aws_route_table_association" "tgw_attach" {
  for_each       = aws_subnet.tgw_attach
  subnet_id      = each.value.id
  route_table_id = aws_route_table.tgw_attach[each.key].id
}

resource "aws_ec2_transit_gateway_vpc_attachment" "egress" {
  transit_gateway_id = aws_ec2_transit_gateway.this.id
  vpc_id              = aws_vpc.egress.id
  subnet_ids          = [for s in aws_subnet.tgw_attach : s.id]
  tags                = { Name = "${var.name_prefix}-egress-attachment" }
}

# The TGW's default route table sends everything to the egress VPC — every
# other attachment (workload VPCs) inherits this via default propagation.
resource "aws_ec2_transit_gateway_route" "default_to_egress" {
  destination_cidr_block        = "0.0.0.0/0"
  transit_gateway_attachment_id = aws_ec2_transit_gateway_vpc_attachment.egress.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway.this.association_default_route_table_id
}

# ---------------------------------------------------------------------------
# Direct Connect (primary hybrid path)
# ---------------------------------------------------------------------------

variable "dx_allowed_prefixes" {
  description = "On-prem CIDR ranges advertised to AWS over the Direct Connect Gateway."
  type        = list(string)
  default     = ["10.0.0.0/8"]
}

resource "aws_dx_gateway_association" "this" {
  count                  = var.enable_direct_connect ? 1 : 0
  dx_gateway_id          = var.direct_connect_gateway_id
  associated_gateway_id  = aws_ec2_transit_gateway.this.id
  allowed_prefixes       = var.dx_allowed_prefixes
}

# ---------------------------------------------------------------------------
# Site-to-Site VPN (backup hybrid path, attached directly to the TGW)
# ---------------------------------------------------------------------------

resource "aws_customer_gateway" "onprem" {
  count      = var.enable_vpn_backup ? 1 : 0
  bgp_asn    = var.customer_gateway_bgp_asn
  ip_address = var.customer_gateway_ip
  type       = "ipsec.1"
  tags       = { Name = "${var.name_prefix}-onprem-cgw" }
}

resource "aws_vpn_connection" "backup" {
  count               = var.enable_vpn_backup ? 1 : 0
  customer_gateway_id = aws_customer_gateway.onprem[0].id
  transit_gateway_id  = aws_ec2_transit_gateway.this.id
  type                = "ipsec.1"
  static_routes_only  = false
  tags                = { Name = "${var.name_prefix}-vpn-backup" }
}
