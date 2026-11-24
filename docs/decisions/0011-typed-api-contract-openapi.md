# ADR-0011: The API contract is the OpenAPI schema, and the web client is generated from it

- **Status:** Accepted (2026-11-24)
- **Date:** 2026-11-23
- **Milestone:** M1

## Context

The web app (TypeScript) calls the API (Python). If both sides describe requests and responses by hand, they drift
apart silently, and the bug shows up only at runtime. FastAPI already generates an OpenAPI 3.1 schema from the
Pydantic models.

## Options

1. **Hand-written TypeScript client and types:** no tooling, but drift is guaranteed over time.
2. **orval:** generates clients and React hooks. Powerful, but more generated code and configuration.
3. **openapi-typescript + openapi-fetch:** generates *types only* (`schema.d.ts`). `openapi-fetch` is a small typed
   wrapper around `fetch` (its README says 6 kB; the 0.17 build measured 17 kB raw, 4.4 kB gzipped), with
   middleware for the auth header.

## Decision

**Option 3.**
- `python -m belegfluss.openapi_export apps/web/src/api/openapi.json` writes the schema (sorted keys, LF line
  endings).
- `pnpm gen:api` turns it into `src/api/schema.d.ts`. Both files are committed and reviewed in PRs, so contract
  changes are visible.
- **Two drift checks:**
  - API test `test_committed_openapi_matches_the_api` fails if the API changed without re-exporting
  - web CI regenerates the types and fails on `git diff`
- An `openapi-fetch` middleware adds `Authorization: Bearer <token>`. Errors use one `ErrorBody {code, message}`
  shape.

## Consequences

- A typo in a path, parameter or field name is a compile error in the web app.
- Changing the API takes one extra command (`openapi_export` + `gen:api`). CI reminds you if it's forgotten.
- Multipart uploads are typed as `string` by the generator. The client sends the real `File` through a
  `bodySerializer`, which is documented in `src/api/client.ts`.

## Sources

- https://openapi-ts.dev/introduction, https://openapi-ts.dev/openapi-fetch/middleware-auth
- https://fastapi.tiangolo.com/how-to/extending-openapi/
