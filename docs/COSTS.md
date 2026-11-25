# Costs

**Policy (agreed 2026-11-23):**
- Free tiers first.
- Paid services are used where they clearly add value, e.g. Azure OpenAI for extraction, or a larger model where
  accuracy needs it.
- Every paid resource is estimated here (Azure pricing calculator) and the estimate is shared **before** the
  resource is created. The measured cost is added afterwards.

| Milestone | Resource | Estimate (€/month) | Measured (€/month) | Evidence |
|---|---|---|---|---|
| M0 | none (local Docker, public downloads) | 0 | 0 | No cloud resources created |
| M1 | Azure subscription (pay-as-you-go, no monthly fee) + Entra External ID tenant "Belegfluss Dev" (free for the first 50,000 monthly active users) | 0 | 0.00 | Portal, 2026-11-24: subscription current cost €0.00; budget "belegfluss" evaluated spend €0.00 |
| M2a | none (validator, worker, queue run locally in Docker) | 0 | 0 | No Azure resource created |

**Budget alert (since M1):** €10 per month on the subscription, alerts by email at 50 % and 100 % of actual cost and
at 100 % of forecast cost. Checked in the portal on 2026-11-24. Azure for Students was not used: it restricts
regions, and Cost Management lists it as unsupported (reasons in
[docs/setup/entra-external-id.md](setup/entra-external-id.md)).

## M3 measured (2026-11-25)

- **Created (free):**
  - Document Intelligence F0 (500 pages/month free)
  - a user-assigned managed identity with a federated credential
  - a GitHub environment and a private release asset
  - gpt-5.4-mini capacity raised 20 → 100 (a rate limit, not a cost)
- **Azure OpenAI live runs:** 5 recorded runs (4 × 79 dev documents, 1 × 127 test documents) = **$2.67**, plus a
  9-document trial (about $0.05) → **about $2.72 (≈ €2.50)**. Calculated from reported tokens × list price, per run in
  `eval/recordings/`. Plan estimate: €3–6; cap per run $2; nothing exceeded.
- **Per document (held-out test):** $0.0054 at reasoning effort low; effort medium costs $0.0090 on dev.
- **Document Intelligence baseline:** €0 on F0 (would be $10 per 1,000 pages on S0).
- **To check:** the Azure cost view after 1–2 days confirms these estimates and that F0 stays free.

## M2b measured (2026-11-24)

- **Created:** resource group `rg-belegfluss-ai-dev` with one Azure OpenAI account (S0) and one gpt-5.4-mini Data Zone
  Standard deployment (capacity 20), Germany West Central. Pay per token; no base fee expected. **To check:** the
  Azure cost view after 1–2 days (it lags), to confirm that no fixed charge appears.
- **First live run:** 4 synthetic documents, 7,937 input + 2,158 output tokens → **$0.0172 in total, about $0.0043 per
  document** (calculated from reported tokens and the list price;
  [evidence](milestones/evidence/m2b-live-run-2026-11-24.md)). That is about 4× below the worst-case assumption.
- **New estimate for M2b:** ~150 live runs × $0.0043 ≈ **$0.65 (about €0.60)**; the €10 budget alert stays on.

## Estimate for M2b (shared 2026-11-24, before anything is created)

> **Changed 2026-11-24, before creation:** the subscription has **0** Data Zone Standard quota for gpt-5-mini in
> Germany West Central and six other EU regions (`az cognitiveservices usage list`), but 200 for **gpt-5.4-mini
> (2026-03-17)**. With the owner's agreement the deployment uses gpt-5.4-mini: $0.825 input / $4.95 output per 1M
> tokens (Data Zone, Retail Prices API 2026-11-24). Same assumption as below → about **$0.019 per document**. Live
> runs are capped at about 150 in M2b → **about €2.50 worst case**; the first 4 measured calls replace the
> assumption. The original estimate stays below for the record.

- **Resource:** Azure OpenAI with a pay-per-token **Data Zone Standard (EU)** deployment of **gpt-5-mini
  (2025-08-07)** in Germany West Central. Available there per the
  [region table](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure-region-availability)
  (updated 2026-10-19).
- **Price** ([Azure Retail Prices API](https://prices.azure.com/api/retail/prices), 2026-11-24, per 1M tokens):
  gpt-5-mini Data Zone $0.275 input / $2.20 output; for comparison gpt-4.1-mini $0.44 / $1.76 and gpt-5.4-mini
  $0.825 / $4.95.
- **Assumption:** ~5,000 input tokens (page images, text layer, schema) and up to ~3,000 output tokens (including
  reasoning) per document → about $0.008 per document. Development: 300–500 live runs → **about €2–4 in total**.
  CI makes no paid calls. The real token usage of the first calls is measured and replaces this assumption.
- **To verify when creating:** that the pay-per-token deployment has no monthly base fee.

## Notes for M4 (to estimate before deploying)

Prices did not render on the Azure pricing pages during M0, so all of these are **open**:
- Container Apps: consumption plan; monthly free grant of 180,000 vCPU-s, 360,000 GiB-s and 2M requests
  ([pricing](https://azure.microsoft.com/en-us/pricing/details/container-apps/)). The validator needs memory, so
  check whether it fits.
- PostgreSQL Flexible Server Burstable B1ms (smallest; "not recommended for production")
  ([compute](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-compute-storage)).
- Storage (blob + queue), Key Vault, container registry, Log Analytics ingestion, Azure OpenAI tokens.
- Budget alert from the first deployment.
