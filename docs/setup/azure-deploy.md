# Setup: Belegfluss on Azure (M4a, dev)

> How the dev environment was created, and how to recreate or remove it. Decisions:
> [ADR-0020](../decisions/0020-terraform-layout-state-and-who-applies.md) (stacks, who applies what),
> [ADR-0021](../decisions/0021-keyless-runtime-shared-free-tier-database.md) (keyless, shared free-tier database,
> region), [ADR-0022](../decisions/0022-release-pipeline-build-once-deploy-dev.md) (release pipeline).
> **Cost:** about €0.50–2 a month in the first year ([COSTS.md](../COSTS.md)).

## What you need

- **Azure CLI**, signed in as the owner: `az login --tenant <tenant-id>` (MFA,
  [azure-openai-dev.md](azure-openai-dev.md)).
- **GitHub CLI**, signed in: `gh auth login`.
- **Terraform 1.17.2** on `PATH`, official build, SHA-256 checked.
- **Docker**, only for the database role script.

## Order (once)

Every step prints what it does. Steps 2–5 change Azure or GitHub: run them only after reading the plan.

1. **Variable files** (read-only):
   - `scripts/azure/m4-tfvars.ps1` writes `infra/bootstrap/bootstrap.auto.tfvars` and
     `infra/shared/shared.auto.tfvars`.
   - Both are git-ignored and contain identifiers and the budget email, no secrets.
2. **Bootstrap:**
   - `cd infra/bootstrap; terraform init; terraform plan -out bootstrap.tfplan; terraform apply bootstrap.tfplan`
   - Creates the resource groups, the state storage (keys off), and the deploy identity per environment with its
     OIDC trust.
   - State stays local on purpose (see ADR-0020).
3. **Shared:**
   - `cd infra/shared; terraform init -backend-config="storage_account_name=<terraform output -raw tfstate_account in bootstrap>"`
   - then `plan -out shared.tfplan`, `apply shared.tfplan`
   - **Creates** the registry, the PostgreSQL server (Entra only) and the app identities.
   - **Grants** the pipeline's limited rights.
   - **Imports** the M1 budget and the M2b/M3 AI resources.
4. **Database roles:** `scripts/azure/db-roles.ps1 -NameSuffix <suffix>`.
   - Creates `belegfluss_dev` and the app identity's role, and revokes `CONNECT` from `PUBLIC`.
   - Opens the firewall for your IP only while it runs.
5. **GitHub environment:** `scripts/azure/github-env.ps1 -NameSuffix <suffix>`.
   - Creates environment `dev` (main only). Azure IDs and resource names become environment **secrets**, only so
     that public logs mask them; sign-in IDs become variables. None is a credential (ADR-0023).
6. **First deploy:** merge to `main` (or run **deploy** manually from `main`). The pipeline then runs, in order:
   - tests, build, scan, push
   - `terraform apply` of `infra/environment`
   - migrations, image updates, smoke test
7. **Sign-in redirect:** add the dev web address (`https://web.<environment domain>`, printed by the pipeline) as a
   **SPA redirect URI** of `belegfluss-web` in the External ID tenant
   ([entra-external-id.md](entra-external-id.md)).

## Every day

- A merge to `main` deploys to dev.
- **Infrastructure changes:**
  - `infra/environment`: applied by the pipeline.
  - `infra/shared`, `infra/bootstrap`: applied by you (steps 2–3).
- **Wake-up time:** the first request after a quiet period wakes the app (cold start, numbers in M4a.md).

## Removing everything

Data first (it has `prevent_destroy`), so this needs deliberate steps:
1. Delete the dev resource group: `az group delete -n rg-belegfluss-dev`. This removes the apps, the storage with
   documents, and the logs.
2. Remove `prevent_destroy` from the database server in `infra/shared/main.tf`, then `terraform destroy` in
   `infra/shared`. This removes the server (both databases), the registry, the identities and the grants.
   It also removes the imported budget and AI resources: remove those from state first (`terraform state rm`) if
   you want to keep them.
3. `terraform destroy` in `infra/bootstrap` (after removing `prevent_destroy` on the state storage).
