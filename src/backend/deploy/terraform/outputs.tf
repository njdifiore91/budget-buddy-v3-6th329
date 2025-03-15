# Output definitions for the Budget Management Application infrastructure

output "cloud_run_job_name" {
  description = "The name of the Cloud Run job"
  value       = module.cloud_run.job_name
}

output "cloud_run_job_id" {
  description = "The full resource ID of the Cloud Run job"
  value       = module.cloud_run.job_id
}

output "cloud_scheduler_job_name" {
  description = "The name of the Cloud Scheduler job"
  value       = module.cloud_scheduler.scheduler_job_name
}

output "cloud_scheduler_job_id" {
  description = "The full resource ID of the Cloud Scheduler job"
  value       = module.cloud_scheduler.scheduler_job_id
}

output "secret_manager_secret_ids" {
  description = "List of Secret Manager secret IDs created for the application"
  value       = module.secret_manager.secret_ids
}

output "deployment_region" {
  description = "The GCP region where resources are deployed"
  value       = var.region
}

output "project_id" {
  description = "The GCP project ID where resources are deployed"
  value       = var.project_id
}