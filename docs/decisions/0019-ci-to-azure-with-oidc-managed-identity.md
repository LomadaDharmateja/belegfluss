# ADR-0019: GitHub Actions signs in to Azure with OIDC and a user-assigned managed identity

- **Status:** Accepted (2026-11-25)
- **Date:** 2026-11-25
- **Milestone:** M3 (reused for deployments in M4)

## Context

M3's live evaluation should be startable from GitHub, so anyone reviewing the repository can rerun it. M4 will
need CI/CD access to Azure anyway. The rule since M1 is **no secrets**: no keys, no passwords, no client secrets
in GitHub or code.

## Options

1. **Service principal with a client secret** in GitHub secrets: common, but a long-lived secret that can leak and
   must be rotated.
2. **App registration with a federated credential (OIDC):** no secret, but an Entra app object outside the
   resource group, so it is harder to keep together with the resources.
3. **User-assigned managed identity with a federated credential (OIDC):**
   - no secret
   - lives in the same resource group as what it may use, which is easy to describe in Terraform (M4)
   - supported for GitHub Actions per Microsoft's workload identity federation documentation

## Decision

**Option 3.**
- **Identity:** `id-belegfluss-eval-ci` in `rg-belegfluss-ai-dev`.
- **Federated credential:**
  - issuer `https://token.actions.githubusercontent.com`
  - **subject `repo:LomadaDharmateja/belegfluss:environment:eval`**
  - audience `api://AzureADTokenExchange`
- **GitHub environment `eval`:** usable **only from `main`** (deployment branch policy). A pull request or another
  branch can't get a token.
- **Roles on single resources only:**
  - "Cognitive Services OpenAI User" on the Azure OpenAI resource
  - "Cognitive Services User" on Document Intelligence
  - nothing on the subscription or the resource group
- **Workflow `eval-live`:**
  - `workflow_dispatch` only, no schedule
  - `permissions: id-token: write, contents: read`
  - client, tenant and subscription IDs are GitHub **variables** (identifiers, not secrets)
  - inputs reach the shell as environment variables, never inlined into scripts
  - cost cap per run

## Consequences

- No credential exists that could leak. The worst case is a run started from `main` by someone with write access,
  limited by the cost cap and the €10 budget alert.
- The GitHub OIDC token is short-lived. The workflow fetches both access tokens right after sign-in; a run must
  finish within the access token's lifetime (it takes minutes).
- In M4, Terraform creates the same pattern for deployments (another federated subject, other roles).

## Sources

- Workload identity federation with a user-assigned managed identity:
  https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation-create-trust-user-assigned-managed-identity
- `azure/login` (OIDC): https://github.com/Azure/login
- GitHub environments and deployment branch policies:
  https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment
