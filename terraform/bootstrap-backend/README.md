# Bootstrap Backend

Run this **once per AWS account** (management, log-archive, audit,
network-hub, and once per workload account) to create that account's
durable Terraform state storage — an S3 bucket (versioned, encrypted,
private) and a DynamoDB table for locking.

Without this, every `environments/*/` stack defaults to **local state**
— a `terraform.tfstate` file that lives only on whichever machine ran
`apply`. That's fine for a quick trial, but it means: no backup if that
machine is lost, no locking (two people/processes applying at once can
corrupt state), and — the thing that actually matters — **if you ever
need to `terraform destroy` real infrastructure, you need that exact
state file, and a local one is one accidental deletion away from gone.**
This bootstrap fixes that, once, per account.

## 1. Apply it (once per account)

```
cd aws-migration/terraform/bootstrap-backend
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars: state_bucket_name must be globally unique across
# all of S3 — e.g. "acme-tfstate-management" for the management account,
# "acme-tfstate-log-archive" for the Log Archive account, etc.

terraform init
terraform apply
```

This itself uses local state (see the comment at the top of `main.tf` for
why) — that's expected and fine for this one stack.

## 2. Point the real environment at it

After apply, note the `backend_hcl` output — it's ready to paste. In the
`environments/<name>/` directory this account runs, create `backend.hcl`
(git-ignored — see `../.gitignore`) from `backend.hcl.example`:

```
cd ../environments/management        # or whichever stack runs in this account
cp backend.hcl.example backend.hcl
# fill in bucket / dynamodb_table / region from bootstrap-backend's output,
# plus a "key" — a per-stack path within the bucket, e.g.:
#   key = "landing-zone/management/terraform.tfstate"

terraform init -backend-config=backend.hcl
```

Terraform will ask to migrate any existing local state into the new S3
backend — say yes if you already have state you want to keep. From then
on, every plan/apply/destroy against that stack (including ones run
through the [Landing Zone UI](../ui/)) automatically uses this remote,
locked, versioned state — no further changes needed.

## 3. Repeat per account

Each account needs its own bucket (bucket names are unique per S3, not
per account, so `-management`/`-log-archive`/`-audit`/`-network-hub`/
`-<app>-<env>` suffixes keep them apart) and its own `terraform apply`
of this stack, run with credentials for that account.

## If you ever need to destroy for real

With remote state in place, destroying is just:
```
cd environments/<name>
terraform init -backend-config=backend.hcl   # if not already initialized
terraform plan -destroy                       # review first
terraform destroy
```
The state needed to do this safely lives in S3, not on whoever's laptop
happened to run the last apply. See [`../DESTROY.md`](../DESTROY.md) for
the full runbook — destroy order across the five stacks, per-stack
gotchas (e.g. `management` vs. `log-archive-account` ordering, emptying a
non-empty log bucket), and what to do if state was never bootstrapped.
