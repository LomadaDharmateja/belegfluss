# Project log

A dated diary: what was done, why, what was learned, what broke. Newest entry at the bottom.

---

## 2026-11-23 — Session 1: M0 research & design

**Done**
- Verified the German e-invoicing rules, formats, validator, test data and accountant export options against
  official sources. Wrote `docs/research/einvoicing.md` (49 facts with sources and status, open questions).
- Ran the official KoSIT validator v1.6.3 with the XRechnung configuration 2026-08-31 (CLI and daemon) on official
  test files plus two modified copies, in an `eclipse-temurin:21-jre` container. Output saved as
  `docs/research/evidence/validator-smoke-2026-11-23.txt`.
- Wrote the user interview guide (DE/EN), `docs/ARCHITECTURE.md` (8 diagrams), ADRs 0001–0009 (Proposed),
  `PLAN.md`, README draft, `COSTS.md`, M0 milestone notes with claims audit.
- Created the private GitHub repo, branch `m0-research`, PR for review.

**Why**
- To build on verified facts, not assumptions, and to agree on the architecture before any code exists.

**Learned**
- Since 2025 the **XML is the leading part** of a hybrid ZUGFeRD invoice. The PDF image no longer wins (BMF FAQ
  Q12a). A PDF-vs-XML consistency check is therefore a meaningful feature.
- Validation is **not** a legal prerequisite for input VAT (BMF FAQ Q7), so the app must phrase findings as hints.
- A **free official viewer** (ELSTER) exists, and DATEV Unternehmen online handles e-invoices. Viewing alone is not a
  product, and the interviews must test whether the workflow pain is real.
- The official validator configuration also covers **plain EN 16931** invoices. "Schematron N" can still be
  "ACCEPTABLE": information/warning messages don't reject.
- The JVM picked a ~1.9 GB default heap in the container, so `-Xmx` must be set later.
- FeRD's ZUGFeRD sample invoices have **no redistribution licence**. They must never be committed.

**What broke / workarounds**
- `bundesfinanzministerium.de` returned HTTP 503 to automated fetching. The pages loaded in a normal browser
  (Chrome), so the official FAQ and the letter landing pages were read there. The letter PDFs' text could not be
  extracted in the browser: loading a PDF library into the page was blocked by the tool permission system, and that
  approach was dropped. The FAQ (as of 29 Oct 2026) summarises the letters. Reading the PDFs is an open task before
  the pilot.
- DATEV's developer portal only renders with JavaScript. Read in Chrome. A cookie banner was left untouched.
- EUR-Lex returned an empty body. ViDA facts are marked as a caveat (search summary of the Commission page).
- Link check: Python's `urllib` reported false failures for some sites. `curl` confirmed HTTP 200. Lesson: verify
  link-check failures with a second client.
- Mermaid: a `;` inside a sequence-diagram message is a statement separator and broke rendering. Found by rendering
  all diagrams with mermaid-cli.

**Decisions**
- ADRs 0001–0009 proposed (see `docs/decisions/README.md`).
- Local AI-assistant instructions are kept out of git (`.gitignore`).

**Next**
- Review and approve the M0 PR; answer the open questions; start interviews; then M1 (local foundation).

---

## 2026-11-23 — M0 review outcome

**Decisions by the project owner**
- **M0 approved.** ADRs 0001–0009 are now *Accepted*. ADR-0003 is still conditional on the Entra External ID data
  location, which is checked in M1.
- **Proposal P1 (deploy right after M2) declined.** Azure deployment (M4) happens only after the full workflow is
  built and evaluated (M1–M3). The roadmap order is unchanged.
- **P2 (interviews during M1) and P3 (PDF-vs-XML check as a headline feature) adopted.**
- **Cost policy:** free tiers first. Paid services (e.g. Azure OpenAI, a larger model where accuracy needs it) are
  fine where they add value. Estimates go into `docs/COSTS.md` and are shared before anything paid is created.

**Next**
- Merge PR #1, then plan M1 (local foundation).

---

## 2026-11-23 — M1 planning and Phase A (local foundation, no Azure needed)

**Decisions in planning (owner)**
- Sign-in tenant through a normal Azure account (free sign-up, €0 in M1, budget alert right after creation),
  not the 30-day trial.
