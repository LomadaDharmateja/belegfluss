# ADR-0010: Web i18n with next-intl, language not in the URL

- **Status:** Accepted (2026-11-24)
- **Date:** 2026-11-23
- **Milestone:** M1

## Context

The app is bilingual (German/English) from day one. Almost all pages are behind a login, so search engines don't
index them. Users should get their browser's language on the first visit and be able to switch, and the choice
should persist. Next.js 16 App Router renders on the server and the client, so the i18n library must work in
both.

## Options

1. **next-intl with i18n routing** (`/de/...`, `/en/...`): good for SEO and shareable language-specific links, but
   it adds a `[locale]` route segment and middleware we don't need behind a login.
2. **next-intl without i18n routing**: the locale comes from a cookie, otherwise from the browser's
   `Accept-Language`, set in `src/i18n/request.ts`. Messages are type-checked through `AppConfig` augmentation.
3. **i18next / react-i18next**: very popular, but App Router server-component support needs more manual wiring.

## Decision

**Option 2.**
- `src/i18n/request.ts` chooses the locale: the cookie if set, otherwise `negotiateLocale()` (browser preference,
  default German).
- `setLocale()` is a server action that sets the cookie for one year. The language switch calls it and refreshes.
- Message keys are type-checked (`src/global.d.ts`).
- A unit test enforces that `de.json` and `en.json` have the same keys and placeholders, and that every API error
  code has a message.
- API errors carry stable codes (e.g. `upload.too_large`). Translation happens only in the web app.

## Consequences

- No locale in URLs. If public marketing pages are added later, they can use routing in their own route group.
- Every page reads a cookie, so pages are rendered per request (no static pre-rendering). That's fine for an app
  behind a login.
- Next.js 16 "Cache Components" is opt-in and **not** enabled. Next.js says it becomes the default in the next
  major version. Migrating is a planned follow-up (read the bundled `cacheComponents` docs first).
- German UI uses the informal "du" (decided by the owner on 2026-11-24).

## Sources

- next-intl App Router setup and TypeScript augmentation: https://next-intl.dev/docs/getting-started/app-router,
  https://next-intl.dev/docs/workflows/typescript
- Next.js 16 `cacheComponents` (bundled docs, `node_modules/next/dist/docs/.../cacheComponents.md`)
