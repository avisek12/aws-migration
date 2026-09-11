# RACI & Governance Model

## RACI matrix (R = Responsible, A = Accountable, C = Consulted, I = Informed)

| Activity | Migration Lead | Cloud Architect | App Owner | DBA | Network/Security | Cutover Coordinator | Business Sponsor |
|---|---|---|---|---|---|---|---|
| Discovery & 6R classification | A | R | C | C | C | I | I |
| Landing zone design | C | A/R | I | I | R | I | I |
| Business case / TCO | R | C | C | I | I | I | A |
| Wave planning | A | C | R | C | C | R | I |
| Replication setup (MGN/DMS) | I | C | I | R | C | I | I |
| Test migration validation | I | C | A/R | R | C | I | I |
| Go/No-Go decision | A | C | R | C | C | R | I |
| Cutover execution | I | C | C | R | R | A/R | I |
| Post-cutover sign-off | I | I | A/R | C | I | I | I |
| Decommission source | I | I | A | R | R | R | I |
| Security guardrail compliance | I | R | I | I | A | I | I |
| Cost optimization (post-migration) | R | C | C | I | I | I | A |

## Governance cadence

| Forum | Frequency | Attendees | Purpose |
|---|---|---|---|
| Factory stand-up | Daily | Migration engineers, DBAs, Cutover Coordinator | Replication health, blockers, today's cutovers |
| Wave go/no-go review | Per wave, T-1 day | Migration Lead, App Owner, DBA, Network/Security | Go/No-Go decision |
| Steering committee | Bi-weekly | Migration Lead, Business Sponsor, Cloud Architect | Program-level risk, budget, scope decisions |
| Security/architecture review board | Per landing zone change, per new account | Cloud Architect, Security | Approve guardrail/architecture changes before rollout |
| Wave retrospective | Per wave | Full factory team | Continuous improvement of runbooks/automation |

## Decision rights

- **Scope changes** (adding/removing apps from a wave, changing 6R classification after workshop sign-off): Migration Lead + Business Sponsor approval required.
- **Landing zone/guardrail exceptions** (e.g., an app requesting an SCP exception): Security/architecture review board approval required, logged with expiry date — no permanent exceptions without re-review.
- **Go/No-Go for cutover:** App Owner has veto power — technical readiness alone does not authorize cutover without business sign-off.
- **Rollback trigger:** Any P1 issue during bake period authorizes the Cutover Coordinator to initiate rollback without waiting for a steering committee meeting — document the decision after the fact.

## Change management (organizational, not just technical)

- Communicate wave schedules to affected business units at least 2–4 weeks ahead, with a clear point of contact.
- For Repurchase moves in particular, run a dedicated training/adoption workstream in parallel — technical success does not equal program success if users can't/won't use the new system.
- Maintain a single source of truth for wave status (Migration Hub + a shared dashboard) so stakeholders aren't chasing status via email.

## Compliance & audit trail

- Every 6R decision, go/no-go decision, and guardrail exception must be logged with owner, date, and rationale — required for audit and for the program retrospective.
- Landing zone changes go through the same PR-review + CI/CD process as application code (see [HLD — Landing Zone §6](04-hld-landing-zone.md)) — no manual console changes to guardrails.

Continue to [Risk Management & Cost Optimization](14-risk-cost-optimization.md).
