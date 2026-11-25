# ADR-0017: Correct only AI-read fields, approve with an explicit override for errors, export only approved documents

- **Status:** Accepted (2026-11-25)
- **Date:** 2026-11-25
- **Milestone:** M2b

## Context

After M2b's AI reading (ADR-0016), a person has to confirm or correct what the model read before anything reaches
the accountant. The rules that matter:
- **For e-invoices the XML is legally leading** (research F15). Changing its values in Belegfluss would make our copy
  differ from the legal document.
- **Some errors can't be fixed by the user.** A supplier's XRechnung that the official validator rejects stays
  rejected until the supplier sends a new one, but the user may still need to pass it on.
- **Every change to data must be traceable**, without putting invoice content into the audit log (ARCHITECTURE §7).
- **The export must be safe to open in German Excel** and must not alter the originals (ADR-0009).

## Options

**Who can correct what**
1. Free editing of every invoice: flexible, but it contradicts the leading XML.
2. **Corrections only for AI-read invoices.** XML and ZUGFeRD invoices are shown as read.

**Approval while errors are open**
1. Block approval until there are no errors: the supplier's rejected XML could never be handed over.
2. **Allow it with an explicit acknowledgement** that is recorded.

**What the export contains**
1. Every document in the period.
2. **Only approved documents**, so nothing unchecked reaches the accountant.

## Decision

**Option 2 in each case.**
- **Corrections** (`PATCH /orgs/{org}/documents/{id}/invoice`, `review.py`):
  - Correctable fields: number, issue and due date, currency, supplier name and VAT ID, IBAN, net, VAT, gross, due.
  - Unknown fields are rejected.
  - Only for `source = ai` and only while not approved; otherwise 409.
  - Each changed field becomes a `field_reviews` row (field, before, after, who, when). That row is customer data,
    org-scoped like the invoice.
  - The audit log records only `invoice.corrected`.
  - Then the code checks run again, without another AI call:
    - arithmetic, mandatory details, formats
    - the duplicate lookup (regression found in the walkthrough)
  - Kept from the AI run: the `BF-AI-READ` note, and presence hints for fields nobody corrected (the text layer isn't
    read again).
- **Approve** (`POST …/approve`):
  - Allowed from `ready` or `needs_review`.
  - With open **errors** it needs `acknowledge_errors: true` (the web shows a checkbox); otherwise 409
    `document.has_errors`.
  - Audit: `document.approved` or `document.approved_with_errors`.
  - Approved documents are never processed again by the worker.
  - `POST …/reopen` returns the document to `needs_review` for corrections.
- **Export** (`GET /orgs/{org}/export?from=&to=&lang=`, ADR-0009 implemented). The ZIP contains:
  - only approved documents, chosen by invoice date (upload date if there is none)
  - the originals, **byte-identical**, named `date_supplier_number.ext` (sanitised, made unique)
  - `summary.csv`: UTF-8 with BOM, `;` as separator, comma decimals, DD.MM.YYYY, German or English headers, net and
    VAT per rate (19 %, 7 %, other), totals, format, profile and the open finding codes
  - cells starting with `=`, `+`, `-` or `@` prefixed with `'` (CSV injection)

  Limits: 500 documents or 200 MB → 413 "choose a shorter period". Audit: `export.created`.
- **The ZIP is built on request and not stored.** That is less data to protect; the audit event records that an
  export happened. ARCHITECTURE had sketched an `EXPORT` table; it isn't needed yet.

## Consequences

- The legal XML is never contradicted. Wrong values in it are explained as findings, and the supplier has to fix
  them.
- An approval despite errors is visible in the audit log, and the CSV lists the open codes. The accountant sees the
  same warnings the user saw.
- `field_reviews` is the training and evaluation signal for later: which fields the model gets wrong (M3, M7).
- Corrections don't re-check the text layer. A corrected value that isn't printed on the document gets no new
  presence hint.
- Not yet: DATEV format (only if accountants ask, ADR-0009), automatic or scheduled exports (M6), per-line
  corrections (only header fields and totals today).

## Sources

- ADR-0006 (LLM boundary), ADR-0009 (export), ADR-0013 (tenancy), ADR-0016 (AI extraction)
- Research F15 (XML is leading for hybrid invoices): [einvoicing.md](../research/einvoicing.md)
- CSV injection: https://owasp.org/www-community/attacks/CSV_Injection
