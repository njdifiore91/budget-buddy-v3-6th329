# Terraform configuration for Budget Management Application on Google Cloud Platform
terraform {
  required_version = ">= 1.0.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.84.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 4.84.0"
    }
  }
}

# Google Cloud Platform provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Local variables for secret configuration and resource naming
locals {
  secret_mounts = [
    {
      name        = "CAPITAL_ONE_API_KEY"
      secret_name = var.capital_one_api_key_secret_id
      version     = "latest"
    },
    {
      name        = "CAPITAL_ONE_CLIENT_ID"
      secret_name = var.capital_one_client_id_secret_id
      version     = "latest"
    },
    {
      name        = "CAPITAL_ONE_CLIENT_SECRET"
      secret_name = var.capital_one_client_secret_secret_id
      version     = "latest"
    },
    {
      name        = "CAPITAL_ONE_CHECKING_ACCOUNT_ID"
      secret_name = var.capital_one_checking_account_id_secret_id
      version     = "latest"
    },
    {
      name        = "CAPITAL_ONE_SAVINGS_ACCOUNT_ID"
      secret_name = var.capital_one_savings_account_id_secret_id
      version     = "latest"
    },
    {
      name        = "GEMINI_API_KEY"
      secret_name = var.gemini_api_key_secret_id
      version     = "latest"
    },
    {
      name        = "MASTER_BUDGET_SHEET_ID"
      secret_name = var.master_budget_sheet_id_secret_id
      version     = "latest"
    },
    {
      name        = "WEEKLY_SPENDING_SHEET_ID"
      secret_name = var.weekly_spending_sheet_id_secret_id
      version     = "latest"
    },
    {
      name        = "GOOGLE_SHEETS_CREDENTIALS"
      secret_name = var.google_sheets_credentials_secret_id
      version     = "latest"
    },
    {
      name        = "GMAIL_CREDENTIALS"
      secret_name = var.gmail_credentials_secret_id
      version     = "latest"
    }
  ]
}

# Cloud Run job module for the Budget Management Application
module "cloud_run" {
  source                = "./cloud_run"
  project_id            = var.project_id
  region                = var.region
  app_name              = var.app_name
  container_image       = var.container_image
  service_account_email = var.service_account_email
  cpu                   = var.cpu
  memory                = var.memory
  timeout_seconds       = var.timeout_seconds
  max_retries           = var.max_retries
  environment_variables = var.environment_variables
  secrets               = local.secret_mounts
}

# Secret Manager module for storing API credentials and sensitive configuration
module "secret_manager" {
  source                                  = "./secret_manager"
  project_id                              = var.project_id
  create_secrets                          = var.create_secrets
  capital_one_api_key_secret_id           = var.capital_one_api_key_secret_id
  capital_one_client_id_secret_id         = var.capital_one_client_id_secret_id
  capital_one_client_secret_secret_id     = var.capital_one_client_secret_secret_id
  capital_one_checking_account_id_secret_id = var.capital_one_checking_account_id_secret_id
  capital_one_savings_account_id_secret_id = var.capital_one_savings_account_id_secret_id
  gemini_api_key_secret_id                = var.gemini_api_key_secret_id
  master_budget_sheet_id_secret_id        = var.master_budget_sheet_id_secret_id
  weekly_spending_sheet_id_secret_id      = var.weekly_spending_sheet_id_secret_id
  google_sheets_credentials_secret_id     = var.google_sheets_credentials_secret_id
  gmail_credentials_secret_id             = var.gmail_credentials_secret_id
}

# Cloud Scheduler module for triggering the Budget Management Application on a weekly schedule
module "cloud_scheduler" {
  source                = "./cloud_scheduler"
  project_id            = var.project_id
  region                = var.region
  app_name              = var.app_name
  schedule_cron         = var.schedule_cron
  schedule_timezone     = var.schedule_timezone
  cloud_run_job_name    = module.cloud_run.job_name
  service_account_email = var.service_account_email
  
  depends_on            = [module.cloud_run]
}

# IAM module for setting up necessary permissions for the Budget Management Application
module "iam" {
  source                = "./iam"
  project_id            = var.project_id
  service_account_email = var.service_account_email
  secret_ids            = module.secret_manager.secret_ids
  
  depends_on            = [module.secret_manager]
}

# Outputs for resource references
output "cloud_run_job_name" {
  description = "The name of the Cloud Run job"
  value       = module.cloud_run.job_name
}

output "cloud_run_job_id" {
  description = "The ID of the Cloud Run job"
  value       = module.cloud_run.job_id
}

output "cloud_scheduler_job_name" {
  description = "The name of the Cloud Scheduler job"
  value       = module.cloud_scheduler.job_name
}

output "cloud_scheduler_job_id" {
  description = "The ID of the Cloud Scheduler job"
  value       = module.cloud_scheduler.job_id
}

output "secret_manager_secret_ids" {
  description = "The list of Secret Manager secret IDs"
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