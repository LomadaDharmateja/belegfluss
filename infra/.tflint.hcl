# tflint for all stacks (run from each stack folder with --config ../.tflint.hcl).
plugin "terraform" {
  enabled = true
  preset  = "recommended"
}

# Checks Azure-specific values (SKU names, locations, ...) against the provider's schema.
plugin "azurerm" {
  enabled = true
  version = "0.33.0"
  source  = "github.com/terraform-linters/tflint-ruleset-azurerm"
}
