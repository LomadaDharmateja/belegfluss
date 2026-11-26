# ADR-0022: Release pipeline: test, build once, scan, push, deploy dev, smoke test

- **Status:** Accepted (2026-11-26)
- **Date:** 2026-11-26
- **Milestone:** M4a (prod and the manual approval follow in M4b)

## Context

Until now CI tested on every pull request and nothing was deployed. M4 needs a path from a merged commit to a running
app that is repeatable, needs no secret, and doesn't let a broken or vulnerable image through.

## Options

1. **Deploy with `terraform apply` only, images as Terraform variables.** One tool, but every image change is an
   infrastructure change. Plans become noisy, and a slow apply blocks every release.
2. **Build separately per environment.** Simple, but prod would run different bytes from what was tested in dev.
3. **Build once per commit and promote the same digest:**
   - Terraform owns the infrastructure.
   - The pipeline deploys images by digest with `az containerapp update`.
   - Terraform ignores image changes.

## Decision

**Option 3.** `.github/workflows/deploy.yml` runs on every push to `main`:

1. **Tests:** the pull-request workflows are called as reusable workflows: api, web, eval gate, compose-smoke,
   secret scan, infra. On `main` they run only here, so a deploy always waits for all of them.
2. **Build:** the API/worker, web and validator images, tagged with the commit. Base images are pinned by digest;
   Dependabot proposes updates.
3. **Scan:**
   - Trivy fails the run on HIGH or CRITICAL vulnerabilities that have a fix.
   - A CycloneDX SBOM per image is kept as an artifact.
   - Trivy is a pinned binary with a verified checksum, not a third-party action.
4. **Push** to the registry with an Entra sign-in (`az acr login`, no registry password). The digests become the job
   outputs.
5. **Deploy to dev** (GitHub environment `dev`, OIDC):
   - `terraform plan` and `apply`
   - the `migrate` job with the new image (waits for success)
   - every app and job switched to the new digests
6. **Smoke test** (`scripts/deploy/smoke.sh`):
   - API `/health` 200 and `/me` 401
   - CORS allows exactly the web origin
   - web answers in German and English
   - the validator has no external ingress; the worker has none at all
   - wake-up times printed (cold start)

**M4b:** environment `prod` with a required reviewer; the same digests and steps.

## Consequences

- **What runs in prod is what was scanned and smoke-tested in dev:** the same bytes, by digest.
- **A new HIGH vulnerability with a fix blocks releases until the base image or dependency is updated.** That is
  intended; Dependabot keeps it moving.
- **Migrations run before the new images go live:** they must stay backward-compatible with the running version
  (expand, then contract).
- **Deploys are serialised** (`concurrency: deploy`) and never cancelled halfway.

## Sources

- Reusable workflows: https://docs.github.com/en/actions/sharing-automations/reusing-workflows
- `az containerapp update` / job commands: https://learn.microsoft.com/en-us/cli/azure/containerapp
- Trivy: https://trivy.dev/latest/docs/ (v0.76.2, checksum from the release's `checksums.txt`)
- OIDC for azurerm: https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/guides/service_principal_oidc
