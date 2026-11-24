# ADR-0014: Read e-invoice XML with the official KoSIT step-1 transform (via Saxon), not our own mapping

- **Status:** Proposed
- **Date:** 2026-11-24
- **Milestone:** M2a

## Context

E-invoices come in two XML syntaxes, UBL (Invoice and CreditNote) and UN/CEFACT CII, also embedded in ZUGFeRD PDFs.
Both carry the same EN 16931 business terms (BT-1 invoice number, BT-112 gross total, …) at different paths. The rest
of Belegfluss (checks, UI, export, later the LLM path) should work on **one** invoice model.

KoSIT's official visualisation (Apache-2.0) has a first step that converts UBL or CII into one intermediate XML in
which every value carries its business-term ID (`xr:id="BT-112"`) and its source path (`xr:src`). It is XSLT 2.0,
so it needs Saxon. The stylesheets say they assume a valid document; for invalid documents "the result is not
defined".

## Options

1. **Our own `lxml` mapping for UBL and CII:** no extra runtime, full control. But two mappings of ~50 business
   terms plus groups to write and maintain, and every XRechnung release (4.0 is expected in 2027) means checking
   both again.
2. **Official step-1 transform via `saxonche`** (SaxonC-HE 13.1, MPL-2.0, official Saxonica wheel with Python 3.14
   builds for Windows and Linux): one model for both syntaxes, maintained by the standard's publisher, including
   source paths. Costs a 35 MB wheel and an XSLT engine in the worker.
3. **Use the validator's output as the reader:** not possible. The validator reports findings, not values.

## Spike (2026-11-24)

Evidence: [`xslt-spike-2026-11-24.txt`](../research/evidence/xslt-spike-2026-11-24.txt), script next to it.
- All **86 files** of the official test suite 2026-08-31 (45 UBL invoices, 41 CII) transformed with **0 errors**.
- BT-106, BT-109, BT-110, BT-112 and BT-115 in the output equal the values read from the source XML with
  independent XPaths in all 86 files (**0 mismatches**).
- Median 5 ms per file, maximum ~50–70 ms; compiling the three stylesheets takes ~0.2 s once per process.
- The suite contains **no UBL credit notes**. The credit-note stylesheet needs our own test file.

## Decision

**Option 2.**
- The five step-1 stylesheets are **vendored unchanged** in `apps/api/src/belegfluss/reading/xslt/` with the
  Apache-2.0 licence and a source note (release, checksum). They are compiled once per worker process.
- The worker turns the intermediate XML into our Pydantic invoice model by business-term ID, so the model's field
  names follow EN 16931 (BT-n).
- **Untrusted input is checked before Saxon sees it:**
  - parsed with `lxml` without network access or entity resolution
  - documents with a `DOCTYPE` are rejected (e-invoices never need one)
  - must be UTF-8
  - the root element decides the stylesheet: UBL Invoice, UBL CreditNote or CII; anything else is "not an
    e-invoice"
- Because the transform is undefined for invalid documents, Belegfluss **always shows the official validator result
  next to what it read**, and tests cover deliberately broken invoices.

## Consequences

- One reader for UBL and CII. XRechnung 4.0 means swapping in KoSIT's next release and re-running the 86-file test.
- `xr:src` paths are kept, so a field shown to the user can be traced to the source XML.
- Worker image grows by ~35 MB (saxonche). MPL-2.0 is file-level copyleft: we don't modify Saxon, so our own code is
  unaffected. The notice goes into `docs/THIRD_PARTY.md`.
- If Saxon ever causes trouble, the lxml mapping (option 1) remains possible behind the same `read_invoice()`
  function, and the 86-file test checks it.

## Sources

- KoSIT visualisation: https://github.com/itplr-kosit/xrechnung-visualization (release v2026-10-13, Apache-2.0)
- SaxonC-HE licence (MPL-2.0): https://www.saxonica.com/html/saxon-c/index.html
- saxonche on PyPI: https://pypi.org/project/saxonche/
