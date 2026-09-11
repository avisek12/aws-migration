# The 6 R's (7 R's) of Migration

AWS originally defined **6 R's** (2016); a 7th — **Relocate** — was added in 2020 for VMware estates. As a migration expert you'll classify every application in the portfolio into exactly one of these before it enters a wave plan.

## Decision tree

```mermaid
flowchart TD
    Start[Application in scope] --> Q1{Still needed by the business?}
    Q1 -- No --> Retire[RETIRE]
    Q1 -- Yes --> Q2{Compliance/tech blocker or no business case yet?}
    Q2 -- Yes --> Retain[RETAIN]
    Q2 -- No --> Q3{Is there a better SaaS/COTS replacement?}
    Q3 -- Yes --> Repurchase[REPURCHASE]
    Q3 -- No --> Q4{Is it a large VMware/hypervisor estate moving as-is?}
    Q4 -- Yes --> Relocate[RELOCATE]
    Q4 -- No --> Q5{Does it need cloud-native scale, resilience, or new features the current design can't support?}
    Q5 -- Yes --> Refactor[REFACTOR / RE-ARCHITECT]
    Q5 -- No --> Q6{Can it benefit from a managed service swap (DB, app server, container) with modest change?}
    Q6 -- Yes --> Replatform[REPLATFORM]
    Q6 -- No --> Rehost[REHOST]
```

---

## 1. Retire

**Definition:** Decommission applications/servers no longer needed.

- **When:** Discovery reveals duplicate systems, orphaned test/dev servers, apps with zero active users, or functionality consolidated elsewhere.
- **Typical finding rate:** 10–20% of a legacy portfolio in most discovery exercises.
- **Tools:** AWS Application Discovery Service (utilization data to prove low/no usage).
- **Output:** Decommission runbook — see [LLD — Retire & Retain](10-lld-retire-retain.md).
- **Risk:** Low technical risk, but requires business sign-off (fear of "someone still uses it").

## 2. Retain

**Definition:** Keep running where it is — for now.

- **When:** Recent CapEx investment not yet depreciated, regulatory/data-residency blockers, hardware-dependent (e.g., specialized peripherals), or simply not prioritized for this program.
- **Hybrid connectivity:** Direct Connect / Site-to-Site VPN / AWS Outposts if the retained system must integrate with newly migrated workloads.
- **Output:** Revisit date + trigger condition documented (don't let "retain" silently become "never").

## 3. Rehost ("Lift & Shift")

**Definition:** Move the server/VM as-is — same OS, same app, no code change — into EC2.

- **When:** Time-boxed exits (data center lease expiry), large homogeneous estates, low appetite for app-level change during the move, or a "migrate first, modernize later" strategy.
- **Primary tool:** **AWS Application Migration Service (MGN)** — agent-based, continuous block-level replication, test/cutover launches without downtime during replication.
- **Effort:** Low per-server effort; scales well via automation (the "migration factory").
- **Risk:** Lowest technical risk of the 6 R's; but perpetuates any existing technical debt (still same OS patch level, same architecture).
- **Details:** [LLD — Rehost](06-lld-rehost.md).

## 4. Relocate

**Definition:** Move VMware (or Classic-hypervisor) workloads to AWS **without** converting the format — using **VMware Cloud on AWS**.

- **When:** Large VMware-virtualized estates where the team wants to keep vCenter/NSX operational tooling, and avoid P2V/V2V conversion effort entirely.
- **Primary tool:** VMware Cloud on AWS, VMware HCX for bulk migration/replication.
- **Effort:** Very low — no OS-level touch at all, same vCenter tooling post-move.
- **Risk:** Low; but doesn't get you native EC2 pricing/flexibility until you later rehost off VMC.

## 5. Replatform ("Lift-Tinker-Shift")

**Definition:** Move to the cloud with a handful of targeted optimizations that don't change core architecture — most commonly swapping a self-managed database or app server for a managed AWS equivalent.

- **When:** Commodity databases (self-managed MySQL/PostgreSQL/SQL Server → RDS/Aurora), self-managed app servers → Elastic Beanstalk, containerizable monoliths → ECS/EKS without a rewrite.
- **Primary tools:** **AWS DMS** (Database Migration Service) for data replication/CDC, **AWS SCT** (Schema Conversion Tool) for engine changes (e.g., Oracle → PostgreSQL), **AWS App2Container** for containerizing existing Java/.NET apps without code changes.
- **Effort:** Medium — requires schema/compatibility testing, but no full rewrite.
- **Risk:** Medium — engine changes (e.g., Oracle → Aurora PostgreSQL) need thorough compatibility and performance testing.
- **Details:** [LLD — Replatform](07-lld-replatform.md).

## 6. Repurchase ("Drop & Shop")

**Definition:** Replace the existing application with a SaaS or COTS product.

- **When:** Commodity functions where a SaaS is objectively better than maintaining custom/legacy software — CRM → Salesforce, HR → Workday, on-prem Exchange → Microsoft 365, homegrown ticketing → ServiceNow/Jira Cloud.
- **Primary tools:** AWS AppFlow (SaaS ↔ AWS data integration), AWS Transfer Family (data migration), IAM Identity Center (SSO federation to the SaaS).
- **Effort:** Medium — mostly data migration, integration remapping, and change management/training.
- **Risk:** Medium; largest risk is usually organizational (user adoption, process change) rather than technical.
- **Details:** [LLD — Repurchase](08-lld-repurchase.md).

## 7. Refactor / Re-architect

**Definition:** Redesign the application to be cloud-native — typically decomposing a monolith into microservices/serverless.

- **When:** The business needs new capabilities, scale, or agility the current architecture structurally cannot deliver; or the app is central enough to justify the investment.
- **Primary tools:** ECS/EKS/Fargate, Lambda + API Gateway + Step Functions, EventBridge/SQS/SNS for decoupling, Aurora Serverless/DynamoDB for data tier redesign, strangler-fig pattern for incremental cutover.
- **Effort:** High — real software engineering effort, not just infrastructure migration.
- **Risk:** Highest — architectural risk, longest timeline; usually done **after** an initial rehost/replatform has already exited the data center.
- **Details:** [LLD — Refactor](09-lld-refactor.md).

---

## Portfolio classification workshop (deliverable)

Run one structured workshop per application (or per app cluster) with app owner + architect + DBA present. Capture in the [App Assessment Template](../templates/app-assessment-template.md):

| Field | Example |
|---|---|
| App name / ID | `CRM-Legacy-01` |
| Business criticality | Tier 1 (revenue-impacting) |
| Technical complexity | High (tight DB coupling, custom middleware) |
| Dependencies | 3 upstream, 5 downstream systems |
| 6R decision | Replatform (DB → Aurora PostgreSQL, app stays on EC2) |
| Target wave | Wave 3 |
| Estimated effort | 6 weeks |
| Risk rating | Medium |

Aggregate all app decisions into the **wave plan** — see [docs/03-migration-methodology.md](03-migration-methodology.md).
