# ADR-0006: Deterministic processing first; the LLM only for unstructured documents

- **Status:** Accepted (2026-11-23)
- **Date:** 2026-11-23
- **Milestone:** M0 (implemented in M2, evaluated in M3)

## Context

Incoming documents are a mix: XRechnung (UBL/CII XML), ZUGFeRD (PDF + embedded XML), and plain PDFs, scans and
photos. The mix will last for years (small-amount invoices, Kleinunternehmer and foreign suppliers are exempt from
issuing e-invoices, see F11–F13). For hybrid invoices **the XML is legally leading** (F15). Validation is not a legal
prerequisite, but the results are what users act on (F16).

## Options

1. **LLM for everything**, including XML: one code path, but non-deterministic, costly, and it ignores the leading XML.
2. **OCR + templates/rules only:** cheap, but brittle across layouts and weak for photos.
3. **Azure Document Intelligence `prebuilt-invoice`:** purpose-built and supports German, but a fixed field set, a
   per-page cost, and less control.
4. **Deterministic first, LLM only where no structured data exists**, with code-based verification and human review.

## Decision

**Option 4.**
- XML (UBL/CII) and embedded ZUGFeRD XML are parsed deterministically. Both paths and the LLM path produce **one
  invoice model shaped by EN 16931 business terms** (BT-n), so checks and UI are shared.
- LLM extraction (Azure OpenAI, EU Data Zone, structured output against a JSON schema generated from our Pydantic
  model) is used only for documents without structured data.
- **Confidence comes from verification by code, not from the model's self-assessment:**
  - schema validity
  - formats (IBAN checksum, VAT-ID pattern, dates)
  - maths (net + VAT = gross per rate)
  - presence (the value appears in the PDF text layer)
  - plausibility (German VAT rates)

  Failed fields get "needs your check".
- **The LLM never** decides legal validity, writes SQL or changes data, calls tools, or sees other tenants' data.
  Invoice content is untrusted input (prompt injection), and the model's output is data only.
- Validator rule codes are explained with **curated DE/EN texts**. An LLM fallback for rare codes may use only the
  rule text and is labelled "AI-generated".
- The extractor is an interface. Document Intelligence can be added as an **eval baseline** in M3, and a
  self-hosted fine-tuned model (vLLM, OpenAI-compatible API) in M7.

## Consequences

- Structured invoices are exact, cheap and testable with official test data.
- Two input paths to maintain, but they converge early, at the shared model.
- The M3 evaluation measures field-level accuracy **and** how often verification catches wrong fields.
- LLM cost is limited to unstructured documents. Token usage per document is a tracked metric (M5).

## Sources

- BMF FAQ E-Rechnung, Q7, Q12a: https://www.bundesfinanzministerium.de/Content/DE/FAQ/e-rechnung.html
- Azure OpenAI deployment types (Data Zone): https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/deployment-types
- Azure OpenAI data privacy: https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/openai/data-privacy