- Sign-in method: email one-time code (no passwords).

**Done**
- `docs/setup/entra-external-id.md`: step-by-step guide for the owner (Azure account → budget alert → external
  tenant → API + SPA registrations → email-OTP user flow). No client secrets anywhere.
- API (`apps/api`), Python 3.14 / FastAPI 0.165:
  - token validation (signature, issuer, audience, expiry, scope; `tid`+`oid`), with no bypass in app code
  - personal organisation on first sign-in; org-scoped routes, where non-members get 404
  - upload with size limit, type detection from content, SHA-256, unchanged originals in Blob, per-org duplicate
    detection, audit events without file names
  - SQLAlchemy 2.1 + Alembic on PostgreSQL 18
  - **63 tests** against real PostgreSQL and Azurite (testcontainers)
- Web (`apps/web`), Next.js 16.4 / React 19.3:
  - next-intl DE/EN without locale in the URL
  - MSAL React sign-in with runtime configuration (one image for all environments)
  - typed client generated from OpenAPI
  - inbox with upload and list
  - **25 Vitest + 5 Playwright tests**
- Docker Compose stack (Postgres, Azurite, API, web). Verified: all healthy, migrations on start, DE/EN, blob
  write/read.
- CI workflows: API, web, compose smoke test, gitleaks (binary pinned by checksum), Dependabot; actions pinned by
  commit SHA.
- ADRs 0010–0013 proposed (i18n, API contract, persistence, tenancy).

**Learned / changed from the plan**
- **TypeScript 5.9 instead of the planned 6.0.3.** openapi-typescript declares a peer dependency on TypeScript 5,
  and the official Next.js 16.4 scaffold uses `^5`. typescript-eslint doesn't support TypeScript 7 yet either.
- **ESLint stays on 9** (deprecated warning): eslint-plugin-react, -import and -jsx-a11y don't support ESLint 10
  yet.
- pnpm 12 blocks install scripts by default. `@parcel/watcher` and `@swc/core` (pulled in by next-intl's unused
  extraction tooling) ship prebuilt binaries, so their scripts are denied in `pnpm-workspace.yaml`.
- Next.js 16 "Cache Components" is opt-in and left off. Next.js says it becomes the default in the next major
  version, so that's a planned migration.
- MSAL React 5 calls `initialize()` and `handleRedirectPromise()` itself (read in its source). Our provider only
  creates the client after hydration, using `useSyncExternalStore`, which satisfies the React Compiler lint rules
  without suppressions.
- `UseDevelopmentStorage=true` points to `127.0.0.1` only (read in the Azure SDK source). Docker Compose uses a
  dedicated Azurite dev account instead, with a fake key marked inline for gitleaks.
- Starlette's test client now prefers `httpx2`; testcontainers moved modules to `testcontainers.community.*`. Both
  were switched, so the test run is warning-free.

**What broke**
- A `sed` edit put a real line break into a Python string, and a chained command committed it although the export
  had failed. Fixed in the next commit and verified (ruff, mypy, 63 tests). Lesson: use `set -e` when chaining
  checks and commits.
- First web test run: the placeholder check matched words inside ICU plural branches. The test regex was fixed.

**Next**
- CI results on draft PR #2 → Phase B once the owner has created the tenant → M1 docs and claims audit.

## 2026-11-24 — M1 Phase B1: Azure subscription and sign-in tenant

**Done**
- Subscription question: Azure for Students vs pay-as-you-go. Chose **pay-as-you-go**. Student subscriptions only
  allow a few regions by policy (Europe usually restricted), the offer is meant for education, Cost Management
  lists it as unsupported, and it is disabled when the credit or the 12 months run out. Reasons and sources added
  to `docs/setup/entra-external-id.md`.
- Owner created the subscription (Azure Plan, active, €0), a **€10/month budget** (alerts: actual 50 %, actual
  100 %, forecast 100 %, by email) and the external tenant **Belegfluss Dev** (`belegflussdev`).
- Read-only check in the portal: tenant country **Germany**, data location **"EU Model Clause compliant
  datacenters"**; the public discovery document reports `tenant_region_scope: EU`. Tenant resource in
  `rg-belegfluss-identity`, location Europe.
