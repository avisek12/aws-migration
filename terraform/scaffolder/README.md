# Environment Scaffolder

A separate local Flask app from [`../ui/`](../ui/). Where `ui/` fills in
variables and runs `terraform plan`/`apply` against the five fixed
environment stacks, this tool has one job: **generate a brand-new
`terraform/environments/<name>/` folder** — real, self-contained Terraform
code, copied from whichever already-tested environment template you pick,
with a real `terraform.tfvars` written from what you filled in.

It never runs `terraform` and never talks to AWS. The output is ordinary
source code: review it, commit it, and run it with `terraform init/plan/
apply` from the CLI on any machine — no dependency on this tool, or any
UI, afterward.

## When to use this vs. `ui/`

- **`ui/`** — you're applying one of the five fixed stacks that already
  exist in this repo (the one real Management account, the one real Log
  Archive account, etc.), or adding another workload account via its
  built-in "New Workload Account" page.
- **This tool** — you need a folder that doesn't fit that fixed set: a
  second Network Hub for a DR region, a second Audit account, or an
  entire second landing zone (Management + Log Archive + Audit + Network
  Hub) for a separate AWS Organization — e.g. a new client engagement.
  It also works for workload accounts, producing the exact same kind of
  folder `ui/`'s "New Workload Account" page does, just as a real
  committable `terraform.tfvars` file instead of a UI-managed
  `terraform.tfvars.json`.

## Run it

```
cd aws-migration/terraform/scaffolder
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5001/` yourself (a different port from
`ui/`'s 5000, so both can run at the same time). It does not open a
browser tab automatically — same reasoning as `ui/`: see its README's
safety notes.

## How it works

1. Pick a stack type (Management, Log Archive, Audit, Network Hub, or
   Workload Account). The field list for each is imported directly from
   [`../ui/config.py`](../ui/config.py) — the two tools can't drift apart
   on what a given stack needs, since they read the same source.
2. Give it a folder name (or, for a workload account, an app name +
   environment — same `<app>-<environment>` convention `ui/` uses).
3. Fill in the fields and submit. The tool:
   - Refuses if `terraform/environments/<name>/` already exists — it
     never overwrites anything.
   - Copies the matching template environment's files
     (`main.tf`, `variables.tf`, `outputs.tf`, `providers.tf`,
     `backend.tf`, `backend.hcl.example`, `terraform.tfvars.example`)
     into the new folder, stripping out any local state/init artifacts
     the template happened to have lying around.
   - Writes a real `terraform.tfvars` in the new folder from your inputs.
4. From there, it's just Terraform:
   ```
   cd terraform/environments/<name>
   terraform init
   terraform plan
   terraform apply
   ```
   See [`../bootstrap-backend/README.md`](../bootstrap-backend/README.md)
   for durable remote state before applying anything you intend to keep,
   and [`../DESTROY.md`](../DESTROY.md) for how to tear it down later.

## Using this together with `ui/`

If you scaffold a workload account here and then also open it in `ui/`'s
"New Workload Account" page, be aware both tools can write a tfvars file
into the same folder — this tool writes `terraform.tfvars` (HCL),
`ui/` writes `terraform.tfvars.json`. Terraform loads both automatically,
and where a variable is set in both, the one loaded later wins (`.tfvars`
before `.tfvars.json`, alphabetically). To avoid confusing precedence,
pick one tool per folder going forward, or delete the other's tfvars file.
