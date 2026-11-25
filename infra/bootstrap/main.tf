# Bootstrap (ADR-0020): applied once by the owner with `az login`. Creates what the other stacks
# need before they can run: resource groups, the Terraform state storage, and one deploy identity
# per environment that GitHub Actions signs in as (OIDC, no secret).
#
# State: local on purpose (it creates the remote state storage). Every name derives from
# var.name_suffix, so a lost local state can be rebuilt with `terraform import`.

terraform {
  required_version = "~> 1.17.0"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 5.15.0" }
  }
}

provider "azurerm" {
  features {}
  subscription_id                 = var.subscription_id
  resource_provider_registrations = "none" # registered below, at apply time only
  storage_use_azuread             = true
}

data "azurerm_client_config" "owner" {}

locals {
  tags = { project = "belegfluss", managed_by = "terraform", stack = "bootstrap" }
  # One state container per stack, so an environment's identity can only touch its own state.
  state_containers = concat(["shared"], var.environments)
}

# Azure services the stacks use that this subscription hadn't used yet (CognitiveServices,
# ManagedIdentity and Consumption were registered in M1–M3). Registering is free.
resource "azurerm_resource_provider_registration" "needed" {
  for_each = toset([
    "Microsoft.App",
    "Microsoft.ContainerRegistry",
    "Microsoft.DBforPostgreSQL",
    "Microsoft.OperationalInsights",
    "Microsoft.Storage",
  ])
  name = each.key
}

resource "azurerm_resource_group" "tfstate" {
  name     = "rg-belegfluss-tfstate"
  location = var.location
  tags     = local.tags
}

resource "azurerm_resource_group" "shared" {
  name     = "rg-belegfluss-shared"
  location = var.location
  tags     = local.tags
}

resource "azurerm_resource_group" "environment" {
  for_each = toset(var.environments)
  name     = "rg-belegfluss-${each.key}"
  location = var.location
  tags     = merge(local.tags, { environment = each.key })
}

# --- Terraform state: keys switched off, versioned, deletions recoverable ---

resource "azurerm_storage_account" "tfstate" {
  name                            = "stbelegflusstf${var.name_suffix}"
  resource_group_name             = azurerm_resource_group.tfstate.name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true
  allow_nested_items_to_be_public = false
  tags                            = local.tags
  depends_on                      = [azurerm_resource_provider_registration.needed]

  blob_properties {
    versioning_enabled = true
    delete_retention_policy { days = 30 }
    container_delete_retention_policy { days = 30 }
  }
}

resource "azurerm_storage_container" "tfstate" {
  for_each           = toset(local.state_containers)
  name               = "tfstate-${each.key}"
  storage_account_id = azurerm_storage_account.tfstate.id
}

resource "azurerm_role_assignment" "owner_state" {
  scope                = azurerm_storage_account.tfstate.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.owner.object_id
}

# --- Deploy identities for GitHub Actions (one per environment) ---
# They live in the state resource group, not in their environment's group: an identity that may
# change its environment must not be able to change its own trust (federated credentials).

resource "azurerm_user_assigned_identity" "deploy" {
  for_each            = toset(var.environments)
  name                = "id-belegfluss-deploy-${each.key}"
  resource_group_name = azurerm_resource_group.tfstate.name
  location            = var.location
  tags                = merge(local.tags, { environment = each.key })
}

resource "azurerm_federated_identity_credential" "deploy" {
  for_each                  = toset(var.environments)
  name                      = "github-${each.key}"
  user_assigned_identity_id = azurerm_user_assigned_identity.deploy[each.key].id
  issuer                    = "https://token.actions.githubusercontent.com"
  audience                  = ["api://AzureADTokenExchange"]
  # GitHub's immutable subject (repositories created after 2026-07-15, see ADR-0019): only jobs that
  # run in this repository's GitHub environment of the same name.
  subject = "repo:${var.github_owner}@${var.github_owner_id}/${var.github_repo}@${var.github_repo_id}:environment:${each.key}"
}

resource "azurerm_role_assignment" "deploy_environment" {
  for_each             = toset(var.environments)
  scope                = azurerm_resource_group.environment[each.key].id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.deploy[each.key].principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "deploy_reads_shared" {
  for_each             = toset(var.environments)
  scope                = azurerm_resource_group.shared.id
  role_definition_name = "Reader"
  principal_id         = azurerm_user_assigned_identity.deploy[each.key].principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "deploy_state" {
  for_each             = toset(var.environments)
  scope                = azurerm_storage_container.tfstate[each.key].id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.deploy[each.key].principal_id
  principal_type       = "ServicePrincipal"
}
