# ADR-0020: Terraform in three stacks; the owner applies shared parts, the pipeline applies environments

- **Status:** Proposed (2026-11-26)
- **Date:** 2026-11-26
- **Milestone:** M4a

## Context

M4 puts every Azure resource into Terraform (azurerm 5.15, Terraform 1.17). Three questions:
- where the state lives
- how dev and prod share code without sharing risk
- who may change what

Constraints:
- no secrets anywhere (ADR-0019)
- a €10/month budget
- one owner, who is also the only reviewer

## Options

1. **One root module for everything,** applied by the pipeline. Simple, but the pipeline then needs rights over
   everything, including the database server and budget both environments depend on.
2. **Terraform workspaces** for dev/prod in one state backend container. Less code, but one identity can reach both
   states, and a wrong workspace selection hits prod.
3. **Three stacks with separate state containers:**
   - `bootstrap` (once)
   - `shared` (rarely)
   - `environment` (per environment, via tfvars and its own state key)

## Decision

**Option 3.**

| Stack | Contents | Applied by | State |
|---|---|---|---|
| `infra/bootstrap` | resource groups; state storage account (keys off, versioning, soft delete); one deploy identity per environment with its federated credential (GitHub's immutable subject) and roles | owner, once | local, by design (it creates the remote storage); every name derives from `name_suffix`, so it can be rebuilt with `terraform import` |
| `infra/shared` | container registry; PostgreSQL server; app identities; the pipeline's extra permissions; budget; imported M2b/M3 AI resources | owner, `az login` | `tfstate-shared` |
| `infra/environment` | logs, Container Apps environment, storage, apps, jobs | pipeline, as that environment's deploy identity | `tfstate-<env>` |

**Pipeline identity rights (least privilege), for example `id-belegfluss-deploy-dev`:**
- **Contributor** on `rg-belegfluss-dev` only.
- **Reader** on `rg-belegfluss-shared`, for data sources.
- **AcrPush** on the registry.
- **Managed Identity Operator** on its own app identity, so it can attach that identity to apps.
- **Blob Data Contributor** on its own state container only.
- **Role Based Access Control Administrator** on its resource group, with an **ABAC condition**:
  - it may assign or remove only Storage Blob Data Contributor, Storage Queue Data Contributor and Cognitive
    Services OpenAI User
  - and only to its own app identity
- **Its trust:** deploy identities live in the state resource group, not in their environment's group, so a
  pipeline can't change its own trust.

**Other rules:**
- **Not in the repository:** resource names, the subscription and role-assignment IDs, the budget email.
  - They live in git-ignored `*.auto.tfvars` written by `scripts/azure/m4-tfvars.ps1`, which is read-only.
  - The pipeline gets them as GitHub environment variables.
- **Pre-Terraform resources** (the M1 budget, M2b/M3 AI resources) are taken over with `import` blocks.
- **Container images** are ignored by Terraform after creation; the pipeline deploys them. So `terraform plan`
  shows no drift after a deploy.
- **Pull-request checks** (`infra.yml`, no Azure access):
  - `fmt`, `validate` (provider from the lock file)
  - tflint with the azurerm ruleset
  - Trivy configuration scan
  - tflint and Trivy are pinned binaries with verified SHA-256, not third-party actions.

## Consequences

- A compromised dev pipeline can't reach prod's state, database or identity, and can't grant itself more.
- Changes to shared resources need the owner's laptop and sign-in. That is slower, and intended.
- Entra External ID objects (app registrations, redirect URIs) live in a separate tenant. They stay scripted and
  documented, not in Terraform.
- **No plan on pull requests:** it would need Azure read access from PRs. Plans run in the deploy job.

## Sources

- azurerm 5.15.0 resource docs (container_app `custom_scale_rule.identity_id`, storage `storage_account_id`,
  federated credential `audience` list): https://github.com/hashicorp/terraform-provider-azurerm/tree/v5.15.0/website/docs/r
- Remote state in Azure Storage with Entra auth: https://developer.hashicorp.com/terraform/language/backend/azurerm
- Constrain role assignments with conditions (ABAC):
  https://learn.microsoft.com/en-us/azure/role-based-access-control/delegate-role-assignments-portal
- Import blocks: https://developer.hashicorp.com/terraform/language/import
