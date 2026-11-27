# M3 evaluation resources (ADR-0018, ADR-0019). Replaced by Terraform in M4.
# Run only after reading docs/setup/eval.md. Every command is printed before it runs; stops at the first error.
#
# What it does (all free or rate limits only; estimate in docs/COSTS.md):
#   1. gpt-5.4-mini deployment: capacity 20 -> 100 (tokens/minute limit, not a cost; quota is 200)
#   2. Document Intelligence F0 (free tier) in Germany West Central, custom domain, keys off (read back)
#   3. user-assigned managed identity for GitHub Actions + a federated credential that trusts only this
#      repository's "eval" environment (no secret exists)
#   4. roles on single resources: CI identity -> OpenAI user (OpenAI) and Cognitive Services User (DI);
#      you -> Cognitive Services User (DI)
#   5. GitHub: environment "eval" (main branch only) and its IDs and endpoints, stored as environment secrets only
#      so that public logs mask them (ADR-0023); none is a credential
#
# Sources (Microsoft Learn / GitHub Docs, read 2026-11-25): az cognitiveservices account / deployment,
# az identity federated-credential, workload identity federation with a user-assigned managed identity,
# Azure/login (OIDC), GitHub environments and variables REST API, GitHub changelog 2026-04-23 "Immutable
# subject claims for GitHub Actions OIDC tokens", Entra "Migrate GitHub Actions federated credentials to
# immutable subjects".

param(
    [Parameter(Mandatory = $true)][string]$OpenAIName,     # existing, e.g. belegfluss-dev-xxxx
    [Parameter(Mandatory = $true)][string]$DocIntelName,   # new, globally unique custom domain
    [string]$ResourceGroup = "rg-belegfluss-ai-dev",
    [string]$Location = "germanywestcentral",
    [string]$Repo = "LomadaDharmateja/belegfluss",
    [string]$IdentityName = "id-belegfluss-eval-ci",
    [int]$Capacity = 100
)

$ErrorActionPreference = "Stop"

function Invoke-Step([string]$Title, [string]$Tool, [string[]]$Arguments) {
    Write-Host ""
    Write-Host "==> $Title" -ForegroundColor Cyan
    Write-Host ("$Tool " + ($Arguments -join " "))
    & $Tool @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Step failed: $Title" }
}

$subscription = (az account show --query id -o tsv)
$tenant = (az account show --query tenantId -o tsv)
if ($LASTEXITCODE -ne 0 -or -not $subscription) { throw "Not signed in. Run 'az login' first." }
$rgId = "/subscriptions/$subscription/resourceGroups/$ResourceGroup/providers/Microsoft.CognitiveServices/accounts"

Invoke-Step "1. Capacity of the gpt-5.4-mini deployment -> $Capacity" "az" @(
    "cognitiveservices", "account", "deployment", "create", "--name", $OpenAIName, "--resource-group", $ResourceGroup,
    "--deployment-name", "gpt-5.4-mini", "--model-name", "gpt-5.4-mini", "--model-version", "2026-03-17",
    "--model-format", "OpenAI", "--sku-name", "DataZoneStandard", "--sku-capacity", "$Capacity", "--output", "none"
)
$now = (az cognitiveservices account deployment show --name $OpenAIName --resource-group $ResourceGroup --deployment-name gpt-5.4-mini --query sku.capacity -o tsv)
if ("$now" -ne "$Capacity") { throw "Capacity is $now, expected $Capacity." }
Write-Host "Checked: capacity = $now"

Invoke-Step "2a. Document Intelligence F0 (free tier)" "az" @(
    "cognitiveservices", "account", "create", "--name", $DocIntelName, "--resource-group", $ResourceGroup,
    "--location", $Location, "--kind", "FormRecognizer", "--sku", "F0", "--custom-domain", $DocIntelName, "--output", "none"
)
Invoke-Step "2b. Switch keys off (Entra ID only)" "az" @(
    "resource", "update", "--ids", "$rgId/$DocIntelName", "--set", "properties.disableLocalAuth=true", "--output", "none"
)
$keysOff = (az cognitiveservices account show --name $DocIntelName --resource-group $ResourceGroup --query properties.disableLocalAuth -o tsv)
if ($keysOff -ne "true") { throw "Keys are still switched on (disableLocalAuth = $keysOff)." }
Write-Host "Checked: disableLocalAuth = true"

