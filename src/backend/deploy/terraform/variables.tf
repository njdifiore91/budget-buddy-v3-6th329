# Basic GCP project configuration
variable "project_id" {
  type        = string
  description = "The Google Cloud Project ID where resources will be deployed"
}

variable "region" {
  type        = string
  description = "The Google Cloud region where resources will be deployed"
  default     = "us-east1"
}

variable "app_name" {
  type        = string
  description = "Name of the Budget Management Application"
  default     = "budget-management"
}

# Container and service account configuration
variable "container_image" {
  type        = string
  description = "The container image to deploy (including tag)"
}

variable "service_account_email" {
  type        = string
  description = "The service account email to use for the application"
}

# Scheduling configuration
variable "schedule_cron" {
  type        = string
  description = "Cron schedule expression for the Cloud Scheduler job"
  default     = "0 12 * * 0"  # Every Sunday at 12:00 PM
}

variable "schedule_timezone" {
  type        = string
  description = "Timezone for the Cloud Scheduler job"
  default     = "America/New_York"  # EST timezone
}

# Resource allocation
variable "cpu" {
  type        = string
  description = "CPU allocation for the Cloud Run job"
  default     = "1"
}

variable "memory" {
  type        = string
  description = "Memory allocation for the Cloud Run job"
  default     = "2Gi"
}

variable "timeout_seconds" {
  type        = number
  description = "Maximum execution time for the Cloud Run job in seconds"
  default     = 600  # 10 minutes
}

variable "max_retries" {
  type        = number
  description = "Maximum number of retries for the Cloud Run job"
  default     = 3
}

# Environment configuration
variable "environment_variables" {
  type        = map(string)
  description = "Environment variables to set in the Cloud Run job"
  default     = {}
}

# Secret Manager configuration
variable "create_secrets" {
  type        = bool
  description = "Whether to create the secrets in Secret Manager"
  default     = true
}

# Capital One API secret IDs
variable "capital_one_api_key_secret_id" {
  type        = string
  description = "Secret ID for the Capital One API key"
  default     = "capital-one-api-key"
}

variable "capital_one_client_id_secret_id" {
  type        = string
  description = "Secret ID for the Capital One client ID"
  default     = "capital-one-client-id"
}

variable "capital_one_client_secret_secret_id" {
  type        = string
  description = "Secret ID for the Capital One client secret"
  default     = "capital-one-client-secret"
}

variable "capital_one_checking_account_id_secret_id" {
  type        = string
  description = "Secret ID for the Capital One checking account ID"
  default     = "capital-one-checking-account-id"
}

variable "capital_one_savings_account_id_secret_id" {
  type        = string
  description = "Secret ID for the Capital One savings account ID"
  default     = "capital-one-savings-account-id"
}

# Gemini API secret ID
variable "gemini_api_key_secret_id" {
  type        = string
  description = "Secret ID for the Gemini API key"
  default     = "gemini-api-key"
}

# Google Sheets and Gmail secret IDs
variable "master_budget_sheet_id_secret_id" {
  type        = string
  description = "Secret ID for the Master Budget Google Sheet ID"
  default     = "master-budget-sheet-id"
}

variable "weekly_spending_sheet_id_secret_id" {
  type        = string
  description = "Secret ID for the Weekly Spending Google Sheet ID"
  default     = "weekly-spending-sheet-id"
}

variable "google_sheets_credentials_secret_id" {
  type        = string
  description = "Secret ID for the Google Sheets API credentials"
  default     = "google-sheets-credentials"
}

variable "gmail_credentials_secret_id" {
  type        = string
  description = "Secret ID for the Gmail API credentials"
  default     = "gmail-credentials"
}

# Generic secrets variable for mounting
variable "secrets" {
  type = list(object({
    name        = string
    secret_name = string
    version     = string
  }))
  description = "List of secrets to mount in the Cloud Run job"
  default     = []
}