# One-time database setup per environment (ADR-0021), run by the owner, the server's only Entra admin.
# For each environment it creates the database belegfluss_<env>, a database role for the app identity
# id-belegfluss-app-<env> (Entra sign-in, no password), and lets only that role connect to it. The app
# identity then owns the tables its migrations create; dev's identity can't connect to prod's database.
#
# Your laptop reaches the server only through a temporary firewall rule for your public IP, which is
# removed at the end (also on errors). psql runs in the postgres:18-alpine image, so no local install.
# Needs: az login (owner), Docker. Safe to run again: every step checks first.

param(
    [Parameter(Mandatory = $true)][string]$NameSuffix,
    [string[]]$Environments = @("dev"),
    [string]$ResourceGroup = "rg-belegfluss-shared",
    [string]$ClientIp = ""
)

$ErrorActionPreference = "Stop"
# The one server in the shared group (its name ends with its region, see infra/shared/main.tf).
$server = (az postgres flexible-server list -g $ResourceGroup --query "[?starts_with(name, 'psql-belegfluss-$NameSuffix')].name | [0]" -o tsv)
$fqdn = (az postgres flexible-server show -g $ResourceGroup -n $server --query fullyQualifiedDomainName -o tsv)
$admin = (az ad signed-in-user show --query userPrincipalName -o tsv)
# The admin's database role name: at most 63 characters, like infra/shared/main.tf.
if ($admin) { $admin = $admin.Substring(0, [Math]::Min(63, $admin.Length)) }
if (-not $fqdn -or -not $admin) { throw "Server or signed-in user not found. Run 'az login' first." }
if (-not $ClientIp) {
    # Your address as the internet sees it (needed for the firewall rule). Pass -ClientIp to skip this.
    $ClientIp = (Invoke-RestMethod -Uri "https://api.ipify.org").Trim()
}
$rule = "owner-setup-" + (Get-Date -Format "yyyyMMddHHmmss")

function Invoke-Sql([string]$Database, [string]$Sql) {
    $env:PGPASSWORD = (az account get-access-token --resource-type oss-rdbms --query accessToken -o tsv)
    $conn = "host=$fqdn port=5432 dbname=$Database user='$admin' sslmode=require"
    $Sql | docker run --rm -i -e PGPASSWORD postgres:18-alpine psql $conn -v ON_ERROR_STOP=1 -q -f -
    $code = $LASTEXITCODE
    Remove-Item Env:\PGPASSWORD
    if ($code -ne 0) { throw "SQL on $Database failed" }
}

Write-Host "==> Temporary firewall rule $rule for $ClientIp" -ForegroundColor Cyan
az postgres flexible-server firewall-rule create -g $ResourceGroup --server-name $server --name $rule `
    --start-ip-address $ClientIp --end-ip-address $ClientIp --output none
try {
    foreach ($envName in $Environments) {
        $role = "id-belegfluss-app-$envName"
        $database = "belegfluss_$envName"
        $principal = (az identity show -g $ResourceGroup -n $role --query principalId -o tsv)
        if (-not $principal) { throw "Identity $role not found (apply infra/shared first)." }

        Write-Host "==> $envName : role $role, database $database" -ForegroundColor Cyan
        Invoke-Sql "postgres" @"
SELECT format('SELECT * FROM pgaadauth_create_principal_with_oid(%L, %L, %L, false, false)', '$role', '$principal', 'service')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$role')\gexec
SELECT 'CREATE DATABASE $database' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$database')\gexec
REVOKE CONNECT, TEMPORARY ON DATABASE $database FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE $database TO "$role";
"@
        Invoke-Sql $database @"
GRANT USAGE, CREATE ON SCHEMA public TO "$role";
"@
        Write-Host "Checked: $role may connect to $database only"
    }
}
finally {
    Write-Host "==> Removing firewall rule $rule" -ForegroundColor Cyan
    az postgres flexible-server firewall-rule delete -g $ResourceGroup --server-name $server --name $rule --yes --output none
}
