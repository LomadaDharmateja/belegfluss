# ADR-0015: Store read invoices as summary columns plus the full model as JSONB; findings in their own table

- **Status:** Accepted (2026-11-24)
- **Date:** 2026-11-24
- **Milestone:** M2a

## Context

The worker turns a document into an invoice model (ADR-0014) and a list of findings (validator + our checks). The
app needs to:
- list documents with supplier, number, date and amount
- find semantic duplicates (same seller + invoice number)
- show the full invoice on a detail page
- export a CSV summary later (M2b)

The model will change: XRechnung 4.0 is expected in 2027, and the LLM path (M2b) adds fields. All of it is derived
data: the original file stays unchanged in Blob storage, so results can be recomputed by a newer pipeline version.

## Options

1. **Fully normalised tables** (invoices, parties, addresses, lines, VAT breakdown): every field queryable, but many
   tables and a migration for every model change, for data the app mostly shows as a whole.
2. **Everything in one JSONB column:** flexible, but list queries, sorting and duplicate checks would dig inside
   JSON.
3. **Summary columns + JSONB:** one `invoices` row per document. Typed columns hold only what is queried or sorted
   (number, issue date, seller name and VAT ID, currency, net/VAT/gross/due totals, validation outcome). The
   complete model is stored as JSONB, validated by the Pydantic model on the way in and out. Findings get their own
   table (one row per finding), because they are listed, counted by severity and later reviewed one by one.

## Decision

**Option 3.**
- `invoices`:
  - one row per document (`document_id` unique)
  - `org_id`, `source` (xml/zugferd), `syntax`, `specification_id` (BT-24)
  - summary columns as above, amounts as `NUMERIC` without fixed scale, so values are stored exactly as read
  - `model` JSONB
  - `pipeline_version`, plus the validator outcome, engine, configuration and scenario
- `findings`:
  - `origin` (`kosit` or `belegfluss`), `code`, `severity` (error/warning/info)
  - `message`: the official rule text, for validator findings only. Our own codes are translated in the web app.
  - `location` (XPath), `business_terms` (e.g. `["BT-112"]`), `params` (values for the message)
- `documents` gains `status_changed_at` (the sweeper finds stuck documents) and `failure_reason` (a stable code).
- Re-processing deletes and rewrites a document's invoice and findings in one transaction (idempotent, ADR-0004).

## Consequences

- Lists and duplicate checks are plain SQL on typed columns. The detail page reads one JSONB value.
- A model change usually needs no migration. Old rows keep their `pipeline_version` and can be re-processed.
- JSONB contents are not constrained by the database. The Pydantic model is the schema, and tests write and read it
  back.
- Every table with customer data still carries `org_id` (ADR-0013).

## Sources

- PostgreSQL JSONB and NUMERIC: https://www.postgresql.org/docs/18/datatype-json.html,
  https://www.postgresql.org/docs/18/datatype-numeric.html
