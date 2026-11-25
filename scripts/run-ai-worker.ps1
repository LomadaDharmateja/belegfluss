# Runs the worker on your machine with AI reading switched on (docs/setup/azure-openai-dev.md).
# Needs: `az login`, the stack started with compose.ai.yaml, and BELEGFLUSS_OPENAI_ENDPOINT in .env.
# Sign-in is keyless: the worker uses your Azure CLI login (DefaultAzureCredential).

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$line = Select-String -Path (Join-Path $root ".env") -Pattern '^BELEGFLUSS_OPENAI_ENDPOINT=(\S+)$'
if (-not $line) { throw "BELEGFLUSS_OPENAI_ENDPOINT is missing in .env" }

$env:BELEGFLUSS_OPENAI_ENDPOINT = $line.Matches[0].Groups[1].Value
$env:BELEGFLUSS_VALIDATOR_URL = "http://127.0.0.1:8081"
# Local Azurite emulator account from compose.yaml: not a secret, only valid for the emulator.
$env:BELEGFLUSS_STORAGE_CONNECTION_STRING = "DefaultEndpointsProtocol=http;AccountName=belegflussdev;AccountKey=ZGV2LWtleS1ub3Qtc2VjcmV0;BlobEndpoint=http://127.0.0.1:10000/belegflussdev;QueueEndpoint=http://127.0.0.1:10001/belegflussdev;" # gitleaks:allow (local emulator only)

Push-Location (Join-Path $root "apps/api")
try { uv run python -m belegfluss.worker } finally { Pop-Location }
