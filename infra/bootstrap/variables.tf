variable "subscription_id" {
  description = "Azure subscription (from bootstrap.auto.tfvars, never committed)."
  type        = string
}

variable "location" {
  type    = string
  default = "germanywestcentral"
}

variable "name_suffix" {
  description = "Short lowercase suffix that makes global names unique (storage, registry, database)."
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9]{4}$", var.name_suffix))
    error_message = "Four lowercase letters or digits."
  }
}

variable "environments" {
  description = "M4a: dev. M4b adds prod."
  type        = list(string)
  default     = ["dev"]
}

variable "github_owner" {
  type    = string
  default = "LomadaDharmateja"
}

variable "github_repo" {
  type    = string
  default = "belegfluss"
}

variable "github_owner_id" {
  description = "Numeric GitHub owner ID (gh api repos/OWNER/REPO --jq .owner.id)."
  type        = string
}

variable "github_repo_id" {
  description = "Numeric GitHub repository ID (gh api repos/OWNER/REPO --jq .id)."
  type        = string
}
