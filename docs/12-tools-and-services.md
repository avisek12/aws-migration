# AWS Tools & Services Reference

Quick lookup: which service to reach for, at each stage of the migration lifecycle.

## Assess

| Tool | Purpose |
|---|---|
| **AWS Application Discovery Service (ADS)** | Agentless or agent-based discovery of on-prem servers, utilization, and process/network dependencies |
| **AWS Migration Evaluator** | Agentless collector for TCO/business-case building — compares current-state cost to AWS |
| **Migration Hub** | Aggregates discovery + migration status across the whole portfolio in one dashboard |
| **AWS Well-Architected Tool** | Structured review against the 6 pillars — useful for target-state readiness assessment too |

## Mobilize (landing zone)

| Tool | Purpose |
|---|---|
| **AWS Organizations** | Multi-account structure, consolidated billing, SCPs |
| **AWS Control Tower** | Automated landing zone setup, account vending (Account Factory), guardrails |
| **AWS Transit Gateway** | Hub-and-spoke network connectivity across VPCs and on-prem |
| **AWS Direct Connect / Site-to-Site VPN** | Hybrid network connectivity |
| **IAM Identity Center** | Federated SSO across all accounts |
| **AWS Config + Conformance Packs** | Detective guardrails, compliance-as-code |
| **GuardDuty / Security Hub / Detective** | Threat detection, security posture, investigation |
| **CloudTrail (org trail)** | Centralized, immutable audit logging |

## Migrate — Rehost

| Tool | Purpose |
|---|---|
| **AWS Application Migration Service (MGN)** | Agent-based, continuous block-level replication for lift-and-shift |
| **VM Import/Export** | One-time VM image import (less common now that MGN covers most rehost cases) |

## Migrate — Relocate

| Tool | Purpose |
|---|---|
| **VMware Cloud on AWS** | Run VMware environment natively on AWS infrastructure |
| **VMware HCX** | Bulk migration/replication of VMware workloads into VMC on AWS |

## Migrate — Replatform

| Tool | Purpose |
|---|---|
| **AWS Database Migration Service (DMS)** | Homogeneous/heterogeneous database replication with CDC |
| **AWS Schema Conversion Tool (SCT)** | Automated schema/code conversion for engine changes |
| **AWS App2Container (A2C)** | Containerize existing Java/.NET apps without code changes |
| **AWS Elastic Beanstalk** | Managed app-server platform for lift-tinker-shift of web apps |

## Migrate — Repurchase

| Tool | Purpose |
|---|---|
| **AWS AppFlow** | Managed, no-code data integration between AWS/S3 and SaaS platforms |
| **AWS Transfer Family** | Managed SFTP/FTPS/FTP for bulk data transfer |
| **IAM Identity Center** | SSO federation into SaaS platforms |

## Migrate — Refactor

| Tool | Purpose |
|---|---|
| **ECS / EKS / Fargate** | Container orchestration for microservices |
| **Lambda + API Gateway + Step Functions** | Serverless compute, API layer, workflow orchestration |
| **EventBridge / SNS / SQS** | Event-driven decoupling between services |
| **DynamoDB / Aurora Serverless** | Cloud-native data tier options |
| **AWS X-Ray** | Distributed tracing across microservices |

## Large-scale data transfer

| Tool | Purpose |
|---|---|
| **AWS DataSync** | Online transfer of large file/object datasets (NFS/SMB/object storage → S3/EFS/FSx) |
| **AWS Snowball / Snowball Edge / Snowmobile** | Offline, physical bulk data transfer for very large datasets or limited bandwidth |

## Mainframe & VMware-specific

| Tool | Purpose |
|---|---|
| **AWS Mainframe Modernization** | Refactor/replatform COBOL/mainframe workloads to AWS |
| **AWS Transform** | AI-assisted modernization for .NET, mainframe, and VMware workloads |

## Optimize & Operate

| Tool | Purpose |
|---|---|
| **AWS Compute Optimizer** | Rightsizing recommendations based on observed utilization |
| **Cost Explorer + Cost Allocation Tags** | Cost visibility and chargeback/showback |
| **Savings Plans / Reserved Instances** | Commitment-based discounts post-rightsizing |
| **AWS Resilience Hub** | Assess and track resilience posture against defined RTO/RPO |
| **AWS Trusted Advisor** | Ongoing cost, security, performance, fault-tolerance checks |

Continue to [RACI & Governance Model](13-raci-governance.md).
