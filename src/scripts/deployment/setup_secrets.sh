#!/bin/bash
#
# Setup Secrets Script
#
# This script creates and populates secrets in Google Secret Manager
# for the Budget Management Application. It handles the secure storage
# of API credentials, account identifiers, and other sensitive configuration.

# Source the shell template
source "$(dirname "$0")/../../templates/shell_template.sh"

# Default settings
PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
CREDENTIALS_DIR=${CREDENTIALS_DIR:-$ROOT_DIR/credentials}
ENV_FILE=${ENV_FILE:-$ROOT_DIR/.env}
FORCE_UPDATE=${FORCE_UPDATE:-false}

# Secret IDs
CAPITAL_ONE_API_KEY_SECRET_ID=${CAPITAL_ONE_API_KEY_SECRET_ID:-capital-one-api-key}
CAPITAL_ONE_CLIENT_ID_SECRET_ID=${CAPITAL_ONE_CLIENT_ID_SECRET_ID:-capital-one-client-id}
CAPITAL_ONE_CLIENT_SECRET_SECRET_ID=${CAPITAL_ONE_CLIENT_SECRET_SECRET_ID:-capital-one-client-secret}
CAPITAL_ONE_CHECKING_ACCOUNT_ID_SECRET_ID=${CAPITAL_ONE_CHECKING_ACCOUNT_ID_SECRET_ID:-capital-one-checking-account-id}
CAPITAL_ONE_SAVINGS_ACCOUNT_ID_SECRET_ID=${CAPITAL_ONE_SAVINGS_ACCOUNT_ID_SECRET_ID:-capital-one-savings-account-id}
GEMINI_API_KEY_SECRET_ID=${GEMINI_API_KEY_SECRET_ID:-gemini-api-key}
MASTER_BUDGET_SHEET_ID_SECRET_ID=${MASTER_BUDGET_SHEET_ID_SECRET_ID:-master-budget-sheet-id}
WEEKLY_SPENDING_SHEET_ID_SECRET_ID=${WEEKLY_SPENDING_SHEET_ID_SECRET_ID:-weekly-spending-sheet-id}
GOOGLE_SHEETS_CREDENTIALS_SECRET_ID=${GOOGLE_SHEETS_CREDENTIALS_SECRET_ID:-google-sheets-credentials}
GMAIL_CREDENTIALS_SECRET_ID=${GMAIL_CREDENTIALS_SECRET_ID:-gmail-credentials}

# Check if gcloud CLI is installed and configured
check_gcloud_installed() {
    log_debug "Checking if gcloud CLI is installed and configured"
    
    if ! check_command_exists "gcloud"; then
        log_error "gcloud CLI is not installed. Please install Google Cloud SDK."
        return 1
    fi
    
    # Verify gcloud is working properly
    if ! gcloud --version >/dev/null 2>&1; then
        log_error "gcloud CLI is installed but not working properly."
        return 1
    fi
    
    # Check if project is set
    local configured_project=$(gcloud config get-value project 2>/dev/null)
    if [[ -z "$configured_project" ]]; then
        log_error "No Google Cloud project is configured. Please run 'gcloud config set project YOUR_PROJECT_ID'."
        return 1
    fi
    
    log_debug "gcloud CLI is properly installed and configured for project: $configured_project"
    return 0
}

# Check if jq is installed for JSON processing
check_jq_installed() {
    log_debug "Checking if jq is installed"
    
    if ! check_command_exists "jq"; then
        log_error "jq is not installed. Please install jq for JSON processing."
        return 1
    fi
    
    # Verify jq is working properly
    if ! jq --version >/dev/null 2>&1; then
        log_error "jq is installed but not working properly."
        return 1
    fi
    
    log_debug "jq is properly installed: $(jq --version)"
    return 0
}

# Ensures the credentials directory exists
ensure_credentials_dir() {
    log_debug "Ensuring credentials directory exists: $CREDENTIALS_DIR"
    
    if [[ ! -d "$CREDENTIALS_DIR" ]]; then
        log_info "Creating credentials directory: $CREDENTIALS_DIR"
        mkdir -p "$CREDENTIALS_DIR"
        chmod 700 "$CREDENTIALS_DIR"  # Secure permissions
    else
        log_debug "Credentials directory already exists"
    fi
    
    if [[ ! -d "$CREDENTIALS_DIR" ]]; then
        log_error "Failed to create credentials directory: $CREDENTIALS_DIR"
        return 1
    fi
    
    return 0
}

# Loads environment variables from .env file
load_env_file() {
    log_debug "Loading environment variables from: $ENV_FILE"
    
    if [[ ! -f "$ENV_FILE" ]]; then
        log_warning ".env file not found at: $ENV_FILE"
        return 0  # Not critical, continue execution
    fi
    
    # Source the .env file to load environment variables
    source "$ENV_FILE"
    log_info "Loaded environment variables from: $ENV_FILE"
    
    return 0
}

# Creates a secret in Secret Manager if it doesn't exist
create_secret() {
    local secret_id="$1"
    
    log_debug "Checking if secret exists: $secret_id"
    
    # Check if secret already exists
    if gcloud secrets describe "$secret_id" --project="$PROJECT_ID" >/dev/null 2>&1; then
        if [[ "$FORCE_UPDATE" == "false" ]]; then
            log_info "Secret already exists: $secret_id"
            return 0
        else
            log_info "Secret exists but will be updated due to --force-update flag: $secret_id"
        fi
    else
        log_info "Creating secret: $secret_id"
        
        # Create the secret
        if ! gcloud secrets create "$secret_id" \
            --project="$PROJECT_ID" \
            --labels=application=budget-management,environment=production \
            --replication-policy="automatic"; then
            log_error "Failed to create secret: $secret_id"
            return 1
        fi
        
        log_info "Secret created successfully: $secret_id"
    fi
    
    return 0
}

# Adds a new version to an existing secret with the provided value
add_secret_version() {
    local secret_id="$1"
    local secret_value="$2"
    
    log_debug "Adding new version to secret: $secret_id"
    
    # Add a new version to the secret
    if ! echo -n "$secret_value" | gcloud secrets versions add "$secret_id" \
        --project="$PROJECT_ID" \
        --data-file=-; then
        log_error "Failed to add new version to secret: $secret_id"
        return 1
    fi
    
    log_info "New version added to secret: $secret_id"
    return 0
}

# Sets up Capital One API related secrets
setup_capital_one_secrets() {
    log_info "Setting up Capital One API secrets"
    
    # API Key
    if ! create_secret "$CAPITAL_ONE_API_KEY_SECRET_ID"; then
        return 1
    fi
    
    local api_key="$CAPITAL_ONE_API_KEY"
    if [[ -z "$api_key" ]]; then
        read -s -p "Enter Capital One API Key: " api_key
        echo
    fi
    
    if [[ -z "$api_key" ]]; then
        log_error "Capital One API Key cannot be empty"
        return 1
    fi
    
    if ! add_secret_version "$CAPITAL_ONE_API_KEY_SECRET_ID" "$api_key"; then
        return 1
    fi
    
    # Client ID
    if ! create_secret "$CAPITAL_ONE_CLIENT_ID_SECRET_ID"; then
        return 1
    fi
    
    local client_id="$CAPITAL_ONE_CLIENT_ID"
    if [[ -z "$client_id" ]]; then
        read -p "Enter Capital One Client ID: " client_id
    fi
    
    if [[ -z "$client_id" ]]; then
        log_error "Capital One Client ID cannot be empty"
        return 1
    fi
    
    if ! add_secret_version "$CAPITAL_ONE_CLIENT_ID_SECRET_ID" "$client_id"; then
        return 1
    fi
    
    # Client Secret
    if ! create_secret "$CAPITAL_ONE_CLIENT_SECRET_SECRET_ID"; then
        return 1
    fi
    
    local client_secret="$CAPITAL_ONE_CLIENT_SECRET"
    if [[ -z "$client_secret" ]]; then
        read -s -p "Enter Capital One Client Secret: " client_secret
        echo
    fi
    
    if [[ -z "$client_secret" ]]; then
        log_error "Capital One Client Secret cannot be empty"
        return 1
    fi
    
    if ! add_secret_version "$CAPITAL_ONE_CLIENT_SECRET_SECRET_ID" "$client_secret"; then
        return 1
    fi
    
    # Checking Account ID
    if ! create_secret "$CAPITAL_ONE_CHECKING_ACCOUNT_ID_SECRET_ID"; then
        return 1
    fi
    
    local checking_account_id="$CAPITAL_ONE_CHECKING_ACCOUNT_ID"
    if [[ -z "$checking_account_id" ]]; then
        read -p "Enter Capital One Checking Account ID: " checking_account_id
    fi
    
    if [[ -z "$checking_account_id" ]]; then
        log_error "Capital One Checking Account ID cannot be empty"
        return 1
    fi
    
    if ! add_secret_version "$CAPITAL_ONE_CHECKING_ACCOUNT_ID_SECRET_ID" "$checking_account_id"; then
        return 1
    fi
    
    # Savings Account ID
    if ! create_secret "$CAPITAL_ONE_SAVINGS_ACCOUNT_ID_SECRET_ID"; then
        return 1
    fi
    
    local savings_account_id="$CAPITAL_ONE_SAVINGS_ACCOUNT_ID"
    if [[ -z "$savings_account_id" ]]; then
        read -p "Enter Capital One Savings Account ID: " savings_account_id
    fi
    
    if [[ -z "$savings_account_id" ]]; then
        log_error "Capital One Savings Account ID cannot be empty"
        return 1
    fi
    
    if ! add_secret_version "$CAPITAL_ONE_SAVINGS_ACCOUNT_ID_SECRET_ID" "$savings_account_id"; then
        return 1
    fi
    
    log_info "Capital One API secrets setup completed"
    return 0
}

