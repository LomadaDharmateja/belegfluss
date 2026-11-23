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

**Next**
- B2: sign in with a real account, check the token's `iss`/`aud`/`scp`/`oid` against the API's verifier.
- B3: manual end-to-end run in DE/EN with screenshots; then Phase C (M1 docs, claims audit, PR).