Invoke-Step "3a. Managed identity for GitHub Actions" "az" @(
    "identity", "create", "--name", $IdentityName, "--resource-group", $ResourceGroup, "--location", $Location, "--output", "none"
)
$clientId = (az identity show --name $IdentityName --resource-group $ResourceGroup --query clientId -o tsv)
$principalId = (az identity show --name $IdentityName --resource-group $ResourceGroup --query principalId -o tsv)
# Repositories created after 2026-07-15 get "immutable" subjects with the owner and repository IDs
# (repo:OWNER@OWNER-ID/REPO@REPO-ID:...), so a renamed or re-created repository can't reuse the trust.
$owner, $repoName = $Repo.Split("/")
$ownerId = (gh api "repos/$Repo" --jq .owner.id)
$repoId = (gh api "repos/$Repo" --jq .id)
if ($LASTEXITCODE -ne 0 -or -not $ownerId -or -not $repoId) { throw "Could not read the repository IDs from GitHub." }
$subject = "repo:${owner}@${ownerId}/${repoName}@${repoId}:environment:eval"
Invoke-Step "3b. Trust only this repository's 'eval' environment" "az" @(
    "identity", "federated-credential", "create", "--name", "github-eval", "--identity-name", $IdentityName,
    "--resource-group", $ResourceGroup, "--issuer", "https://token.actions.githubusercontent.com",
    "--subject", $subject, "--audiences", "api://AzureADTokenExchange", "--output", "none"
)
$trusted = (az identity federated-credential show --name github-eval --identity-name $IdentityName --resource-group $ResourceGroup --query subject -o tsv)
if ($trusted -ne $subject) { throw "Federated subject is $trusted, expected $subject." }
Write-Host "Checked: subject = $subject"

$me = (az ad signed-in-user show --query id -o tsv)
Invoke-Step "4a. CI identity: OpenAI user on the OpenAI resource only" "az" @(
    "role", "assignment", "create", "--assignee-object-id", $principalId, "--assignee-principal-type", "ServicePrincipal",
    "--role", "Cognitive Services OpenAI User", "--scope", "$rgId/$OpenAIName", "--output", "none"
)
Invoke-Step "4b. CI identity: Cognitive Services User on Document Intelligence only" "az" @(
    "role", "assignment", "create", "--assignee-object-id", $principalId, "--assignee-principal-type", "ServicePrincipal",
    "--role", "Cognitive Services User", "--scope", "$rgId/$DocIntelName", "--output", "none"
)
Invoke-Step "4c. You: Cognitive Services User on Document Intelligence only" "az" @(
    "role", "assignment", "create", "--assignee", $me, "--role", "Cognitive Services User",
    "--scope", "$rgId/$DocIntelName", "--output", "none"
)

$openaiEndpoint = (az cognitiveservices account show --name $OpenAIName --resource-group $ResourceGroup --query properties.endpoint -o tsv)
$diEndpoint = (az cognitiveservices account show --name $DocIntelName --resource-group $ResourceGroup --query properties.endpoint -o tsv)

Invoke-Step "5a. GitHub environment 'eval', usable from main only" "gh" @(
    "api", "--method", "PUT", "repos/$Repo/environments/eval",
    "-F", "deployment_branch_policy[protected_branches]=false", "-F", "deployment_branch_policy[custom_branch_policies]=true"
)
Invoke-Step "5b. ... branch policy: main" "gh" @(
    "api", "--method", "POST", "repos/$Repo/environments/eval/deployment-branch-policies", "-f", "name=main", "-f", "type=branch"
)
$variables = [ordered]@{
    AZURE_CLIENT_ID = $clientId; AZURE_TENANT_ID = $tenant; AZURE_SUBSCRIPTION_ID = $subscription
    BELEGFLUSS_OPENAI_ENDPOINT = $openaiEndpoint; BELEGFLUSS_DI_ENDPOINT = $diEndpoint
}
foreach ($name in $variables.Keys) {
    Write-Host "==> 5c. Secret $name (an identifier, masked in logs; value on stdin)" -ForegroundColor Cyan
    $variables[$name] | gh secret set $name --env eval --repo $Repo
    if ($LASTEXITCODE -ne 0) { throw "Step failed: 5c. $name" }
}

Write-Host ""
Write-Host "Done. Put this into .env (not a secret):" -ForegroundColor Green
Write-Host "BELEGFLUSS_DI_ENDPOINT=$diEndpoint"
Write-Host "To delete the new parts again: az cognitiveservices account delete -n $DocIntelName -g $ResourceGroup; az identity delete -n $IdentityName -g $ResourceGroup"
