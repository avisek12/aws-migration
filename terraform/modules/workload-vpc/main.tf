# Apply this module once per migrated application account
# (docs/04-hld-landing-zone.md §1 — "one account per app(-group)").
# Three subnet tiers per AZ: public (load balancer only), private-app
# (EC2/ECS), private-data (RDS) — matching the target architecture in
# docs/05 and docs/06-09's LLDs. Nothing but the load balancer gets a
# public IP; everything else reaches the internet (if at all) through the
# centralized egress VPC in the network hub, via the Transit Gateway.

variable "onprem_cidrs" {
  description = "On-prem CIDR ranges the data tier is allowed to reach over the Transit Gateway (e.g. a central AD or backup target). Leave empty to keep the data tier fully isolated from anything but the VPC itself."
  type        = list(string)
  default     = []
}

variable "app_port" {
  type    = number
  default = 8080
}

variable "tags" {
  type    = map(string)
  default = {}
}

locals {
  common_tags = merge(var.tags, {
    App         = var.app_name
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = merge(local.common_tags, { Name = "${var.app_name}-${var.environment}-vpc" })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = merge(local.common_tags, { Name = "${var.app_name}-igw" })
}

# --- subnets: /24 base VPC -> 6x /27 across 3 tiers x up to 2 AZs shown here
resource "aws_subnet" "public" {
  for_each                = { for idx, az in var.azs : az => idx }
  vpc_id                  = aws_vpc.this.id
  availability_zone       = each.key
  cidr_block              = cidrsubnet(var.vpc_cidr, 3, each.value)
  map_public_ip_on_launch = false # ALB gets its own EIP; instances here shouldn't auto-assign public IPs
  tags                    = merge(local.common_tags, { Name = "${var.app_name}-public-${each.key}", Tier = "public" })
}

resource "aws_subnet" "app" {
  for_each          = { for idx, az in var.azs : az => idx }
  vpc_id            = aws_vpc.this.id
  availability_zone = each.key
  cidr_block        = cidrsubnet(var.vpc_cidr, 3, each.value + length(var.azs))
  tags              = merge(local.common_tags, { Name = "${var.app_name}-app-${each.key}", Tier = "app" })
}

resource "aws_subnet" "data" {
  for_each          = { for idx, az in var.azs : az => idx }
  vpc_id            = aws_vpc.this.id
  availability_zone = each.key
  cidr_block        = cidrsubnet(var.vpc_cidr, 3, each.value + 2 * length(var.azs))
  tags              = merge(local.common_tags, { Name = "${var.app_name}-data-${each.key}", Tier = "data" })
}

# --- Transit Gateway attachment lives in the app subnets
resource "aws_ec2_transit_gateway_vpc_attachment" "this" {
  transit_gateway_id = var.transit_gateway_id
  vpc_id              = aws_vpc.this.id
  subnet_ids          = [for s in aws_subnet.app : s.id]
  tags                = merge(local.common_tags, { Name = "${var.app_name}-tgw-attachment" })
}

# --- route tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  tags   = merge(local.common_tags, { Name = "${var.app_name}-public-rt" })
}

resource "aws_route" "public_to_igw" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id              = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "public" {
  for_each       = aws_subnet.public
  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "app" {
  vpc_id = aws_vpc.this.id
  tags   = merge(local.common_tags, { Name = "${var.app_name}-app-rt" })
}

# General internet egress from the app tier goes via the TGW to the
# centralized egress VPC's NAT gateways — no per-account NAT gateway cost.
resource "aws_route" "app_to_tgw" {
  route_table_id         = aws_route_table.app.id
  destination_cidr_block = "0.0.0.0/0"
  transit_gateway_id     = var.transit_gateway_id
  depends_on              = [aws_ec2_transit_gateway_vpc_attachment.this]
}

resource "aws_route_table_association" "app" {
  for_each       = aws_subnet.app
  subnet_id      = each.value.id
  route_table_id = aws_route_table.app.id
}

resource "aws_route_table" "data" {
  vpc_id = aws_vpc.this.id
  tags   = merge(local.common_tags, { Name = "${var.app_name}-data-rt" })
}

# Data tier gets NO default internet route — only explicit on-prem CIDRs
# via the TGW, if any were provided.
resource "aws_route" "data_to_onprem" {
  for_each                = toset(var.onprem_cidrs)
  route_table_id          = aws_route_table.data.id
  destination_cidr_block  = each.value
  transit_gateway_id      = var.transit_gateway_id
  depends_on               = [aws_ec2_transit_gateway_vpc_attachment.this]
}

resource "aws_route_table_association" "data" {
  for_each       = aws_subnet.data
  subnet_id      = each.value.id
  route_table_id = aws_route_table.data.id
}

# --- security groups
resource "aws_security_group" "alb" {
  name        = "${var.app_name}-alb-sg"
  description = "Internet-facing load balancer"
  vpc_id      = aws_vpc.this.id

  ingress {
    description = "HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = local.common_tags
}

resource "aws_security_group" "app" {
  name        = "${var.app_name}-app-sg"
  description = "Application tier — only reachable from the load balancer"
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "App traffic from the ALB"
    from_port       = var.app_port
    to_port         = var.app_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = local.common_tags
}

resource "aws_security_group" "data" {
  name        = "${var.app_name}-data-sg"
  description = "Data tier — only reachable from the application tier"
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "Database traffic from the app tier"
    from_port       = var.db_port
    to_port         = var.db_port
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
  tags = local.common_tags
}

# --- VPC Flow Logs
resource "aws_cloudwatch_log_group" "flow_logs" {
  name              = "/vpc/flow-logs/${var.app_name}-${var.environment}"
  retention_in_days = var.log_retention_days
}

resource "aws_iam_role" "flow_logs" {
  name = "${var.app_name}-vpc-flow-logs"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "vpc-flow-logs.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "flow_logs" {
  name = "${var.app_name}-vpc-flow-logs"
  role = aws_iam_role.flow_logs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "${aws_cloudwatch_log_group.flow_logs.arn}:*"
    }]
  })
}

resource "aws_flow_log" "this" {
  vpc_id                = aws_vpc.this.id
  log_destination_type  = "cloud-watch-logs"
  log_destination       = aws_cloudwatch_log_group.flow_logs.arn
  iam_role_arn          = aws_iam_role.flow_logs.arn
  traffic_type          = "ALL"
  tags                  = local.common_tags
}

# --- per-account KMS key for EBS/RDS encryption
resource "aws_kms_key" "this" {
  description             = "${var.app_name} workload encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

resource "aws_kms_alias" "this" {
  name          = "alias/${var.app_name}-${var.environment}"
  target_key_id = aws_kms_key.this.key_id
}
