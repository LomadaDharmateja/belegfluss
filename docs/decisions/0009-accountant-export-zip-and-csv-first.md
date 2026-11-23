# ADR-0009: Accountant export — ZIP of originals + CSV summary first

- **Status:** Accepted (2026-11-23)
- **Date:** 2026-11-23
- **Milestone:** M0 (implemented in M2 basic, M6 automated)

## Context

Users hand approved invoices to their accountant. Facts checked
([einvoicing.md §6](../research/einvoicing.md#6-accountant-export)):
- **DATEV-Format** is a public CSV spec (`EXTF_…csv`, header + column titles + rows). A *Buchungsstapel* needs the
  accountant's Berater/Mandant numbers and **Konto/Gegenkonto** (chart-of-accounts numbers) on every row.
- DATEV interfaces can be built without a partnership, but DATEV reviews them technically. API data services exist,
  but their terms and costs were not verified.
- **DATEV Unternehmen online** already receives and processes e-invoices for DATEV clients.
- The original e-invoice (at least its XML) must be kept unaltered for 8 years (F18, F19), so the originals are what
  the accountant ultimately needs.

## Options

1. **ZIP of originals + CSV summary:** works with every accountant and tool, low effort, keeps the legal documents
   intact.
2. **DATEV-Format EXTF Buchungsstapel:** saves the accountant typing, but requires choosing accounts (bookkeeping, a
   non-goal) and their numbers.
3. **DATEV API integration:** deepest integration, but a review process, unknown cost and high effort.

## Decision

**Option 1 first.**
- ZIP contains the files **exactly as received** (byte-identical, names = date + supplier + number, sanitised) and
  `summary.csv`: one row per invoice (supplier, VAT ID, invoice number, dates, net/VAT/gross per rate, currency,
  format/profile, status, open findings).
- CSV in UTF-8 with BOM, semicolon separator and comma decimals, so it opens correctly in German Excel. It is tested
  with umlauts.
- Option 2 only if accountant interviews ask for it, as an optional mapping configured *by the accountant*
  (new ADR). Option 3 not before real demand from pilot users.

## Consequences

- Export is simple, testable and format-neutral.
- Accountants still do the booking. That is fine: bookkeeping is out of scope.
- The accountant interview (user-interviews.md §6) decides whether option 2 is worth building in M6.

## Sources

- DATEV-Format: https://developer.datev.de/de/file-formats/details/datev-format/getting-started
- DATEV Marktplatz (partnership/review): https://www.datev.de/web/de/berufsgruppenuebergreifend/ueber-datev/portfolio/oekosystem/partnering/datev-marktplatz
- DATEV Unternehmen online: https://www.datev.de/web/de/unternehmen/loesungen/rechnungswesen/buchfuehrung/buchfuehrung-effizienter-gestalten/durchgaengig-digitale-kaufmaennische-prozesse
