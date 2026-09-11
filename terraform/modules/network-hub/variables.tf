variable "name_prefix" {
  type    = string
  default = "network-hub"
}

variable "azs" {
  description = "Availability Zones for the centralized egress VPC."
  type        = list(string)
}

variable "egress_vpc_cidr" {
  type    = string
  default = "10.0.0.0/24"
}

variable "amazon_side_asn" {
  description = "ASN for the Transit Gateway's Amazon side. Must not collide with your on-prem ASN."
  type        = number
  default     = 64512
}

variable "enable_direct_connect" {
  type    = bool
  default = false
}

variable "direct_connect_gateway_id" {
  description = "Existing Direct Connect Gateway id to associate with the Transit Gateway. Required if enable_direct_connect = true."
  type        = string
  default     = null
}

variable "enable_vpn_backup" {
  description = "Attach a Site-to-Site VPN directly to the Transit Gateway as a backup path to Direct Connect."
  type        = bool
  default     = false
}

variable "customer_gateway_ip" {
  description = "Public IP of the on-prem VPN device. Required if enable_vpn_backup = true."
  type        = string
  default     = null
}

variable "customer_gateway_bgp_asn" {
  type    = number
  default = 65000
}

variable "workload_account_ids" {
  description = "Account ids allowed to attach their VPCs to this Transit Gateway via AWS RAM."
  type        = list(string)
  default     = []
}
