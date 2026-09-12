# Landing Zone UI

A local Flask app so an employee who doesn't know Terraform can fill in
a form, review a `terraform plan`, and click Apply — without touching
the command line. It's a thin front end over the real code in
[`../modules/`](../modules/) and [`../environments/`](../environments/);
see [docs/15-terraform-code-walkthrough.md](../../docs/15-terraform-code-walkthrough.md)
for what every field actually controls and why.

## Run it

```
cd aws-migration/terraform/ui
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000/` yourself in a browser. It does **not**
open a tab automatically — this app runs real `terraform` commands
against real AWS accounts, and an auto-opened, pre-filled form is how a
stray click turns into a real `apply`. Leave the terminal window open
while you use it — closing it stops the server.

## Prerequisites (one-time, per machine)

- **Terraform CLI** installed and on `PATH` (`terraform -version` should work from a normal terminal).
- **AWS CLI profiles** configured for each account you'll target — one for `mgmt`, `log-archive`, `audit`, `network-hub`, and one per workload account. Each page's "AWS Profile" dropdown lists whatever named profiles already exist in `~/.aws/config`. See [AWS_PROFILE_SETUP.md](AWS_PROFILE_SETUP.md) for exact commands/file format if you haven't set these up yet.
- **Remote state (strongly recommended before real use)** — apply [`../bootstrap-backend/`](../bootstrap-backend/) once per account, then follow the matching `backend.tf` comment in that environment's directory. Without it, an environment defaults to local state (a `terraform.tfstate` file only on this machine) — fine for a first look, but not durable, and it's exactly what you'd need if you ever have to destroy that stack for real.
- Everything else [`../README.md`](../README.md) already calls out as manual: enabling IAM Identity Center once in the console, and accepting each workload account's Transit Gateway RAM share invitation.

## How it works

- **One page per environment** — Management Account, Log Archive Account, Audit Account, Network Hub Account, and a "New Workload Account" page that copies `environments/workload-account-example/` into `environments/<app>-<environment>/` the first time you plan it.
- **Save & Plan** writes your inputs to that environment's `terraform.tfvars.json`, then runs `terraform init` and `terraform plan -out=tfplan`, and shows the full CLI output on the page.
- **Apply** only unlocks after a plan has been run against the *current* inputs — change any field and you must re-run Plan before Apply is clickable again. It also requires typing `APPLY` into a confirmation box and confirming a browser dialog, then runs `terraform apply` against the exact saved plan file, never a fresh, unreviewed plan.
- Every plan/apply attempt (environment, profile, pass/fail, timestamp) is appended to `audit.log` in this folder.

## Safety notes

- This binds to `127.0.0.1` only — it is **not** meant to be exposed on a network or shared host. Anyone who can reach it can run real Terraform applies with whatever AWS profile they select.
- It never asks for or stores AWS access keys — it only sets the `AWS_PROFILE` environment variable for the `terraform` subprocess, so credentials stay wherever the AWS CLI already manages them (e.g. the SSO token cache).
- There is no "destroy" button by design — this tool only builds forward. See [`../DESTROY.md`](../DESTROY.md) for how to tear an environment down via the CLI, including the order and gotchas per stack.
- Generated `terraform.tfvars.json` / `tfplan` files and `audit.log` are git-ignored (see `../.gitignore`) since they contain real account ids, bucket names, and CIDRs for whatever you've filled in.
- This app never touches `terraform.tfstate` itself — it only writes `terraform.tfvars.json` and `tfplan`. **Never delete an environment's `terraform.tfstate`/`.tfstate.backup` by hand once you've applied it for real** — it's the only record of what Terraform manages there, and losing it is how a `destroy` becomes impossible. See the remote-state prerequisite above for how to stop it living only on one machine.
- The app does not open a browser tab for you on startup — open the URL yourself, deliberately, each time. (An earlier version auto-opened a tab; that's how a stray click once turned into a real, unintended `apply` during testing of this tool.)
