# Architecture Decision Records

Format and rules: [ADR-0001](0001-record-architecture-decisions.md).

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record decisions as short ADRs | Accepted |
| [0002](0002-plain-monorepo-layout.md) | Plain-folder monorepo with native tooling (uv, pnpm) | Accepted |
| [0003](0003-auth-entra-external-id.md) | Sign-in with Microsoft Entra External ID from M1 (EU data location confirmed in M1) | Accepted |
| [0004](0004-jobs-storage-queue-with-db-status.md) | Background jobs: Azure Storage Queue + DB status as source of truth | Accepted |
| [0005](0005-validator-as-internal-daemon.md) | Official KoSIT validator as an internal-only daemon container | Accepted |
| [0006](0006-deterministic-first-llm-boundary.md) | Deterministic first; LLM only for unstructured documents | Accepted |
| [0007](0007-container-apps-first-aks-later.md) | Container Apps in M4, AKS in M8 (time-boxed) | Accepted |
| [0008](0008-test-data-sourcing-and-licensing.md) | Test data: fetch pinned official suites, generate our own, never commit unlicensed samples | Accepted |
| [0009](0009-accountant-export-zip-and-csv-first.md) | Accountant export: ZIP of originals + CSV summary first | Accepted |
| [0010](0010-web-i18n-next-intl-without-url-locale.md) | Web i18n with next-intl, language not in the URL | Accepted |
| [0011](0011-typed-api-contract-openapi.md) | OpenAPI is the contract; web client types are generated, drift fails CI | Accepted |
| [0012](0012-persistence-sync-sqlalchemy-and-real-db-tests.md) | Sync SQLAlchemy 2.1 + psycopg 3 + Alembic; tests against real PostgreSQL | Accepted |
| [0013](0013-tenancy-org-scoped-routes.md) | Organisation-scoped routes with one membership check (RLS in M9) | Accepted |
| [0014](0014-read-xml-with-official-kosit-transform.md) | Read e-invoice XML with the official KoSIT step-1 transform (Saxon), not own parsers | Accepted |
| [0015](0015-store-results-as-summary-columns-plus-jsonb.md) | Store read invoices as summary columns + JSONB; findings in their own table | Accepted |
| [0016](0016-ai-extraction-azure-openai-verified-by-code.md) | Plain PDFs and photos read by Azure OpenAI gpt-5.4-mini (EU Data Zone, keyless), verified by code, always reviewed | Proposed |
| [0017](0017-review-approval-and-export.md) | Correct only AI-read fields; approve with an explicit override for errors; export only approved documents | Proposed |
