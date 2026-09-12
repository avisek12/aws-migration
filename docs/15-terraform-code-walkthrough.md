# Terraform Code Walkthrough — Landing Zone

This document explains **every file, resource, and decision** in [`terraform/`](../terraform/), resource by resource. [docs/04-hld-landing-zone.md](04-hld-landing-zone.md) is the *why* (the target architecture); [terraform/README.md](../terraform/README.md) is the *how to run it* (deployment order, prerequisites); this doc is the *what's actually in the code* — for when you need to explain, modify, or debug a specific resource.

```
terraform/
  modules/            reusable building blocks (no environment-specific values)
    org-foundation/       Organizations, OUs, SCPs
    log-archive/          central S3 bucket + KMS key for logs
    account-baseline/     Config recorder + password policy (every account)
    security-baseline/    GuardDuty + Security Hub delegation
    network-hub/          Transit Gateway, egress VPC, DX/VPN
    workload-vpc/         3-tier VPC + TGW attachment
    iam-identity-center/  SSO permission sets
  environments/       one folder = one Terraform state = one AWS account
    management/
    log-archive-account/
    audit-account/
    network-hub-account/
    workload-account-example/
```

**Mental model:** `modules/` never gets applied directly — each `environments/<name>/main.tf` picks the modules that account needs and wires their variables/outputs together. `environments/` is what you actually run `terraform apply` against, one folder per AWS account, each with its own state file.

---

## 0. Mandatory vs. Optional — at a glance

"Mandatory" here means: part of the minimum viable landing zone this code implements — remove it and the HLD in docs/04 is no longer satisfied. "Optional" means: a real `variable` toggle (a `count`/`for_each` gated on a boolean or an empty-by-default collection) that this code ships with off/empty, or a deliberate either/or choice where a different mechanism covers the same need.

| # | Module / feature | Status | Why |
|---|---|---|---|
| 1 | `org-foundation` — organization, OUs | **Mandatory** | Every other guardrail (SCPs, delegated admin, RAM) needs an org and OU structure to attach to. |
| 1 | `org-foundation` — SCPs: `deny-leave-organization`, `deny-root-user-actions` | **Mandatory** | Root-level guardrails docs/04 §4 treats as non-negotiable for every account. |
| 1 | `org-foundation` — SCPs: `require-imdsv2`, `region-restriction` | **Optional (recommended)** | Real `variable`-driven policy content (`allowed_regions`) and could be dropped/adjusted per your org's actual policy without breaking the rest of the landing zone. Shipped on by default, attached only to Workloads. |
| 1 | `org-foundation` — `member_accounts` (vend accounts directly) | **Optional** | Explicit either/or with Control Tower's Account Factory — default is `{}` (does nothing). Pick one vending path, not both. |
| 2 | `log-archive` | **Mandatory** | Single destination every account's CloudTrail/Config logs and the security-baseline module depend on. No toggles — only tunable defaults (retention days, transition days). |
| 3 | `account-baseline` | **Mandatory, everywhere** | Applied in every account with no feature flags — AWS Config is per-account/per-region, so there's no central alternative. |
| 4 | `security-baseline` | **Mandatory** | GuardDuty/Security Hub delegated administration is core to docs/04 §4's detective-guardrail requirement. The specific `security_hub_standards` list is customizable, not optional (you'll always subscribe to *some* standards). |
| 5 | `network-hub` — Transit Gateway, egress VPC, NAT, RAM share | **Mandatory** | The hub-and-spoke network model workload-vpc's routing assumes; without it, workload accounts have no shared egress or path to each other/on-prem. |
| 5 | `network-hub` — Direct Connect (`enable_direct_connect`) | **Optional**, default `false` | Hybrid connectivity only needed if you have an on-prem DX circuit; the physical circuit itself is provisioned outside Terraform regardless. |
| 5 | `network-hub` — Site-to-Site VPN backup (`enable_vpn_backup`) | **Optional**, default `false` | Backup hybrid path — only relevant if you're using DX (or want VPN as your only hybrid path) and want redundancy. |
| 6 | `workload-vpc` — 3-tier VPC, routing, security groups, flow logs, per-workload KMS key | **Mandatory, per app account** | This is what actually hosts a migrated workload; every migrated app needs one. |
| 6 | `workload-vpc` — `onprem_cidrs` (data-tier route to on-prem) | **Optional**, default `[]` | Data tier is fully isolated unless you explicitly need it to reach something on-prem (e.g. central AD, backup target). |
| 7 | `iam-identity-center` — permission sets | **Mandatory** (some form of SSO access is needed), but the *specific* three default permission sets are a **customizable starting point**, not a fixed requirement | You'll always need at least one permission set; which ones and what they grant is yours to define. |
| 7 | `iam-identity-center` — account assignments (mapping permission sets to accounts/users) | **Not implemented — required follow-up**, not truly optional | Without `aws_ssoadmin_account_assignment` resources, the permission sets exist but grant access to no one. |
| — | Manual bootstrap steps (Terraform state backend, Identity Center console "Enable", TGW RAM-share acceptance) | **Mandatory, one-time, by hand** | Not Terraform-managed by design — see §10. |
| — | TGW route-table segmentation (single shared route table today) | **Works as shipped, but a required upgrade before real prod/non-prod isolation** | See the segmentation caveat under module 5 and README §"Extending toward prod/non-prod route isolation". |

