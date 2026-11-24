# ADR-0013: Multi-tenancy with organisation-scoped routes and one membership check

- **Status:** Accepted (2026-11-24)
- **Date:** 2026-11-23
- **Milestone:** M1

## Context

Invoices belong to a business (an *organisation*), not to a single login. Later, a business may have several
members, and an accountant may access several businesses (M6). One organisation seeing another's documents would
be the worst possible bug for this product.

## Options

1. **Organisation implied by the token or a header** (e.g. "current org" claim): short URLs, but the org is
   invisible in the request, and a missing check is easy to overlook.
2. **Organisation-scoped routes** `/orgs/{org_id}/...` with one FastAPI dependency `require_membership` on every
   such route. Data-access queries always filter by `org_id`.
3. **PostgreSQL row-level security (RLS)** from the start: strong defence in depth, but more complex sessions
   (setting the tenant per connection) and harder debugging at this stage.

## Decision

**Option 2 now, RLS as an extra layer in M9.**
- Every route that touches customer data has `{org_id}` in its path and depends on `require_membership`.
  Non-members get **404 `org.not_found`**, not 403, so the existence of other organisations is not revealed.
- Queries for a document filter by **both** `org_id` and `id`. A document ID from another organisation returns
  404, even under the caller's own org.
- On first sign-in a **personal organisation** is created, with the user as owner. Users are identified by token
  `tid` + `oid` (Microsoft: `oid` is the stable user ID in external tenants). Only these IDs are stored, no email
  or name (data minimisation).
- Uploads are deduplicated per organisation (`UNIQUE(org_id, sha256)`). The same file in two organisations is two
  documents.

## Consequences

- Isolation is tested explicitly (`tests/test_tenant_isolation.py`): list, read and upload across organisations
  all fail.
- Every new route must use the dependency. Reviewers check this, and M9 adds RLS as a safety net.
- Accountant access (M6) fits as additional memberships with role `accountant`.

## Sources

- Entra External ID, user identifier `oid`: https://learn.microsoft.com/en-us/entra/identity-platform/tutorial-single-page-app-react-sign-in-sign-out
