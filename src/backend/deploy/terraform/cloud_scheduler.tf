# Define the Cloud Scheduler job resource to trigger the Budget Management Application
# on a weekly schedule (Sunday at 12 PM EST)
# Provider: hashicorp/google ~> 4.84.0

# Cloud Run job name variable (if not already defined)
variable "cloud_run_job_name" {
  type        = string
  description = "The name of the Cloud Run job to trigger"
}

# Local values for resource naming and configuration
locals {
  scheduler_job_name = "${var.app_name}-scheduler"
  scheduler_job_description = "Weekly scheduler for Budget Management Application (Sundays at 12 PM EST)"
  
  # Retry configuration for handling transient failures
  retry_config = {
    retry_count = 3
    min_backoff_duration = "1s"
    max_backoff_duration = "60s"
    max_retry_duration = "300s"
    max_doublings = 3
  }
}

# Cloud Scheduler job resource
resource "google_cloud_scheduler_job" "budget_management_scheduler" {
  name        = local.scheduler_job_name
  description = local.scheduler_job_description
  schedule    = var.schedule_cron
  time_zone   = var.schedule_timezone
  project     = var.project_id
  region      = var.region
  
  # Retry configuration using local values
  retry_config = local.retry_config
  
  # HTTP target for triggering the Cloud Run job
  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${var.cloud_run_job_name}:run"
    
    # Authentication with OAuth token from service account
    oauth_token {
      service_account_email = var.service_account_email
    }
  }
}

# Output the scheduler job name
output "scheduler_job_name" {
  value       = google_cloud_scheduler_job.budget_management_scheduler.name
  description = "The name of the Cloud Scheduler job"
}

# Output the scheduler job ID
output "scheduler_job_id" {
  value       = google_cloud_scheduler_job.budget_management_scheduler.id
  description = "The ID of the Cloud Scheduler job"
}