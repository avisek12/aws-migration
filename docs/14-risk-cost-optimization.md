# Risk Management & Cost Optimization

## 1. Risk register (starter set — extend per engagement)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Undiscovered application dependency breaks during cutover | Medium | High | Thorough dependency mapping in Assess phase; parallel-run/bake period before decommission |
| Replication bandwidth insufficient for cutover window | Medium | High | Size Direct Connect/VPN bandwidth from discovery data; test replication throughput before committing wave dates |
| Data loss/corruption during database replatform | Low | Critical | DMS data validation (checksums/row counts); source kept read-only and intact until sign-off |
| Landing zone guardrail gap allows misconfiguration | Medium | High | Security review board sign-off before any account takes production traffic; Config conformance packs |
| Business stakeholder unavailable for go/no-go | Medium | Medium | Schedule go/no-go reviews with confirmed attendance ≥1 week ahead; designate a backup approver |
| SaaS repurchase adoption failure (Repurchase) | Medium | High | Change management workstream, training, parallel-run before legacy freeze |
| Cost overrun vs. business case | Medium | Medium | Track actuals vs. Migration Evaluator estimate per wave; rightsize at migration, not "later" |
| Refactor scope creep | High | High | Lock service boundaries before build; changes go through steering committee, not ad hoc |
| Key personnel dependency (single DBA/engineer bottleneck) | Medium | Medium | Cross-train factory roles; document runbooks so no step is tribal knowledge |
| Rollback plan untested | Low | Critical | Rollback rehearsed in the pilot wave; mandatory checklist item in every cutover runbook |

Maintain this as a living RAID log — see [`templates/raid-log-template.md`](../templates/raid-log-template.md).

## 2. Risk management process

1. Identify risks in each phase gate review (Assess exit, Mobilize exit, per-wave go/no-go).
2. Score likelihood × impact; anything High/High escalates to the steering committee.
3. Assign an owner and mitigation action with a due date — a risk without an owner isn't managed.
4. Review open risks weekly in the factory stand-up; closed/accepted risks logged with rationale.

## 3. Cost optimization — before migration

- **Migration Evaluator TCO** as the baseline business case — track actuals against it per wave to catch drift early.
- **Rightsize at migration**, not after: use discovery utilization data (not on-prem nameplate specs) to size EC2/RDS instances — the single biggest lever to avoid over-provisioning day one.
- **Choose the cheapest 6R that meets the requirement**: don't refactor when replatform would do; every step up in effort should be justified by a business need, not migration-team preference.

## 4. Cost optimization — after migration (FinOps motion)

| Lever | Tool | Typical impact |
|---|---|---|
| Rightsizing idle/over-provisioned instances | AWS Compute Optimizer | 15–30% compute cost reduction |
| Commitment discounts | Savings Plans / Reserved Instances | 20–72% off on-demand, once usage patterns stabilize (wait ~4–8 weeks post-migration before committing) |
| Storage lifecycle policies | S3 Lifecycle (Standard → IA → Glacier) | Significant reduction on infrequently accessed/archived data |
| Idle resource cleanup | Trusted Advisor, tagging audits | Eliminates orphaned EBS volumes, unattached EIPs, idle load balancers |
| Cost allocation & accountability | Cost Allocation Tags + Cost Explorer / Budgets | Enables per-app/per-team chargeback, surfaces cost owners |
| Serverless/managed-service adoption | Refactor workstream | Pay-per-use vs. always-on infrastructure for spiky workloads |

## 5. Cost governance

- **Mandatory tagging policy** (enforced via SCP or Config rule) from account vending onward: `app`, `env`, `cost-center`, `owner` at minimum — retrofitting tags after the fact is expensive and error-prone.
- **Budgets + alerts** per account/workload, not just at the org level — catch runaway costs at the source.
- **Quarterly Well-Architected Cost Optimization pillar review** as part of the Optimize & Operate phase — cost optimization is continuous, not a one-time post-migration task.

---

This completes the end-to-end playbook. Start from [../README.md](../README.md) for the navigation index, or jump straight to the [Execution Runbook](11-execution-runbook.md) if a wave is already underway.
