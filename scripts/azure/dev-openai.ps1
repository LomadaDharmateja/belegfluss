# Creates the Azure OpenAI resource for local AI development (M2b, ADR-0016).
# Replaced by Terraform in M4. Run only after reading docs/setup/azure-openai-dev.md.
#
# What it creates (pay per token, no monthly fee expected; estimate in docs/COSTS.md):
#   1. resource group      rg-belegfluss-ai-dev (Germany West Central)
#   2. Azure OpenAI        S0, custom domain = name (required for Entra ID sign-in; can't be changed later)
#   3. keys switched off   disableLocalAuth = true -> only Microsoft Entra ID sign-in works
#   4. deployment          gpt-5-mini 2025-08-07, Data Zone Standard (EU processing, pay per token),
#                          capacity 20 = rate limit of 20K tokens/minute (not a fixed cost)
#   5. role                "Cognitive Services OpenAI User" for the signed-in user, on this resource only
#
# Every command is printed before it runs. The script stops at the first error.
# Sources (Microsoft Learn, read 2026-11-24): az cognitiveservices account / deployment reference,
# deployment types (SKU name DataZoneStandard), App Service tutorial (role assignment, endpoint),
# "Disable local authentication in Foundry Tools" (property disableLocalAuth), custom subdomains,
# az resource update (generic --set). No --yes: if Azure asks you to accept terms, you decide.

param(
    [Parameter(Mandatory = $true)][string]$Name,  # globally unique, e.g. belegfluss-dev-7k3q
    [string]$ResourceGroup = "rg-belegfluss-ai-dev",
    [string]$Location = "germanywestcentral",
    [string]$Model = "gpt-5-mini",
    [string]$ModelVersion = "2025-08-07",
    [int]$Capacity = 20
)

$ErrorActionPreference = "Stop"

function Invoke-Step([string]$Title, [string[]]$Arguments) {
    Write-Host ""
    Write-Host "==> $Title" -ForegroundColor Cyan
    Write-Host ("az " + ($Arguments -join " "))
    & az @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Step failed: $Title" }
}

$subscription = (az account show --query id -o tsv)
if ($LASTEXITCODE -ne 0 -or -not $subscription) { throw "Not signed in. Run 'az login' first." }
Write-Host "Subscription: $subscription"

Invoke-Step "1. Resource group" @("group", "create", "--name", $ResourceGroup, "--location", $Location, "--output", "none")

Invoke-Step "2. Azure OpenAI account" @(
    "cognitiveservices", "account", "create", "--name", $Name, "--resource-group", $ResourceGroup,
    "--location", $Location, "--kind", "OpenAI", "--sku", "s0", "--custom-domain", $Name, "--output", "none"
)

$accountId = "/subscriptions/$subscription/resourceGroups/$ResourceGroup/providers/Microsoft.CognitiveServices/accounts/$Name"
Invoke-Step "3. Switch keys off (Entra ID only)" @(
    "resource", "update", "--ids", $accountId, "--set", "properties.disableLocalAuth=true", "--output", "none"
)
$keysOff = (az cognitiveservices account show --name $Name --resource-group $ResourceGroup --query properties.disableLocalAuth -o tsv)
if ($keysOff -ne "true") { throw "Keys are still switched on (disableLocalAuth = $keysOff). Stopping before the deployment." }
Write-Host "Checked: disableLocalAuth = true"

Invoke-Step "4. Model deployment (Data Zone Standard, EU)" @(
    "cognitiveservices", "account", "deployment", "create", "--name", $Name, "--resource-group", $ResourceGroup,
    "--deployment-name", $Model, "--model-name", $Model, "--model-version", $ModelVersion,
    "--model-format", "OpenAI", "--sku-name", "DataZoneStandard", "--sku-capacity", "$Capacity", "--output", "none"
)

$me = (az ad signed-in-user show --query id -o tsv)
if ($LASTEXITCODE -ne 0 -or -not $me) { throw "Could not read your user ID (az ad signed-in-user show)." }
Invoke-Step "5. Role for you on this resource only" @(
    "role", "assignment", "create", "--assignee", $me, "--role", "Cognitive Services OpenAI User",
    "--scope", $accountId, "--output", "none"
)

$endpoint = (az cognitiveservices account show --name $Name --resource-group $ResourceGroup --query properties.endpoint -o tsv)
Write-Host ""
Write-Host "Done. Put this into .env (it is not a secret):" -ForegroundColor Green
Write-Host "BELEGFLUSS_OPENAI_ENDPOINT=$endpoint"
Write-Host "To delete everything again: az group delete --name $ResourceGroup"
