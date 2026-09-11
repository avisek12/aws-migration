# Cutover Runbook Template

Copy this per application/wave. See [docs/11-execution-runbook.md](../docs/11-execution-runbook.md) for the full lifecycle this supports.

## Header

| Field | Value |
|---|---|
| Application | |
| 6R strategy | |
| Wave | |
| Cutover date/time | |
| Maintenance window | |
| Migration Lead | |
| App Owner | |
| Cutover Coordinator | |
| Rollback owner | |

## Pre-cutover checklist (complete before window opens)

- [ ] Replication healthy and lag within threshold for the required lookback window
- [ ] Test migration validated and signed off
- [ ] Backup of source verified and restorable
- [ ] Rollback plan reviewed with all parties
- [ ] Stakeholders notified of window
- [ ] Go/No-Go decision recorded: ______________

## Cutover steps

| # | Step | Owner | Expected duration | Actual start | Actual end | Status |
|---|---|---|---|---|---|---|
| 1 | Freeze changes on source | | | | | |
| 2 | Confirm final sync complete | | | | | |
| 3 | Launch/promote target | | | | | |
| 4 | Update DNS/LB/connection strings | | | | | |
| 5 | Run smoke tests | | | | | |
| 6 | Confirm monitoring active | | | | | |
| 7 | Resume traffic to target | | | | | |

## Rollback trigger criteria

- [ ] P1: data loss/corruption/security exposure → rollback immediately
- [ ] P2: major functional break → rollback unless verified fix within 30 min
- [ ] P3: minor/cosmetic → proceed, log as post-migration defect

## Rollback steps (if triggered)

| # | Step | Owner |
|---|---|---|
| 1 | Re-point DNS/LB back to source | |
| 2 | Confirm source still serving correctly | |
| 3 | Notify stakeholders of rollback | |
| 4 | Log root cause investigation ticket | |

## Post-cutover bake period

| Field | Value |
|---|---|
| Bake period duration | |
| Monitoring dashboard link | |
| Incidents during bake period | |
| App owner sign-off | |
| Sign-off date | |

## Decommission

- [ ] Source decommission ticket raised
- [ ] Migration Hub status updated to Complete
