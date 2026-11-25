# ADR-0021: Keyless runtime, scale to zero, one shared free-tier database for dev and prod

- **Status:** Proposed (2026-11-26)
- **Date:** 2026-11-26
- **Milestone:** M4a
- **Supersedes:** [ADR-0007](0007-container-apps-first-aks-later.md) in one point: prod does not keep the API at one
  replica.

## Context

**The owner's limits:**
- The budget is **€10 a month**, careful path, about €12–15 for the whole project.
- The app is mostly opened by the owner to show in interviews, so real users will be rare.

**What would make it expensive:**
- One PostgreSQL server per environment costs about $19 a month each.
- The registry costs $5–20 a month.
- An always-on API costs about $16 a month.

**Free offers that apply:**
- New pay-as-you-go customers get one PostgreSQL B1MS server (750 hours a month, 32 GB) and one Standard registry
  free for 12 months.
- Container Apps has a monthly free grant, and an app scaled to zero is not charged.

## Options

1. **Separate database servers per environment.** Cleanest isolation; about €17 a month for the second one.
2. **One server, stopped when not in use.** Cheap, but the live link breaks whenever the database is stopped.
3. **One shared free-tier server, one database and one identity per environment.**

## Decision

**Option 3, with keyless access everywhere.**

- **PostgreSQL:**
  - Entra ID authentication only (password authentication off).
  - Each connection uses a fresh token of the app's managed identity as its password (`db.py`, tested against a
    real PostgreSQL).
  - The owner is the only Entra admin. `scripts/azure/db-roles.ps1` creates `belegfluss_<env>` and the role
    `id-belegfluss-app-<env>`, and revokes `CONNECT` from `PUBLIC`.
  - The app identity owns the tables its migrations create.
- **Storage:** shared-key access off; the app uses its managed identity (`storage_clients.py`). KEDA reads the
  queue length with the same identity.
- **Registry:** admin user off; apps pull with their identity (AcrPull).
- **Azure OpenAI:** keys off (ADR-0016). dev uses the M2b account; prod gets its own in M4b.
- **Scaling:** every app at `min_replicas = 0`, prod included (this is the point that supersedes ADR-0007).
- **Sweep job:** runs every 15 minutes, because the worker's own sweep doesn't run while it is at zero.
- **Migrations:** a separate step; the `migrate` service in Compose, a manual job in Azure.
- **No Key Vault and no Application Insights in M4.**
  - No secret exists to put into a vault.
  - The first secret-like value is the Application Insights connection string, which comes with telemetry in M5.
- **Database network:** public access limited to "Azure services", with Entra tokens and TLS. Private networking is
  M9 hardening.

**Found while building it (worker, with regression tests):**
- The worker took 4 messages at once with 300 s visibility, but one document can take up to 390 s (3 AI attempts
  of 120 s plus validator), so a second replica could process a document twice.
- **Now:** one message at a time, 900 s visibility, and a temporary failure is retried after 30 s rather than
  after the full timeout. A validator that is still starting doesn't delay a document by 15 minutes.

## Consequences

- **Cost:** about €0.50–2 a month in year one (docs/COSTS.md). After 12 months the database and registry cost
  money: a dated reminder in COSTS.md and PLAN.md.
- **First request after idle waits for a cold start.** Measured in M4a.md; the README says so.
- **The shared server is one failure domain for dev and prod.** Acceptable before real users; revisit at M5.
- **The validator's internal ingress is reachable inside the environment,** not only by the worker. Per-app network
  rules come with Kubernetes in M8 (ADR-0007).

## Sources

- Free services (12 months for new pay-as-you-go customers: PostgreSQL B1MS 750 h + 32 GB, Container Registry
  Standard): https://azure.microsoft.com/en-us/pricing/free-services,
  https://azure.microsoft.com/en-us/pricing/purchase-options/azure-account
- Container Apps billing (free grant, no charge at zero replicas):
  https://learn.microsoft.com/en-us/azure/container-apps/billing
- Entra authentication for PostgreSQL flexible server:
  https://learn.microsoft.com/en-us/azure/postgresql/security/security-entra-configure
- Scale rules with managed identity: https://learn.microsoft.com/en-us/azure/container-apps/scale-app
- Prices: Azure Retail Prices API, Germany West Central, 2026-11-25 (docs/COSTS.md)