---

## 1. `modules/org-foundation`

**Status: Mandatory** (organization + OUs + core SCPs) **— unless you use Control Tower instead**, in which case Control Tower's Account Factory/guardrails replace this module's account-vending and some guardrail packaging (see the "Scope note" in [terraform/README.md](../terraform/README.md)); the OU/SCP parts of this module still apply either way if you're not using Control Tower's own OU setup.
**Applied from:** the Organizations management account, once for the whole org.
**Files:** `main.tf`, `variables.tf`, `outputs.tf`, `scps/*.json`

### What it builds

**The organization itself** — `aws_organizations_organization.this`:
```hcl
aws_service_access_principals = [cloudtrail, config, guardduty, securityhub, sso, ram, account]
feature_set                   = "ALL"
enabled_policy_types          = ["SERVICE_CONTROL_POLICY", "TAG_POLICY"]
```
Every principal listed is a service that needs org-wide trust to do its job later: CloudTrail for the org trail, Config for aggregators, GuardDuty/Security Hub for delegated administration, SSO for Identity Center, RAM for sharing the Transit Gateway, `account.amazonaws.com` for centrally managing alternate contacts.

Since almost every AWS account is already inside an organization (created the moment you sign up), the top comment tells you to `terraform import aws_organizations_organization.this <org-id>` instead of letting this resource try to create a second one, which would fail.

**Organizational Units** — six OUs mirroring [docs/04 §1](04-hld-landing-zone.md):
```
Root
├── Security          (Log Archive + Audit accounts live here)
├── Infrastructure    (Network Hub, shared services)
├── Workloads
│   ├── Prod
│   └── NonProd
└── Sandbox
```
`Workloads/Prod` and `Workloads/NonProd` are nested one level under `Workloads` (`parent_id = aws_organizations_organizational_unit.workloads.id`) so an SCP attached to `Workloads` applies to both without duplicating the attachment.

`local.ou_id_by_name` is a lookup map (`"Workloads/Prod" → ou-xxxx`) that both `member_accounts` (below) and any other stack can reference by human-readable name instead of a raw OU id.

### Service Control Policies (preventive guardrails)

Four SCPs, each a separate `aws_organizations_policy` resource whose JSON lives in `scps/`:

| Policy | File | What it denies | Attached to |
|---|---|---|---|
| `deny-leave-organization` | `scps/deny-leave-organization.json` | `organizations:LeaveOrganization` | **Root** (every account) |
| `deny-root-user-actions` | `scps/deny-root-user.json` | Every action, when the caller is the account's root user (`aws:PrincipalArn` matches `arn:aws:iam::*:root`) | **Root** |
| `require-imdsv2` | `scps/require-imdsv2.json` | `ec2:RunInstances` unless `ec2:MetadataHttpTokens = required` | **Workloads** OU only |
| `region-restriction` | `scps/region-restriction.json.tpl` | Everything **not** in `NotAction` list, when `aws:RequestedRegion` isn't in `var.allowed_regions` | **Workloads** OU only |

**Mandatory:** `deny-leave-organization` and `deny-root-user-actions`, attached at the **root** so Security/Infrastructure accounts (management, log archive, audit, network hub) are covered too — you never want any account leaving the org or logging in as root.

**Optional (recommended defaults):** `require-imdsv2` and `region-restriction`, attached only to the **Workloads** OU. These encode a specific policy choice (which regions, whether IMDSv2 is mandatory) rather than a structural requirement — adjust or drop them per your own org's policy without breaking anything else in this codebase. They're deliberately scoped away from Security/Infrastructure so those accounts stay free to run global tooling (e.g. a CloudFront distribution, an IAM Identity Center instance, or a global WAF) that would otherwise trip the region guardrail.

The region-restriction policy is a `.json.tpl` (Terraform template file, rendered with `templatefile()`) rather than plain JSON because `allowed_regions` is a variable — `${allowed_regions}` in the template gets substituted with `jsonencode(var.allowed_regions)`, e.g. `["us-east-1","us-east-2"]`. Its `NotAction` list is every global-endpoint service (IAM, Organizations, Route 53, CloudFront, WAF, Support, Budgets, STS, Shield, Global Accelerator, etc.) — without excluding these, the SCP would break global services that don't have a "region" in the normal sense.

Each policy is created once (`aws_organizations_policy`) and attached separately (`aws_organizations_policy_attachment`) — SCPs and attachments are different resources in the AWS provider because one policy can attach to multiple targets.

### Vending member accounts — **Optional**

