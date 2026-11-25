# Creates the GitHub environment for a deploy target (usable from main only) and sets its variables
# (ADR-0020, ADR-0022). Every value is an identifier or a URL, none is a secret: the pipeline signs in
# with OIDC. Values come from the bootstrap stack's outputs and the sign-in settings in your .env.
# Needs: gh auth login, terraform on PATH, infra/bootstrap applied. Each command is printed first.

param(
    [string]$Environment = "dev",
    [string]$Repo = "LomadaDharmateja/belegfluss",
    [Parameter(Mandatory = $true)][string]$NameSuffix
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

function Invoke-Step([string]$Title, [string[]]$Arguments) {
    Write-Host "==> $Title" -ForegroundColor Cyan
    Write-Host ("gh " + ($Arguments -join " "))
    & gh @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Step failed: $Title" }
}

# Sign-in settings (public IDs) from the local .env, the same ones Compose uses.
$dotenv = @{}
Get-Content "$root\.env" | Where-Object { $_ -match "^\s*([A-Z_]+)\s*=\s*(.*)$" } | ForEach-Object {
    $dotenv[$Matches[1]] = $Matches[2].Trim().Trim('"')
}
$outputs = terraform -chdir="$root\infra\bootstrap" output -json | ConvertFrom-Json
$subscription = az account show --query id -o tsv

$variables = [ordered]@{
    AZURE_CLIENT_ID        = $outputs.deploy_client_ids.value.$Environment
    AZURE_TENANT_ID        = $outputs.tenant_id.value
    AZURE_SUBSCRIPTION_ID  = $subscription
    NAME_SUFFIX            = $NameSuffix
    TFSTATE_ACCOUNT        = $outputs.tfstate_account.value
    AUTH_ISSUER            = $dotenv["BELEGFLUSS_AUTH_ISSUER"]
    AUTH_JWKS_URL          = $dotenv["BELEGFLUSS_AUTH_JWKS_URL"]
    AUTH_AUDIENCE          = $dotenv["BELEGFLUSS_AUTH_AUDIENCE"]
    ENTRA_CLIENT_ID        = $dotenv["ENTRA_CLIENT_ID"]
    ENTRA_TENANT_SUBDOMAIN = $dotenv["ENTRA_TENANT_SUBDOMAIN"]
    ENTRA_TENANT_ID        = $dotenv["ENTRA_TENANT_ID"]
    ENTRA_API_SCOPE        = $dotenv["ENTRA_API_SCOPE"]
    OPENAI_ENDPOINT        = $dotenv["BELEGFLUSS_OPENAI_ENDPOINT"]
}
foreach ($name in $variables.Keys) {
    if (-not $variables[$name]) { throw "No value for $name (check .env and the bootstrap outputs)." }
}

Invoke-Step "GitHub environment '$Environment', usable from main only" @(
    "api", "--method", "PUT", "repos/$Repo/environments/$Environment",
    "-F", "deployment_branch_policy[protected_branches]=false", "-F", "deployment_branch_policy[custom_branch_policies]=true"
)
$policies = gh api "repos/$Repo/environments/$Environment/deployment-branch-policies" --jq "[.branch_policies[].name]" | ConvertFrom-Json
if ($policies -notcontains "main") {
    Invoke-Step "... branch policy: main" @(
        "api", "--method", "POST", "repos/$Repo/environments/$Environment/deployment-branch-policies", "-f", "name=main", "-f", "type=branch"
    )
}
foreach ($name in $variables.Keys) {
    Invoke-Step "Variable $name (not a secret)" @("variable", "set", $name, "--env", $Environment, "--repo", $Repo, "--body", $variables[$name])
}
Write-Host "Done: environment '$Environment' with $($variables.Count) variables." -ForegroundColor Green
