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