```hcl
resource "aws_organizations_account" "member" {
  for_each  = var.member_accounts
  ...
  lifecycle { ignore_changes = [role_name] }
}
```
This is **optional** — if you use Control Tower's Account Factory (or vend accounts by hand) instead, leave `var.member_accounts` at its default `{}` and this resource creates nothing. If you do use it, `for_each` over a map keyed by account name means each entry becomes its own account resource (`each.key` = name, `each.value.email`/`.ou` = its config), and `ou` is looked up against `local.ou_id_by_name` to place it. `close_on_deletion = false` is a safety rail — removing an entry from `var.member_accounts` and re-applying will *not* delete/close the real AWS account. `ignore_changes = [role_name]` stops Terraform from trying to rename the account's default `OrganizationAccountAccessRole` after creation, since that's set once at birth.

### Variables
- `allowed_regions` (list, default `["us-east-1","us-east-2"]`) — feeds the region-restriction SCP.
- `member_accounts` (map, default `{}`) — see above.

### Outputs
- `organization_id`, `root_id` — consumed by `log-archive` (bucket policy scoping) and other stacks.
- `ou_ids` — the name→id map, for anything that needs to move/target an OU later.
- `member_account_ids` — only populated for accounts vended by this module.

---

## 2. `modules/log-archive`

**Status: Mandatory.** No feature flags in this module — every resource in it is always created.
**Applied from:** the Log Archive account.
**Files:** `main.tf`, `variables.tf`, `outputs.tf`

Builds the **destination** bucket that every account's CloudTrail/Config logs land in. It does **not** create the org CloudTrail trail resource itself — `is_organization_trail = true` can only be set from the management account, so that resource lives in `environments/management/main.tf` instead and just points at this bucket by name.

### KMS key (`aws_kms_key.logs` + `aws_kms_alias.logs`)
Encrypts everything in the bucket. `enable_key_rotation = true` rotates the backing key material yearly; `deletion_window_in_days = 30` is the AWS maximum pending-deletion window (safety margin if someone fat-fingers a `terraform destroy`). The key policy has three statements:
1. `AllowAccountAdmin` — the Log Archive account's root principal gets full `kms:*`. This is normal/required for every KMS key (without it, you can permanently lock yourself out) and is *not* the same as the SCP that blocks root-user *actions* — this is a policy on the key resource, not an IAM principal being used.
2. `AllowCloudTrailEncrypt` / `AllowConfigEncrypt` — let the CloudTrail and Config **services** call `GenerateDataKey`/`DescribeKey`, scoped with `"aws:PrincipalOrgID" = var.organization_id` so only your org's CloudTrail/Config (not anyone else's AWS account) can use the key.

### The bucket itself
- `aws_s3_bucket.logs` — just the bucket, name from `var.bucket_name` (must be globally unique across all of S3, not just your account).
- `aws_s3_bucket_public_access_block.logs` — all four block flags true. Belt-and-suspenders since the bucket policy below never grants public access anyway, but this is what actually prevents a *future* misconfigured bucket policy or ACL from exposing it.
- `aws_s3_bucket_versioning.logs` — `Enabled`, so a log object can't be silently overwritten/deleted without a trace.
- `aws_s3_bucket_server_side_encryption_configuration.logs` — forces `aws:kms` using the key above, with `bucket_key_enabled = true` (an S3 Bucket Key cuts KMS request costs/throttling for high-volume log writes — CloudTrail can write a lot of small objects).
- `aws_s3_bucket_lifecycle_configuration.logs` — transitions to `STANDARD_IA` at `var.transition_to_ia_days` (default 30), then `GLACIER` at `var.transition_to_glacier_days` (default 90). Expiration is a `dynamic` block that only exists if `var.log_retention_days != null` — the default (`2555` days, ~7 years) sets an expiration, but pass `null` to keep logs forever (common when a compliance regime requires indefinite CloudTrail retention).

### Bucket policy (`aws_s3_bucket_policy.logs`)
Five statements:
1. `AWSCloudTrailAclCheck` — lets `cloudtrail.amazonaws.com` call `GetBucketAcl` (CloudTrail checks this before it will start delivering).
2. `AWSCloudTrailWrite` — lets CloudTrail `PutObject` under `AWSLogs/*`, conditioned on `bucket-owner-full-control` ACL and the org-id condition.
3. `AWSConfigBucketPermissionsCheck` / 4. `AWSConfigWrite` — same pattern for AWS Config's per-account snapshot delivery (each account's own Config recorder writes here — see `account-baseline` below).
5. `DenyUnencryptedTransport` — denies **all** S3 actions on the bucket/its objects when `aws:SecureTransport = false`, i.e. blocks plain-HTTP access entirely.

Every statement that isn't the deny is scoped to `"aws:PrincipalOrgID" = var.organization_id` — this is the mechanism that lets *every account in your org* deliver logs here without needing 200 individual bucket-policy statements or cross-account roles.

### Variables
`organization_id`, `bucket_name` (required, no default — must be globally unique), `log_retention_days` (default 2555 / ~7yr, `null` = forever), `transition_to_ia_days` (30), `transition_to_glacier_days` (90).

