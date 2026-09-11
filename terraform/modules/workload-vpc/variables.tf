variable "app_name" {
  description = "Short name for the workload this VPC hosts, used in tags (e.g. \"ordermgmt\")."
  type        = string
}

variable "environment" {
  description = "prod | nonprod — used in tags and to help pick TGW route table associations later."
  type        = string
}

variable "vpc_cidr" {
  type = string
}

variable "azs" {
  type = list(string)
}

variable "transit_gateway_id" {
  description = "Shared Transit Gateway id from the network-hub module/RAM share."
  type        = string
}

variable "db_port" {
  description = "Port the data-tier security group opens to the app-tier security group (5432 Postgres, 3306 MySQL/Aurora, 1521 Oracle, ...)."
  type        = number
  default     = 5432
}

variable "log_retention_days" {
  type    = number
  default = 90
}
