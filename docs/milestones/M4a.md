# M4a — Azure foundation with Terraform, dev environment, release pipeline

> **Status:** done ([PR #13](https://github.com/LomadaDharmateja/belegfluss/pull/13), accepted 2026-11-26). Decisions:
> [ADR-0020](../decisions/0020-terraform-layout-state-and-who-applies.md) (Terraform stacks, who applies what),
> [ADR-0021](../decisions/0021-keyless-runtime-shared-free-tier-database.md) (keyless runtime, shared free-tier
> database, region), [ADR-0022](../decisions/0022-release-pipeline-build-once-deploy-dev.md) (release pipeline).
> Owner steps: [setup/azure-deploy.md](../setup/azure-deploy.md). Costs: [COSTS.md](../COSTS.md).

## Like I'm 10

Until now Belegfluss lived only on my laptop. Now there is a copy on Microsoft's computers in Ireland that anyone with
the link can open.
- **Written down, not clicked:** I didn't click it together. I wrote a description of everything it needs
  (Terraform), and a robot builds it from that description.
- **Every change goes through the robot:** when I change the code, it tests everything, builds new boxes
  (container images), checks them for known security holes, and puts them online. Then it clicks through the most
  important pages to see that they answer.
- **No keys anywhere:** the robot and the app prove who they are with an identity card Microsoft gives them. So
  there is nothing to steal.
- **It sleeps when nobody uses it:** it costs almost nothing. The first visitor wakes it up, which takes a little
  while.

## Technical

### What runs in Azure now

| Part | Resource | Notes |
|---|---|---|
| Web, API | Container Apps `web`, `api` (external HTTPS) | scale 0–2 |
| Validator | Container App `validator`, internal ingress only | scale 0–1; JVM startup probe (up to 2 min) |
| Worker | Container App `worker`, no ingress | KEDA `azure-queue` rule with the app identity; scale 0–2 |
| Migrations | Container Apps job `migrate` | started by the pipeline before new images go live |
| Sweep | Container Apps job `sweep`, every 15 min | the worker's own sweep doesn't run while it is at zero |
| Database | PostgreSQL 18 B1ms, **one server** with `belegfluss_dev` (prod gets its own database in M4b) | free in year one; Entra authentication only, no password exists |
| Files, jobs | Storage account, blob `documents`, queues `documents`, `documents-poison` | shared-key access off |
| Images | Container registry (Standard) | free in year one; admin user off, pulls with the app identity |
| Logs | Log Analytics, daily cap 0.08 GB | the first 5 GB a month are free |
| Identities | `id-belegfluss-app-dev` (what the containers run as); `id-belegfluss-deploy-dev` (what GitHub Actions signs in as, OIDC) | no secret anywhere |

- **Region:** North Europe for apps and data ([ADR-0021](../decisions/0021-keyless-runtime-shared-free-tier-database.md)).
  Germany West Central refused PostgreSQL for this subscription, West Europe refused new customers, and Sweden
  Central had no capacity. AI, identities and state stay in Germany West Central.
- **Terraform:** `infra/bootstrap` and `infra/shared` (applied by the owner), `infra/environment` (applied by the
  pipeline).

### What replaced each secret

| Before (local) | In Azure (M4a) | Where |
|---|---|---|
| Azurite account key in a connection string | Managed Identity + account URL, shared keys switched off | `storage_clients.py`, `infra/environment/main.tf` |
| Database password in the URL | Entra token of the Managed Identity as password, fresh per connection | `db.py`, tested in `tests/test_db.py` against real PostgreSQL |
| `az login` for Azure OpenAI | the same identity (`AZURE_CLIENT_ID`, `AZURE_TOKEN_CREDENTIALS=ManagedIdentityCredential`) | `identity.py` |
| Registry password | AcrPull role for the app identity | `infra/shared/main.tf` |
| Queue connection string for the scaler | `identity` on the KEDA rule | `infra/environment/apps.tf` |
| Cloud credentials in GitHub | OIDC federation to `id-belegfluss-deploy-dev`, GitHub's immutable subject | `infra/bootstrap/main.tf` |

### How a release works ([ADR-0022](../decisions/0022-release-pipeline-build-once-deploy-dev.md))

`.github/workflows/deploy.yml`, on every push to `main`:
1. **Tests:** API, web, eval gate, Compose smoke, secret scan, infra checks.
2. **Build once:** the API/worker, web and validator images.
3. **Scan:** Trivy fails on fixable HIGH/CRITICAL; a CycloneDX SBOM per image is kept.
4. **Push** to the registry by digest.
5. **Apply:** `terraform plan` and `apply` for dev.
6. **Migrate:** the `migrate` job with the new image.
7. **Deploy:** every app and job switched to the new digests.
8. **Smoke test** (`scripts/deploy/smoke.sh`).

Prod (M4b) repeats steps 5–8 with the same digests after a manual approval.

**Least privilege for the pipeline** (ADR-0020):
- Contributor on its own resource group only.
- Reader on the shared group.
- AcrPush.
- Managed Identity Operator on its app identity.
- Its own state container.
- Role grants limited by an ABAC condition to three data roles and its own app identity.

It can't touch prod, the database server or its own trust.

### Results (evidence)

| Check | Result | Evidence |
|---|---|---|
| Release pipeline end to end | green: tests → build → scan → push → apply → migrate → deploy → smoke | [run 45769630636](https://github.com/LomadaDharmateja/belegfluss/actions/runs/45769630636) (first green) |
| No drift after a deploy (acceptance) | `terraform plan` in the pipeline: "No changes. Your infrastructure matches the configuration." | [run 45771194607](https://github.com/LomadaDharmateja/belegfluss/actions/runs/45771194607) |
| No secret | "Azure CLI login succeeds by using OIDC" in build and deploy; the workflow and Terraform contain no secret | same runs, `deploy.yml` |
| Tests in the pipeline | API 253 passed (1 live test skipped), web 47 unit + 5 end-to-end, eval 24 + gate, secret scan "no leaks found", infra fmt/validate/tflint/Trivy | [run 45773112690](https://github.com/LomadaDharmateja/belegfluss/actions/runs/45773112690) |
| Image scan | first run **blocked**: `libzstd1` (Debian fix available) and 5 HIGH in libraries bundled in the base image's pip. After the fix: no fixable HIGH/CRITICAL in the 3 images | [run 45766958861](https://github.com/LomadaDharmateja/belegfluss/actions/runs/45766958861) (blocked), later runs green |
| Walkthrough in dev (owner signed in) | official XRechnung test file (`01.01a-INVOICE_uncefact.xml`): read and checked by the official validator, €336.90, "Checked". Synthetic PDF: read by Azure OpenAI through the app identity, "Please check" with the AI note | [inbox](evidence/m4a-01-dev-inbox.jpg), [AI review](evidence/m4a-02-dev-ai-review.jpg) |
| Scale from zero on a queue message | 2 worker replicas about 20–40 s after the upload; validator started by the worker | `az containerapp replica list`, 2026-11-26 |
| Cold starts (first request after both apps were at zero replicas) | API `/health` **30.2 s and 28.4 s** (49 s before the readiness check went from every 10 s to every 3 s); web **25.3 s and 20.1 s**; warm 0.20 s (API) and 0.26 s (web). A first visit therefore takes about half a minute to a minute; the first document after idle about a minute until checked (worker and validator start too) | two `curl` rounds, 07:24 and 07:31 UTC on 2026-11-26; walkthrough |
| Image pulls | 4–6 s; images 73 MB (web), 130 MB (validator), 140 MB (API/worker) | Log Analytics `ContainerAppSystemLogs_CL`, 2026-11-26 |
| Read back after apply | storage shared keys off, TLS 1.2, no public blobs; PostgreSQL password auth off, Entra on, `require_secure_transport` on, firewall "Azure services" only; encryption at rest with Microsoft-managed keys; registry admin off; validator `external: false`; worker no ingress; KEDA rule with identity and no secret | `az` read-backs, 2026-11-26 ([PROJECT_LOG](../PROJECT_LOG.md)) |
| Pipeline identity rights | Reader (shared), Contributor (dev), Blob Data Contributor (own state container), AcrPush, Managed Identity Operator (own app identity), RBAC Administrator with the ABAC condition | `az role assignment list`, 2026-11-26 |

### Changes from the plan

- **Region:** North Europe instead of Germany West Central (see above, ADR-0021). Three EU regions failed for
  different reasons; Azure's pre-flight validation passed everywhere, so only real creation tells.
- **Log Analytics per environment, not one shared workspace:** the Container Apps environment needs the workspace
  key, and a workspace in the environment's own group avoids giving the pipeline rights on shared resources.
- **Databases are created by the owner's role script, not by Terraform:** their ownership and grants are SQL-level
  (`scripts/azure/db-roles.ps1`).
- **No Key Vault and no Application Insights in M4:** nothing secret exists to store yet. Both move to M5 with
  telemetry (ADR-0021).
- **A transient failure is retried after 30 s:** the worker's visibility timeout had to grow to 900 s, and a
  validator still starting must not delay a document by 15 minutes.
- **Hardened runtime images:** OS updates at build time; no pip, npm, corepack or yarn in the images.
- **Temporary:** while M4a was in review, the pipeline also ran on the M4a branch, so the deployment could be proven
  before the merge. That exception was removed before merging.

### What broke and what I learned

1. **"Offered" isn't "available" for a new tenant.**
   - Germany West Central: "Provisioning is restricted in this region".
   - West Europe: "not accepting new customers".
   - Sweden Central: "RegionalAllocationFailed", twice.
   - Learned: try for real, because a failed creation is free; and put the region into names, because Azure keeps a
     failed resource's name reserved in its region.
2. **PostgreSQL role names have at most 63 characters.** Azure shortened the Entra admin's name, and Terraform
   kept replacing it until it did the same.
3. **The image scanner blocked the first release.** The findings were in tools the app never runs: pip's bundled
   libraries. Removing them was the fix, not ignoring them.
4. **Drift after a deploy:**
   - Azure adds a workload profile.
   - The provider reads an identity-based queue rule back without its identity.
   - Running `terraform plan -detailed-exitcode` right after every apply found both.
5. **tflint** found that the Terraform state had no `prevent_destroy` guard.
6. **The CLI reference beats memory:** the migrate script's first version used the wrong argument names. The
   migration itself had worked.

### What M4a can and cannot do

- **Can:**
  - a real, reproducible Azure deployment in Terraform, with no secret anywhere
  - least-privilege pipeline identities
  - build once, scan, SBOM, deploy by digest
  - no drift after a deploy
  - an idle environment costing almost nothing
- **Cannot (yet):**
  - **prod:** M4b
  - **instant first load:** cold starts (above)
  - **private networking:** M9; storage and database are reachable over the internet, but only with Entra
    identities
  - **per-app network isolation of the validator:** M8
  - **telemetry and alerts:** M5
  - **free hosting after month 12** without changes (COSTS.md)

## For interviews

**Say it in 6 sentences:**
1. "Belegfluss runs on Azure Container Apps, and every resource is in Terraform, in three stacks with separate state
   and separate permissions."
2. "There isn't a single secret: the containers use a managed identity for the database, storage, the queue scaler,
   the registry and Azure OpenAI, and GitHub Actions signs in with OIDC."
3. "The pipeline builds each image once, scans it with Trivy, generates an SBOM, deploys by digest, runs
   migrations as a job and smoke-tests the result."
4. "The pipeline's identity can only grant three data roles to its own app identity, enforced by an Azure ABAC
   condition, so a compromised pipeline can't escalate."
5. "Everything scales to zero and runs on free tiers in year one, so an idle environment costs cents; the price is a
   cold start, which I measured."
6. "Azure refused the database in two regions and had no capacity in a third. I treated that as engineering data:
   tested regions for real, documented it in an ADR, and put the region into resource names."

**Likely questions and good answers:**

- **Why Container Apps and not AKS?** Scale to zero, managed ingress and KEDA without running a cluster: right for
  one developer and a demo budget. AKS follows in M8 to learn the trade-offs (ADR-0007).
- **How does the database work without a password?**
  - The app requests an Entra token for the PostgreSQL resource with its managed identity and uses it as the
    password when a connection opens.
  - The database knows that identity as a role, created once by the admin.
  - I tested the hook against a real PostgreSQL with a password-free URL.
- **Why doesn't the pipeline apply everything?** A change to the shared database server or the budget affects
  both environments, so the owner applies those; the pipeline only changes its own environment.
- **How do you avoid drift if the pipeline changes images outside Terraform?** Terraform ignores the image
  attribute after creation; the pipeline's plan after each deploy shows "No changes".
- **What would you change for real customers?**
  - private networking for database and storage
  - a separate database server for prod
  - minimum replicas for the API
  - Application Insights with alerts
  - a custom domain

## Claims audit (end of M4a)

Scope: README, ARCHITECTURE (§7, §8.2, §9, §10.9), ADRs 0020–0022 (and the ADR-0007 note), COSTS, PLAN (M4, M5),
setup guide, this document.

| # | Claim | Where | Status | Evidence / action |
|---|---|---|---|---|
| 1 | Dev runs on Azure Container Apps in North Europe | README, M4a, ARCHITECTURE | ✅ confirmed | `az containerapp list`; walkthrough screenshots |
| 2 | Every Azure resource of M4a is in Terraform | M4a, ADR-0020 | ⚠️ caveat | Entra External ID objects (separate tenant) and the databases/roles inside PostgreSQL are scripted, not Terraform |
| 3 | No secret anywhere | README, M4a, ARCHITECTURE §7 | ✅ confirmed | read-backs (keys off, password auth off, admin off, KEDA rule without auth); OIDC log lines; gitleaks |
| 4 | `terraform plan` shows no drift after a deploy | M4a | ✅ confirmed | run 45771194607 ("No changes"); local plan the same |
| 5 | The pipeline can only grant three data roles to its own app identity | ADR-0020, M4a | ✅ confirmed | role assignment with the ABAC condition read back |
| 6 | Images are scanned and blocked on fixable HIGH/CRITICAL | ADR-0022, M4a | ✅ confirmed | run 45766958861 blocked; later runs pass |
| 7 | The validator isn't reachable from the internet | ARCHITECTURE §7, M4a | ✅ confirmed | `ingress.external = false`, checked by the smoke test on every deploy |
| 8 | Data at rest is encrypted, TLS required | ARCHITECTURE §7 | ✅ confirmed | storage `keySource = Microsoft.Storage`, PostgreSQL `SystemManaged`, `require_secure_transport = on` |
| 9 | Year-one cost about €0.50–2 a month | COSTS, README | ⚠️ caveat | estimate from list prices and free offers; **the first bills must confirm** that the database and registry are free and no management fee appears |
| 10 | Cold starts: API about 30 s, web 20–25 s, warm 0.2–0.3 s | M4a | ⚠️ caveat | two rounds on one day; Azure placement time varies |
| 11 | Worker scales from zero on a queue message | M4a | ✅ confirmed | replica counts during the walkthrough |
| 12 | Germany West Central / West Europe / Sweden Central failures | ADR-0021, M4a | ✅ confirmed | Terraform and capabilities API outputs, 2026-11-26 (PROJECT_LOG) |
| 13 | Links in the changed docs resolve | all | ✅ confirmed | 2026-11-26: 133/133 relative links, 25/25 public web links, 8/8 private repo links (via `gh api`) |

## Next

- Review outcome (2026-11-26): ADR-0020–0022 accepted, PR #13 merged. The temporary branch trigger and the branch
  exception in the GitHub environment `dev` were removed before the merge; the first release from `main` follows.
- **Cost check:** in 1–2 days, the Azure cost view (free database and registry, no management fee).
- **M4b:**
  - prod (own database on the shared server, own Azure OpenAI, own External ID tenant)
  - manual approval
  - budget alert test
  - repository goes public