### Outputs
`bucket_name`, `bucket_arn`, `kms_key_arn` — consumed by `account-baseline` (every account's Config delivery channel) and `environments/management` (the org CloudTrail trail).

---

## 3. `modules/account-baseline`

**Status: Mandatory, everywhere.** No feature flags — this module has no optional resources.
**Applied from:** literally every account (log archive, audit, network hub, every workload account, and implicitly management via its own stack). AWS Config is per-account **and per-region**, so there is no "set it up once centrally" option — this module exists to be copy-pasted into every environment's `main.tf`.

### AWS Config (detective guardrail)
- `aws_iam_role.config` — trust policy lets `config.amazonaws.com` assume it.
- `aws_iam_role_policy_attachment.config_managed` — attaches the AWS-managed `AWS_ConfigRole` policy (grants Config permission to *describe* resources across the account).
- `aws_iam_role_policy.config_s3_delivery` — a separate **inline** policy for the one thing the managed policy doesn't cover: writing snapshots to the *central* Log Archive bucket (cross-account). Three statements: `PutObject` under `AWSLogs/<this account id>/Config/*` (conditioned on `bucket-owner-full-control`), `GetBucketAcl`/`ListBucket` on the bucket itself, and `GenerateDataKey*`/`Decrypt` on the log-archive KMS key (Config needs `Decrypt` too, not just `GenerateDataKey`, because it reads back its own delivered snapshots in some flows).
- `aws_config_configuration_recorder.this` — `all_supported = true` + `include_global_resource_types = true` means Config tracks every resource type AWS supports in this region, including account-global ones like IAM (recorded once per account to avoid duplicate global-resource events across regions — Config handles the dedup).
- `aws_config_delivery_channel.this` — points at the central bucket with a per-account key prefix (`AWSLogs/<account-id>/Config`) so every account's snapshots land in the same bucket without colliding. `depends_on = [aws_config_configuration_recorder.this]` is required — the delivery channel API call fails if the recorder doesn't exist yet, and Terraform can't infer that ordering from attributes alone since there's no direct reference between them.
- `aws_config_configuration_recorder_status.this` — recorder and delivery channel can exist while still "off"; this resource is the actual on/off switch (`is_enabled = true`), applied last (`depends_on = [aws_config_delivery_channel.this]`) because starting the recorder before the delivery channel exists would error.

### Account-level hardening
- `aws_s3_account_public_access_block.this` — the **account-wide** version of the public-access-block (vs. the per-bucket one in `log-archive`). This is a single resource per account/region that blocks public access as the *default* for every bucket in the account, including ones created later without their own explicit block.
- `aws_iam_account_password_policy.this` — 14-char minimum, all four character classes required, 90-day max age, 24-password reuse prevention. This only matters for accounts with IAM users that log in with a password; if the account is 100% federated through Identity Center (the intended design here), it's a low-cost baseline that also satisfies most compliance scanners (CIS benchmark checks for exactly this).

### Variables
`log_archive_bucket_name`, `log_archive_kms_key_arn` (both required — output from `log-archive`, passed in as plain strings since this module runs in a different account/state), `config_delivery_frequency` (default `TwentyFour_Hours`).

### Outputs
`config_role_arn` — not consumed elsewhere today, exposed for convenience (e.g. if you later add custom Config rules needing the role ARN).

---

## 4. `modules/security-baseline`

**Status: Mandatory.** No feature flags — every resource always creates; the only customizable piece is *which* Security Hub standards you subscribe to (`security_hub_standards`), not *whether* you subscribe to any.
**Applied from:** the management account, but it's the one module in this codebase that needs **two provider configurations simultaneously** — the default `aws` provider (management account) and an aliased `aws.audit` (Audit account) — because GuardDuty/Security Hub *delegation* is a management-account action, while *configuring* the delegated service happens in the Audit account itself.

```hcl
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", configuration_aliases = [aws.audit] }
  }
}
```
This `configuration_aliases` block is what lets a *module* (not just the root config) declare it needs a second aliased provider — the caller must pass both explicitly:
```hcl
module "security_baseline" {
  source    = "../../modules/security-baseline"
  providers = { aws = aws, aws.audit = aws.audit }
}
```
(see `environments/management/providers.tf`, where `aws.audit` is defined with an `assume_role` block targeting the Audit account's `OrganizationAccountAccessRole`).

### Delegation (runs as management account)
- `aws_guardduty_organization_admin_account.this` — makes the Audit account the GuardDuty delegated administrator for the whole org.
- `aws_securityhub_organization_admin_account.this` — same, for Security Hub.

### Configuration (runs as Audit account, via `provider = aws.audit`)
- `aws_guardduty_detector.audit` — turns GuardDuty on in the Audit account, with `depends_on = [aws_guardduty_organization_admin_account.this]` (must be delegated first) — Terraform can't infer this dependency automatically since the two resources don't reference each other's attributes.
- Three `aws_guardduty_detector_feature` resources — `S3_DATA_EVENTS`, `EKS_AUDIT_LOGS`, `EBS_MALWARE_PROTECTION`. The comment in the file explains why these are three separate resources instead of one `datasources` block: that nested-block API was deprecated in AWS provider v5 and removed in v6, replaced by one resource per feature.
- `aws_guardduty_organization_configuration.audit` — `auto_enable_organization_members = "ALL"` means every *new* account born into the org automatically gets GuardDuty turned on with no extra Terraform apply needed.
- `aws_securityhub_account.audit` — `enable_default_standards = false` deliberately, because standards are subscribed to explicitly and individually below (avoids silently enabling a standard you didn't choose, which shows up as a cost and a wall of findings).
- `aws_securityhub_organization_configuration.audit` — `auto_enable = true`, the Security Hub equivalent of the GuardDuty auto-enable above.
- `aws_securityhub_standards_subscription.audit` — `for_each` over `var.security_hub_standards`, defaulting to CIS AWS Foundations Benchmark v1.4.0 and AWS Foundational Security Best Practices v1.0.0.

### Variables
`audit_account_id` (required), `security_hub_standards` (list of standard ARNs, defaulted as above — note these ARNs are region-specific in general, so if you deploy outside `us-east-1` you'll want to override this).

### Outputs
`guardduty_detector_id`.

---

## 5. `modules/network-hub`

**Status: Mandatory** for the Transit Gateway + egress VPC + NAT + RAM share (the core hub-and-spoke networking every workload VPC's routing depends on). **Optional** for Direct Connect and the VPN backup — both off by default, toggled independently.
**Applied from:** the Network Hub account. This is the most resource-dense module — it builds the Transit Gateway, a centralized egress VPC (so NAT lives in one account instead of every workload account paying for its own NAT Gateway), and optional hybrid connectivity.

### Transit Gateway + sharing
- `aws_ec2_transit_gateway.this` — `auto_accept_shared_attachments = "enable"` means workload accounts' VPC attachments (created *from their own account*, via the RAM share below) get auto-accepted without a manual step in the hub account. `vpn_ecmp_support = "enable"` allows equal-cost multi-path routing if you ever add a second VPN/DX path.
- `aws_ram_resource_share.tgw` / `aws_ram_resource_association.tgw` / `aws_ram_principal_association.tgw` — three resources that together do what the AWS RAM console does in one flow: create a resource share, put the TGW into it, and grant each account in `var.workload_account_ids` access to it. All three are conditioned on `length(var.workload_account_ids) > 0` (via `count`) — **mechanically optional** (creates nothing with an empty list) but **practically mandatory** the moment you have even one workload account, since that account's `workload-vpc` attachment has nothing to attach to without it.

### Centralized egress VPC
- `aws_vpc.egress`, `aws_internet_gateway.egress` — standard.
- `aws_subnet.nat` and `aws_subnet.tgw_attach` — one of each per AZ in `var.azs`, carved out of the `/24` `egress_vpc_cidr` using `cidrsubnet(cidr, 2, index)` (splits into four `/26`s: NAT subnets take indices `0..len(azs)-1`, TGW-attach subnets take `len(azs)..2*len(azs)-1`).
- `aws_eip.nat` + `aws_nat_gateway.this` — one NAT Gateway per AZ (not one for the whole VPC), so a single AZ outage doesn't take down egress for the other AZ. `depends_on = [aws_internet_gateway.egress]` because NAT Gateway creation can fail if the IGW isn't attached yet, and there's no direct attribute reference to make Terraform infer that ordering.
- Two separate route tables: `aws_route_table.nat` (the NAT subnets themselves route `0.0.0.0/0` → IGW) and `aws_route_table.tgw_attach` (per-AZ, each one routing `0.0.0.0/0` → **the NAT Gateway in the same AZ**) — this keeps cross-AZ data transfer charges from applying to egress traffic that arrives over the TGW.
- `aws_ec2_transit_gateway_vpc_attachment.egress` — attaches this VPC to the TGW using the `tgw_attach` subnets.
- `aws_ec2_transit_gateway_route.default_to_egress` — the key routing decision: a `0.0.0.0/0` route in the TGW's **default association route table**, pointing at the egress attachment. Because every other attachment (each workload VPC) uses default route-table association/propagation, they all inherit this route automatically — a workload VPC's `0.0.0.0/0` traffic reaches the TGW, and the TGW's default route table already knows to send it to the egress VPC's NAT gateways.

  **Segmentation caveat (called out in the file's own header comment):** this is a *single shared* TGW route table. It's fine for a first landing zone, but it means every attached VPC can currently route to every other attached VPC by default. The README's "Extending toward prod/non-prod route isolation" section describes the upgrade path — set `default_route_table_association`/`propagation` to `"disable"` and create explicit `aws_ec2_transit_gateway_route_table` resources per segment.

### Direct Connect (primary hybrid path) — **Optional**, default off (`enable_direct_connect = false`)
- `aws_dx_gateway_association.this` — `count = var.enable_direct_connect ? 1 : 0`, so this resource creates nothing unless you flip the flag. Note this only *associates* an existing Direct Connect Gateway (`var.direct_connect_gateway_id`) with the TGW — the physical cross-connect and virtual interface are provisioned out-of-band (AWS Support ticket + your network carrier), as the module header and the top-level README both flag. `allowed_prefixes` (default `10.0.0.0/8`) is what gets advertised to on-prem over BGP.

### Site-to-Site VPN (backup hybrid path) — **Optional**, default off (`enable_vpn_backup = false`)
- `aws_customer_gateway.onprem` + `aws_vpn_connection.backup` — both gated on `var.enable_vpn_backup`, both `count = 0` by default. `static_routes_only = false` means this expects BGP dynamic routing from the on-prem VPN device, matching the DX gateway's BGP-based approach above (consistent routing story across both paths).

### Variables
`name_prefix` (default `"network-hub"`), `azs` (required, no default), `egress_vpc_cidr` (default `10.0.0.0/24`), `amazon_side_asn` (default `64512` — must not collide with your on-prem ASN), `enable_direct_connect`/`direct_connect_gateway_id`, `enable_vpn_backup`/`customer_gateway_ip`/`customer_gateway_bgp_asn` (default `65000`), `workload_account_ids` (default `[]`), and `dx_allowed_prefixes` (declared inline mid-file rather than in `variables.tf` — a minor inconsistency worth knowing about if you go looking for it).

### Outputs
`transit_gateway_id`, `transit_gateway_route_table_id`, `egress_vpc_id`, `ram_share_arn` (`null` if no workload accounts were passed).

---

## 6. `modules/workload-vpc`

**Status: Mandatory, per app account** — the VPC, three subnet tiers, routing, security groups, flow logs, and per-workload KMS key all always create. The one optional piece is `onprem_cidrs` (empty by default — see below).
**Applied from:** every migrated application account, once per app(-group) per docs/04 §1's "one account per app(-group)" pattern. This is the module you're meant to compose behind each real workload — `environments/workload-account-example/` is a thin wrapper around it.

### Addressing
Give it a `/24` (`var.vpc_cidr`); the subnet math (`cidrsubnet(var.vpc_cidr, 3, index)`) splits it into eight `/27`s, of which six are used: public/app/data × up to 2 AZs. Index assignment: public tier gets `0..azs-1`, app tier gets `azs..2*azs-1`, data tier gets `2*azs..3*azs-1`.

### Three tiers
- **Public** (`aws_subnet.public`) — `map_public_ip_on_launch = false` *deliberately*, even though it's the "public" tier: the ALB gets its own Elastic IP/AWS-assigned public IP as part of being internet-facing, but nothing else in this subnet should auto-assign one.
- **App** (`aws_subnet.app`) — hosts EC2/ECS/etc.; also where the TGW attachment's subnets live (`aws_ec2_transit_gateway_vpc_attachment.this` uses `aws_subnet.app`).
- **Data** (`aws_subnet.data`) — hosts RDS/Aurora/etc.

### Routing — the security-relevant part
- Public route table → IGW directly (`aws_route.public_to_igw`).
- App route table → **TGW** for `0.0.0.0/0` (`aws_route.app_to_tgw`) — general internet egress goes over the TGW to the Network Hub's NAT gateways, not a per-account NAT Gateway. `depends_on = [aws_ec2_transit_gateway_vpc_attachment.this]` because the route would fail to create before the attachment exists.
- Data route table → **no default route at all.** Only `aws_route.data_to_onprem`, a `for_each` over `var.onprem_cidrs` — **optional**, default `[]`, so by default this `for_each` creates zero routes — each one a specific route to the TGW. If you never pass `onprem_cidrs`, the data tier has zero path to the internet or on-prem — fully isolated except within the VPC. This is called out explicitly in both the module header and the top-level README as intentional: "no database or app server gets a public IP, by design."

### Security groups (three-tier chaining, not CIDR-based)
- `alb` — `443` open to `0.0.0.0/0` (it's the internet-facing tier, so this is correct/expected).
- `app` — `var.app_port` (default `8080`) open **only from the ALB security group** (`security_groups = [aws_security_group.alb.id]`), not from a CIDR block. This is the standard "reference the SG, not the IP range" pattern — it stays correct even if subnet CIDRs change.
- `data` — `var.db_port` (default `5432`, i.e. Postgres; override to `3306` for MySQL/Aurora-MySQL or `1521` for Oracle) open only from the **app** security group. Notably `data`'s security group has no `egress` block at all — the AWS provider defaults a security group with no explicit egress rule to **deny all egress** (the opposite of a VPC's implicit-allow-all default), which is intentional hardening: even if something on the data tier tried to phone home, the SG blocks it in addition to the route table already having nowhere for it to go.

### VPC Flow Logs
`aws_cloudwatch_log_group.flow_logs` + `aws_iam_role.flow_logs` (trust: `vpc-flow-logs.amazonaws.com`) + inline policy scoped to `CreateLogStream`/`PutLogEvents` on just this log group + `aws_flow_log.this` with `traffic_type = "ALL"` (accepted and rejected traffic both). Retention is `var.log_retention_days` (default 90) — shorter than the log-archive bucket's default 7-year retention because flow logs are operational/debugging data in CloudWatch, not the compliance-grade audit trail (that's what CloudTrail → the central S3 bucket is for).

### Per-workload KMS key
`aws_kms_key.this` + `aws_kms_alias.this` (`alias/<app>-<environment>`) — a **separate key per workload account**, for encrypting that app's EBS volumes/RDS instances. This is distinct from the log-archive module's key (which only encrypts the central log bucket) — each workload gets its own key so a key-level blast radius (compromise, accidental policy change) stays contained to one app.

### Variables
`app_name`, `environment` (`"prod"`/`"nonprod"` — used in tags and, per its description, meant to guide which TGW route table a VPC attaches to once you implement the segmented-route-table upgrade), `vpc_cidr`, `azs`, `transit_gateway_id`, `db_port` (default `5432`), `log_retention_days` (default 90), `onprem_cidrs` (default `[]`), `app_port` (default `8080`), `tags` (default `{}`, merged with `App`/`Environment`/`ManagedBy` into `local.common_tags` and applied to every taggable resource).

### Outputs
`vpc_id`, `public_subnet_ids`, `app_subnet_ids`, `data_subnet_ids`, `alb_security_group_id`, `app_security_group_id`, `data_security_group_id`, `kms_key_arn`, `transit_gateway_attachment_id`.

---

## 7. `modules/iam-identity-center`

**Status: Mandatory in shape, customizable in content** — you'll always need some permission sets for federated access, but the three shipped here are a starting point to override, not a fixed set. **Account assignments are a required gap** (see Outputs below), not an optional feature.
**Applied from:** the management account (or wherever Identity Center administration is delegated to).

The header comment is the single most important operational note in this module: **IAM Identity Center itself has no cold-start API** — it must be enabled once, by hand, in the console (Settings → Enable) before this module's `data "aws_ssoadmin_instances" "this" {}` will resolve to anything. Run `terraform apply` here before that click, and it fails on the data source.

Once enabled:
- `aws_ssoadmin_permission_set.this` — `for_each` over `var.permission_sets`, one permission set per map entry (`session_duration` is an ISO-8601 duration string, e.g. `"PT8H"` = 8 hours).
- `aws_ssoadmin_managed_policy_attachment.this` — this one has a slightly denser `for_each`: each permission set can have *multiple* managed policy ARNs, so the code flattens `{name → {managed_policy_arns: [...]}}` into a flat list of `{key, name, policy_arn}` pairs first (`flatten([for name, cfg in var.permission_sets : [for policy_arn in cfg.managed_policy_arns : {...}]])`), then turns that list into a map keyed by `"<name>-<policy_arn>"` so `for_each` has stable, unique keys. This is the standard Terraform pattern for "one resource per (parent, child) combination" — needed because `aws_ssoadmin_managed_policy_attachment` only accepts one policy ARN per resource instance.

### Default permission sets
| Name | Purpose | Managed policy | Session |
|---|---|---|---|
| `MigrationEngineer` | Runs MGN/DMS tooling, no IAM/Org access | `AWSApplicationMigrationAgentPolicy` | 8h |
| `AppOwnerReadOnly` | App owners validating a migration | `ReadOnlyAccess` | 4h |
| `SecurityAuditor` | Security/compliance review | `SecurityAudit` | 4h |

These are starting points, not a complete set — there's no admin/break-glass permission set defined here (deliberately: the `deny-root-user` SCP pushes break-glass access toward a dedicated Identity Center permission set instead of root, per its own description, but that permission set isn't pre-built in this default map — add one, e.g. an `AdministratorAccess`-backed `BreakGlassAdmin` set, before you actually need it).

### Variables
`permission_sets` — the map above is the *default*; override entirely to add more roles (there's no way to "add one more" without repeating the whole default map, since Terraform variable defaults don't merge).

### Outputs
`permission_set_arns` — map of name → ARN, for wiring up account assignments.

**Gap, not optional:** `aws_ssoadmin_account_assignment` resources — which map a permission set to a specific account + principal (user/group) — aren't included here. Without them, the permission sets exist but are assigned to no one, so this module alone doesn't yet grant anyone access. Treat this as a required addition before relying on Identity Center for real access, not a nice-to-have.

---

## 8. `environments/*` — how the modules get composed

Each environment folder is a separate Terraform state / AWS account. All five follow the same three-file shape: `providers.tf` (pins `hashicorp/aws ~> 5.0`, sets `region = var.aws_region`), `backend.tf` (a **commented-out** S3+DynamoDB backend block — intentionally inert until you bootstrap that bucket/table by hand, since Terraform can't create the backend it's about to store its own state in), `variables.tf`, `main.tf`, and (except `management`) `outputs.tf`.

### `environments/management`
Composes `org_foundation` + `security_baseline` (with the dual-provider wiring described in module 5 above) + `identity_center`, and additionally owns the **org CloudTrail trail** directly (not wrapped in a module):
```hcl
resource "aws_cloudtrail" "organization" {
  is_organization_trail      = true   # management-account-only setting
  is_multi_region_trail      = true
  s3_bucket_name             = var.log_archive_bucket_name   # from the log-archive-account stack, applied separately
  kms_key_id                 = var.log_archive_kms_key_arn
  event_selector { read_write_type = "All"; include_management_events = true }
  depends_on = [module.org_foundation]
}
```
`depends_on = [module.org_foundation]` because the trail needs the organization/OUs to exist first, but nothing in the trail resource's arguments actually references an `org_foundation` output — hence the explicit dependency. Notice this stack takes `log_archive_bucket_name`/`log_archive_kms_key_arn` as **plain input variables**, not module outputs — because the log-archive module runs in a *different account* with its own state; you copy its output values into this stack's `terraform.tfvars` by hand (or via remote state data source, if you set one up — not done here).

`providers.tf` here is also the one place the dual-provider pattern is set up concretely:
```hcl
provider "aws" { region = var.aws_region }                       # management account
provider "aws" {
  alias = "audit"
  assume_role { role_arn = "arn:aws:iam::${var.audit_account_id}:role/OrganizationAccountAccessRole" }
}
```

### `environments/log-archive-account`
Composes `log_archive` + `account_baseline`, feeding the just-created bucket/key straight into its own baseline (`module.account_baseline.log_archive_bucket_name = module.log_archive.bucket_name`) — this account bootstraps itself and needs no cross-stack input. **Apply this one first** (see README deployment order) since every other stack needs its bucket/key outputs.

### `environments/audit-account`
Just `account_baseline` — its GuardDuty/Security Hub setup is entirely remote-controlled from `environments/management`'s `security_baseline` module (delegated administration), so there's nothing security-specific to declare locally; the file's own comment says as much.

### `environments/network-hub-account`
Composes `network_hub` + `account_baseline`. Note `workload_account_ids` must be known **before** this apply (it drives the RAM share) — in practice this means either over-provisioning the list up front, or re-applying this stack each time a new workload account needs TGW access.

### `environments/workload-account-example`
Composes `workload_vpc` + `account_baseline`; **meant to be copied**, not applied directly (per both this file's header comment and the top-level README: `cp -r environments/workload-account-example environments/ordermgmt-prod`). Its header also documents the one manual step every new workload account needs before its first apply: accept the Transit Gateway's RAM share invitation (`aws ram get-resource-share-invitations` / `accept-resource-share-invitation`, or uncomment the `aws_ram_resource_share_accepter` resource sketched in the comment) — otherwise `aws_ec2_transit_gateway_vpc_attachment.this` inside `workload-vpc` has no share to attach into.

---

## 9. End-to-end request path (tying it all together)

A packet leaving an app-tier EC2 instance in a workload account, headed to the internet:
1. App-tier route table → `0.0.0.0/0` → **Transit Gateway** (workload-vpc's `app_to_tgw` route).
2. TGW's default association route table → `0.0.0.0/0` → **egress VPC attachment** (network-hub's `default_to_egress` route) — every workload VPC shares this one route table today (see the segmentation caveat above).
3. Egress VPC's TGW-attach subnet route table → `0.0.0.0/0` → **NAT Gateway in the same AZ** (network-hub's `tgw_attach_to_nat` route).
4. NAT Gateway → **Internet Gateway** → internet.

A CloudTrail/Config log being delivered:
1. Every account's AWS Config (from `account-baseline`) writes to `s3://<central-bucket>/AWSLogs/<account-id>/Config/*`, permitted by the log-archive bucket policy's `AWSConfigWrite` statement (scoped by org id) and the account's own `config_s3_delivery` IAM policy.
2. The org CloudTrail trail (`environments/management`) writes to `s3://<central-bucket>/AWSLogs/*` under the `AWSCloudTrailWrite` statement — one trail covers every account in the org because `is_organization_trail = true`.
3. Everything is encrypted with the log-archive KMS key, and any plain-HTTP access attempt is denied outright by `DenyUnencryptedTransport`.

A security finding surfacing:
1. GuardDuty/Security Hub run *in the Audit account* (delegated from management by `security-baseline`), because `auto_enable_organization_members = "ALL"` / `auto_enable = true` mean every current and future org member gets scanned automatically without a per-account apply.

---

## 10. Things to know before you run this for real

- **Nothing here has been `terraform init`/`plan`/`apply`-tested against live AWS** — this is reference architecture code matching the HLD, meant to be reviewed, adapted to your naming/CIDR/account-id conventions, and validated in a sandbox OU before touching Security/Infrastructure or production workload accounts.
- **Bootstrap order matters and is manual in three places:** the S3+DynamoDB backend per account (`backend.tf` comments), Identity Center's console "Enable" click, and each workload account's TGW RAM-share acceptance.
- **The org CloudTrail trail and the log-archive bucket are in different stacks/accounts** — you must apply `log-archive-account` first and hand-copy its `bucket_name`/`kms_key_arn` outputs into `management`'s `terraform.tfvars` (or wire up `terraform_remote_state`, which isn't set up here).
- **The Transit Gateway route table is unsegmented by default** — treat "flip to per-segment route tables" as a required follow-up before this goes to production with a real prod/non-prod boundary, not an optional nice-to-have (see README §"Extending toward prod/non-prod route isolation").
- **No account assignments exist yet** for the Identity Center permission sets (`iam-identity-center` builds the permission sets but never maps them to accounts/users/groups via `aws_ssoadmin_account_assignment`) — that's the natural next module to add.
