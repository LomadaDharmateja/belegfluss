# Belegfluss

**A bilingual (German / English) e-invoice inbox for freelancers and small businesses in Germany.**

> **Status: M4a done.** A dev environment runs on Azure (Container Apps, North Europe), created with
> Terraform and released by GitHub Actions without any secret. Earlier milestones: XRechnung and ZUGFeRD invoices are
> read exactly and checked by the official KoSIT validator. Plain PDFs and photos are read by AI (Azure OpenAI, EU
> Data Zone, keyless), every value is checked by code, and a person confirms it. Approved documents are exported for
> the accountant. AI reading is measured on 206 labelled documents, and a CI gate blocks changes that make it worse.
> Next: prod and a public repository (M4b). See [PLAN.md](PLAN.md) and the milestones [M1](docs/milestones/M1.md),
> [M2a](docs/milestones/M2a.md), [M2b](docs/milestones/M2b.md), [M3](docs/milestones/M3.md),
> [M4a](docs/milestones/M4a.md).

## The problem

Since **1 January 2025** every business in Germany must be able to **receive** structured e-invoices (XRechnung,
ZUGFeRD). Issuing them becomes mandatory step by step until **1 January 2028**
([research, F7–F10](docs/research/einvoicing.md#8-verified-facts)). Meanwhile the inbox stays mixed for years:
XML files that need extra viewer software to read, hybrid PDFs whose embedded XML is the legally leading part
(F15), plain PDFs, and photos of receipts. Many documents are exempt and will never be e-invoices (F11–F13).

*Our hypothesis, to be tested in [user interviews](docs/research/user-interviews.md):* freelancers and small
businesses still sort this mix and pass it to their accountant largely by hand, and they can't easily tell whether
an invoice is correct.

## What Belegfluss will do

1. Receive invoices: upload, later by email forwarding.
2. Read structured e-invoices (XRechnung UBL/CII, ZUGFeRD/Factur-X) **directly from the XML**.
3. Extract data from plain PDFs and images with an LLM pipeline. Every extracted field is checked by code, and
   uncertain fields go to a human review step.
4. Validate with the **official KoSIT validator** plus plain business checks (VAT maths, duplicates, missing
   fields, PDF-vs-XML mismatch), and explain problems in simple German or English.
5. Show a readable view of each invoice.
6. Export approved invoices for the accountant: originals + CSV first, more formats if accountants need them.
7. Dashboard: totals, VAT, open items, problems found.

Not in scope: sending invoices, payments, bookkeeping, tax advice.

## Screenshots (M2a and M2b, local, synthetic test invoices)

| | |
|---|---|
| ![Inbox with read invoices and their status](docs/milestones/evidence/m2a-01-inbox-en.jpg) | ![A wrong total explained](docs/milestones/evidence/m2a-02-wrong-total-en.jpg) |
| Inbox: supplier, number, date, amount and status, read from the e-invoices | A wrong total: the official rules, explained in plain language |
| ![ZUGFeRD PDF whose visible number differs from the XML](docs/milestones/evidence/m2a-05-pdf-xml-mismatch-de.jpg) | ![Invoice view](docs/milestones/evidence/m2a-03-invoice-view-en.jpg) |
| ZUGFeRD: the visible PDF shows a different invoice number than the XML (German) | The invoice as read from the XML |
| ![Plain PDF read by AI: the wrong VAT amount caught by code](docs/milestones/evidence/m2b-02-wrong-vat-findings-en.jpg) | ![Review form for AI-read fields](docs/milestones/evidence/m2b-03-review-form-en.jpg) |
| A plain PDF read by AI: the misprinted VAT is caught by code, not by the model | Every AI-read field can be checked and corrected before approval |

## Design

- [Architecture](docs/ARCHITECTURE.md): components, data flow, where the LLM is and isn't used, Azure services,
  security/GDPR boundaries
- [Decisions (ADRs)](docs/decisions/README.md)
- [E-invoicing research](docs/research/einvoicing.md): verified facts with official sources, and a hands-on run of
  the official validator ([evidence](docs/research/evidence/validator-smoke-2026-11-23.txt))
- [User interview guide](docs/research/user-interviews.md)

Planned stack: Next.js + TypeScript, FastAPI + PostgreSQL, KoSIT validator, Azure (Container Apps → AKS, Azure
OpenAI in the EU data zone, Blob/Queue, Key Vault, Managed Identity, Entra External ID), Terraform, GitHub Actions.

## How to run (local)

Requirements: Docker. For development without Docker: [uv](https://docs.astral.sh/uv/) and Node 24 with
Corepack (pnpm).

```bash
cp .env.example .env          # optional: sign-in values from docs/setup/entra-external-id.md
docker compose up --build     # web http://localhost:3000 · API http://localhost:8000/docs
```

Without the sign-in values the app runs, but shows "sign-in not configured". AI reading of plain PDFs and photos is
off by default; switching it on needs an Azure OpenAI resource ([setup](docs/setup/azure-openai-dev.md)).

| Part | Checks |
|---|---|
| API (`apps/api`) | `uv run ruff check . && uv run mypy src && uv run pytest` (tests start PostgreSQL 18 and Azurite containers) |
| Web (`apps/web`) | `pnpm lint && pnpm build && pnpm typecheck && pnpm test && pnpm test:e2e` |
| API contract | after an API change: `uv run python -m belegfluss.openapi_export ../web/src/api/openapi.json`, then `pnpm gen:api` |

CI runs all of this on every pull request, plus a Docker Compose smoke test and a secret scan.

## Results

Measured on a labelled set, not on real users yet (usage comes with M5). Every number links to evidence.

| What | Result | Evidence |
|---|---|---|
| AI reading, held-out test set (127 documents: official test-file renders, synthetic layouts, photos, scans) | **71.7 %** of documents fully right (95 % CI 63.3–78.8 %); 10 of 13 fields 95–99 %, due date 93.7 %, IBAN 89.0 %, seller VAT ID 83.5 %. A repeat run scored 74.8 % | [M3 report](eval/reports/test-final.md), [repeat](eval/reports/test-repeat.md) |
| Same set read by Azure Document Intelligence `prebuilt-invoice` | 47.2 % (95 % CI 38.8–55.9 %) | [M3 report](eval/reports/test-final.md) |
| Cost and speed per document (AI reading) | $0.0054, 2.9 s median | [M3](docs/milestones/M3.md#results-evidence) |
| Regression gate | a deliberate parsing bug dropped accuracy to 3.1 % and the PR was blocked | [PR #10](https://github.com/LomadaDharmateja/belegfluss/pull/10) |

The set is cleaner than real mail, so treat these numbers as an upper bound until consented pilot invoices exist.
Test results and screenshots per milestone: [M1](docs/milestones/M1.md#test-results-evidence),
[M2a](docs/milestones/M2a.md#test-results-evidence), [M2b](docs/milestones/M2b.md#test-results-evidence),
[M3](docs/milestones/M3.md#results-evidence).

## Project docs

[PLAN.md](PLAN.md) · [Project log](docs/PROJECT_LOG.md) · [Milestones](docs/milestones/) · [Costs](docs/COSTS.md) ·
[Third-party components](docs/THIRD_PARTY.md)

## Licence

[MIT](LICENSE) for the code in this repository. Third-party components keep their own licences ([docs/THIRD_PARTY.md](docs/THIRD_PARTY.md)).
Security reports: [SECURITY.md](SECURITY.md).