- Steps 4–6 redone in the external tenant (with the owner's approval, in the owner's browser): `belegfluss-api`
  (scope `access_as_user`, Admins only; `requestedAccessTokenVersion` was already 2), `belegfluss-web` (SPA,
  redirect `http://localhost:3000`, no secret, implicit grant off, admin consent granted), user flow
  `SignUpSignIn` (email one-time passcode, Display Name only) with the web app added.
- `.env` (git-ignored) filled with the public IDs; issuer and JWKS URL taken from the tenant's discovery document.

**What broke**
- Steps 4–6 were first done in the owner's **Default Directory** instead of the external tenant: the Azure portal
  and the Entra admin center each remember their own directory. The guide didn't warn about it; it now does, with
  a check of the directory label before Step 4. The leftover apps and user flow in the Default Directory are to be
  deleted by the owner once sign-in works.
- **The sign-in button did nothing** (first real test). The browser console showed MSAL's
  `endpoints_resolution_error`. Cause, read in the msal-common 16.17 source (`Authority.validateIssuer`): the
  tenant's discovery document names a tenant-ID-based issuer (`https://<tenant-id>.ciamlogin.com/<tenant-id>/v2.0`),
  while the app signs in via `belegflussdev.ciamlogin.com`. MSAL accepts a different issuer host only if it is in
  `knownAuthorities`. Fix: new variable `ENTRA_TENANT_ID`; both hosts are listed. Regression test first
  (`config.test.ts`, failed before the fix), then web lint, types, 27 unit and 5 browser tests pass. Verified in
  Chrome: the button now opens the Belegfluss Dev sign-in page (authorization code + PKCE, our API scope).
- My own slip: the first attempt to log this ran in the same command as the commit, failed on the line endings, and
  the commit went ahead without the log entry. Logged in a separate commit; checks and commits now run as separate
  steps.

**B2: first real sign-in (owner, email one-time code) and upload, verified**
- API log: `GET /me` 200, `GET /orgs/{org}/documents` 200, `POST /orgs/{org}/documents` 201. The verifier only
  accepts a token with a valid RS256 signature from the tenant's JWKS, the exact issuer, audience = API client ID,
  scope `access_as_user`, and `exp`/`tid`/`oid` present, so the real token passed all of these checks.
- Database: 1 user (only `idp_tenant_id` = our tenant ID and `idp_object_id`; no email or name), 1 organisation
  "My business", 1 owner membership, 1 document (`application/pdf`, 4,911 bytes, `received`), audit events
  `user.created`, `org.created`, `document.uploaded`.
- Storage: the blob at `orgs/{org}/originals/{sha256}` starts with `%PDF`, and its recomputed SHA-256 matches the
  database. The API log contains no file names.

**B3: manual end-to-end run with screenshots** (owner signed in; the rest driven in the owner's Chrome)
- Test data: official KoSIT test suite `xrechnung-3.0.2-testsuite-2026-08-31.zip` (5,586,900 bytes, SHA-256
  `1e81ef75…e3d7`), unpacked into the git-ignored `testdata/external/`. Files used: `01.01a-INVOICE_ubl.xml` (UBL)
  and `01.01a-INVOICE_uncefact.xml` (CII).
- Results, each with the server response from the API log:
  - UBL and CII test invoices added (201), shown as XML / "Received"
  - same UBL file again → "was already in your inbox" (200, no new row)
  - `notes.txt` → "This file type is not supported…" (415)
  - 21 MiB file (generated in the page, because the browser tool only uploads files under 10 MB) → "The file is too
    large." The browser stops it before upload; the server-side 413 is covered by API tests.
  - Language switch to German: navigation, messages, dates (24.11.2026, 01:07), decimal comma (9,6 kB), status
    "Eingegangen". Switched back to English afterwards.
- Database: 3 documents, 3 `document.uploaded` audit events; no rows for duplicates or rejected files. API log: no
  file names.
- Storage holds one extra blob (`orgs/aa5915c9…/originals/aaaa…`, 13 bytes, 2026-11-23 07:10): a placeholder from
  my Phase A storage check, not from the app. It belongs to no organisation in the database.
- Screenshots: `docs/milestones/evidence/m1-01` … `m1-05`. No email or name is visible; file names are test files
  and one PDF the owner confirmed as harmless.

**What broke**
- The "Uploading …" line stayed under the result and looked as if the upload were still running (only one request
  reached the API). Fixed: the result replaces the line. Regression test first; 28 unit tests pass.

**Next**
- Phase C: M1 docs (three parts + claims audit), ARCHITECTURE/COSTS updates, ADRs 0010–0013 for review, PR ready.

## 2026-11-24 — M1 Phase C: docs, claims audit, clean-up

**Done**
- Leftovers in the owner's Default Directory deleted (with the owner's approval): app registrations
  `belegfluss-api` and `belegfluss-web`, user flow `B2X_1_SignUpSignIn`. `aad-extensions-app` (created by Azure)
  kept.
