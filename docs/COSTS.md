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

## Whole-project budget: careful path (agreed 2026-11-25)

- **Target: about €12–15 for the whole project**, including ≈ €3.20 already spent on AI calls in M2b/M3.
- The €10 budget is a **monthly alert**, not a limit: the pay-as-you-go subscription has no spending limit.
- **Choices that keep it there:**
  - M4: free-tier database and registry; everything scales to zero.
  - M5: no custom domain unless it is needed.
  - M6: n8n runs on a schedule, not always on.
  - M7: fine-tuning on free GPUs (Kaggle/Colab).
  - M8: AKS for about one day, then deleted.
  - M9: load test from GitHub.

## Estimate for M4a (shared 2026-11-25, before anything is created)

List prices, Germany West Central, from the Azure Retail Prices API (2026-11-25). Free amounts from the official
free-services and purchase-options pages.

| Resource | List price | Months 1–12 | After 12 months |
|---|---|---|---|
| PostgreSQL Flexible Server B1ms + 32 GB, **one** server for dev and prod | $0.0199/h + $0.137/GB-month ≈ $19/month | €0: 750 h/month B1MS, 32 GB storage, 32 GB backup free for new pay-as-you-go customers | ≈ $19/month |
| Container Registry **Standard** (one) | $0.6666/day ≈ $20/month | €0: one Standard registry free | switch to Basic ($0.1666/day ≈ $5) or GHCR (free once the repository is public) |
| Container Apps, consumption, every app at 0 replicas | vCPU $0.000024/s active, $0.000003/s idle; memory $0.000003/GiB-s | €0: free grant 180,000 vCPU-s, 360,000 GiB-s, 2M requests per month | €0 |
| Storage (blob + queues, LRS hot), KEDA queue polling | $0.0196/GB-month; queue operations $0.004 per 10K | < €0.50 | < €0.50 |
| Log Analytics, one workspace per environment, daily cap 0.08 GB | $2.99/GB after the free amount | €0 if within the free monthly amount (to confirm on the bill) | €0 |
| Azure OpenAI (dev account from M2b) | pay per token | ≈ $0.005 per document read | same |
| **Total** | | **≈ €0.50–2 a month** | **re-plan before the free year ends (≈ November 2027)** |

**Risks checked on the first bill:**
- The free tier must show the database and the registry at €0. If not, the fallback is to stop the server when
  not demoing (≈ €5 a month).
- Container Apps has a new meter, `Environment Management Hour` ($0.10/h, effective 2026-11-01). The billing docs say
  it applies to dedicated workload profiles, private endpoints and planned maintenance, none of which M4 uses.
  This is confirmed on the bill the day after creation.

## M3 measured (2026-11-25)

- **Created (free):**
  - Document Intelligence F0 (500 pages/month free)
  - a user-assigned managed identity with a federated credential
  - a GitHub environment and a private release asset
  - gpt-5.4-mini capacity raised 20 → 100 (a rate limit, not a cost)
- **Azure OpenAI live runs:** 6 recorded runs (4 × 79 dev documents, 2 × 127 test documents, the second from
  GitHub) = **$3.36**, plus a 9-document trial (about $0.05) → **about $3.41 (≈ €3.10)**. Calculated from reported tokens × list price, per run in
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
