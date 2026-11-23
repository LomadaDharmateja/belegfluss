# ADR-0008: Test data — fetch official suites pinned, generate our own, never commit unlicensed samples

- **Status:** Accepted (2026-11-23)
- **Date:** 2026-11-23
- **Milestone:** M0 (implemented in M2, extended in M3)

## Context

Until real users exist we may only use official test invoices and synthetic data. Licences differ
([einvoicing.md §5](../research/einvoicing.md#5-test-data)):
- KoSIT XRechnung test suite: **Apache-2.0** (86 XML files in release 2026-08-31).
- ConnectingEurope EN 16931 examples: **EUPL-1.2**.
- Mustang test resources: Apache-2.0 repo, but some files come from third parties.
- akretion `factur-x` (Python): BSD, can generate ZUGFeRD/Factur-X PDFs.
- **FeRD ZUGFeRD sample invoices: no redistribution licence found.** FeRD's terms require AWV approval to reproduce
  texts; only schemas/Schematron are Apache-2.0.

## Options

1. **Vendor all sample files into git:** simple, but it mixes licences into our repo, FeRD samples would be a
   violation, and it bloats the repo.
2. **Synthetic data only:** licence-clean, but loses the value of official reference cases.
3. **Fetch pinned official releases by script, generate the rest ourselves.**

## Decision

**Option 3.**
- `scripts/fetch-test-data` downloads pinned release assets (URL + **SHA-256**) into a git-ignored folder
  (`testdata/external/`). CI caches it. A checksum mismatch fails the build.
- FeRD samples: usable **locally only** after accepting FeRD's terms. **Never committed**, never in CI.
- Our own fixtures (committed): small synthetic invoices we generate — ZUGFeRD via `factur-x`, plus edge cases
  (umlauts, multi-page, wrong VAT, duplicates, foreign currency, MINIMUM/BASIC-WL profiles).
- **Labelled PDF set for M3:** render the official XML test cases to PDF with the official KoSIT visualisation. The
  XML is the exact ground truth. Synthetic layouts, photos and scans are added for realism, and (later) real pilot
  invoices only with explicit consent.
- Attribution for fetched suites lives in `docs/THIRD_PARTY.md` (created in M2).

## Consequences

- Our repo stays licence-clean, and our own licence choice (decided before the repo goes public, M4) is unaffected.
- First CI run needs network access to GitHub releases (then cached).
- The eval set is reproducible: same pinned inputs and checksums.

## Sources

- https://github.com/itplr-kosit/xrechnung-testsuite
- https://github.com/ConnectingEurope/eInvoicing-EN16931
- https://github.com/ZUGFeRD/mustangproject
- https://github.com/akretion/factur-x
- https://www.ferd-net.de/en/ueber-uns/ressourcen-1/veroeffentlichungen/disclaimer-and-rights-of-use-zugferd
