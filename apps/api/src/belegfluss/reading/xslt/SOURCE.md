# Vendored: KoSIT XRechnung visualisation, step-1 transforms

These five XSLT files convert an EN 16931 invoice (UBL Invoice, UBL CreditNote or CII) into one intermediate
"semantic model" XML in which every value carries its business-term ID (`xr:id="BT-…"`) and its source path
(`xr:src`). Belegfluss reads that model instead of mapping both syntaxes itself
([ADR-0014](../../../../../../docs/decisions/0014-read-xml-with-official-kosit-transform.md)).

- Source: https://github.com/itplr-kosit/xrechnung-visualization, release `v2026-10-13`
  (asset `xrechnung-3.0.2-visualization-2026-10-13.zip`, SHA-256
  `ecf3913029218822ee4c90a86a3e23689768bf3568a061cf9bc742115e52264e`), folder `xsl/`
- Files: `ubl-invoice-xr.xsl`, `ubl-creditnote-xr.xsl`, `cii-xr.xsl`, `common-xr.xsl`, `functions.xsl`
- Licence: Apache License 2.0 (`LICENSE` in this folder, copied from the repository at the same tag). The project
  has no NOTICE file.
- Changes: none. Git normalises line endings to LF (`.gitattributes`), so byte checksums differ from the zip.
- Note from the stylesheets themselves: they assume a document that is valid against the source schema and
  Schematron; for invalid documents "the result is not defined". Belegfluss always shows the official validator
  result next to what it read.

To update: download the new release, replace the five files, run the 86-file test (`tests/test_reading_suite.py`)
and update this file.
