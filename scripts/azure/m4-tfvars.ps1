# Writes the git-ignored variable files for the owner stacks (infra/bootstrap, infra/shared) from
# what exists in Azure and GitHub today. Read-only: it changes nothing in Azure or GitHub.
# Run after `az login --tenant <tenant>` and `gh auth login`. ADR-0020.
#
# The files hold identifiers (subscription, names, role assignment IDs) and the budget email.
# None is a secret, but they stay out of the repository (*.tfvars is git-ignored).

param(
    [string]$Repo = "LomadaDharmateja/belegfluss",
    [string]$AiGroup = "rg-belegfluss-ai-dev"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

function Get-Az([string[]]$Arguments) {
    $out = & az @Arguments
    if ($LASTEXITCODE -ne 0) { throw "az $($Arguments -join ' ') failed" }
    return $out
}

$subscription = Get-Az @("account", "show", "--query", "id", "-o", "tsv")
$openai = Get-Az @("cognitiveservices", "account", "list", "-g", $AiGroup, "--query", "[?kind=='OpenAI'].name | [0]", "-o", "tsv")
$docIntel = Get-Az @("cognitiveservices", "account", "list", "-g", $AiGroup, "--query", "[?kind=='FormRecognizer'].name | [0]", "-o", "tsv")
$suffix = ($openai -split "-")[-1] # the same suffix as the M2b resources
$ownerId = Get-Az @("ad", "signed-in-user", "show", "--query", "id", "-o", "tsv")
$ownerName = Get-Az @("ad", "signed-in-user", "show", "--query", "userPrincipalName", "-o", "tsv")
$evalPrincipal = Get-Az @("identity", "show", "-g", $AiGroup, "-n", "id-belegfluss-eval-ci", "--query", "principalId", "-o", "tsv")
$githubOwnerId = gh api "repos/$Repo" --jq .owner.id
$githubRepoId = gh api "repos/$Repo" --jq .id

$budgetUrl = "https://management.azure.com/subscriptions/$subscription/providers/Microsoft.Consumption/budgets/belegfluss?api-version=2023-05-01"
$budgetStart = Get-Az @("rest", "--method", "get", "--url", $budgetUrl, "--query", "properties.timePeriod.startDate", "-o", "tsv")
$budgetEmails = Get-Az @("rest", "--method", "get", "--url", $budgetUrl, "--query", "properties.notifications.*.contactEmails[] | [0]", "-o", "tsv")

$aiScope = "/subscriptions/$subscription/resourceGroups/$AiGroup/providers/Microsoft.CognitiveServices/accounts"
function Get-AssignmentId([string]$Account, [string]$Role, [string]$Principal) {
    $id = Get-Az @("role", "assignment", "list", "--scope", "$aiScope/$Account", "--role", $Role, "--assignee", $Principal, "--query", "[0].id", "-o", "tsv")
    if (-not $id) { throw "No '$Role' assignment found on $Account" }
    return $id
}
$assignments = [ordered]@{
    owner_uses_openai_dev           = Get-AssignmentId $openai "Cognitive Services OpenAI User" $ownerId
    owner_uses_doc_intelligence_dev = Get-AssignmentId $docIntel "Cognitive Services User" $ownerId
    eval_uses_openai_dev            = Get-AssignmentId $openai "Cognitive Services OpenAI User" $evalPrincipal
    eval_uses_doc_intelligence_dev  = Get-AssignmentId $docIntel "Cognitive Services User" $evalPrincipal
}

$bootstrap = @"
subscription_id = "$subscription"
name_suffix     = "$suffix"
github_owner_id = "$githubOwnerId"
github_repo_id  = "$githubRepoId"
"@

$assignmentLines = ($assignments.Keys | ForEach-Object { "  $_ = `"$($assignments[$_])`"" }) -join "`n"
$shared = @"
subscription_id           = "$subscription"
name_suffix               = "$suffix"
owner_principal_name      = "$ownerName"
budget_contact_emails     = ["$budgetEmails"]
budget_start_date         = "$budgetStart"
openai_dev_name           = "$openai"
doc_intelligence_dev_name = "$docIntel"
github_owner_id           = "$githubOwnerId"
github_repo_id            = "$githubRepoId"
existing_role_assignment_ids = {
$assignmentLines
}
"@

$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText("$root\infra\bootstrap\bootstrap.auto.tfvars", $bootstrap + "`n", $utf8)
[System.IO.File]::WriteAllText("$root\infra\shared\shared.auto.tfvars", $shared + "`n", $utf8)
Write-Host "Written (git-ignored): infra/bootstrap/bootstrap.auto.tfvars, infra/shared/shared.auto.tfvars"
