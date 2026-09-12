# Learning Resources — AWS Migration

A prioritized reading/training list for building real depth in AWS cloud migration, not just this repo's playbook. Nothing here is affiliated with or endorsed by AWS — these are well-known, widely-used resources, presented in the order I'd actually work through them for this role.

## 1. Read the source material first (free)

This whole playbook is built on two AWS frameworks — read the originals, not just the summary in [docs/02](02-6r-migration-strategies.md) and [docs/03](03-migration-methodology.md):

- **"6 Strategies for Migrating Applications to the Cloud"** (AWS whitepaper) — the origin of the 6/7 R's framework.
- **AWS Cloud Adoption Framework (CAF)** (AWS whitepaper) — underlies the Assess → Mobilize → Migrate & Modernize methodology.

Search "AWS whitepapers" on AWS's own site — they're free PDFs, no account needed.

## 2. Free official hands-on training

**AWS Skill Builder** (skillbuilder.aws) — AWS's own free digital training platform:
- The "AWS Cloud Migration" learning plan
- Digital courses specifically on AWS Application Migration Service (MGN) and AWS Database Migration Service (DMS)

**AWS Workshop Studio** — guided, hands-on labs (real console, real steps) for MGN and DMS that mirror exactly what's in [docs/06](06-lld-rehost.md) and [docs/07](07-lld-replatform.md), and match the illustrative walkthroughs in the [Migration Atlas](../atlas/README.md)'s console-walkthrough section.

## 3. Certification

AWS doesn't have a certification named specifically "Migration." The closest official validation:

- **AWS Certified Solutions Architect – Professional** — the exam that actually goes deep on migration and hybrid-architecture scenarios. More relevant to this role than the Associate level, which is more foundational.
- Third-party prep if you want structured video (not AWS-official, but widely regarded): Stephane Maarek's SA Pro course (Udemy), A Cloud Guru/Pluralsight equivalents.

## 4. The highest-value thing: run this for real

You already have a full working landing zone (`terraform/`) and two UIs (`terraform/ui/`, `terraform/scaffolder/`) to drive it. Standing this up in a real sandbox AWS account — even just Log Archive + Management + one workload account with MGN — will surface the exact real-world snags a course glosses over. This session already hit one: a genuine Terraform dependency race condition in `log-archive-account` (see [docs/15 §8](15-terraform-code-walkthrough.md#environmentslog-archive-account)), found and fixed by actually applying it, not by reading about it.

**Suggested first hands-on exercise, using what's already in this repo:**
1. Bootstrap remote state for one throwaway sandbox account ([`terraform/bootstrap-backend/`](../terraform/bootstrap-backend/)).
2. Apply `log-archive-account`, then `management`, in that account (via [`terraform/ui/`](../terraform/ui/) or the CLI directly).
3. Install the MGN agent on a real (or even a small test) EC2 instance and walk through a full Rehost cycle: replicate → test-launch → cutover.
4. Destroy everything afterward per [`terraform/DESTROY.md`](../terraform/DESTROY.md) — practicing teardown is as valuable as practicing build.
