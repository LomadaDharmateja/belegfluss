#!/usr/bin/env bash
# Point every app and job at the new images (pinned by digest, so dev and prod run the same bytes).
# Terraform ignores image changes (infra/environment/apps.tf), so this doesn't create drift.
# Usage: update-apps.sh <resource-group> <api-image> <web-image> <validator-image>
set -euo pipefail
rg="$1"
api="$2"
web="$3"
validator="$4"

az containerapp update --name validator --resource-group "$rg" --image "$validator" --output none
az containerapp update --name api --resource-group "$rg" --image "$api" --output none
az containerapp update --name worker --resource-group "$rg" --image "$api" --output none
az containerapp update --name web --resource-group "$rg" --image "$web" --output none
az containerapp job update --name sweep --resource-group "$rg" --image "$api" --output none
echo "apps updated"
