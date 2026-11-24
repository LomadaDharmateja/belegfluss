# Belegfluss — Plan

> Living roadmap. Updated at the end of every session. Changes to the plan are explained in an ADR and logged in
> [docs/PROJECT_LOG.md](docs/PROJECT_LOG.md). Last update: **2026-11-24 (M2a done, M2b planning)**.

## Status

| # | Milestone | Key output | Status |
|---|---|---|---|
| M0 | Research & design | Verified research, interview guide, architecture, ADRs 0001–0009, this plan | ✅ done (PR #1, approved 2026-11-23) |
| M1 | Local foundation | Monorepo, FastAPI + Postgres + Next.js (DE/EN), auth, upload, Docker Compose, CI | ✅ done (PR #2, approved 2026-11-24, [M1.md](docs/milestones/M1.md)); interviews deferred, see §4 |
| M2a | Reading & validating (deterministic) | XML/ZUGFeRD reading, official validator, worker, business checks, document page | ✅ done (PR #7, approved 2026-11-24, [M2a.md](docs/milestones/M2a.md)) |
| M2b | LLM extraction, review, export | Azure OpenAI (EU Data Zone) for plain PDFs/photos, review step, ZIP + CSV export | 🟡 planning (first paid service, estimate in [COSTS.md](docs/COSTS.md)) |
| M3 | Evaluation & quality gates | Labelled set, field-level accuracy report, CI gate | ⏳ |
| M4 | Azure with Terraform | Container Apps, Postgres, Blob/Queue, Key Vault, Managed Identity, Entra, Azure OpenAI, CI/CD, budget alert | ⏳ |
| M5 | First real users | Pilot onboarding, legal pages, App Insights, alerts, incident log, usage metrics | ⏳ |
| M6 | Automation | Email ingestion, scheduled accountant export, notifications (n8n, see licence note) | ⏳ |
| M7 | Fine-tuning & serving | LoRA fine-tune of a small open model, vLLM serving, comparison vs Azure OpenAI | ⏳ |
| M8 | Kubernetes | AKS + Helm, KEDA, rollout strategy, autoscaling, keep-or-tear-down decision | ⏳ |
| M9 | Hardening | Security review, GDPR features complete, EU AI Act assessment, load test, restore test | ⏳ |
| M10 | Launch & write-up | Final docs, demo video, final claims audit, public write-up | ⏳ |

**Order confirmed (2026-11-23):** Azure deployment (M4) comes only after the full workflow is built and evaluated
(M1–M3). See [§4](#4-proposed-changes-to-the-roadmap) for the review outcome of proposals P1–P3.

## 1. Definition of done (every milestone)

A milestone is done when **all** of these hold:
1. **Tests:** all tests pass locally and in CI (command + output shown in the PR). New features have tests, and bugs
   have a regression test first.
2. **Docs:**
   - `docs/milestones/M<n>.md` written (Like I'm 10 / Technical / For interviews)
   - ADRs for significant decisions
   - `ARCHITECTURE.md`, `README.md` and this plan updated
   - `docs/PROJECT_LOG.md` entry added
3. **Claims audit:** every claim in README/docs marked confirmed / caveat / unverified. Unverified claims are fixed
   or removed.
4. **Clean-up pass:** dead code deleted, names and structure simplified.
5. **Security & privacy:** no secrets in git (secret scan green), no invoice content in logs, new data flows listed
   in ARCHITECTURE §7.
6. **Cost:** free tiers first. Paid services are used where they clearly add value (e.g. Azure OpenAI for
   extraction, or a larger model where accuracy needs it). Every paid resource is estimated in
   [docs/COSTS.md](docs/COSTS.md) and the estimate is shared **before** the resource is created.
7. **Git:** milestone branch `m<n>-<topic>`, small Conventional Commits, one PR with a summary, merged after review.

## 2. Milestones in detail

### M0 — Research & design (no application code)
- **Tasks:** verify rules/formats/validator/test data/export with official sources; validator smoke test; interview
  guide; architecture; ADRs; this plan; doc skeleton; private GitHub repo + PR.
- **Acceptance:** every fact in `docs/research/einvoicing.md` has a source link and status; the validator smoke test
  is reproducible from the evidence log; diagrams render; PR open.

### M1 — Local foundation
- **Tasks:**
  1. Repo layout per [ADR-0002](docs/decisions/0002-plain-monorepo-layout.md); `uv` (Python 3.12+) and `pnpm`
     workspaces; pre-commit (ruff, mypy, eslint, prettier, gitleaks).
  2. **API:** FastAPI app with `/health`, `/me`, organisations + memberships, `POST /documents` (multipart upload,
     size/type limits, SHA-256, original to Blob), `GET /documents`. PostgreSQL + SQLAlchemy 2 + Alembic. Audit
     event on upload. Data-access layer that requires `org_id`.
  3. **Auth:** Entra External ID dev tenant (country Germany, data location recorded, ADR-0003 condition). MSAL React
     in web; JWT validation in API; locally signed test tokens in tests.
  4. **Web:** Next.js (App Router) + TypeScript strict. DE/EN via an i18n library (M1 ADR). Pages: sign-in, inbox
     (upload + list), settings (language). Typed API client generated from OpenAPI, with a CI check that fails if it
     is out of date.
  5. **Docker Compose:** web, api, postgres, azurite. `.env.example` documents every variable.
  6. **CI (GitHub Actions):** lint + type check + tests for Python and TypeScript, build images, secret scan, path
     filters.
  7. **Interviews:** run at least 3 of the 5 interviews in parallel (they decide the M2 priorities).
     → **Deferred** on 2026-11-24 (see §4, P2).
- **Acceptance criteria:**
  - `docker compose up` → sign in → upload an official test XML and a PDF → both listed as `received`, in German and
    English.
  - Test proves that user A cannot list or fetch organisation B's documents.
  - Upload limits are enforced (oversized/unsupported file → clear error, in both languages).
  - CI is green on the PR, and the secret scan is green.

### M2 — Reading & validating invoices

**Split into two PRs (decided 2026-11-24):** M2a = tasks 1–7, 9 and the invoice view and findings list of task 10
(no cloud service, €0). M2b = tasks 8, 10 (review, corrections, approve) and 11, with its own plan and cost
estimate before it starts. Status: M2a built ([M2a.md](docs/milestones/M2a.md)); the FeRD Schematron spike (task 4)
was not done and stays optional.

- **Tasks:**
  1. `scripts/fetch-test-data` (pinned + SHA-256, [ADR-0008](docs/decisions/0008-test-data-sourcing-and-licensing.md)).
  2. Classifier: UBL / CII / PDF with embedded XML / unstructured.
  3. Parsers → one invoice model (EN 16931 BTs). **Spike:** official KoSIT visualisation step-1 transform (via Saxon)
     vs. own `lxml` mapping, then an ADR.
  4. ZUGFeRD: extract embedded XML; detect profile; flag MINIMUM/BASIC-WL as "not an e-invoice" (F3). **Spike:** FeRD
     Schematron as an extra KoSIT scenario.
  5. Validator container + Python client + finding mapping ([ADR-0005](docs/decisions/0005-validator-as-internal-daemon.md)).
     Measure memory and set `-Xmx`.
  6. Worker, queue, sweeper, poison queue ([ADR-0004](docs/decisions/0004-jobs-storage-queue-with-db-status.md)).
  7. Business checks:
     - VAT maths per rate
     - exact and semantic duplicates
     - mandatory fields (KoSIT/FeRD Pflichtangaben table, F29)
     - PDF-vs-XML consistency (F15)
     - small-amount rules (F11)
     - plausible VAT rates
     - foreign currency
  8. LLM extraction for unstructured PDFs/images (Azure OpenAI EU Data Zone, structured output) with
     verification-based confidence ([ADR-0006](docs/decisions/0006-deterministic-first-llm-boundary.md)). Local dev
     uses `az login` credentials, so no API keys.
  9. Curated DE/EN explanations for the most frequent rule codes.
  10. UI:
      - invoice view (sandboxed rendering)
      - findings list
      - review step ("needs your check") with field corrections, audited
      - approve
  11. Basic export: ZIP of originals + CSV ([ADR-0009](docs/decisions/0009-accountant-export-zip-and-csv-first.md)).
- **Acceptance criteria:**
  - All 86 official test-suite files are classified and parsed without error.
  - For every official case, parsed totals (BT-106, BT-109, BT-110, BT-112, BT-115) equal the XML values exactly.
  - Validator results for the official standard cases are "acceptable". Deliberately broken variants are rejected
    with the expected rule codes (regression tests).
  - A synthetic plain-PDF invoice goes end to end through LLM extraction, and a deliberately wrong field is caught
    by verification and routed to review.
  - Exported originals are byte-identical to the uploads (hash test). The CSV opens correctly with umlauts.

### M3 — Evaluation & quality gates
- **Tasks:**
  - Labelled set:
    - official XML rendered to PDF (exact labels)
    - synthetic layouts
    - photo/scan variants
    - split into dev and **held-out test** sets
  - Field-level metrics: exact match after normalisation; amounts exact to the cent; per-field and per-document
    accuracy; verification catch-rate; cost and latency per document.
  - Eval runner + Markdown/HTML report in `eval/reports/`, baseline committed.
  - CI gate:
    - deterministic (XML) suite must stay at 100%
    - LLM eval runs on recorded responses for PRs, and live runs on demand/nightly with a cost cap
    - a PR that lowers accuracy below the baseline fails
  - Optional baseline: Document Intelligence `prebuilt-invoice`.
- **Acceptance criteria:**
  - A report with numbers, dataset version and model/prompt version is committed.
  - A deliberate regression PR is shown to be blocked by the gate.

### M4 — Azure with Terraform
- **Tasks:**
  - Terraform (azurerm) with remote state in Azure Storage. Modules for:
    - resource group
    - Container Apps environment + apps
    - PostgreSQL Flexible Server
    - Storage (blob + queue)
    - Key Vault
    - container registry
    - Log Analytics + Application Insights
    - Azure OpenAI deployment
    - Managed Identities + role assignments
    - **budget alert**
  - Environments `dev` and `prod` (Germany West Central, availability confirmed).
  - GitHub Actions with OIDC federation (no cloud secrets in GitHub): test → build → scan → push → deploy dev → smoke
    test → manual approval → prod.
  - Custom domain + managed TLS certificate. The free managed certificate needs the app reachable during issuance
    and renewal, so decide min replicas for `web` (ARCHITECTURE §11).
  - Cost estimate in COSTS.md **before** the first `apply`.
  - Before the repo goes public: choose a licence, re-check that no personal data or secrets are in the git
    history, and add THIRD_PARTY notices.
- **Acceptance criteria:**
  - The app is live at a public URL.
  - `terraform plan` shows no drift.
  - The budget alert is tested.
  - Managed Identity is used for DB/Blob/Queue/OpenAI (no keys in config).
  - Measured monthly cost is recorded.

### M5 — First real users
- **Tasks:**
  - Before the first real user:
    - Impressum (§ 5 DDG)
    - privacy policy (Datenschutzerklärung)
    - consent flow
    - data-processing agreement (AVV) template
    - processing records
    - "export my data" and "delete my organisation" working
  - Pilot onboarding of 3–10 users from the interviews.
  - Application Insights dashboards; alerts (error rate, queue age, validator health, budget).
  - `docs/incidents/` with a post-mortem template.
  - Privacy-friendly usage metrics (no tracking cookies without consent).
  - A feedback channel.
  - Re-check the BMF FAQ/letters for changes.
- **Acceptance criteria:**
  - ≥ 3 real users have processed real invoices with consent.
  - Uptime, usage numbers and incidents are reported **from dashboards and logs** (screenshots/exports as evidence).
    No invented numbers.

### M6 — Automation (n8n)
- **Tasks:**
  - ADR on n8n's Sustainable Use License vs. alternatives for customer-facing email ingestion
    (ARCHITECTURE §10.9).
  - Per-organisation inbound email address; idempotent ingestion (Message-ID), attachment limits.
  - Scheduled export to the accountant (email/ZIP).
  - Notifications ("3 invoices need your check").
  - DATEV-Format only if accountants asked for it in interviews.
- **Acceptance criteria:**
  - A forwarded email with an XRechnung attachment appears processed in the inbox.
  - Duplicate forwards don't create duplicates.
  - Workflows are exported and versioned in git.

### M7 — Fine-tuning & serving
- **Tasks:**
  - Choose a small open vision-language model (licence check).
  - LoRA fine-tune on the M3 dev set + synthetic data (never the held-out test set, never user data without consent).
  - Serve with vLLM (OpenAI-compatible endpoint, so the same extractor interface).
  - Compare accuracy, latency and cost per document vs Azure OpenAI on the held-out set.
  - ADR: use in prod or not.
  - **GPU cost estimate shared first** (paid GPU time is acceptable where it adds value).
- **Acceptance criteria:** comparison report with reproducible configs, and a cost table.

### M8 — Kubernetes
- **Tasks:**
  - AKS (free control-plane tier, small node pool) with Terraform.
  - Helm charts per component.
  - KEDA for the worker, HPA for api/web.
  - Workload Identity.
  - NetworkPolicy (only the worker reaches the validator).
  - Rolling and canary strategy.
  - Migration runbook.
  - **Time box + cost cap** agreed first; keep-or-tear-down ADR at the end
    ([ADR-0007](docs/decisions/0007-container-apps-first-aks-later.md)).
- **Acceptance criteria:**
  - The same smoke tests pass on AKS.
  - A zero-downtime rollout is demonstrated.
  - Autoscaling is demonstrated under load.
  - Costs are recorded.

### M9 — Hardening
- **Tasks:**
  - Security review (OWASP ASVS Level 1 checklist), DAST baseline scan, dependency/image scanning, SBOM.
  - Tenant-isolation tests; PostgreSQL row-level security as defence in depth.
  - GDPR features complete (retention settings, audit-log viewer).
  - EU AI Act assessment (role, risk class, transparency duties) as a written document.
  - Load test (k6) with stated targets.
  - Backup/restore drill.
- **Acceptance criteria:** written reports with evidence; findings fixed or accepted with reasons.

### M10 — Launch & write-up
- **Tasks:** final README with screenshots and results linked to evidence; demo video; final claims audit; public
  write-up of the journey (including plan changes).
- **Acceptance criteria:** every number in the public material points to evidence in the repo.

## 3. Risks

Likelihood/impact: L = low, M = medium, H = high.

| ID | Risk | L | I | Mitigation | When |
|---|---|---|---|---|---|
| **U1** | Not enough pilot users | M | H | Interviews deferred (2026-11-24): recruit and interview pilot users before M5 onboarding; accountants as a channel (one accountant → many clients); free pilot | before M5 |
| **U2** | Problem not painful enough: free ELSTER viewer, DATEV Unternehmen online, lexoffice/sevDesk already cover it (F17, F49) | M | H | Interviews with explicit kill/pivot criteria, **deferred to before M5** (risk stays open until then); position on the workflow (mixed inbox, checks, handoff) and the bilingual niche, not on "viewing XML" | before M5 |
| U3 | Users won't upload financial documents to an unknown tool | M | H | EU hosting, transparent architecture, Impressum + privacy policy, start with people who know us, open-source repo (from M4) | M5 |
| U4 | Few e-invoices before 2027/2028 | M | M | Value from day one through PDF extraction and checks. Volume grows sharply in 2027 (F9), so the timing works for us | M2 |
| **T1** | LLM extraction accuracy too low on photos/scans | M | M | Verification-based confidence + human review; eval gate; start with PDFs; photos as beta | M2–M3 |
| T2 | Format changes: XRechnung 4.0 (spring 2027), ZUGFeRD releases | H | M | Pinned versions; validator configs side by side; version stored with every result; watch releases | ongoing |
| T3 | ZUGFeRD validation gap (profile Schematron, PDF/A-3) | M | M | M2 spike; Mustang CLI as fallback | M2 |
| T4 | Validator memory / cold start in Container Apps | M | L | Measure, set `-Xmx`, min 1 replica in prod if needed | M2/M4 |
| T5 | Entra External ID + Next.js integration takes longer than planned | M | M | Spike first in M1; fallback per ADR-0003 | M1 |
| T6 | Malicious files (XXE, zip/PDF bombs, script injection in rendered HTML) | M | H | Hardened XML parser, size/page limits, sandboxed rendering, security tests | M1–M2, M9 |
| T7 | Scope: 11 milestones for one developer | H | M | Time box per milestone; P1 reorder; cut scope inside a milestone, never quality gates | ongoing |
| **L1** | Findings understood as tax advice / liability | M | H | Wording "please check", never "invalid / no input VAT" (F16); disclaimer; no verdicts | M2, M5 |
| L2 | GDPR duties before real users (privacy policy, AVV, TOMs, Impressum) | H | H | M5 checklist; public templates and guidance; no real data before it is done | M5 |
| L3 | Deletion vs. users' 8-year retention duty | M | M | Clear UX: export before delete; "Belegfluss is not your archive" (F18, F19) | M2, M9 |
| L4 | Licences: FeRD samples, EUPL examples, n8n Sustainable Use License | M | M | ADR-0008; n8n ADR in M6 | M2, M6 |
| L5 | Rules change (new BMF letters every October so far; reporting system planned, F21–F22) | H | M | Research doc dated; re-check BMF FAQ before M5 and after each October | ongoing |
| L6 | EU AI Act obligations | L | M | Written assessment in M9; transparency labels for AI-extracted fields from M2 | M2, M9 |
| **C1** | Azure costs creep (always-on DB, registry, log ingestion, AKS nodes, GPUs) | M | M | Budget alerts from first deploy; scale-to-zero; estimates in COSTS.md shared before creating; free tiers first | M4+ |
| C2 | LLM costs in CI evals | M | L | Recorded responses for PRs; live eval nightly with a cap | M3 |
| C3 | GPU cost for M7 | H | M | Short rented sessions or spot capacity; estimate shared first; small model | M7 |

## 4. Proposed changes to the roadmap

Review outcome (2026-11-23): **P1 declined**, **P2 and P3 adopted**. Logged in
[PROJECT_LOG](docs/PROJECT_LOG.md). The roadmap order is unchanged, so no ADR was needed.

- **P1 — Deploy a thin slice to Azure right after M2 (swap M3 and M4). → Declined.** Deploy only after the
  workflow is built and evaluated (M1–M3). Original reasoning, kept for the record: A live URL with XML invoices (fully
  deterministic, tested on official data) makes the pilot possible about one milestone earlier. The LLM path is
  labelled "beta" until the M3 gate exists. *Cost:* Azure spending starts earlier (a few € per month in dev).
  *Risk:* LLM quality without a gate, mitigated by review-before-export.
- **P2 — Run interviews during M1, not after. → Adopted, then deferred on 2026-11-24.** The owner can't run
  interviews right now. Impact:
  - M2 keeps its planned priorities. They follow the law and the official formats (reading XML, the official
    validator, VAT and duplicate checks), so they don't depend on interview answers.
  - Choices that did depend on the interviews stay at their safe defaults: accountant export as ZIP + CSV
    ([ADR-0009](docs/decisions/0009-accountant-export-zip-and-csv-first.md)), no DATEV format yet, both languages.
  - The interviews (or a short questionnaire to the same people) must happen **before M5**, because M5 onboards
    pilot users anyway. Until then, risks U1 and U2 stay open.
  - German UI tone was decided without interviews: informal "du" (owner, 2026-11-24).
- **Split M2 into M2a and M2b (decided 2026-11-24, with the owner).** Two reviewable PRs, and the paid Azure OpenAI
  part starts only after the deterministic part works. The order of milestones is unchanged.
- **P3 — Make the "PDF vs. XML mismatch" check a headline feature. → Adopted.** It is legally grounded (F15), rare in free
  viewers, and easy to explain.

## 5. Proposed improvements (engineering depth and credibility)

| Idea | Adds | Effort |
|---|---|---|
| Verification-based confidence for LLM fields (ADR-0006) | Explainable AI quality instead of "trust the model" | in M2 scope |
| Public eval report + model card per extractor | Evidence-based quality claims | S (M3) |
| LLM ops metrics: tokens, cost, latency per document in App Insights | Production LLM monitoring | S (M5) |
| Supply-chain basics: Dependabot, gitleaks, Trivy image scan, SBOM, signed images (cosign) | Security maturity at near-zero cost | S (M1/M4) |
| OpenAPI contract check between API and web client | Typed end-to-end contract | S (M1) |
| Availability test + simple status page | Real uptime numbers | S (M5) |
| Incident post-mortem template + runbooks | Operational maturity | S (M5) |
| Feature flag to switch extraction providers per org | Safe A/B comparison (Azure OpenAI vs. fine-tuned model) | M (M7) |
| "Supplier should have sent an e-invoice" hint for 2027/2028 (F9, F10) | Timely, legally grounded value | S (M2/M6) |
| Tenant-isolation property tests (generated cross-tenant requests) | Strong security evidence | S (M1) |

## 6. Working rules

How this project is run, so that every claim stays checkable:
1. **Explain before building:** for anything non-trivial, write what/how, the options, the choice and why, and the
   limits before the code. Significant choices get an ADR (ADR-0001).
2. **Verify, don't assume:** run code and tests before claiming something works. Cite official documentation for
   standards, laws, cloud services and libraries. Every number in README/docs points to evidence.
3. **Change rule:** when an earlier decision turns out wrong, stop, explain the options and impact, write a
   **superseding ADR**, re-plan here, log it, and change the code under the protection of the existing tests.
4. **Simple code:** typed Python with Pydantic at boundaries, TypeScript strict, small modules, well-known
   libraries, no speculative abstractions.
5. **Privacy & safety:** EU only; no invoice content in logs; no secrets in git; only official test data and
   synthetic data until the pilot is legally ready; the LLM never writes SQL or data.
6. **Cost:** free tiers first; paid where it clearly adds value; estimate shared before creating; budget alerts
   from the first deployment.
7. **Git:** one branch per milestone, Conventional Commits, one PR per milestone.
