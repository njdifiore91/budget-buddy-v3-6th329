# Project identification
project_id       = "budget-management-dev"
region           = "us-east1"
app_name         = "budget-management"

# Container image configuration
container_image  = "gcr.io/budget-management-dev/budget-management:latest"

# Service account details
service_account_email = "budget-management-sa@budget-management-dev.iam.gserviceaccount.com"

# Cloud Scheduler settings
schedule_cron      = "0 12 * * 0"
schedule_timezone  = "America/New_York"

# Cloud Run job resource allocations
cpu               = "1"
memory            = "2Gi"
timeout_seconds   = 600
max_retries       = 3

# Environment variables
environment_variables = {
  LOG_LEVEL                = "DEBUG"
  CAPITAL_ONE_BASE_URL     = "https://api.capitalone.com"
  CAPITAL_ONE_AUTH_URL     = "https://api.capitalone.com/oauth2/token"
  GEMINI_MODEL_NAME        = "gemini-1.0-pro"
  GMAIL_SENDER_EMAIL       = "njdifiore@gmail.com"
  GMAIL_RECIPIENT_EMAILS   = "njdifiore@gmail.com"
  MIN_TRANSFER_AMOUNT      = "1.00"
  TRANSACTION_DAYS_LOOKBACK = "7"
}

# Secret Manager configuration
create_secrets = true

# Secret IDs
capital_one_api_key_secret_id           = "capital-one-api-key"
capital_one_client_id_secret_id         = "capital-one-client-id"
capital_one_client_secret_secret_id     = "capital-one-client-secret"
capital_one_checking_account_id_secret_id = "capital-one-checking-account-id"
capital_one_savings_account_id_secret_id  = "capital-one-savings-account-id"
gemini_api_key_secret_id                = "gemini-api-key"
master_budget_sheet_id_secret_id        = "master-budget-sheet-id"
weekly_spending_sheet_id_secret_id      = "weekly-spending-sheet-id"
google_sheets_credentials_secret_id     = "google-sheets-credentials"
gmail_credentials_secret_id             = "gmail-credentials"

# API configuration
capital_one_base_url      = "https://api.capitalone.com"
capital_one_auth_url      = "https://api.capitalone.com/oauth2/token"
gemini_model_name         = "gemini-1.0-pro"

# Email settings
gmail_sender_email        = "njdifiore@gmail.com"
gmail_recipient_emails    = "njdifiore@gmail.com"

# Logging and operational parameters
log_level                 = "DEBUG"
min_transfer_amount       = "1.00"
transaction_days_lookback = 7