variable "subscription_id" {
  type = string
}

variable "location" {
  description = "Apps, storage and logs, next to the database (ADR-0021: Sweden Central)."
  type        = string
  default     = "swedencentral"
}

variable "environment" {
  description = "dev or prod."
  type        = string
  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "dev or prod."
  }
}

variable "name_suffix" {
  description = "Same suffix as in bootstrap and shared."
  type        = string
}

variable "images" {
  description = "Images used when an app is first created; later deploys update them outside Terraform."
  type        = map(string)
  validation {
    condition     = alltrue([for name in ["api", "web", "validator"] : contains(keys(var.images), name)])
    error_message = "Needs api, web and validator."
  }
}

variable "log_daily_quota_gb" {
  description = "Daily log cap. Two environments at 0.08 GB stay below the free 5 GB a month."
  type        = number
  default     = 0.08
}

# --- Sign-in (Entra External ID): public identifiers, not secrets (docs/setup/entra-external-id.md) ---

variable "auth_issuer" {
  type = string
}

variable "auth_jwks_url" {
  type = string
}

variable "auth_audience" {
  description = "The API's application (client) ID."
  type        = string
}

variable "entra_client_id" {
  description = "The web app's application (client) ID."
  type        = string
}

variable "entra_tenant_subdomain" {
  type = string
}

variable "entra_tenant_id" {
  type = string
}

variable "entra_api_scope" {
  type = string
}

variable "openai_endpoint" {
  description = "Azure OpenAI endpoint for AI reading; empty switches AI reading off."
  type        = string
  default     = ""
}
