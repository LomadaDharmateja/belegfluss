# Cost check, 2026-11-27 (after M4a was created)

Azure Cost Management query API, `ActualCost`, month to date (November 2026), grouped by meter category and meter.
Read-only (`az rest`, `Microsoft.CostManagement/query`, api-version 2023-11-01). The data can lag about a day.

| Cost (EUR) | Meter category | Meter |
|---:|---|---|
| 1.7833 | Foundry Models | 5.4 mini Opt Dz 1M Tokens |
| 1.2869 | Foundry Models | 5.4 mini Inp Dz 1M Tokens |
| 0.0023 | Foundry Models | 5.4 mini cd Inp Dz 1M Tokens |
| 0.0008 | Storage | Class 2 Operations |
| 0.0001 | Storage | All Other Operations |
| 0.0000 | Azure Database for PostgreSQL | B1MS Compute - Free |
| 0.0000 | Azure Database for PostgreSQL | Storage Data Stored - Free |
| 0.0000 | Container Registry | Standard Registry Unit - Free |
| 0.0000 | Log Analytics | Analytics Logs Data Ingestion |
| 0.0000 | Storage | Hot LRS Data Stored - Free (and other free storage meters) |
| 0.0000 | Bandwidth | data transfer (free) |
| 0.0000 | Microsoft Entra | Basic Monthly Active Users |
| 0.0000 | Foundry Tools | Free Transactions (Document Intelligence F0) |
| **3.0734** | | **total, month to date** |

**What it shows:**
- **PostgreSQL B1MS and the Standard registry** run on the 12-month free offer: "Free" meters at €0.
- **Container Apps:** no meter at all, so no environment management fee and usage within the free grant.
- **Azure OpenAI tokens: €3.07.** Calculated from tokens × list price, M2b and M3 came to about $3.41 (≈ €3.10),
  plus about $0.005 in the M4a walkthrough.
- **No base fee** for the Azure OpenAI account or the Document Intelligence F0 account.
