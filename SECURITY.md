# Security policy

Belegfluss handles invoices, which contain personal and business data. Reports about security problems are very
welcome.

## Reporting a vulnerability

- Please use GitHub's **private vulnerability reporting** ("Security" tab → "Report a vulnerability"), not a public
  issue.
- Describe what you found and how to reproduce it. Don't include real invoices, personal data or credentials. Test
  data from the official XRechnung test suite or invented data is enough.
- Please don't test against other people's data or run load tests against the live demo.
- You get an answer within a few days. A fix and its disclosure are agreed with you.

## What to expect in this repository

- **No credentials exist in this repository or its pipelines.**
  - Azure is reached with managed identities.
  - GitHub Actions signs in to Azure with OIDC.
  - Database passwords, storage keys and registry passwords are switched off
    ([ADR-0021](docs/decisions/0021-keyless-runtime-shared-free-tier-database.md)).
- **Every pull request is scanned for secrets (gitleaks).** Every release image is scanned for vulnerabilities
  (Trivy) and gets an SBOM ([ADR-0022](docs/decisions/0022-release-pipeline-build-once-deploy-dev.md)).
- **Supported version:** only the current `main` branch and the deployed version are supported.