- [docs/milestones/M1.md](milestones/M1.md): three parts, test evidence with CI links, screenshots, changes from the
  plan, what broke, claims audit (24 claims).
- Fixed during the audit:
  - ADR-0003: condition marked as met; implementation notes (`tid` + `oid`, issuer host)
  - ARCHITECTURE: data model and tenancy rule updated to what M1 built; i18n/API-client choices marked as decided;
    EU data location confirmed
  - ADR-0011: package size stated as measured; ADR-0012: test duration as measured
  - COSTS: M1 row (€0.00 measured) and the budget alert
  - README: status, screenshots, pointer to M1 evidence
- Clean-up: scanned for exported code that nothing imports. Only `defaultLocale` was exported without need; the
  export was removed. No dead code found in the API.
- Checks: API 63 tests (29.9 s), ruff, format, mypy strict; web lint, types, 28 unit tests. Link check: 46/46 public
  links, 5/5 private repo links (via `gh api`), all relative links and anchors.

**Open**
- Diagrams: both changed diagrams render on GitHub (checked in the branch view; mermaid-cli not installed).
- ADRs 0010–0013 wait for the owner's review. Interviews (M1 task 7) are still open.

## 2026-11-24 — M1 review outcome

**Decisions (owner)**
- ADRs 0010–0013 accepted.
- German UI keeps the informal "du" (recorded in ADR-0010).
- PR #2 approved for merge.
- **User interviews deferred.** The owner can't run them right now. M2's priorities follow the law and the official
  formats, so they don't depend on the answers. Choices that did depend on interviews stay at their safe defaults
  (ZIP + CSV export, no DATEV format yet). Interviews or a short questionnaire must happen before M5 (pilot
  onboarding). Risks U1/U2 stay open until then. Recorded in PLAN §3 and §4 (P2).

**Next**
- M2 planning: explain the approach, options and costs (first paid service: Azure OpenAI) before building.

## 2026-11-24 — M2a: reading and validating invoices

**Planning (with the owner)**
- M2 split into two PRs: M2a (deterministic, no cloud, €0) and M2b (LLM extraction, review, export; first paid
  service). Keyless Azure login for M2b via Azure CLI.
- M2b estimate shared before anything is created: gpt-5-mini Data Zone EU in Germany West Central, $0.275 / $2.20 per
  1M tokens (Azure Retail Prices API), about €2–4 for development (COSTS.md).

**Done**
- Spike: official KoSIT step-1 XSLT via saxonche on the 86-file suite: 86/86, 0 mismatches on BT-106/109/110/112/115,
  ~5 ms per file → adopted (ADR-0014). Evidence: `docs/research/evidence/xslt-spike-2026-11-24.*`.
- Five step-1 stylesheets vendored unchanged (Apache-2.0) with licence and source note.
- `scripts/fetch_test_data.py`: pinned, checksummed test suite into `testdata/external/`; cached in CI.
- Validator container (1.6.3 + configuration 2026-08-31, checksums as in M0, non-root, no GUI, health check).
  All 86 suite files accepted (median ~30 ms). Memory: 627 MiB at 512 MB heap; 256 MB handled the suite three times
  (446 MiB) but large attachments are untested, so 512 MB stays.