# Sets up Gemini API related secrets
setup_gemini_secrets() {
    log_info "Setting up Gemini API secrets"
    
    # API Key
    if ! create_secret "$GEMINI_API_KEY_SECRET_ID"; then
        return 1
    fi
    
    local api_key="$GEMINI_API_KEY"
    if [[ -z "$api_key" ]]; then
        read -s -p "Enter Gemini API Key: " api_key
        echo
    fi
    
    if [[ -z "$api_key" ]]; then
        log_error "Gemini API Key cannot be empty"
        return 1
    fi
    
    if ! add_secret_version "$GEMINI_API_KEY_SECRET_ID" "$api_key"; then
        return 1
    fi
    
    log_info "Gemini API secrets setup completed"
    return 0
}

# Sets up Google Sheets API related secrets
setup_google_sheets_secrets() {
    log_info "Setting up Google Sheets API secrets"
    
    # Master Budget Sheet ID
    if ! create_secret "$MASTER_BUDGET_SHEET_ID_SECRET_ID"; then
        return 1
    fi
    
    local master_budget_sheet_id="$MASTER_BUDGET_SHEET_ID"
    if [[ -z "$master_budget_sheet_id" ]]; then
        read -p "Enter Master Budget Sheet ID: " master_budget_sheet_id
    fi
    
    if [[ -z "$master_budget_sheet_id" ]]; then
        log_error "Master Budget Sheet ID cannot be empty"
        return 1
    fi
    
    if ! add_secret_version "$MASTER_BUDGET_SHEET_ID_SECRET_ID" "$master_budget_sheet_id"; then
        return 1
    fi
    
    # Weekly Spending Sheet ID
    if ! create_secret "$WEEKLY_SPENDING_SHEET_ID_SECRET_ID"; then
        return 1
    fi
    
    local weekly_spending_sheet_id="$WEEKLY_SPENDING_SHEET_ID"
    if [[ -z "$weekly_spending_sheet_id" ]]; then
        read -p "Enter Weekly Spending Sheet ID: " weekly_spending_sheet_id
    fi
    
    if [[ -z "$weekly_spending_sheet_id" ]]; then
        log_error "Weekly Spending Sheet ID cannot be empty"
        return 1
    fi
    
    if ! add_secret_version "$WEEKLY_SPENDING_SHEET_ID_SECRET_ID" "$weekly_spending_sheet_id"; then
        return 1
    fi
    
    # Google Sheets Credentials
    if ! create_secret "$GOOGLE_SHEETS_CREDENTIALS_SECRET_ID"; then
        return 1
    fi
    
    local credentials_content=""
    local credentials_file="$CREDENTIALS_DIR/google_sheets_credentials.json"
    
    if [[ -f "$credentials_file" ]]; then
        log_info "Using Google Sheets credentials from: $credentials_file"
        credentials_content=$(cat "$credentials_file")
    else
        log_info "Google Sheets credentials file not found at: $credentials_file"
        read -p "Enter path to Google Sheets credentials JSON file: " custom_credentials_file
        
        if [[ ! -f "$custom_credentials_file" ]]; then
            log_error "Credentials file not found at: $custom_credentials_file"
            return 1
        fi
        
        credentials_content=$(cat "$custom_credentials_file")
        
        # Copy to credentials directory
        log_info "Copying credentials to: $credentials_file"
        cp "$custom_credentials_file" "$credentials_file"
        chmod 600 "$credentials_file"  # Secure permissions
    fi
    
    if [[ -z "$credentials_content" ]]; then
        log_error "Google Sheets credentials content cannot be empty"
        return 1
    fi
    
    # Validate JSON
    if ! echo "$credentials_content" | jq empty >/dev/null 2>&1; then
        log_error "Invalid JSON format in Google Sheets credentials file"
        return 1
    fi
    
    if ! add_secret_version "$GOOGLE_SHEETS_CREDENTIALS_SECRET_ID" "$credentials_content"; then
        return 1
    fi
    
    log_info "Google Sheets API secrets setup completed"
    return 0
}

