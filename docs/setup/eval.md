# Setup: running the evaluation (M3)

> How to rerun the numbers in [`eval/reports/`](../../eval/reports/). Decisions: [ADR-0018](../decisions/0018-evaluation-dataset-metrics-and-gate.md)
> (dataset, metrics, gate) and [ADR-0019](../decisions/0019-ci-to-azure-with-oidc-managed-identity.md) (CI → Azure).

## Free, no Azure: the gate

```powershell
cd eval
uv sync
uv run pytest                              # metrics, generator, gate
uv run python -m belegfluss_eval gate      # replays the baseline with the current code
```

The same runs in CI on every pull request (`eval` workflow).

## Live runs (cost money: about $0.005 per document)

Needs: `az login` (see [azure-openai-dev.md](azure-openai-dev.md)) and the GitHub CLI signed in.

```powershell
cd eval
uv run python -m belegfluss_eval fetch     # download the dataset release, check every SHA-256
$env:BELEGFLUSS_OPENAI_ENDPOINT = "https://<resource>.openai.azure.com/"
uv run python -m belegfluss_eval run --split dev --max-usd 1
uv run python -m belegfluss_eval report my-report <run folder>
```

- **dev** is for trying changes; **test** is the held-out split for reported numbers. Run it once per prompt
  version.
- After a prompt or model change: run `test`, then `uv run python -m belegfluss_eval baseline <run folder>` and
  commit the recordings, the report and `baseline.json` together.
- Document Intelligence baseline: `--extractor di` with `BELEGFLUSS_DI_ENDPOINT` (free tier F0: 500 pages a
  month, first 2 pages per document).

## From GitHub (on demand)

Actions → **eval-live** → Run workflow (from `main` only), with split, extractor and cost cap. It signs in with
OIDC (no secret), runs, and attaches the recordings and the report as an artifact. The report also appears in the
run summary.

## Azure resources (created once, 2026-11-25, after the owner's yes)

`scripts/azure/dev-eval.ps1`. Each command is printed before it runs:
1. gpt-5.4-mini capacity 100 (rate limit only)
2. Document Intelligence F0, keys off
3. managed identity `id-belegfluss-eval-ci` with a federated credential for the `eval` environment
4. roles on single resources
5. GitHub environment `eval` (main only) and its variables

To remove the M3 parts:

```powershell
az cognitiveservices account delete -n <di-resource> -g rg-belegfluss-ai-dev
az identity delete -n id-belegfluss-eval-ci -g rg-belegfluss-ai-dev
```

## Rebuilding the dataset (only for a new dataset version)

Needs Docker (Apache FOP image `eval/fop/Dockerfile`) and Playwright Chromium (`uv run playwright install
chromium`):

```powershell
docker build -t belegfluss-eval-fop:2.12 eval/fop
uv run python -m belegfluss_eval build-dataset
```

A rebuild gives the same labels and splits, but the file bytes differ (PDF timestamps). A new version therefore
means a new release asset, a new manifest, new live runs and a new baseline.
