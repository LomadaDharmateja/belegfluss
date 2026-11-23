# ADR-0002: Plain-folder monorepo with native tooling

- **Status:** Accepted (2026-11-23)
- **Date:** 2026-11-23
- **Milestone:** M0 (applies from M1)

## Context

Belegfluss has a TypeScript web app, a Python API and worker, a Java validator (official, not our code),
Terraform, later Helm charts, n8n workflows, evaluation and ML code. One developer works on it, and each milestone
usually touches several of these parts at once.

## Options

1. **Polyrepo** (web, api, infra, ...): clear boundaries, but every feature needs coordinated PRs and version pinning
   between repos.
2. **Monorepo with Nx / Turborepo**: task graph and caching, but mainly designed for JavaScript/TypeScript. Extra
   configuration to learn and explain, and little benefit for Python.
3. **Plain-folder monorepo** with each part using its own standard tool: `uv` for Python, `pnpm` for the web app,
   `terraform`, `helm`. CI runs jobs per folder (path filters).

## Decision

**Option 3.** Layout (folders are only created when a milestone needs them):

```text
apps/web            Next.js + TypeScript (strict)
apps/api            one Python package "belegfluss" with two entrypoints: API and worker
services/validator  Dockerfile + pinned official KoSIT configuration (no own code)
infra/terraform     modules + envs/dev, envs/prod
deploy/helm         charts (M8)
automation/n8n      exported workflows (M6)
eval/               evaluation sets manifest, runner, reports (M3)
ml/                 fine-tuning (M7)
scripts/            small helper scripts (e.g. fetch pinned test data)
docs/               documentation, ADRs, milestones
```

API and worker share one Python package because they share the domain code (invoice model, parsers, checks). A
separate package would mean versioning between them with no benefit.

Why not the others: polyrepo adds coordination cost for one developer; Nx/Turborepo adds tooling that solves
problems (large JS build graphs) we don't have.

## Consequences

- One pull request per milestone can contain web + API + infra + docs changes.
- CI must use path filters so a docs change doesn't rebuild everything.
- If the repo ever gets slow to build, Turborepo can be added for the web part only (new ADR).

## Sources

- uv (Python project manager): https://docs.astral.sh/uv/
- pnpm workspaces: https://pnpm.io/workspaces
