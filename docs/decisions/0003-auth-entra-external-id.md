# ADR-0003: Sign-in with Microsoft Entra External ID from M1

- **Status:** Proposed (conditional, see "Condition")
- **Date:** 2026-11-23
- **Milestone:** M0 (implemented in M1)

## Context

Users are freelancers and small businesses (and later their accountants). They sign in with email or a social
account. We must not become a password store, because a breach would be serious for an app holding financial
documents. The project is Azure-based, and Entra ID is part of the planned stack.

Facts checked (2026-11-23):
- Entra External ID is Microsoft's current CIAM solution. **Azure AD B2C has not been sold to new customers since
  1 May 2025.** ([overview](https://learn.microsoft.com/en-us/entra/external-id/customers/overview-customers-ciam),
  [B2C](https://learn.microsoft.com/en-us/azure/active-directory-b2c/overview))
- **Free for the first 50,000 monthly active users** ([pricing](https://azure.microsoft.com/en-us/pricing/details/microsoft-entra-external-id/)).
- Sign-in methods include email + password, email one-time passcode, Google, Apple, Facebook and custom OIDC.
- The tenant's country/region is chosen at creation and **cannot be changed later**. For EU tenants Entra stores
  most data in the EU Data Boundary, but external tenant data locations "may differ"
  ([data residency](https://learn.microsoft.com/en-us/entra/fundamentals/data-residency)).
- SPA pattern: MSAL in the browser gets an access token, and the API validates signature, issuer, audience and expiry
  ([protected web API](https://learn.microsoft.com/en-us/entra/identity-platform/scenario-protected-web-api-overview)).

## Options

1. **Entra External ID:** Azure-native, free at our scale, no credentials stored by us. Vendor-specific setup;
   local development needs internet access.
2. **Own auth** (fastapi-users, or Auth.js with email magic links): works offline and gives full control, but we
   own the credential/token security, and it builds no Azure identity experience.
3. **Keycloak, self-hosted:** open source and EU-hosted by us, but one more stateful service to run, patch and back
   up.
4. **Auth0 / Clerk:** easiest developer experience, but US vendors (extra GDPR assessment) and cost at scale.

## Decision

**Option 1, Entra External ID, from M1** (no throw-away auth code):
- Web: MSAL React (authorisation code flow with PKCE) requests an access token for the API scope.
- API: validates the JWT with the tenant's published signing keys (JWKS). User identity = token subject. Our own DB
  maps it to organisations and roles (owner, member, accountant).
- Tests: tokens signed by a local test key, with the API configured to trust that key **only in the test settings**.
  No "skip auth" switch in application code.

**Condition:** when creating the external tenant in M1 we choose Germany as country/region and record where its data
is stored. If the data location is outside the EU, this ADR is superseded (fallback: Keycloak in our EU
environment).

## Consequences

- No password database, no password-reset emails to build.
- Local development needs the dev tenant (free) and internet. CI does not (test tokens).
- Accountant multi-org access is handled in our DB (memberships), not in the identity provider.
- Lock-in to Entra is limited: the API only depends on standard OIDC/JWT validation.

## Sources

Linked inline above (all read 2026-11-23).
