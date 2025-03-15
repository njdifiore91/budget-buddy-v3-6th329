# Secret Manager configuration for the Budget Management Application
# This file defines all the secret resources needed for secure API authentication

# Local variables for secret configuration
locals {
  secret_ids = [
    "${var.capital_one_api_key_secret_id}",
    "${var.capital_one_client_id_secret_id}",
    "${var.capital_one_client_secret_secret_id}",
    "${var.capital_one_checking_account_id_secret_id}",
    "${var.capital_one_savings_account_id_secret_id}",
    "${var.gemini_api_key_secret_id}",
    "${var.master_budget_sheet_id_secret_id}",
    "${var.weekly_spending_sheet_id_secret_id}",
    "${var.google_sheets_credentials_secret_id}",
    "${var.gmail_credentials_secret_id}"
  ]
}

# Capital One API secrets
resource "google_secret_manager_secret" "capital_one_api_key" {
  count     = var.create_secrets ? 1 : 0
  project   = var.project_id
  secret_id = var.capital_one_api_key_secret_id
  
  replication {
    auto {}
  }
  
  labels = {
    application = "budget-management"
    environment = "production"
  }
}

resource "google_secret_manager_secret" "capital_one_client_id" {
  count     = var.create_secrets ? 1 : 0
  project   = var.project_id
  secret_id = var.capital_one_client_id_secret_id
  
  replication {
    auto {}
  }
  
  labels = {
    application = "budget-management"
    environment = "production"
  }
}

resource "google_secret_manager_secret" "capital_one_client_secret" {
  count     = var.create_secrets ? 1 : 0
  project   = var.project_id
  secret_id = var.capital_one_client_secret_secret_id
  
  replication {
    auto {}
  }
  
  labels = {
    application = "budget-management"
    environment = "production"
  }
}

resource "google_secret_manager_secret" "capital_one_checking_account_id" {
  count     = var.create_secrets ? 1 : 0
  project   = var.project_id
  secret_id = var.capital_one_checking_account_id_secret_id
  
  replication {
    auto {}
  }
  
  labels = {
    application = "budget-management"
    environment = "production"
  }
}

resource "google_secret_manager_secret" "capital_one_savings_account_id" {
  count     = var.create_secrets ? 1 : 0
  project   = var.project_id
  secret_id = var.capital_one_savings_account_id_secret_id
  
  replication {
    auto {}
  }
  
  labels = {
    application = "budget-management"
    environment = "production"
  }
}

# Gemini API secret
resource "google_secret_manager_secret" "gemini_api_key" {
  count     = var.create_secrets ? 1 : 0
  project   = var.project_id
  secret_id = var.gemini_api_key_secret_id
  
  replication {
    auto {}
  }
  
  labels = {
    application = "budget-management"
    environment = "production"
  }
}

# Google Sheets related secrets
resource "google_secret_manager_secret" "master_budget_sheet_id" {
  count     = var.create_secrets ? 1 : 0
  project   = var.project_id
  secret_id = var.master_budget_sheet_id_secret_id
  
  replication {
    auto {}
  }
  
  labels = {
    application = "budget-management"
    environment = "production"
  }
}

resource "google_secret_manager_secret" "weekly_spending_sheet_id" {
  count     = var.create_secrets ? 1 : 0
  project   = var.project_id
  secret_id = var.weekly_spending_sheet_id_secret_id
  
  replication {
    auto {}
  }
  
  labels = {
    application = "budget-management"
    environment = "production"
  }
}

resource "google_secret_manager_secret" "google_sheets_credentials" {
  count     = var.create_secrets ? 1 : 0
  project   = var.project_id
  secret_id = var.google_sheets_credentials_secret_id
  
  replication {
    auto {}
  }
  
  labels = {
    application = "budget-management"
    environment = "production"
  }
}

# Gmail API secret
resource "google_secret_manager_secret" "gmail_credentials" {
  count     = var.create_secrets ? 1 : 0
  project   = var.project_id
  secret_id = var.gmail_credentials_secret_id
  
  replication {
    auto {}
  }
  
  labels = {
    application = "budget-management"
    environment = "production"
  }
}

# Output the list of secret IDs for use in IAM permissions
output "secret_ids" {
  value       = local.secret_ids
  description = "List of Secret Manager secret IDs for IAM permissions"
}