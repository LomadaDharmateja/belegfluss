# Evidence: deploy and eval-live runs of M3/M4a (excerpts)

These runs were deleted before the repository went public (ADR-0023): their logs showed the Azure subscription,
tenant and identity IDs. Below are the key lines of every run, extracted from the full logs on 2026-11-27. IDs,
resource names, IP addresses and email addresses are replaced by `<id>`, `<sfx>`, `<env-domain>`, `<ip>`,
`<email>`; GitHub owner and repository numbers by `<owner-id>`/`<repo-id>`. Nothing else was changed.

## Run 45907385839

First release from main after the M4a merge.

- Workflow `deploy.yml`, branch `main`, event `push`, started 2026-11-26T22:51:22Z, result **success**

| Job | Line |
|---|---|
| api / test | `================== 253 passed, 1 skipped in 81.03s (0:01:21) ===================` |
| secret-scan / gitleaks | `no leaks found` |
| web / test | `Tests  47 passed (47)` |
| web / test | `5 passed (3.0s)` |
| eval / gate | `============================== 24 passed in 1.27s ==============================` |
| eval / gate | `gate passed` |
| build | `subject claim - repo:LomadaDharmateja@<owner-id>/belegfluss@<repo-id>:environment:dev` |
| build | `Azure CLI login succeeds by using OIDC.` |
| deploy-dev | `subject claim - repo:LomadaDharmateja@<owner-id>/belegfluss@<repo-id>:environment:dev` |
| deploy-dev | `Azure CLI login succeeds by using OIDC.` |
| deploy-dev | `No changes. Your infrastructure matches the configuration.` |
| deploy-dev | `Apply complete! Resources: 0 added, 0 changed, 0 destroyed.` |
| deploy-dev | `migrate job started: migrate-06w0zit` |
| deploy-dev | `migrations applied` |
| deploy-dev | `apps updated` |
| deploy-dev | `api awake after 0 s` |
| deploy-dev | `web awake after 2 s` |
| deploy-dev | `smoke test passed` |

## Run 45776175543

Final run on the M4a branch: "No changes", smoke green.

- Workflow `deploy.yml`, branch `m4a-azure-dev`, event `push`, started 2026-11-26T07:33:13Z, result **success**

| Job | Line |
|---|---|
| web / test | `Tests  47 passed (47)` |
| web / test | `5 passed (2.7s)` |
| secret-scan / gitleaks | `no leaks found` |
| eval / gate | `============================== 24 passed in 1.79s ==============================` |
| eval / gate | `gate passed` |
| api / test | `================== 253 passed, 1 skipped in 85.14s (0:01:25) ===================` |
| build | `subject claim - repo:LomadaDharmateja@<owner-id>/belegfluss@<repo-id>:environment:dev` |
| build | `Azure CLI login succeeds by using OIDC.` |
| deploy-dev | `subject claim - repo:LomadaDharmateja@<owner-id>/belegfluss@<repo-id>:environment:dev` |
| deploy-dev | `Azure CLI login succeeds by using OIDC.` |
| deploy-dev | `No changes. Your infrastructure matches the configuration.` |
| deploy-dev | `Apply complete! Resources: 0 added, 0 changed, 0 destroyed.` |
| deploy-dev | `migrate job started: migrate-gf3kpkf` |
| deploy-dev | `migrations applied` |
| deploy-dev | `apps updated` |
| deploy-dev | `api awake after 1 s` |
| deploy-dev | `web awake after 1 s` |
| deploy-dev | `smoke test passed` |

## Run 45774741253

Documentation-only push, cancelled during tests on purpose (cold-start measurement running).

- Workflow `deploy.yml`, branch `m4a-azure-dev`, event `push`, started 2026-11-26T07:21:46Z, result **cancelled**

| Job | Line |
|---|---|
| compose-smoke / smoke | `##[error]The operation was canceled.` |
| infra / check | `##[error]The operation was canceled.` |
| secret-scan / gitleaks | `no leaks found` |
| web / test | `##[error]The operation was canceled.` |
| api / test | `##[error]The operation was canceled.` |
| eval / gate | `============================== 24 passed in 1.46s ==============================` |
| eval / gate | `gate passed` |
| eval / gate | `##[error]The operation was canceled.` |

## Run 45773112690

Readiness probe change (1 planned change), smoke green.

- Workflow `deploy.yml`, branch `m4a-azure-dev`, event `push`, started 2026-11-26T07:08:27Z, result **success**

