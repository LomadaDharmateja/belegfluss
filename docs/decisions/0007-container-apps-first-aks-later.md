# ADR-0007: Azure Container Apps first (M4), AKS later (M8, time-boxed)

- **Status:** Accepted (2026-11-23). One point superseded by [ADR-0021](0021-keyless-runtime-shared-free-tier-database.md)
  (2026-11-26): prod also scales to zero, for the budget; cold starts are measured.
- **Date:** 2026-11-23
- **Milestone:** M0 (applies to M4 and M8)

## Context

We want to go live early with real users at very low cost, and we also want hands-on Kubernetes experience (AKS,
Helm, rollouts, autoscaling). The workload is small: a web app, an API, a queue worker, and an internal validator.

Facts checked: Container Apps scale to zero with no usage charges at zero replicas, support KEDA scale rules
(incl. `azure-queue`), and include a monthly free grant of 180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million
requests per subscription ([scaling](https://learn.microsoft.com/en-us/azure/container-apps/scale-app),
[pricing](https://azure.microsoft.com/en-us/pricing/details/container-apps/)).

## Options

1. **Container Apps in M4, AKS in M8:** cheapest and fastest path to production. AKS is learned on a system that
   already runs, which also gives a real migration story. Cost: two runtimes to learn.
2. **AKS from M4:** Kubernetes from day one, but always-on node costs, more operations work before any user, and a
   later first production date.
3. **App Service:** simple, but a poor fit for the queue worker and the internal validator, and no Kubernetes story.

## Decision

**Option 1.**
- **M4:** one Container Apps environment per environment (dev, prod) in **Germany West Central** (region availability
  confirmed in M4), provisioned with Terraform. dev scales to zero, prod keeps min 1 replica for the API (measure cold
  starts first).
- **M8:** the same images on AKS with Helm. Data services stay managed (PostgreSQL, Storage, Key Vault). We set a
  **cost cap and a time box** before starting. Afterwards we decide (new ADR) whether prod stays on AKS or goes back to
  Container Apps, based on measured cost and operations effort.
- Container images, configuration through environment variables, health endpoints and graceful shutdown are built
  "12-factor" from M1, so the move is a deployment change, not a code change.

## Consequences

- Production can start in M4 at a few euros per month (estimate in COSTS.md before deploying).
- Kubernetes work (Helm charts, NetworkPolicy, Workload Identity, KEDA ScaledObjects) is concentrated in M8.
- Running AKS continuously would raise monthly costs noticeably. That is why the keep-or-tear-down decision is
  explicit.

## Sources

Linked inline above (read 2026-11-23).
