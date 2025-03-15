# IAM configuration for the Budget Management Application
# This file defines the necessary IAM permissions for the application's service account

# Variable for the Google Cloud Project ID
variable "project_id" {
  type        = string
  description = "The Google Cloud Project ID where resources will be deployed"
}

# Variable for the service account email
variable "service_account_email" {
  type        = string
  description = "The service account email to use for the application"
}

# Variable for Secret Manager secret IDs
variable "secret_ids" {
  type        = list(string)
  description = "List of Secret Manager secret IDs to grant access to"
}

# Local variables for IAM configuration
locals {
  # Define the roles required by the service account following the principle of least privilege
  service_account_roles = [
    "roles/run.invoker",               # Allows invoking Cloud Run jobs
    "roles/secretmanager.secretAccessor", # Allows accessing secrets in Secret Manager
    "roles/logging.logWriter",         # Allows writing logs 
    "roles/cloudscheduler.jobRunner"   # Allows running Cloud Scheduler jobs
  ]
  
  # Format the service account member string
  service_account_member = "serviceAccount:${var.service_account_email}"
}

# Project-level IAM role bindings for the service account
resource "google_project_iam_member" "service_account_roles" {
  for_each = toset(local.service_account_roles)
  
  project = var.project_id
  role    = each.value
  member  = local.service_account_member
}

# Grant access to specific secrets in Secret Manager
resource "google_secret_manager_secret_iam_member" "secret_accessor" {
  for_each  = toset(var.secret_ids)
  
  project   = var.project_id
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = local.service_account_member
}

# Grant access to Google Sheets API
resource "google_project_iam_member" "sheets_api_access" {
  project = var.project_id
  role    = "roles/sheets.reader"
  member  = local.service_account_member
}

# Grant access to Gmail API
resource "google_project_iam_member" "gmail_api_access" {
  project = var.project_id
  role    = "roles/gmail.sender"
  member  = local.service_account_member
}

# Output the list of IAM roles granted to the service account
output "service_account_roles" {
  value       = local.service_account_roles
  description = "List of IAM roles granted to the service account"
}