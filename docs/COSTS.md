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

## Notes for M4 (to estimate before deploying)

Prices did not render on the Azure pricing pages during M0, so all of these are **open**:
- Container Apps: consumption plan; monthly free grant of 180,000 vCPU-s, 360,000 GiB-s and 2M requests
  ([pricing](https://azure.microsoft.com/en-us/pricing/details/container-apps/)). The validator needs memory, so
  check whether it fits.
- PostgreSQL Flexible Server Burstable B1ms (smallest; "not recommended for production")
  ([compute](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-compute-storage)).
- Storage (blob + queue), Key Vault, container registry, Log Analytics ingestion, Azure OpenAI tokens.
- Budget alert from the first deployment.