# Sets up Gmail API related secrets
setup_gmail_secrets() {
    log_info "Setting up Gmail API secrets"
    
    # Gmail Credentials
    if ! create_secret "$GMAIL_CREDENTIALS_SECRET_ID"; then
        return 1
    fi
    
    local credentials_content=""
    local credentials_file="$CREDENTIALS_DIR/gmail_credentials.json"
    
    if [[ -f "$credentials_file" ]]; then
        log_info "Using Gmail credentials from: $credentials_file"
        credentials_content=$(cat "$credentials_file")
    else
        log_info "Gmail credentials file not found at: $credentials_file"
        read -p "Enter path to Gmail credentials JSON file: " custom_credentials_file
        
        if [[ ! -f "$custom_credentials_file" ]]; then
            log_error "Credentials file not found at: $custom_credentials_file"
            return 1
        fi
        
        credentials_content=$(cat "$custom_credentials_file")
        
        # Copy to credentials directory
        log_info "Copying credentials to: $credentials_file"
        cp "$custom_credentials_file" "$credentials_file"
        chmod 600 "$credentials_file"  # Secure permissions
    fi
    
    if [[ -z "$credentials_content" ]]; then
        log_error "Gmail credentials content cannot be empty"
        return 1
    fi
    
    # Validate JSON
    if ! echo "$credentials_content" | jq empty >/dev/null 2>&1; then
        log_error "Invalid JSON format in Gmail credentials file"
        return 1
    fi
    
    if ! add_secret_version "$GMAIL_CREDENTIALS_SECRET_ID" "$credentials_content"; then
        return 1
    fi
    
    log_info "Gmail API secrets setup completed"
    return 0
}

# Parse script-specific command line arguments
parse_custom_args() {
    local args=("$@")
    
    local i=0
    while [[ $i -lt ${#args[@]} ]]; do
        case "${args[$i]}" in
            --project-id)
                i=$((i + 1))
                PROJECT_ID="${args[$i]}"
                ;;
            --credentials-dir)
                i=$((i + 1))
                CREDENTIALS_DIR="${args[$i]}"
                ;;
            --env-file)
                i=$((i + 1))
                ENV_FILE="${args[$i]}"
                ;;
            --force-update)
                FORCE_UPDATE=true
                ;;
            *)
                log_error "Unknown option: ${args[$i]}"
                return 1
                ;;
        esac
        i=$((i + 1))
    done
    
    return 0
}

# Display script-specific help information
show_custom_help() {
    echo "CUSTOM OPTIONS:"
    echo "  --project-id ID     Google Cloud project ID (default: current gcloud project)"
    echo "  --credentials-dir DIR Path to credentials directory (default: $ROOT_DIR/credentials)"
    echo "  --env-file FILE     Path to .env file (default: $ROOT_DIR/.env)"
    echo "  --force-update      Force update of existing secrets"
    echo
    echo "DESCRIPTION:"
    echo "  This script creates and populates secrets in Google Secret Manager"
    echo "  for the Budget Management Application. It handles the secure storage"
    echo "  of API credentials, account identifiers, and other sensitive configuration."
    echo
    echo "EXAMPLES:"
    echo "  $SCRIPT_NAME"
    echo "  $SCRIPT_NAME --project-id my-gcp-project"
    echo "  $SCRIPT_NAME --credentials-dir /path/to/credentials --force-update"
}

# Main function that orchestrates the secrets setup process
main() {
    log_info "Starting secrets setup for Budget Management Application"
    
    # Check if gcloud is installed
    if ! check_gcloud_installed; then
        return 1
    fi
    
    # Check if jq is installed
    if ! check_jq_installed; then
        return 1
    fi
    
    # Ensure credentials directory exists
    if ! ensure_credentials_dir; then
        return 1
    fi
    
    # Load environment variables from .env file (if exists)
    load_env_file
    
    # Set up Capital One secrets
    if ! setup_capital_one_secrets; then
        log_error "Failed to set up Capital One secrets"
        # Continue with other secrets
    fi
    
    # Set up Gemini secrets
    if ! setup_gemini_secrets; then
        log_error "Failed to set up Gemini secrets"
        # Continue with other secrets
    fi
    
    # Set up Google Sheets secrets
    if ! setup_google_sheets_secrets; then
        log_error "Failed to set up Google Sheets secrets"
        # Continue with other secrets
    fi
    
    # Set up Gmail secrets
    if ! setup_gmail_secrets; then
        log_error "Failed to set up Gmail secrets"
        # Continue with other secrets
    fi
    
    log_info "Secrets setup completed successfully"
    return 0
}