# Setting up AWS CLI profiles for the Landing Zone UI

The [Landing Zone UI](README.md) never asks for or stores AWS credentials
itself — each page has an "AWS Profile" dropdown, and whatever you pick
there is passed to Terraform via the `AWS_PROFILE` environment variable.
That means every profile you'll want to select must already exist and be
logged in on this machine **before** you click Save & Plan or Apply.

Profiles live in a plain-text config file at:

- Windows: `C:\Users\<you>\.aws\config`
- macOS/Linux: `~/.aws/config`

You need one profile per AWS account this tool talks to:

| Profile (suggested name) | Account |
|---|---|
| `mgmt` | Organizations management account |
| `log-archive` | Log Archive account |
| `audit` | Audit account |
| `network-hub` | Network Hub account |
| `<app>-<environment>` (e.g. `ordermgmt-prod`) | One per workload account |

## Option A — let the AWS CLI write it for you (recommended if your org uses IAM Identity Center / SSO)

Run this once per profile, filling in a different `--profile` name each time:

```
aws configure sso --profile mgmt
```

It walks you through: SSO start URL, SSO region, then lets you pick the
account + permission set/role from a list, then asks what to name the
profile and its default region. It writes the block into `~/.aws/config`
for you — no manual editing needed.

Repeat for every account:
```
aws configure sso --profile log-archive
aws configure sso --profile audit
aws configure sso --profile network-hub
aws configure sso --profile ordermgmt-prod
```

Then log in before using the UI (SSO sessions expire after a few hours,
so you'll repeat this periodically):
```
aws sso login --profile mgmt
```

## Option B — long-lived access keys (if you're not using SSO)

```
aws configure --profile mgmt
```
Prompts for an Access Key ID, Secret Access Key, default region, and
output format. Region/output are written to `~/.aws/config`; the keys go
into `~/.aws/credentials`. This works without Identity Center, but the
keys don't expire on their own — rotate them periodically and never
commit `~/.aws/credentials` anywhere.

## Option C — edit `~/.aws/config` by hand

If you already know the values, create or edit the file directly:

```ini
[profile mgmt]
sso_start_url  = https://your-org.awsapps.com/start
sso_region     = us-east-1
sso_account_id = 111111111111
sso_role_name  = AdministratorAccess
region         = us-east-1
output         = json

[profile log-archive]
sso_start_url  = https://your-org.awsapps.com/start
sso_region     = us-east-1
sso_account_id = 222222222222
sso_role_name  = AdministratorAccess
region         = us-east-1

[profile audit]
sso_start_url  = https://your-org.awsapps.com/start
sso_region     = us-east-1
sso_account_id = 333333333333
sso_role_name  = AdministratorAccess
region         = us-east-1

[profile network-hub]
sso_start_url  = https://your-org.awsapps.com/start
sso_region     = us-east-1
sso_account_id = 444444444444
sso_role_name  = AdministratorAccess
region         = us-east-1
```

Note the section header is `[profile <name>]` (with the literal word
"profile") for every profile — except one actually named `default`,
which is just `[default]` with no `profile` prefix.

## Checking it worked

```
aws sts get-caller-identity --profile mgmt
```
should print that account's id and your assumed role/user ARN. If it
errors, log in again (`aws sso login --profile mgmt`) or re-check the
profile block.

Once a profile exists, it shows up automatically in the Landing Zone
UI's "AWS Profile" dropdown on every page — no need to restart the app.

## Why the tool doesn't need a profile for the assume-role into Audit

The `security-baseline` module (used by the Management page) needs a
second, aliased provider that assumes `OrganizationAccountAccessRole`
into the Audit account — see
[`docs/15-terraform-code-walkthrough.md` §4](../../docs/15-terraform-code-walkthrough.md#4-modulessecurity-baseline).
That assume-role happens automatically inside
`environments/management/providers.tf` using your `mgmt` profile's
credentials, as long as that role trusts the management account — you
do **not** need a separate profile just for it. You still need a direct
`audit` profile for the **Audit Account** page itself, since that page
applies `account-baseline` straight into the Audit account, not through
an assumed role.
