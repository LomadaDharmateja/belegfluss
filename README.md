# Belegfluss

**A bilingual (German / English) e-invoice inbox for freelancers and small businesses in Germany.**

> **Status: M0 — research & design.** There is no application code yet. See [PLAN.md](PLAN.md) for the roadmap.

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

## Design

- [Architecture](docs/ARCHITECTURE.md): components, data flow, where the LLM is and isn't used, Azure services,
  security/GDPR boundaries
- [Decisions (ADRs)](docs/decisions/README.md)
- [E-invoicing research](docs/research/einvoicing.md): verified facts with official sources, and a hands-on run of
  the official validator ([evidence](docs/research/evidence/validator-smoke-2026-11-23.txt))
- [User interview guide](docs/research/user-interviews.md)

Planned stack: Next.js + TypeScript, FastAPI + PostgreSQL, KoSIT validator, Azure (Container Apps → AKS, Azure
OpenAI in the EU data zone, Blob/Queue, Key Vault, Managed Identity, Entra External ID), Terraform, GitHub Actions.

## How to run

Nothing to run yet. Local setup arrives with M1 (Docker Compose).

## Results

None yet. Every number published here will link to evidence (test output, eval report or dashboard).

## Project docs

[PLAN.md](PLAN.md) · [Project log](docs/PROJECT_LOG.md) · [Milestones](docs/milestones/) · [Costs](docs/COSTS.md)

## Licence

To be decided before the repository is made public (planned with M4).