| Job | Line |
|---|---|
| secret-scan / gitleaks | `no leaks found` |
| web / test | `Tests  47 passed (47)` |
| web / test | `5 passed (4.6s)` |
| api / test | `================== 253 passed, 1 skipped in 130.83s (0:02:10) ==================` |
| eval / gate | `============================== 24 passed in 1.78s ==============================` |
| eval / gate | `gate passed` |
| build | `subject claim - repo:LomadaDharmateja@<owner-id>/belegfluss@<repo-id>:environment:dev` |
| build | `Azure CLI login succeeds by using OIDC.` |
| deploy-dev | `subject claim - repo:LomadaDharmateja@<owner-id>/belegfluss@<repo-id>:environment:dev` |
| deploy-dev | `Azure CLI login succeeds by using OIDC.` |
| deploy-dev | `Plan: 0 to add, 1 to change, 0 to destroy.` |
| deploy-dev | `Apply complete! Resources: 0 added, 1 changed, 0 destroyed.` |
| deploy-dev | `migrate job started: migrate-ivekzmv` |
| deploy-dev | `migrations applied` |
| deploy-dev | `apps updated` |
| deploy-dev | `api awake after 0 s` |
| deploy-dev | `web awake after 22 s` |
| deploy-dev | `smoke test passed` |

## Run 45771194607

No drift: plan "No changes" after the drift fixes.

- Workflow `deploy.yml`, branch `m4a-azure-dev`, event `push`, started 2026-11-26T06:52:12Z, result **success**

| Job | Line |
|---|---|
| secret-scan / gitleaks | `no leaks found` |
| web / test | `Tests  47 passed (47)` |
| web / test | `5 passed (2.7s)` |
| api / test | `================== 253 passed, 1 skipped in 78.99s (0:01:18) ===================` |
| eval / gate | `============================== 24 passed in 1.75s ==============================` |
| eval / gate | `gate passed` |
| build | `subject claim - repo:LomadaDharmateja@<owner-id>/belegfluss@<repo-id>:environment:dev` |
| build | `Azure CLI login succeeds by using OIDC.` |
| deploy-dev | `subject claim - repo:LomadaDharmateja@<owner-id>/belegfluss@<repo-id>:environment:dev` |
| deploy-dev | `Azure CLI login succeeds by using OIDC.` |
| deploy-dev | `No changes. Your infrastructure matches the configuration.` |
| deploy-dev | `Apply complete! Resources: 0 added, 0 changed, 0 destroyed.` |
| deploy-dev | `migrate job started: migrate-78d9u5g` |
| deploy-dev | `migrations applied` |
| deploy-dev | `apps updated` |
| deploy-dev | `api awake after 1 s` |
| deploy-dev | `web awake after 1 s` |
| deploy-dev | `smoke test passed` |

## Run 45769630636

First fully green release (tests, build, scan, push, apply, migrate, deploy, smoke).

- Workflow `deploy.yml`, branch `m4a-azure-dev`, event `push`, started 2026-11-26T06:38:50Z, result **success**

| Job | Line |
|---|---|
| web / test | `Tests  47 passed (47)` |
| web / test | `5 passed (3.4s)` |
| secret-scan / gitleaks | `no leaks found` |
| api / test | `================== 253 passed, 1 skipped in 90.15s (0:01:30) ===================` |
| eval / gate | `============================== 24 passed in 1.74s ==============================` |
| eval / gate | `gate passed` |
| build | `subject claim - repo:LomadaDharmateja@<owner-id>/belegfluss@<repo-id>:environment:dev` |
| build | `Azure CLI login succeeds by using OIDC.` |
| deploy-dev | `subject claim - repo:LomadaDharmateja@<owner-id>/belegfluss@<repo-id>:environment:dev` |
| deploy-dev | `Azure CLI login succeeds by using OIDC.` |
| deploy-dev | `Plan: 0 to add, 7 to change, 0 to destroy.` |
| deploy-dev | `Apply complete! Resources: 0 added, 7 changed, 0 destroyed.` |
| deploy-dev | `migrate job started: migrate-tq1clsm` |
| deploy-dev | `migrations applied` |
| deploy-dev | `apps updated` |
| deploy-dev | `api awake after 0 s` |
| deploy-dev | `web awake after 1 s` |
| deploy-dev | `smoke test passed` |

## Run 45768046744

Second run: build passed; migrate polling used wrong CLI arguments (the migration itself succeeded).

- Workflow `deploy.yml`, branch `m4a-azure-dev`, event `push`, started 2026-11-26T06:25:05Z, result **failure**

