# Landing Zone — Terraform

Implements the account, network, logging, and security foundation from [`docs/04-hld-landing-zone.md`](../docs/04-hld-landing-zone.md). Every migrated workload (docs/06–10's LLDs) lands into an account built from the `workload-vpc` module here.

For a resource-by-resource explanation of everything in this folder — what each module builds, why each decision was made, and how the environments compose them — see [`docs/15-terraform-code-walkthrough.md`](../docs/15-terraform-code-walkthrough.md).

**Don't want to drive Terraform by hand?** Two small local tools cover the two different jobs:
- [`ui/`](ui/) — fill in the fields for one of the five stacks below, review a `terraform plan`, then click Apply. `python ui/app.py`.
- [`scaffolder/`](scaffolder/) — need a folder `ui/` doesn't already know about (a second Network Hub, a second Audit account, an entire second landing zone for another client/org)? Pick a stack type, fill in the same fields, and it generates a brand-new `environments/<name>/` folder with real, committable Terraform code — no dependency on any UI afterward. `python scaffolder/app.py`.

**Scope note:** this does *not* stand up AWS Control Tower itself — Control Tower's account factory and guardrail packaging are a console/CloudFormation-managed product, not something to hand-roll in Terraform (if you want Control Tower, enable it via the console first, then this code manages everything docs/04 §4 calls "anything Control Tower doesn't manage"). If you're **not** using Control Tower, the `org-foundation` module is a complete, lighter-weight standalone alternative: Organizations + OUs + SCPs, no Control Tower required.

## Layout

```
terraform/
  bootstrap-backend/    Creates each account's S3+DynamoDB state backend  → run once per account
  modules/
    org-foundation/       Organizations, OUs, SCPs               → management account
    log-archive/          Central S3 bucket + KMS key            → Log Archive account
    account-baseline/     Config recorder, password policy       → EVERY account
    security-baseline/    GuardDuty + Security Hub delegation     → management + Audit account
    network-hub/          Transit Gateway, egress VPC, DX/VPN     → Network Hub account
    workload-vpc/         3-tier VPC + TGW attachment             → EVERY workload account
    iam-identity-center/  SSO permission sets                     → management account
  environments/
    management/                 composes org-foundation + security-baseline + identity-center
    log-archive-account/        composes log-archive + account-baseline
    audit-account/              composes account-baseline (GuardDuty/Security Hub come from management)
    network-hub-account/        composes network-hub + account-baseline
    workload-account-example/   composes workload-vpc + account-baseline — COPY this per app
  ui/            Browser UI: plan/apply the fixed stacks above  → python ui/app.py
  scaffolder/    Browser UI: generate a NEW environments/ folder → python scaffolder/app.py
```

## Deployment order

Matches [docs/04 §5](../docs/04-hld-landing-zone.md#5-landing-zone-build-sequence). Each environment is a separate Terraform state — apply in this order because later stacks consume earlier ones' outputs as input variables:

1. **`environments/log-archive-account`** — nothing depends on anything else. Note its outputs (`bucket_name`, `kms_key_arn`).
2. **`environments/management`** — needs the Log Archive account's bucket/key outputs, and the Audit account's id (the account itself must already exist — vend it via Control Tower, `org-foundation`'s `member_accounts`, or by hand before running this). Sets up Organizations, SCPs, delegates GuardDuty/Security Hub to the Audit account, creates the org CloudTrail trail, and configures Identity Center permission sets.
3. **`environments/audit-account`** — baseline only; GuardDuty/Security Hub in this account are configured remotely by step 2.
4. **`environments/network-hub-account`** — needs the Log Archive outputs and the list of workload account ids that will attach to the Transit Gateway. Note its `transit_gateway_id` and `ram_share_arn` outputs.
5. **Per workload account** — copy `environments/workload-account-example/` to e.g. `environments/ordermgmt-prod/`, fill in `terraform.tfvars`, accept the TGW's RAM share, then apply.

Tearing infrastructure back down is the reverse of this order, with its own per-stack gotchas — see [`DESTROY.md`](DESTROY.md).

## Prerequisites

- Terraform >= 1.5, AWS provider `~> 5.0`.
- An S3 bucket + DynamoDB table per account for remote state — apply [`bootstrap-backend/`](bootstrap-backend/) once per account to create them (see its README), then point each environment at it per that environment's `backend.tf` comment. Without this, an environment defaults to local state — fine for a first look, but not durable, and it's exactly what you'd need if you ever have to `terraform destroy` that stack for real.
- Credentials for each account, typically via `aws sso login` + `AWS_PROFILE`, or by assuming `OrganizationAccountAccessRole` from the management account. The `security-baseline` module needs both a management-account provider and an aliased Audit-account provider simultaneously — see `environments/management/providers.tf`.
- IAM Identity Center enabled once by hand in the console (no cold-start API for this) before `iam-identity-center`'s `data "aws_ssoadmin_instances"` will resolve.
- If using Direct Connect: the physical connection/virtual interface is provisioned separately (AWS Support ticket + your network carrier) — this code only associates an existing Direct Connect Gateway with the Transit Gateway.

## Sizing conventions baked into `workload-vpc`

- Give it a `/24` VPC CIDR — the subnet math carves it into 3 tiers (public/app/data) × up to 2 AZs as `/27`s.
- The data tier gets **no default route to the internet** — only explicit `onprem_cidrs` routes over the TGW, if you pass any. This is deliberate (docs/04 §2's "no database or app server gets a public IP, by design").
- General egress from the app tier routes over the Transit Gateway to the Network Hub account's NAT gateways — there's no per-account NAT Gateway cost.

## Extending toward prod/non-prod route isolation

`network-hub`'s Transit Gateway ships with a single shared route table (`default_route_table_association/propagation = "enable"`) — adequate for an initial landing zone. As the estate grows, flip both to `"disable"` and create explicit `aws_ec2_transit_gateway_route_table` resources per segment (prod / non-prod / shared-services), associating each workload attachment to the right one, so prod cannot route to non-prod by default — the segmentation the HLD calls for.
