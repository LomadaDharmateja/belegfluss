# ADR-0018: Evaluate AI reading on a versioned labelled set; gate pull requests by replaying recorded answers

- **Status:** Proposed (2026-11-25)
- **Date:** 2026-11-25
- **Milestone:** M3

## Context

M2b reads plain PDFs and photos with gpt-5.4-mini (ADR-0016). It was checked on 4 live samples, which is no
accuracy number. M3 must answer three questions with evidence:
1. How often is a document read completely right?
2. How often does verification by code catch a wrong reading?
3. What does a document cost, and how long does it take?

It must also stop code changes from silently making reading worse. Constraints:
- **No real invoices** before users exist (CLAUDE.md §9).
- Test data must be **licence-clean** (ADR-0008).
- CI must stay **free of paid calls and secrets** on pull requests.

## Options

**Labels**
1. Hand-labelled real invoices: realistic, but none are allowed yet.
2. Synthetic only: exact labels, but one source of layouts (ours).
3. **Official KoSIT test suite rendered with the official KoSIT PDF view, plus synthetic layouts, plus photo/scan
   variants.** The official XML gives exact labels for layouts we didn't design.

**Gate**
1. Live model calls on every pull request: real, but costs money, is slow and flaky, and needs Azure access in
   pull requests.
2. **Replay recorded answers** through the current code: free, deterministic, no secrets. It catches parsing,
   mapping and verification regressions. Prompt or model changes are caught by a **fingerprint** that forces a new
   live run.

**Where the rendered files live**
1. In git: simplest, but about 17 MB of binaries in the history.
2. Local only: not reproducible.
3. **A private GitHub release asset**, checked by SHA-256 like the official suite.

## Decision

**Option 3 for labels, option 2 for the gate, option 3 for files.**
- **Dataset `eval-dataset-v1`: 206 documents.**

  | Part | How it's made | Count |
  |---|---|---|
  | Official | 86 KoSIT suite files, official `xr-pdf.xsl` + Apache FOP 2.12, four looks (de/en, normal/tabular) | 86 |
  | Synthetic | Seeded fictional invoices in 4 templates (letter, Handwerk, English freelancer, till receipt), Chromium; covers mixed rates, reverse charge, Kleinunternehmer, receipts, foreign currency, credit note, partial payment, terms without a date, documents over the 3-page limit | 80 |
  | Variants | 20 phone photos and 20 image-only scans of page 1 | 40 |

  - **Split by source document**, so variants stay with their source: dev 79 / test 127.
  - **The test split is used once per prompt version, never for tuning.**
  - `eval/dataset/manifest.json` holds the labels and the SHA-256 of every file. Its hash is the dataset version.
- **Metrics** (`eval/src/belegfluss_eval/metrics.py`):
  - **14 fields:** number, dates, currency, seller name and VAT ID, buyer, IBAN, net, VAT, gross, due, VAT
    breakdown, line count.
  - Compared strictly after normalising notation (case, spaces, amounts to the cent).
  - **Document accuracy** = all export fields right (line count reported separately: the AI sees 3 pages at most),
    with a 95 % Wilson interval.
  - **Catch rate / false alarms:** counted only on reading-verification findings (formats, sums, presence,
    VAT-rate plausibility), not on mandatory-detail hints about the invoice itself.
  - Two documented conventions:
    - "no VAT" written as 0.00 or left out is the same
    - placeholders of the official test files ("[Seller name]") count as empty
- **Runs** record every answer, the text layer and the usage. The header records the model, effort, prompt
  fingerprint, dataset version and the date used for plausibility checks (so replays are deterministic).
- **Gate** (`eval` workflow, every pull request touching `apps/api/**` or `eval/**`). It fails if:
  - any field, the document accuracy or the catch rate is lower than `eval/baseline.json`
  - the dataset changed
  - the prompt fingerprint of the current code differs from the baseline's
- **Live runs:** locally with `az login`, or from GitHub on demand (`eval-live`, ADR-0019), each with a cost cap.

## Consequences

- Every accuracy claim points to a committed report, a dataset version and a prompt version (`eval/reports/`).
- A prompt or model change is a deliberate act: new live run, new baseline, visible diff.
- The replay cannot see model drift between runs; a live re-run on demand can.
- **Limits:** official renders and synthetic layouts are cleaner than real mail. Numbers here are an upper bound
  for real-world accuracy until consented pilot invoices exist (M5). `field_reviews` will then show real errors.
- The numbers depend on our strict definitions; the report states them next to every figure.

## Sources

- KoSIT XRechnung visualisation v2026-10-13 (`xr-pdf.xsl`, Apache-2.0):
  https://github.com/itplr-kosit/xrechnung-visualization
- Apache FOP 2.12: https://xmlgraphics.apache.org/fop/download.html
- Playwright for Python (Chromium printing): https://playwright.dev/python/docs/intro
- Wilson score interval: Wilson, E. B. (1927), *Journal of the American Statistical Association* 22(158), 209–212
