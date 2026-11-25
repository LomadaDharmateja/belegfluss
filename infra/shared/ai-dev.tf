# The development AI resources, created by scripts in M2b/M3 (scripts/azure/dev-openai.ps1,
# dev-eval.ps1) and taken over by Terraform in M4a (imports.tf). Same settings as created:
# keys switched off, sign-in with Entra ID only.

resource "azurerm_resource_group" "ai_dev" {
  name     = "rg-belegfluss-ai-dev"
  location = var.location
  tags     = local.tags
}

resource "azurerm_cognitive_account" "openai_dev" {
  name                          = var.openai_dev_name
  resource_group_name           = azurerm_resource_group.ai_dev.name
  location                      = var.location
  kind                          = "OpenAI"
  sku_name                      = "S0"
  custom_subdomain_name         = var.openai_dev_name
  local_auth_enabled            = false
  public_network_access_enabled = true
  tags                          = local.tags
}

resource "azurerm_cognitive_deployment" "gpt_dev" {
  name                   = "gpt-5.4-mini"
  cognitive_account_id   = azurerm_cognitive_account.openai_dev.id
  rai_policy_name        = "Microsoft.DefaultV2"
  version_upgrade_option = "OnceNewDefaultVersionAvailable"

  model {
    format  = "OpenAI"
    name    = "gpt-5.4-mini"
    version = "2026-03-17"
  }

  sku {
    name     = "DataZoneStandard" # processed only inside the EU data zone (ADR-0016)
    capacity = 100                # thousand tokens per minute; a rate limit, not a cost
  }
}

resource "azurerm_cognitive_account" "doc_intelligence_dev" {
  name                          = var.doc_intelligence_dev_name
  resource_group_name           = azurerm_resource_group.ai_dev.name
  location                      = var.location
  kind                          = "FormRecognizer"
  sku_name                      = "F0" # free tier, the M3 baseline
  custom_subdomain_name         = var.doc_intelligence_dev_name
  local_auth_enabled            = false
  public_network_access_enabled = true
  tags                          = local.tags
}

# --- Who may use them ---

resource "azurerm_role_assignment" "owner_uses_openai_dev" {
  scope                = azurerm_cognitive_account.openai_dev.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = data.azurerm_client_config.owner.object_id
}

resource "azurerm_role_assignment" "owner_uses_doc_intelligence_dev" {
  scope                = azurerm_cognitive_account.doc_intelligence_dev.id
  role_definition_name = "Cognitive Services User"
  principal_id         = data.azurerm_client_config.owner.object_id
}

resource "azurerm_role_assignment" "app_dev_uses_openai_dev" {
  scope                = azurerm_cognitive_account.openai_dev.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.app["dev"].principal_id
  principal_type       = "ServicePrincipal"
}

# --- Live evaluation from GitHub (ADR-0019) ---

resource "azurerm_user_assigned_identity" "eval_ci" {
  name                = "id-belegfluss-eval-ci"
  resource_group_name = azurerm_resource_group.ai_dev.name
  location            = var.location
  tags                = local.tags
}

resource "azurerm_federated_identity_credential" "eval_ci" {
  name                      = "github-eval"
  user_assigned_identity_id = azurerm_user_assigned_identity.eval_ci.id
  issuer                    = "https://token.actions.githubusercontent.com"
  audience                  = ["api://AzureADTokenExchange"]
  subject                   = "repo:${var.github_owner}@${var.github_owner_id}/${var.github_repo}@${var.github_repo_id}:environment:eval"
}

resource "azurerm_role_assignment" "eval_uses_openai_dev" {
  scope                = azurerm_cognitive_account.openai_dev.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.eval_ci.principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "eval_uses_doc_intelligence_dev" {
  scope                = azurerm_cognitive_account.doc_intelligence_dev.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_user_assigned_identity.eval_ci.principal_id
  principal_type       = "ServicePrincipal"
}
