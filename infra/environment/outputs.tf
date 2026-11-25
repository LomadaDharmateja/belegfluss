output "web_url" {
  value = local.web_url
}

output "api_url" {
  value = local.api_url
}

output "storage_account" {
  value = azurerm_storage_account.main.name
}
