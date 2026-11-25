# Shared (ADR-0020, ADR-0021): applied by the owner. Things both environments use, and the
# permissions that connect them. Kept out of the pipeline on purpose: a change here affects prod.
#
# Year one runs on free offers for new pay-as-you-go customers: one PostgreSQL B1MS server and one
# Standard registry (docs/COSTS.md). dev and prod therefore share the server, each with its own
# database and identity.

terraform {
  required_version = "~> 1.17.0"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 5.15.0" }
  }
  backend "azurerm" {
    # Partial configuration: storage_account_name comes from -backend-config (README).
    resource_group_name = "rg-belegfluss-tfstate"
    container_name      = "tfstate-shared"
    key                 = "shared.tfstate"
    use_azuread_auth    = true
  }
}

provider "azurerm" {
  features {}
  subscription_id                 = var.subscription_id
  resource_provider_registrations = "none"
  storage_use_azuread             = true
}

data "azurerm_client_config" "owner" {}

locals {
  tags = { project = "belegfluss", managed_by = "terraform", stack = "shared" }
  # Roles an environment's pipeline may hand out, and only to its own app identity.
  data_roles = {
    storage_blob  = "ba92f5b4-2d11-453d-a403-e96b0029c9fe" # Storage Blob Data Contributor
    storage_queue = "974c5e8b-45b9-4653-ba55-5f855dd0fb88" # Storage Queue Data Contributor
    openai_user   = "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd" # Cognitive Services OpenAI User
  }
}

data "azurerm_resource_group" "shared" {
  name = "rg-belegfluss-shared"
}

data "azurerm_resource_group" "environment" {
  for_each = toset(var.environments)
  name     = "rg-belegfluss-${each.key}"
}

data "azurerm_user_assigned_identity" "deploy" {
  for_each            = toset(var.environments)
  name                = "id-belegfluss-deploy-${each.key}"
  resource_group_name = "rg-belegfluss-tfstate"
}

# --- Container registry: images are built once and promoted dev -> prod by digest ---

resource "azurerm_container_registry" "main" {
  name                   = "crbelegfluss${var.name_suffix}"
  resource_group_name    = data.azurerm_resource_group.shared.name
  location               = var.location
  sku                    = "Standard"
  admin_enabled          = false # pulls and pushes use Entra identities only
  anonymous_pull_enabled = false
  tags                   = local.tags
}

# --- PostgreSQL: Entra ID sign-in only, no password exists ---

resource "azurerm_postgresql_flexible_server" "main" {
  name                          = "psql-belegfluss-${var.name_suffix}"
  resource_group_name           = data.azurerm_resource_group.shared.name
  location                      = var.location
  version                       = "18"
  sku_name                      = "B_Standard_B1ms"
  storage_mb                    = 32768
  backup_retention_days         = 7
  geo_redundant_backup_enabled  = false
  public_network_access_enabled = true # limited by the firewall rule below; private network in M9
  zone                          = "1"
  tags                          = local.tags

  authentication {
    active_directory_auth_enabled = true
    password_auth_enabled         = false
    tenant_id                     = data.azurerm_client_config.owner.tenant_id
  }

  lifecycle {
    prevent_destroy = true # holds data: deleting it needs a deliberate code change
  }
}

resource "azurerm_postgresql_flexible_server_active_directory_administrator" "owner" {
  server_name         = azurerm_postgresql_flexible_server.main.name
  resource_group_name = data.azurerm_resource_group.shared.name
  tenant_id           = data.azurerm_client_config.owner.tenant_id
  object_id           = data.azurerm_client_config.owner.object_id
  principal_name      = var.owner_principal_name
  principal_type      = "User"
}

# 0.0.0.0 means "Azure services": Container Apps have no fixed outbound address on the consumption
# plan. Every connection still needs an Entra token and TLS.
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# --- App identities: what the containers run as (one per environment) ---

resource "azurerm_user_assigned_identity" "app" {
  for_each            = toset(var.environments)
  name                = "id-belegfluss-app-${each.key}"
  resource_group_name = data.azurerm_resource_group.shared.name
  location            = var.location
  tags                = merge(local.tags, { environment = each.key })
}

resource "azurerm_role_assignment" "app_pulls_images" {
  for_each             = toset(var.environments)
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.app[each.key].principal_id
  principal_type       = "ServicePrincipal"
}

# --- What each environment's pipeline identity may do beyond its own resource group ---

resource "azurerm_role_assignment" "deploy_pushes_images" {
  for_each             = toset(var.environments)
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPush"
  principal_id         = data.azurerm_user_assigned_identity.deploy[each.key].principal_id
  principal_type       = "ServicePrincipal"
}

# Attaching the app identity to container apps needs ".../assign/action" on it.
resource "azurerm_role_assignment" "deploy_attaches_app_identity" {
  for_each             = toset(var.environments)
  scope                = azurerm_user_assigned_identity.app[each.key].id
  role_definition_name = "Managed Identity Operator"
  principal_id         = data.azurerm_user_assigned_identity.deploy[each.key].principal_id
  principal_type       = "ServicePrincipal"
}

# The pipeline may grant roles in its resource group, but only the data roles above and only to its
# own app identity (an Azure ABAC condition on the role assignment).
resource "azurerm_role_assignment" "deploy_grants_data_roles" {
  for_each             = toset(var.environments)
  scope                = data.azurerm_resource_group.environment[each.key].id
  role_definition_name = "Role Based Access Control Administrator"
  principal_id         = data.azurerm_user_assigned_identity.deploy[each.key].principal_id
  principal_type       = "ServicePrincipal"
  condition_version    = "2.0"
  condition = templatefile("${path.module}/constrained-grants.tftpl", {
    roles     = join(", ", values(local.data_roles))
    principal = azurerm_user_assigned_identity.app[each.key].principal_id
  })
}

# --- Budget: the existing €10 monthly alert (created in M1), now in code ---

resource "azurerm_consumption_budget_subscription" "monthly" {
  name            = "belegfluss"
  subscription_id = "/subscriptions/${var.subscription_id}"
  amount          = 10
  time_grain      = "Monthly"

  time_period {
    start_date = var.budget_start_date
  }

  dynamic "notification" {
    for_each = {
      actual_50    = { threshold = 50, type = "Actual" }
      actual_100   = { threshold = 100, type = "Actual" }
      forecast_100 = { threshold = 100, type = "Forecasted" }
    }
    content {
      operator       = "GreaterThan"
      threshold      = notification.value.threshold
      threshold_type = notification.value.type
      contact_emails = var.budget_contact_emails
    }
  }
}
