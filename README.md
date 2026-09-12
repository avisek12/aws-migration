# AWS Migration Playbook

End-to-end reference for running an AWS cloud migration engagement as a **Migration Expert / Cloud Migration Architect** — covering the 6 R's (7 R's), execution methodology, governance, and both High-Level (HLD) and Low-Level (LLD) designs for every migration strategy.

## How to use this repo

Read in this order if you're building a migration practice from scratch:

1. [Executive Summary](docs/01-executive-summary.md) — the elevator pitch, scope, and success metrics for a migration program.
2. [6 R's (7 R's) Migration Strategies](docs/02-6r-migration-strategies.md) — decision framework for classifying every application.
3. [End-to-End Migration Methodology](docs/03-migration-methodology.md) — Assess → Mobilize → Migrate & Modernize, mapped to AWS CAF.
4. [HLD — Landing Zone & Account Architecture](docs/04-hld-landing-zone.md) — the foundation every workload migrates into.
5. [HLD — Migration Factory](docs/05-hld-migration-factory.md) — the operating model that runs waves at scale.
6. LLDs per strategy:
   - [LLD — Rehost (Lift & Shift)](docs/06-lld-rehost.md)
   - [LLD — Replatform (Lift-Tinker-Shift)](docs/07-lld-replatform.md)
   - [LLD — Repurchase (Drop & Shop / SaaS)](docs/08-lld-repurchase.md)
   - [LLD — Refactor / Re-architect](docs/09-lld-refactor.md)
   - [LLD — Retire & Retain](docs/10-lld-retire-retain.md)
7. [Execution Runbook & Wave Checklists](docs/11-execution-runbook.md) — the day-to-day operating checklists.
8. [Tools & Services Reference](docs/12-tools-and-services.md) — which AWS service to reach for, per job.
9. [RACI & Governance Model](docs/13-raci-governance.md) — who owns what, and how decisions get made.
10. [Risk Management & Cost Optimization](docs/14-risk-cost-optimization.md) — the risk register and FinOps motion post-migration.
11. [Terraform Code Walkthrough](docs/15-terraform-code-walkthrough.md) — resource-by-resource explanation of every file in [`terraform/`](terraform/), for when you need to explain, modify, or debug the landing zone code itself.

Reusable templates (copy per wave/app) live in [`templates/`](templates/); architecture diagrams live in [`diagrams/`](diagrams/); a single-page navigable version of this whole playbook with an interactive execution checklist lives in [`atlas/`](atlas/) ([live version](https://claude.ai/code/artifact/5bbc80cf-53e3-41e1-84a6-02547984e138)).

## Quick reference: the 6 R's (+1)

| Strategy | One-liner | Typical effort | Typical use case |
|---|---|---|---|
| **Retire** | Turn it off | Lowest | Unused/redundant apps found in discovery |
| **Retain** | Leave it, revisit later | None (now) | Compliance-locked, recently invested, or no clear business case yet |
| **Rehost** | Lift & shift, no code change | Low | Time-boxed exits (DC lease end), large homogeneous VM estates |
| **Relocate** | Move VMware/hypervisor as-is | Low | Large VMware estates → VMware Cloud on AWS |
| **Replatform** | Lift-tinker-shift (swap DB/OS, containerize) | Medium | Commodity databases, app servers wanting managed services |
| **Repurchase** | Move to SaaS / COTS | Medium | CRM, HR, ERP where a SaaS replaces custom/legacy software |
| **Refactor / Re-architect** | Redesign for cloud-native | High | Apps needing new features, scale, or performance the current architecture can't deliver |

See [docs/02-6r-migration-strategies.md](docs/02-6r-migration-strategies.md) for the full decision tree, tooling, and worked examples for each.
