# One environment (dev now, prod in M4b), applied by the pipeline as that environment's deploy
# identity (ADR-0020). Everything scales to zero; nothing here holds a key or a password (ADR-0021).

terraform {
  required_version = "~> 1.17.0"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 5.15.0" }
  }
  backend "azurerm" {
    # Partial configuration: storage_account_name, container_name (tfstate-<env>) and key come from
    # -backend-config (README, deploy workflow).
    resource_group_name = "rg-belegfluss-tfstate"
    use_azuread_auth    = true
  }
}

provider "azurerm" {
  features {}
  subscription_id                 = var.subscription_id
  resource_provider_registrations = "none"
  storage_use_azuread             = true
}

locals {
  tags = { project = "belegfluss", managed_by = "terraform", environment = var.environment }
  # Public addresses follow from the environment's default domain (known after it exists).
  web_url = "https://web.${azurerm_container_app_environment.main.default_domain}"
  api_url = "https://api.${azurerm_container_app_environment.main.default_domain}"
}

data "azurerm_resource_group" "environment" {
  name = "rg-belegfluss-${var.environment}"
}

data "azurerm_container_registry" "main" {
  name                = "crbelegfluss${var.name_suffix}"
  resource_group_name = "rg-belegfluss-shared"
}

data "azurerm_postgresql_flexible_server" "main" {
  name                = "psql-belegfluss-${var.name_suffix}"
  resource_group_name = "rg-belegfluss-shared"
}

data "azurerm_user_assigned_identity" "app" {
  name                = "id-belegfluss-app-${var.environment}"
  resource_group_name = "rg-belegfluss-shared"
}

# --- Logs: one small workspace, capped so it stays within the free monthly amount ---

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-belegfluss-${var.environment}"
  resource_group_name = data.azurerm_resource_group.environment.name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  daily_quota_gb      = var.log_daily_quota_gb
  tags                = local.tags
}

resource "azurerm_container_app_environment" "main" {
  name                       = "cae-belegfluss-${var.environment}"
  resource_group_name        = data.azurerm_resource_group.environment.name
  location                   = var.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  logs_destination           = "log-analytics"
  tags                       = local.tags
  # Consumption only: no workload profiles, no private endpoint, no planned maintenance window,
  # so no environment management fee (docs/COSTS.md, checked on the bill).
}

# --- Storage for originals (blob) and processing jobs (queue): no account keys ---

resource "azurerm_storage_account" "main" {
  name                            = "stbelegfluss${var.environment}${var.name_suffix}"
  resource_group_name             = data.azurerm_resource_group.environment.name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true
  allow_nested_items_to_be_public = false
  tags                            = local.tags

  blob_properties {
    delete_retention_policy { days = 7 }
  }

  lifecycle {
    prevent_destroy = true # holds data: deleting it needs a deliberate code change
  }
}

resource "azurerm_storage_container" "documents" {
  name               = "documents"
  storage_account_id = azurerm_storage_account.main.id

  lifecycle {
    prevent_destroy = true # holds data: deleting it needs a deliberate code change
  }
}

resource "azurerm_storage_queue" "documents" {
  for_each           = toset(["documents", "documents-poison"])
  name               = each.key
  storage_account_id = azurerm_storage_account.main.id

  lifecycle {
    prevent_destroy = true # holds data: deleting it needs a deliberate code change
  }
}

resource "azurerm_role_assignment" "app_blob" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_user_assigned_identity.app.principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "app_queue" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = data.azurerm_user_assigned_identity.app.principal_id
  principal_type       = "ServicePrincipal"
}
