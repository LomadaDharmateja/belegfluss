# The four apps and two jobs (ARCHITECTURE §8.2). All run as the environment's app identity and
# pull from the shared registry with it. min_replicas = 0 everywhere: an idle environment costs
# nothing, and the first request after a quiet period wakes it (cold start, measured in M4a.md).
#
# Images: set here only when an app is first created. After that the pipeline deploys new images
# (`az containerapp update`), so Terraform ignores them and `terraform plan` shows no drift.

locals {
  identity_id = data.azurerm_user_assigned_identity.app.id
  database_url = join("", [
    "postgresql+psycopg://${data.azurerm_user_assigned_identity.app.name}",
    "@${data.azurerm_postgresql_flexible_server.main.fqdn}:5432/belegfluss_${var.environment}",
    "?sslmode=require",
  ])
  # Same settings for the API, the worker and the jobs (one image, ADR-0004).
  backend_env = {
    BELEGFLUSS_DATABASE_URL        = local.database_url
    BELEGFLUSS_DATABASE_ENTRA_AUTH = "true"
    BELEGFLUSS_STORAGE_ACCOUNT     = azurerm_storage_account.main.name
    AZURE_CLIENT_ID                = data.azurerm_user_assigned_identity.app.client_id
    AZURE_TOKEN_CREDENTIALS        = "ManagedIdentityCredential"
  }
}

resource "azurerm_container_app" "api" {
  name                         = "api"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = data.azurerm_resource_group.environment.name
  revision_mode                = "Single"
  max_inactive_revisions       = 3
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [local.identity_id]
  }

  registry {
    server   = data.azurerm_container_registry.main.login_server
    identity = local.identity_id
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "auto"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 0
    max_replicas = 2

    container {
      name   = "api"
      image  = var.images["api"]
      cpu    = 0.5
      memory = "1Gi"

      dynamic "env" {
        for_each = merge(local.backend_env, {
          BELEGFLUSS_AUTH_ISSUER   = var.auth_issuer
          BELEGFLUSS_AUTH_JWKS_URL = var.auth_jwks_url
          BELEGFLUSS_AUTH_AUDIENCE = var.auth_audience
          BELEGFLUSS_CORS_ORIGINS  = jsonencode([local.web_url])
          FORWARDED_ALLOW_IPS      = "*" # only the Container Apps proxy can reach the container
        })
        content {
          name  = env.key
          value = env.value
        }
      }

      readiness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/health"
      }
      liveness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/health"
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }
}

resource "azurerm_container_app" "web" {
  name                         = "web"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = data.azurerm_resource_group.environment.name
  revision_mode                = "Single"
  max_inactive_revisions       = 3
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [local.identity_id]
  }

  registry {
    server   = data.azurerm_container_registry.main.login_server
    identity = local.identity_id
  }

  ingress {
    external_enabled = true
    target_port      = 3000
    transport        = "auto"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 0
    max_replicas = 2

    container {
      name   = "web"
      image  = var.images["web"]
      cpu    = 0.25
      memory = "0.5Gi"

      dynamic "env" {
        for_each = {
          ENTRA_CLIENT_ID        = var.entra_client_id
          ENTRA_TENANT_SUBDOMAIN = var.entra_tenant_subdomain
          ENTRA_TENANT_ID        = var.entra_tenant_id
          ENTRA_API_SCOPE        = var.entra_api_scope
          API_BASE_URL           = local.api_url # called from the browser
        }
        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }
}

# The KoSIT validator has no authentication (ADR-0005): internal ingress only, so it is reachable
# inside this environment and not from the internet. (Per-app isolation needs Kubernetes, M8.)
resource "azurerm_container_app" "validator" {
  name                         = "validator"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = data.azurerm_resource_group.environment.name
  revision_mode                = "Single"
  max_inactive_revisions       = 3
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [local.identity_id]
  }

  registry {
    server   = data.azurerm_container_registry.main.login_server
    identity = local.identity_id
  }

  ingress {
    external_enabled = false
    target_port      = 8080
    transport        = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name   = "validator"
      image  = var.images["validator"]
      cpu    = 0.5
      memory = "1Gi" # 627 MiB measured with a 512 MB heap (M2a)

      startup_probe {
        transport               = "HTTP"
        port                    = 8080
        path                    = "/server/health"
        interval_seconds        = 5
        failure_count_threshold = 24 # the JVM loads the XRechnung rules: up to 2 minutes
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }
}

# The worker has no ingress. KEDA wakes it when the queue has messages and scales it back to zero;
# it reads the queue length with the app identity (no connection string).
resource "azurerm_container_app" "worker" {
  name                         = "worker"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = data.azurerm_resource_group.environment.name
  revision_mode                = "Single"
  max_inactive_revisions       = 3
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [local.identity_id]
  }

  registry {
    server   = data.azurerm_container_registry.main.login_server
    identity = local.identity_id
  }

  template {
    min_replicas = 0
    max_replicas = 2

    custom_scale_rule {
      name             = "documents-queue"
      custom_rule_type = "azure-queue"
      identity_id      = local.identity_id
      metadata = {
        accountName = azurerm_storage_account.main.name
        queueName   = "documents"
        queueLength = "1"
      }
    }

    container {
      name    = "worker"
      image   = var.images["api"]
      command = ["python", "-m", "belegfluss.worker"]
      cpu     = 0.5
      memory  = "1Gi"

      dynamic "env" {
        for_each = merge(local.backend_env, {
          BELEGFLUSS_VALIDATOR_URL   = "http://validator" # internal ingress, port 80 -> 8080
          BELEGFLUSS_OPENAI_ENDPOINT = var.openai_endpoint
        })
        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }
}

# --- Jobs ---

# Database migrations, started by the pipeline before the apps get a new image.
resource "azurerm_container_app_job" "migrate" {
  name                         = "migrate"
  location                     = var.location
  resource_group_name          = data.azurerm_resource_group.environment.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  replica_timeout_in_seconds   = 600
  replica_retry_limit          = 0
  tags                         = local.tags

  manual_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [local.identity_id]
  }

  registry {
    server   = data.azurerm_container_registry.main.login_server
    identity = local.identity_id
  }

  template {
    container {
      name    = "migrate"
      image   = var.images["api"]
      command = ["alembic", "upgrade", "head"]
      cpu     = 0.25
      memory  = "0.5Gi"

      dynamic "env" {
        for_each = local.backend_env
        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }
}

# The sweep built into the worker doesn't run while the worker is at zero, so it also runs on a
# schedule (ADR-0004: re-enqueue documents that waited too long).
resource "azurerm_container_app_job" "sweep" {
  name                         = "sweep"
  location                     = var.location
  resource_group_name          = data.azurerm_resource_group.environment.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  replica_timeout_in_seconds   = 300
  replica_retry_limit          = 0
  tags                         = local.tags

  schedule_trigger_config {
    cron_expression          = "*/15 * * * *"
    parallelism              = 1
    replica_completion_count = 1
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [local.identity_id]
  }

  registry {
    server   = data.azurerm_container_registry.main.login_server
    identity = local.identity_id
  }

  template {
    container {
      name    = "sweep"
      image   = var.images["api"]
      command = ["python", "-m", "belegfluss.sweep"]
      cpu     = 0.25
      memory  = "0.5Gi"

      dynamic "env" {
        for_each = local.backend_env
        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }
}
