# One-time takeover of resources that existed before Terraform (M1 budget, M2b/M3 scripts).
# Terraform only reads them into state; after the first apply these blocks are no-ops. IDs come
# from variables (shared.auto.tfvars, never committed), filled by scripts/azure/import-ids.ps1.

locals {
  sub   = "/subscriptions/${var.subscription_id}"
  ai_rg = "${local.sub}/resourceGroups/rg-belegfluss-ai-dev"
}

import {
  to = azurerm_consumption_budget_subscription.monthly
  id = "${local.sub}/providers/Microsoft.Consumption/budgets/belegfluss"
}

import {
  to = azurerm_resource_group.ai_dev
  id = local.ai_rg
}

import {
  to = azurerm_cognitive_account.openai_dev
  id = "${local.ai_rg}/providers/Microsoft.CognitiveServices/accounts/${var.openai_dev_name}"
}

import {
  to = azurerm_cognitive_deployment.gpt_dev
  id = "${local.ai_rg}/providers/Microsoft.CognitiveServices/accounts/${var.openai_dev_name}/deployments/gpt-5.4-mini"
}

import {
  to = azurerm_cognitive_account.doc_intelligence_dev
  id = "${local.ai_rg}/providers/Microsoft.CognitiveServices/accounts/${var.doc_intelligence_dev_name}"
}

import {
  to = azurerm_user_assigned_identity.eval_ci
  id = "${local.ai_rg}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/id-belegfluss-eval-ci"
}

import {
  to = azurerm_federated_identity_credential.eval_ci
  id = "${local.ai_rg}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/id-belegfluss-eval-ci/federatedIdentityCredentials/github-eval"
}

import {
  to = azurerm_role_assignment.owner_uses_openai_dev
  id = var.existing_role_assignment_ids["owner_uses_openai_dev"]
}

import {
  to = azurerm_role_assignment.owner_uses_doc_intelligence_dev
  id = var.existing_role_assignment_ids["owner_uses_doc_intelligence_dev"]
}

import {
  to = azurerm_role_assignment.eval_uses_openai_dev
  id = var.existing_role_assignment_ids["eval_uses_openai_dev"]
}

import {
  to = azurerm_role_assignment.eval_uses_doc_intelligence_dev
  id = var.existing_role_assignment_ids["eval_uses_doc_intelligence_dev"]
}