- Reading: classification by content, ZUGFeRD XML extraction, safe XML parsing (no network/entities, DOCTYPE
  rejected, UTF-8 only), invoice model named after EN 16931 terms. Synthetic UBL credit note and CII fixtures.
- Worker on Storage Queue (sweeper, poison queue, idempotent), results in `invoices` (summary + JSONB) and `findings`
  (ADR-0015), business checks with 30 `BF-` codes, curated DE/EN explanations for 22 official rules (texts taken from
  the configuration), KoSIT mandatory-details table read (research F29 updated).
- Web: list with summary and counts (polling), document page with official result, findings and invoice view.
- Compose: `validator` (no published port) and `worker`. CI: test data, real validator in tests, smoke test checks the
  validator is internal.
- Tests: API 202, web 37 + 5 Playwright; CI green on PR #7. Walkthrough with screenshots (`m2a-01` … `m2a-06`).

**What broke**
- A real receipt was reported as password-protected: it was encrypted with an empty password. Fixed (try the empty
  password first), regression test.
- ZUGFeRD MINIMUM showed "rejected": the configuration has no scenario for it (`noScenarioMatched`), and our own
  arithmetic was skipped. New outcome `no_scenario`, our checks run, real rejections always need review. Regression
  tests.
- The newest Azure queue SDK uses an API version Azurite doesn't list: tests now run Azurite 3.38.0 with
  `--skipApiVersionCheck`, like Compose.
- `ADD <url>` files are root-only in Docker; the non-root validator couldn't read its jar. The Docker SDK can't build
  `ADD --checksum`, so the test fixture builds with the docker CLI.
- Azure's minimum visibility timeout is 1 s; the poison test waits accordingly.
- My process: several scripted edits failed on line endings or reformatted text; all were caught by exact-once checks
  before anything was committed.

**Next**
- Owner reviews ADR-0014/0015 → merge PR #7. Then the M2b plan (Azure CLI install, explicit yes before creating Azure
  OpenAI). Open: Dependabot PRs #3–#6 (two are major runtime upgrades: Python 3.15, Node 26), unit codes shown as
  words.

## 2026-11-24 — M2a review outcome

- Owner accepted ADR-0014 and ADR-0015 and approved PR #7 for merge.
- Next: M2b plan (LLM extraction, review, export).

## 2026-11-24 — M2b steps 1–2: review, approval, export, AI reading (no Azure yet)

**What was done**
- Plan approved with the owner: Claude runs documented `az` commands only after an explicit yes at that moment;
  only synthetic documents go to Azure OpenAI; approving with open errors is allowed after a confirmation.
- Step 1 (commit `9b4fc36`): status `approved`, `field_reviews` table and migration, corrections for AI-read invoices
  (checks re-run, audit log with field names only), approve/reopen, export `ZIP` of byte-identical originals plus
  `summary.csv` (UTF-8 BOM, `;`, comma decimals, CSV-injection guard). Web: review form, approval box, export box.
- Step 2 (commit `11168bd`): `extraction` package. Page images and text layer (EXIF rotation, metadata dropped),
  strict structured-output schema, Azure v1 client (keyless, no tools, `store=False`), fake for tests. Verification by
  code: IBAN checksum, VAT ID shape, plausible dates, values present in the text layer. AI-read documents always need
  review; tokens and time stored; transient AI errors retried.
- Step 3 prepared, nothing created in Azure: `scripts/azure/dev-openai.ps1` (every command checked against Microsoft
  Learn), `compose.ai.yaml`, `scripts/run-ai-worker.ps1`, `docs/setup/azure-openai-dev.md`, opt-in live test.
- Tests: API 242 passed, web 45 passed.

**What broke**
- Amounts in the PDF text were matched as text fragments, so `0,00` was "found" inside `340,00`. Found by the
  prompt-injection test. Now amounts are read from the text as whole numbers. Regression test; the ZUGFeRD
  PDF-vs-XML check uses the same function.
- The test first imported `httpx`; the openai SDK 3.x uses `httpx2`.

**Learned**
- A custom subdomain is required for Entra ID sign-in and can't be changed later. Microsoft's key-switch-off page shows
  PowerShell/Bicep only, so the script uses the generic `az resource update --set` and reads the value back.