| Job | Line |
|---|---|
| eval / gate | `============================== 24 passed in 1.77s ==============================` |
| eval / gate | `gate passed` |
| web / test | `Tests  47 passed (47)` |
| web / test | `5 passed (2.7s)` |
| api / test | `================== 253 passed, 1 skipped in 98.34s (0:01:38) ===================` |
| secret-scan / gitleaks | `no leaks found` |
| build | `subject claim - repo:LomadaDharmateja@<owner-id>/belegfluss@<repo-id>:environment:dev` |
| build | `Azure CLI login succeeds by using OIDC.` |
| deploy-dev | `subject claim - repo:LomadaDharmateja@<owner-id>/belegfluss@<repo-id>:environment:dev` |
| deploy-dev | `Azure CLI login succeeds by using OIDC.` |
| deploy-dev | `Plan: 14 to add, 0 to change, 0 to destroy.` |
| deploy-dev | `Apply complete! Resources: 14 added, 0 changed, 0 destroyed.` |
| deploy-dev | `migrate job started: migrate-u9f3hwx` |
| deploy-dev | `##[error]Process completed with exit code 2.` |

## Run 45766958861

First release run: blocked by the image scan.

- Workflow `deploy.yml`, branch `m4a-azure-dev`, event `push`, started 2026-11-26T06:15:37Z, result **failure**

| Job | Line |
|---|---|
| web / test | `Tests  47 passed (47)` |
| web / test | `5 passed (4.4s)` |
| secret-scan / gitleaks | `no leaks found` |
| api / test | `================== 253 passed, 1 skipped in 73.74s (0:01:13) ===================` |
| eval / gate | `============================== 24 passed in 1.74s ==============================` |
| eval / gate | `gate passed` |
| build | `Total: 1 (HIGH: 1, CRITICAL: 0)` |
| build | `│ libzstd1 │ CVE-2026-124851 │ HIGH     │ fixed  │ 1.5.7+dfsg-1      │ 1.5.7+dfsg-1+deb13u1 │ zstd: Zstandard Information Disclosure via Uninitialized │` |
| build | `Total: 5 (HIGH: 5, CRITICAL: 0)` |
| build | `│ msgpack    │ CVE-2026-114613     │ HIGH     │ fixed  │ 1.1.2             │ 1.2.3         │ msgpack: msgpack: Denial of Service via memory leak during │` |
| build | `│ setuptools │ CVE-2025-47273      │          │        │ 70.3.0            │ 78.1.1        │ setuptools: Path Traversal Vulnerability in setuptools     │` |
| build | `│ urllib3    │ CVE-2026-97687      │          │        │ 2.7.0             │ 2.8.0         │ urllib3: urllib3: Traffic interception via HTTPS proxy TLS │` |
| build | `##[error]Process completed with exit code 1.` |

## Run 45564923717

Live evaluation from GitHub after the subject fix: 127 of 127 documents.

- Workflow `eval-live.yml`, branch `main`, event `workflow_dispatch`, started 2026-11-25T07:01:25Z, result **success**

| Job | Line |
|---|---|
| run | `subject claim - repo:LomadaDharmateja@<owner-id>/belegfluss@<repo-id>:environment:eval` |
| run | `Azure CLI login succeeds by using OIDC.` |
| run | `dataset ok` |
| run | `1/127 official-003                 ok             5.3s $0.009` |
| run | `127/127 synthetic-040-scan           ok             2.6s $0.690` |
| run | `recorded: 2026-11-25-azure-test-p97843178-2` |

## Run 45561359881

First live evaluation from GitHub: refused at sign-in (AADSTS700213, subject format).

- Workflow `eval-live.yml`, branch `main`, event `workflow_dispatch`, started 2026-11-25T06:32:29Z, result **failure**

| Job | Line |
|---|---|
| run | `subject claim - repo:LomadaDharmateja@<owner-id>/belegfluss@<repo-id>:environment:eval` |
| run | `##[error]AADSTS700213: No matching federated identity record found for presented assertion subject 'repo:LomadaDharmateja@<owner-id>/belegfluss@<repo-id>:environment:eval'. Check your federated identity credential Subject, Audience and Issuer against the presented assertion. https://learn.microsoft.com/entra/workload-id/workload-identity-federation Trace ID: <redacted>` |
| run | `##[error]Login failed with Error: The process '/usr/bin/az' failed with exit code 1. Double check if the 'auth-type' is correct. Refer to https://github.com/Azure/login#readme for more information.` |

