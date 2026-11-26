output "tfstate_account" {
  value = azurerm_storage_account.tfstate.name
}

output "deploy_client_ids" {
  description = "AZURE_CLIENT_ID per GitHub environment (an identifier, not a secret)."
  value       = { for env, identity in azurerm_user_assigned_identity.deploy : env => identity.client_id }
}

output "tenant_id" {
  value = data.azurerm_client_config.owner.tenant_id
}
