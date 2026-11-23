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
