# Destroying Landing Zone Infrastructure

There is no destroy button anywhere in this codebase — not in the
[Landing Zone UI](ui/README.md), and no `terraform destroy` wrapper script.
This is deliberate: tearing down a landing zone is rare, high-impact, and
each stack has its own ordering gotchas (below), so it should always be a
deliberate CLI action by someone who can read the plan output first, not a
button.

## Before you do anything: find the state

Every command below acts on whatever `terraform.tfstate` Terraform can find
for that environment — either a local file in that directory, or (if you've
run [`bootstrap-backend/`](bootstrap-backend/)) the S3 object its
`backend.hcl` points at. If that state doesn't exist or is stale, `destroy`
either has nothing to act on or acts on wrong information — it is **not** a
generic "find and delete everything with these tags" tool.

```
cd aws-migration/terraform/environments/<name>
terraform state list
```

If this prints the resources you expect, you're looking at the right state.
If it's empty or errors, stop and figure out why before proceeding (see
"If the state is missing" at the bottom).

## Standard destroy sequence, per stack

### 1. Reconnect to the right state

**If you bootstrapped remote state** (see [`bootstrap-backend/README.md`](bootstrap-backend/README.md)):
```
terraform init -backend-config=backend.hcl
```

**If still on local state** (the default until you bootstrap):
```
terraform init -input=false
```
(only needed if `.terraform/` isn't already present in the directory.)

### 2. Review before touching anything

```
terraform plan -destroy
```
Read it. Confirm the resource count and identities (bucket names, account
ids in ARNs) match what you actually intend to remove — this is the same
step Apply's UI confirmation is standing in for; here, you *are* the
confirmation step.

### 3. Destroy

```
terraform destroy
```
Terraform will show the same plan again and prompt for a typed `yes`. Add
`-auto-approve` only in a scripted/CI context where the plan was already
reviewed by something else — never as a habit for interactive use.

## Order matters — reverse of the apply order

Apply order is log-archive → management → audit → network-hub → per
workload (see [README.md](README.md#deployment-order)). Destroy roughly in
reverse, because later stacks depend on earlier ones' outputs:

1. **Workload accounts first.** Each app's `workload-vpc` stack owns its own
   Transit Gateway attachment — destroying it detaches cleanly from the
   Network Hub's TGW without you needing to touch the hub. Do this for every
   workload account before touching Network Hub or Log Archive.
2. **`network-hub-account`.** Safe once no workload VPCs are still attached
   (an attached workload would otherwise block or orphan on TGW deletion).
   If `workload_account_ids` still lists accounts you haven't destroyed yet,
   the RAM share also stays live pointing at them — harmless, just untidy;
   clean up the variable and re-apply, or just destroy the whole stack.
3. **`audit-account`.** Straightforward — its baseline is self-contained.
   GuardDuty/Security Hub delegation itself is undone in the next step.
4. **`management`.** Destroy this **before or together with**
   `log-archive-account`, not after — its `aws_cloudtrail.organization`
   resource points at the Log Archive bucket by name. If you destroy the
   bucket first and then try to destroy the trail, or leave the trail
   pointing at a bucket that's already gone, you can end up with a
   dangling/errored trail resource in state.  Destroying `management` also
   tears down GuardDuty/Security Hub organization delegation and Identity
   Center permission sets — expect any active SSO sessions using those
   permission sets to lose access immediately.
5. **`log-archive-account` last.** Nothing else in this codebase depends on
   it once the above are gone. Note: if `log_retention_days` was left at
   its default (~7 years) or `null` (forever) and the bucket has real
   objects in it (actual CloudTrail/Config history, not just this
   codebase's own test runs), `aws_s3_bucket` deletion will fail with
   `BucketNotEmpty` — Terraform does not empty non-empty buckets for you.
   Empty it first (`aws s3 rm s3://<bucket> --recursive`, and if versioning
   is on, delete the versions/delete-markers too) if you actually intend to
   delete the log history, not just stop paying for the infrastructure.

### `management`'s dual-provider requirement still applies

`environments/management` needs both providers from its `providers.tf` —
the default one (management account) and `aws.audit` (assumes
`OrganizationAccountAccessRole` into the Audit account) — for
`security-baseline`'s Audit-account-side resources (the GuardDuty detector,
Security Hub subscriptions) to be destroyed correctly. Destroy it with the
same credentials/profile setup you'd use to apply it, not a stripped-down
one.

## If the state is missing

If `terraform.tfstate` was never bootstrapped to remote storage and the
machine that ran the last `apply` is gone, wiped, or its local file was
deleted, there is no clean `terraform destroy` path — Terraform has no
knowledge of what it created. Your options, worst to best:

- **Delete by hand in the AWS Console/CLI**, resource by resource, using
  the resource names/patterns in
  [`docs/15-terraform-code-walkthrough.md`](../docs/15-terraform-code-walkthrough.md)
  as your checklist (e.g. `aws-config-role`, `alias/log-archive`,
  `aws-config-configuration-recorder` named `default`, etc.). Tedious and
  error-prone, but works when nothing else does.
- **Reconstruct state with `terraform import`** per resource, then destroy
  normally — only worth it if you have a lot of these resources and want a
  clean, verifiable destroy rather than a manual sweep.
- **Prevent this from ever being necessary again**: bootstrap remote state
  ([`bootstrap-backend/`](bootstrap-backend/)) before you next apply
  anything you intend to keep. This is the whole reason that stack exists.

## Quick reference

| Stack | Destroy safe once... | Extra step |
|---|---|---|
| workload (`<app>-<env>`) | always, independently | none |
| `network-hub-account` | all workload accounts detached | none |
| `audit-account` | always, independently | none |
| `management` | before/with log-archive-account, not after | needs `aws.audit` provider too |
| `log-archive-account` | last | empty the bucket first if it holds real log history |