**Next**
- Owner installs the Azure CLI and runs `az login`. Claude checks model offer and quota read-only, shows the script,
  and creates the resource only after the owner's yes. Then live runs, measured cost, docs, PR.

## 2026-11-24 — M2b steps 3–4: Azure OpenAI created, model changed, first live run

**What was done**
- Owner installed the Azure CLI. `az login` first failed: the Default Directory (where the subscription lives) needs
  multi-factor sign-in; `az login --tenant <id>` worked.
- Read-only checks: provider `Microsoft.CognitiveServices` was not registered; quota for **gpt-5-mini Data Zone
  Standard was 0** in Germany West Central and six other EU regions. gpt-5.4-mini (2026-03-17) had 200.
- **Plan change (with the owner):** gpt-5.4-mini instead of gpt-5-mini. About 2.5× the token price, but EU Data Zone
  quota now and a later retirement (2027-09-21 vs 2027-07-13). Rejected: waiting for a quota request; Global Standard
  (processing outside the EU). Recorded in COSTS.md; ADR-0016 will record it.
- After the owner's yes: provider registered, `scripts/azure/dev-openai.ps1` run. Read back: keys off, Data Zone
  Standard, capacity 20, role only on this resource, nothing else in the group.
- Live run on 4 synthetic documents: all fields right; misprinted VAT caught (`BF-VAT-AMOUNT`); the injected
  instruction ignored; $0.0172 in total ([evidence](milestones/evidence/m2b-live-run-2026-11-24.md)).

**Learned**
- "Offered in a region" (region table, `model list`) and "usable" (quota) are different things. A new pay-as-you-go
  subscription can have 0 quota for an older model. Check `az cognitiveservices usage list` before planning a model.
- Before the AI worker ran, checked that no local document is in `received`/`processing`, so the sweeper can't send
  the owner's real receipt.

## 2026-11-25 — M2b step 5: walkthrough, two bugs fixed, docs

**What was done**
- The computer had restarted: Docker Desktop and the host AI worker were gone. Restarted both; `az login` still valid.
- Before the AI worker ran: no local document in `received`/`processing`, so nothing old (the owner's real receipt)
  could be sent to Azure.
- Walkthrough in the owner's Chrome. The owner signed in with the one-time code; Claude did the rest with **synthetic
  files only** (`testdata/external/m2b-walkthrough/`, git-ignored):
  - two plain PDFs and a "phone photo" read by AI within seconds
  - wrong VAT → 2 errors
  - the same invoice number → duplicate hint
  - a demo correction (due date) stored before/after in `field_reviews` and audited
  - approve with and without acknowledgement
  - export of November: 2 originals byte-identical (SHA-256), CSV with BOM and the open findings
- Docs: ADR-0016 (AI extraction) and ADR-0017 (review, approval, export), both proposed; `M2b.md` with claims audit;
  ARCHITECTURE (data model as built, decisions, Azure facts), README, PLAN, THIRD_PARTY.
- Tests: API 243 passed (1 live test skipped), web 47 + 5 Playwright, build OK. Link check: 111 relative and 46 web
  links resolve.

**What broke**
- **A correction hid the duplicate warning:** the re-check ran without the duplicate lookup. Regression test first,
  fixed (`b6e5542`).
- **Times were shown in UTC** (container zone): 03:34 showed as 2:34. Now `Europe/Berlin`. The first regression test
  passed by accident on this laptop (German zone), so it now asserts the setting itself (`f73bf28`).
- The start page still said the export was "coming soon". Fixed.
- Chrome screenshots time out while the Chrome window is in the background; clicks did not reach the page either.
  Used the page's own events instead; only 3 screenshots so far.

- PR #9 opened. The secret scan failed on a false positive (`../../etc/passwd` in a test matched the generic-key
  rule). Added `--verbose` to see where (values stay redacted), changed the test to `etc/hosts`, and listed the one
  historical fingerprint in `.gitleaksignore`. All CI checks green afterwards.

**Next**
- Owner: review ADR-0016/0017 and the PR. Check the Azure cost view for a base fee (claim 13 in M2b.md).
- Optional: more screenshots (correction history, approved state, German view) when Chrome is in front.
