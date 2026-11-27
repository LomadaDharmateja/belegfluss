# Creates or updates the GitHub environment for a deploy target (usable from main only) and its settings
# (ADR-0020, ADR-0022, ADR-0023). No value is a credential: the pipeline signs in with OIDC.
# - Azure IDs and resource names are stored as environment *secrets*, only so that public run logs show ***.
# - The sign-in IDs of Entra External ID stay plain *variables*; the web app sends them to every browser anyway.
# Values come from the bootstrap stack's outputs and the sign-in settings in the environment's .env file.
# Needs: gh auth login, terraform on PATH, az login, infra/bootstrap applied. Each command is printed first;
# secret values are passed on stdin, never printed or put on the command line.

param(
    [string]$Environment = "dev",
    [string]$Repo = "LomadaDharmateja/belegfluss",
    [Parameter(Mandatory = $true)][string]$NameSuffix,
    [string]$EnvFile = "",          # default: .env for dev, .env.<environment> otherwise (both git-ignored)
    [string]$OpenAIEndpoint = "",   # default: BELEGFLUSS_OPENAI_ENDPOINT from the env file
    [string]$Reviewer = ""          # GitHub login whose approval each deployment needs (prod)
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $EnvFile) { $EnvFile = if ($Environment -eq "dev") { ".env" } else { ".env.$Environment" } }

function Invoke-Step([string]$Title, [string[]]$Arguments) {
    Write-Host "==> $Title" -ForegroundColor Cyan
    Write-Host ("gh " + ($Arguments -join " "))
    & gh @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Step failed: $Title" }
}

# Sign-in settings (public IDs) from the environment's .env file.
$dotenv = @{}
Get-Content (Join-Path $root $EnvFile) | Where-Object { $_ -match "^\s*([A-Z_]+)\s*=\s*(.*)$" } | ForEach-Object {
    $dotenv[$Matches[1]] = $Matches[2].Trim().Trim('"')
}
$outputs = terraform -chdir="$root\infra\bootstrap" output -json | ConvertFrom-Json
if (-not $OpenAIEndpoint) { $OpenAIEndpoint = $dotenv["BELEGFLUSS_OPENAI_ENDPOINT"] }

$secrets = [ordered]@{
    AZURE_CLIENT_ID       = $outputs.deploy_client_ids.value.$Environment
    AZURE_TENANT_ID       = $outputs.tenant_id.value
    AZURE_SUBSCRIPTION_ID = (az account show --query id -o tsv)
    NAME_SUFFIX           = $NameSuffix
    TFSTATE_ACCOUNT       = $outputs.tfstate_account.value
    OPENAI_ENDPOINT       = $OpenAIEndpoint
}
$variables = [ordered]@{
    AUTH_ISSUER            = $dotenv["BELEGFLUSS_AUTH_ISSUER"]
    AUTH_JWKS_URL          = $dotenv["BELEGFLUSS_AUTH_JWKS_URL"]
    AUTH_AUDIENCE          = $dotenv["BELEGFLUSS_AUTH_AUDIENCE"]
    ENTRA_CLIENT_ID        = $dotenv["ENTRA_CLIENT_ID"]
    ENTRA_TENANT_SUBDOMAIN = $dotenv["ENTRA_TENANT_SUBDOMAIN"]
    ENTRA_TENANT_ID        = $dotenv["ENTRA_TENANT_ID"]
    ENTRA_API_SCOPE        = $dotenv["ENTRA_API_SCOPE"]
}
foreach ($set in @($secrets, $variables)) {
    foreach ($name in $set.Keys) {
        if (-not $set[$name]) { throw "No value for $name (check $EnvFile and the bootstrap outputs)." }
    }
}

$body = @("api", "--method", "PUT", "repos/$Repo/environments/$Environment",
    "-F", "deployment_branch_policy[protected_branches]=false", "-F", "deployment_branch_policy[custom_branch_policies]=true")
if ($Reviewer) {
    $reviewerId = gh api "users/$Reviewer" --jq .id
    $body += @("-F", "reviewers[][type]=User", "-F", "reviewers[][id]=$reviewerId", "-F", "prevent_self_review=false")
}
Invoke-Step "GitHub environment '$Environment', usable from main only" $body
$policies = gh api "repos/$Repo/environments/$Environment/deployment-branch-policies" --jq "[.branch_policies[].name]" | ConvertFrom-Json
if ($policies -notcontains "main") {
    Invoke-Step "... branch policy: main" @(
        "api", "--method", "POST", "repos/$Repo/environments/$Environment/deployment-branch-policies", "-f", "name=main", "-f", "type=branch"
    )
}

$existing = gh variable list --env $Environment --repo $Repo --json name --jq ".[].name"
foreach ($name in $secrets.Keys) {
    Write-Host "==> Secret $name (an identifier, masked in logs)" -ForegroundColor Cyan
    Write-Host "gh secret set $name --env $Environment --repo $Repo  (value on stdin)"
    $secrets[$name] | gh secret set $name --env $Environment --repo $Repo
    if ($LASTEXITCODE -ne 0) { throw "Setting secret $name failed" }
    if ($existing -contains $name) {
        Invoke-Step "Remove the old plain variable $name" @("variable", "delete", $name, "--env", $Environment, "--repo", $Repo)
    }
}
foreach ($name in $variables.Keys) {
    Invoke-Step "Variable $name (public sign-in ID)" @("variable", "set", $name, "--env", $Environment, "--repo", $Repo, "--body", $variables[$name])
}
Write-Host "Done: environment '$Environment' with $($secrets.Count) secrets and $($variables.Count) variables." -ForegroundColor Green
