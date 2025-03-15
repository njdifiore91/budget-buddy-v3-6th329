# This file configures the Google Cloud Run job for the Budget Management Application.
# The job executes on a scheduled basis to process transactions, analyze budget data,
# and perform automated savings transfers.

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.84.0"
    }
  }
}

# Local variables for resource naming and configuration
locals {
  job_name        = "${var.app_name}-job"
  job_description = "Budget Management Application weekly job for transaction processing and budget analysis"
}

# Cloud Run job resource that executes the Budget Management Application container
resource "google_cloud_run_v2_job" "budget_management_job" {
  name        = local.job_name
  location    = var.region
  project     = var.project_id
  description = local.job_description
  labels      = var.labels

  template {
    template {
      containers {
        image = var.container_image
        
        resources {
          limits = {
            cpu    = var.cpu
            memory = var.memory
          }
        }
        
        # Environment variables
        dynamic "env" {
          for_each = var.environment_variables
          content {
            name  = env.key
            value = env.value
          }
        }
        
        # Secret volume mounts
        dynamic "volume_mounts" {
          for_each = var.secrets
          content {
            name       = "${volume_mounts.value.name}-volume"
            mount_path = "/secrets/${volume_mounts.value.name}"
          }
        }
      }
      
      # Secret volumes for API credentials
      dynamic "volumes" {
        for_each = var.secrets
        content {
          name = "${volumes.value.name}-volume"
          secret {
            secret = volumes.value.secret_name
            items {
              version = volumes.value.version
              path    = volumes.value.name
            }
          }
        }
      }
      
      service_account = var.service_account_email
      timeout         = "${var.timeout_seconds}s"
    }
    
    # Configure the job to retry up to the specified number of times
    max_retries = var.max_retries
  }
}

# Output: The name of the Cloud Run job
output "job_name" {
  value       = google_cloud_run_v2_job.budget_management_job.name
  description = "The name of the Cloud Run job"
}

# Output: The ID of the Cloud Run job
output "job_id" {
  value       = google_cloud_run_v2_job.budget_management_job.id
  description = "The ID of the Cloud Run job"
}