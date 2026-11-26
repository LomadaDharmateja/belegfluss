output "registry" {
  value = azurerm_container_registry.main.login_server
}

output "database_host" {
  value = azurerm_postgresql_flexible_server.main.fqdn
}

output "app_identity_client_ids" {
  value = { for env, identity in azurerm_user_assigned_identity.app : env => identity.client_id }
}

output "openai_dev_endpoint" {
  value = azurerm_cognitive_account.openai_dev.endpoint
}
