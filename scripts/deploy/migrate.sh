#!/usr/bin/env bash
# Run the database migrations in Azure: the "migrate" Container Apps job, with the new API image,
# as the environment's app identity (it owns its database). Waits until the job has finished.
# Usage: migrate.sh <resource-group> <api-image>
set -euo pipefail
rg="$1"
image="$2"

az containerapp job update --name migrate --resource-group "$rg" --image "$image" --output none
execution=$(az containerapp job start --name migrate --resource-group "$rg" --query name --output tsv)
echo "migrate job started: $execution"

for _ in $(seq 1 60); do
  status=$(az containerapp job execution show --name "$execution" --job-name migrate \
    --resource-group "$rg" --query properties.status --output tsv)
  case "$status" in
    Succeeded) echo "migrations applied"; exit 0 ;;
    Failed | Stopped | Degraded) echo "::error::migrate job ended: $status"; exit 1 ;;
  esac
  sleep 10
done
echo "::error::migrate job did not finish within 10 minutes"
exit 1
