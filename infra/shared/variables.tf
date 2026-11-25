variable "subscription_id" {
  type = string
}

variable "location" {
  type    = string
  default = "germanywestcentral"
}

variable "name_suffix" {
  description = "Same suffix as in bootstrap."
  type        = string
}

variable "environments" {
  type    = list(string)
  default = ["dev"]
}

variable "owner_principal_name" {
  description = "The owner's Entra sign-in name; it becomes the database administrator role name."
  type        = string
}

variable "budget_contact_emails" {
  description = "Who gets the budget emails (kept out of the repository)."
  type        = list(string)
}

variable "budget_start_date" {
  description = "Start of the existing budget (RFC 3339), e.g. 2026-11-01T00:00:00Z."
  type        = string
}

variable "openai_dev_name" {
  description = "Name of the existing dev Azure OpenAI account (M2b)."
  type        = string
}

variable "doc_intelligence_dev_name" {
  description = "Name of the existing Document Intelligence F0 account (M3)."
  type        = string
}

variable "existing_role_assignment_ids" {
  description = "IDs of the four role assignments made by the M2b/M3 scripts, for the import."
  type        = map(string)
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
  type = string
}

variable "github_repo_id" {
  type = string
}
