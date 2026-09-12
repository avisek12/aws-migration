"""
Field definitions for each Landing Zone UI page.

Each list mirrors one environment's variables.tf in ../environments/<dirname>/
one-to-one. See docs/15-terraform-code-walkthrough.md for what every
variable actually controls and why — this file only decides how it's
presented as a form.
"""

ENVIRONMENTS = {
    "log-archive-account": {
        "title": "Log Archive Account",
        "dirname": "log-archive-account",
        "description": (
            "The central S3 bucket + KMS key every account's CloudTrail/Config "
            "logs land in. Apply this one first — every other page needs its outputs."
        ),
        "fields": [
            {"name": "aws_region", "label": "AWS Region", "type": "text",
             "default": "us-east-1", "required": True},
            {"name": "organization_id", "label": "Organization ID", "type": "text",
             "required": True,
             "help": "e.g. o-xxxxxxxxxx — from the AWS Organizations console, or the "
                     "Management page's output once applied."},
            {"name": "bucket_name", "label": "Central Log Bucket Name", "type": "text",
             "required": True,
             "help": "Must be globally unique across all of S3 (not just this account)."},
        ],
    },
    "management": {
        "title": "Management Account",
        "dirname": "management",
        "description": (
            "Organizations, OUs, SCPs, GuardDuty/Security Hub delegation, "
            "Identity Center, and the org-wide CloudTrail trail. Apply the "
            "Log Archive Account page first — you'll need its outputs here."
        ),
        "fields": [
            {"name": "aws_region", "label": "AWS Region", "type": "text",
             "default": "us-east-1", "required": True},
            {"name": "allowed_regions", "label": "Allowed Regions (comma-separated)",
             "type": "list", "default": "us-east-1, us-east-2", "required": True,
             "help": "Regions the region-restriction SCP allows Workloads-OU accounts to use."},
            {"name": "audit_account_id", "label": "Audit Account ID", "type": "text",
             "required": True,
             "help": "12-digit account id delegated as GuardDuty/Security Hub administrator."},
            {"name": "log_archive_account_id", "label": "Log Archive Account ID",
             "type": "text", "required": True},
            {"name": "log_archive_bucket_name", "label": "Log Archive Bucket Name (output)",
             "type": "text", "required": True,
             "help": "The 'bucket_name' output from the Log Archive Account page."},
            {"name": "log_archive_kms_key_arn", "label": "Log Archive KMS Key ARN (output)",
             "type": "text", "required": True,
             "help": "The 'kms_key_arn' output from the Log Archive Account page."},
        ],
    },
    "audit-account": {
        "title": "Audit Account",
        "dirname": "audit-account",
        "description": (
            "Baseline only — GuardDuty and Security Hub in this account are "
            "configured remotely by the Management page's delegated administration."
        ),
        "fields": [
            {"name": "aws_region", "label": "AWS Region", "type": "text",
             "default": "us-east-1", "required": True},
            {"name": "log_archive_bucket_name", "label": "Log Archive Bucket Name (output)",
             "type": "text", "required": True},
            {"name": "log_archive_kms_key_arn", "label": "Log Archive KMS Key ARN (output)",
             "type": "text", "required": True},
        ],
    },
    "network-hub-account": {
        "title": "Network Hub Account",
        "dirname": "network-hub-account",
        "description": (
            "Transit Gateway, centralized egress VPC/NAT, and optional Direct "
            "Connect / VPN. Every workload account needs this page's "
            "'transit_gateway_id' output."
        ),
        "fields": [
            {"name": "aws_region", "label": "AWS Region", "type": "text",
             "default": "us-east-1", "required": True},
            {"name": "azs", "label": "Availability Zones (comma-separated)", "type": "list",
             "default": "us-east-1a, us-east-1b", "required": True},
            {"name": "egress_vpc_cidr", "label": "Egress VPC CIDR", "type": "text",
             "default": "10.0.0.0/24", "required": True},
            {"name": "enable_direct_connect", "label": "Enable Direct Connect",
             "type": "checkbox",
             "help": "Only if you already have a Direct Connect Gateway — the physical "
                     "circuit is provisioned separately (AWS Support + your carrier)."},
            {"name": "direct_connect_gateway_id", "label": "Direct Connect Gateway ID",
             "type": "text", "help": "Required only if Direct Connect is enabled above."},
            {"name": "enable_vpn_backup", "label": "Enable Site-to-Site VPN backup",
             "type": "checkbox"},
            {"name": "customer_gateway_ip", "label": "On-prem VPN Device Public IP",
             "type": "text", "help": "Required only if VPN backup is enabled above."},
            {"name": "workload_account_ids",
             "label": "Workload/Shared-Services Account IDs (comma-separated)",
             "type": "list",
             "help": "Every account id that needs to attach a VPC to this Transit "
                     "Gateway via RAM. Leave blank if none yet."},
            {"name": "log_archive_bucket_name", "label": "Log Archive Bucket Name (output)",
             "type": "text", "required": True},
            {"name": "log_archive_kms_key_arn", "label": "Log Archive KMS Key ARN (output)",
             "type": "text", "required": True},
        ],
    },
}

WORKLOAD_ENV = {
    "title": "New Workload Account",
    "template_dirname": "workload-account-example",
    "description": (
        "Copies workload-account-example into environments/<app>-<environment>/ "
        "and builds the 3-tier VPC in that app's own AWS account. Accept the "
        "Transit Gateway's RAM share invitation in that account before Applying."
    ),
    "fields": [
        {"name": "vpc_cidr", "label": "VPC CIDR", "type": "text", "required": True,
         "help": "A /24 works cleanly with the subnet math (3 tiers x up to 2 AZs = 6x /27)."},
        {"name": "azs", "label": "Availability Zones (comma-separated)", "type": "list",
         "default": "us-east-1a, us-east-1b", "required": True},
        {"name": "aws_region", "label": "AWS Region", "type": "text",
         "default": "us-east-1", "required": True},
        {"name": "transit_gateway_id", "label": "Transit Gateway ID (output)", "type": "text",
         "required": True,
         "help": "The 'transit_gateway_id' output from the Network Hub Account page."},
        {"name": "db_port", "label": "Database Port", "type": "number", "default": 5432,
         "help": "5432 Postgres, 3306 MySQL/Aurora-MySQL, 1521 Oracle."},
        {"name": "onprem_cidrs", "label": "On-prem CIDRs (comma-separated, optional)",
         "type": "list",
         "help": "Leave blank to keep the data tier fully isolated from anything but "
                 "the VPC itself."},
        {"name": "log_archive_bucket_name", "label": "Log Archive Bucket Name (output)",
         "type": "text", "required": True},
        {"name": "log_archive_kms_key_arn", "label": "Log Archive KMS Key ARN (output)",
         "type": "text", "required": True},
    ],
}

from icons import ICONS_BY_KEY  # noqa: E402

for _key, _env in ENVIRONMENTS.items():
    _env["icon"] = ICONS_BY_KEY[_key]
WORKLOAD_ENV["icon"] = ICONS_BY_KEY["workload"]
