"""
Field catalog for the customer-intake chat agent. A deliberate, standalone
copy of ../ui/config.py's field definitions (not a cross-import): this
service only ever fetches plain data files (.tf/.md/.example) from GitHub
at runtime, never executable code, so its own logic — including which
fields exist — has to ship with it rather than being pulled in live. Keep
this in sync by hand if ../ui/config.py's fields change.
"""

STACK_CATALOG = {
    "management": {
        "title": "Management Account",
        "template_dirname": "management",
        "description": "Organizations, OUs, SCPs, GuardDuty/Security Hub delegation, "
                        "Identity Center, and the org-wide CloudTrail trail.",
        "fields": [
            {"name": "aws_region", "label": "AWS Region", "required": True, "default": "us-east-1"},
            {"name": "allowed_regions", "label": "Allowed Regions (list)", "required": True,
             "default": "us-east-1, us-east-2",
             "help": "Regions the region-restriction SCP allows Workloads-OU accounts to use."},
            {"name": "audit_account_id", "label": "Audit Account ID", "required": True,
             "help": "12-digit AWS account id that will be delegated as GuardDuty/Security Hub administrator."},
            {"name": "log_archive_account_id", "label": "Log Archive Account ID", "required": True},
            {"name": "log_archive_bucket_name", "label": "Log Archive Bucket Name", "required": True,
             "help": "The central log bucket's name — an output of the Log Archive Account stack."},
            {"name": "log_archive_kms_key_arn", "label": "Log Archive KMS Key ARN", "required": True,
             "help": "The central log bucket's KMS key ARN — an output of the Log Archive Account stack."},
        ],
    },
    "log-archive-account": {
        "title": "Log Archive Account",
        "template_dirname": "log-archive-account",
        "description": "The central S3 bucket + KMS key every account's CloudTrail/Config logs land in.",
        "fields": [
            {"name": "aws_region", "label": "AWS Region", "required": True, "default": "us-east-1"},
            {"name": "organization_id", "label": "Organization ID", "required": True,
             "help": "Looks like o-xxxxxxxxxx, from AWS Organizations. If they're not sure they're in an "
                     "Organization yet, flag that this needs to exist first."},
            {"name": "bucket_name", "label": "Central Log Bucket Name", "required": True,
             "help": "Must be globally unique across all of S3."},
        ],
    },
    "audit-account": {
        "title": "Audit Account",
        "template_dirname": "audit-account",
        "description": "Baseline only — GuardDuty/Security Hub in this account come from the Management stack.",
        "fields": [
            {"name": "aws_region", "label": "AWS Region", "required": True, "default": "us-east-1"},
            {"name": "log_archive_bucket_name", "label": "Log Archive Bucket Name", "required": True},
            {"name": "log_archive_kms_key_arn", "label": "Log Archive KMS Key ARN", "required": True},
        ],
    },
    "network-hub-account": {
        "title": "Network Hub Account",
        "template_dirname": "network-hub-account",
        "description": "Transit Gateway, centralized egress VPC/NAT, and optional Direct Connect / VPN.",
        "fields": [
            {"name": "aws_region", "label": "AWS Region", "required": True, "default": "us-east-1"},
            {"name": "azs", "label": "Availability Zones (list)", "required": True,
             "default": "us-east-1a, us-east-1b"},
            {"name": "egress_vpc_cidr", "label": "Egress VPC CIDR", "required": True, "default": "10.0.0.0/24"},
            {"name": "enable_direct_connect", "label": "Enable Direct Connect (true/false)", "required": False,
             "default": "false"},
            {"name": "direct_connect_gateway_id", "label": "Direct Connect Gateway ID", "required": False,
             "help": "Only needed if Direct Connect is enabled."},
            {"name": "enable_vpn_backup", "label": "Enable Site-to-Site VPN backup (true/false)", "required": False,
             "default": "false"},
            {"name": "customer_gateway_ip", "label": "On-prem VPN device public IP", "required": False},
            {"name": "workload_account_ids", "label": "Workload/Shared-Services Account IDs (list)",
             "required": False, "help": "Every account id that will attach a VPC to this Transit Gateway."},
            {"name": "log_archive_bucket_name", "label": "Log Archive Bucket Name", "required": True},
            {"name": "log_archive_kms_key_arn", "label": "Log Archive KMS Key ARN", "required": True},
        ],
    },
    "workload": {
        "title": "Workload Account",
        "template_dirname": "workload-account-example",
        "description": "The 3-tier VPC for one migrated application, once per app.",
        "is_workload": True,
        "fields": [
            {"name": "app_name", "label": "App name (letters/numbers only)", "required": True,
             "help": "Used to build the folder name — e.g. ordermgmt."},
            {"name": "environment", "label": "Environment (prod or nonprod)", "required": True, "default": "prod"},
            {"name": "vpc_cidr", "label": "VPC CIDR", "required": True,
             "help": "A /24 works cleanly with the subnet math."},
            {"name": "azs", "label": "Availability Zones (list)", "required": True,
             "default": "us-east-1a, us-east-1b"},
            {"name": "aws_region", "label": "AWS Region", "required": True, "default": "us-east-1"},
            {"name": "transit_gateway_id", "label": "Transit Gateway ID", "required": True,
             "help": "Output of the Network Hub Account stack."},
            {"name": "db_port", "label": "Database port", "required": False, "default": "5432",
             "help": "5432 Postgres, 3306 MySQL/Aurora-MySQL, 1521 Oracle."},
            {"name": "onprem_cidrs", "label": "On-prem CIDRs (list, optional)", "required": False,
             "help": "Leave empty to keep the data tier fully isolated."},
            {"name": "log_archive_bucket_name", "label": "Log Archive Bucket Name", "required": True},
            {"name": "log_archive_kms_key_arn", "label": "Log Archive KMS Key ARN", "required": True},
        ],
    },
}

# Value types drive coercion in app.py (comma-split lists, real booleans,
# real numbers) — everything not listed here defaults to plain text.
_LIST_FIELDS = {"allowed_regions", "azs", "workload_account_ids", "onprem_cidrs"}
_CHECKBOX_FIELDS = {"enable_direct_connect", "enable_vpn_backup"}
_NUMBER_FIELDS = {"db_port"}

for _stack in STACK_CATALOG.values():
    for _field in _stack["fields"]:
        name = _field["name"]
        if name in _LIST_FIELDS:
            _field["type"] = "list"
        elif name in _CHECKBOX_FIELDS:
            _field["type"] = "checkbox"
        elif name in _NUMBER_FIELDS:
            _field["type"] = "number"
        else:
            _field["type"] = "text"
