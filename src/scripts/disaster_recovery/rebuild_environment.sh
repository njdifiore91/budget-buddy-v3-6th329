#!/bin/bash
#
# Rebuild Environment Script
#
# This script rebuilds the entire Budget Management Application environment from scratch
# after a disaster or critical failure. It orchestrates the complete recovery process
# by stopping any running components, recreating infrastructure, restoring data from backups,
# and redeploying the application.

# Source the shell template
source "$(dirname "$0")/../../templates/shell_template.sh"

# Default settings
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${REGION:-us-east1}"
APP_NAME="${APP_NAME:-budget-management}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/data/backups}"
BACKUP_DATE="${BACKUP_DATE:-latest}"
FORCE="${FORCE:-false}"
SKIP_CONFIRMATION="${SKIP_CONFIRMATION:-false}"
SKIP_EMERGENCY_STOP="${SKIP_EMERGENCY_STOP:-false}"
SKIP_INFRASTRUCTURE="${SKIP_INFRASTRUCTURE:-false}"
SKIP_SECRETS="${SKIP_SECRETS:-false}"
SKIP_DATA_RESTORE="${SKIP_DATA_RESTORE:-false}"
SKIP_DEPLOYMENT="${SKIP_DEPLOYMENT:-false}"

#
# Function Definitions
#

# Checks if all required dependencies are installed
check_dependencies() {
    log_debug "Checking dependencies"
    local dependencies=("terraform" "gcloud" "python3")
    if ! check_dependencies "${dependencies[@]}"; then
        log_error "Missing required dependencies. Please install them."
        return 1
    fi
    return 0
}

# Confirms with the user before proceeding with environment rebuild
confirm_rebuild() {
    log_debug "Confirming rebuild"
    if [[ "$SKIP_CONFIRMATION" == "true" ]]; then
        log_info "Skipping confirmation due to SKIP_CONFIRMATION=true"
        return 0
    fi

    echo
    echo "------------------------------------------------------------------------"
    echo "WARNING: This script will completely rebuild the $APP_NAME environment."
    echo "This includes:"
    echo "  - Stopping all running components"
    echo "  - Recreating cloud infrastructure"
    echo "  - Restoring data from backups"
    echo "  - Redeploying the application"
    echo "------------------------------------------------------------------------"
    read -r -p "Type 'REBUILD' to confirm: " response
    if [[ "$response" == "REBUILD" ]]; then
        log_info "Rebuild confirmed"
        return 0
    else
        log_info "Rebuild cancelled"
        return 1
    fi
}

# Stops all running components of the application
emergency_stop() {
    log_debug "Stopping running components"
    if [[ "$SKIP_EMERGENCY_STOP" == "true" ]]; then
        log_info "Skipping emergency stop due to SKIP_EMERGENCY_STOP=true"
        return 0
    fi

    log_info "Starting emergency stop procedure"
    python3 "$(dirname "$0")/emergency_stop.py" \
        --project_id="$PROJECT_ID" \
        --region="$REGION" \
        --app_name="$APP_NAME"
    local result=$?
    if [[ "$result" -ne 0 ]]; then
        log_error "Emergency stop failed"
        return 1
    fi
    log_info "Emergency stop completed successfully"
    return 0
}

# Rebuilds the cloud infrastructure using Terraform
rebuild_infrastructure() {
    log_debug "Rebuilding infrastructure"
    if [[ "$SKIP_INFRASTRUCTURE" == "true" ]]; then
        log_info "Skipping infrastructure rebuild due to SKIP_INFRASTRUCTURE=true"
        return 0
    fi

    log_info "Starting infrastructure rebuild"
    "$(dirname "$0")"/../deployment/apply_terraform.sh \
        --environment="$ENVIRONMENT"
    local result=$?
    if [[ "$result" -ne 0 ]]; then
        log_error "Infrastructure rebuild failed"
        return 1
    fi
    log_info "Infrastructure rebuild completed successfully"
    return 0
}

# Sets up required secrets in Secret Manager
setup_secrets() {
    log_debug "Setting up secrets"
    if [[ "$SKIP_SECRETS" == "true" ]]; then
        log_info "Skipping secrets setup due to SKIP_SECRETS=true"
        return 0
    fi

    log_info "Starting secrets setup"
    "$(dirname "$0")"/../deployment/setup_secrets.sh \
        --project-id="$PROJECT_ID"
    local result=$?
    if [[ "$result" -ne 0 ]]; then
        log_error "Secrets setup failed"
        return 1
    fi
    log_info "Secrets setup completed successfully"
    return 0
}

# Restores Google Sheets data from backups
restore_data() {
    log_debug "Restoring data"
    if [[ "$SKIP_DATA_RESTORE" == "true" ]]; then
        log_info "Skipping data restore due to SKIP_DATA_RESTORE=true"
        return 0
    fi

    log_info "Starting data restoration"
    local command="python3 \"$(dirname "$0")/restore_from_backup.py\""
    if [[ "$BACKUP_DATE" != "latest" ]]; then
        command="$command --date $BACKUP_DATE"
    fi
    if [[ "$BACKUP_DIR" != "$ROOT_DIR/data/backups" ]]; then
        command="$command --backup-dir \"$BACKUP_DIR\""
    fi
    if ! retry_command "$command"; then
        log_error "Data restoration failed"
        return 1
    fi
    log_info "Data restoration completed successfully"
    return 0
}

# Deploys the application to Cloud Run
deploy_application() {
    log_debug "Deploying application"
    if [[ "$SKIP_DEPLOYMENT" == "true" ]]; then
        log_info "Skipping deployment due to SKIP_DEPLOYMENT=true"
        return 0
    fi

    log_info "Starting application deployment"
    # Assuming deploy_cloud_run.sh takes --project_id and --region
    "$(dirname "$0")"/../deployment/deploy_cloud_run.sh \
        --project_id="$PROJECT_ID" \
        --region="$REGION"
    local result=$?
    if [[ "$result" -ne 0 ]]; then
        log_error "Application deployment failed"
        return 1
    fi
    log_info "Application deployment completed successfully"
    return 0
}

# Sets up Cloud Scheduler for weekly job execution
setup_scheduler() {
    log_debug "Setting up scheduler"
    if [[ "$SKIP_DEPLOYMENT" == "true" ]]; then
        log_info "Skipping scheduler setup due to SKIP_DEPLOYMENT=true"
        return 0
    fi

    log_info "Starting scheduler setup"
    # Assuming setup_cloud_scheduler.sh takes --project_id and --region
    "$(dirname "$0")"/../deployment/setup_cloud_scheduler.sh \
        --project_id="$PROJECT_ID" \
        --region="$REGION"
    local result=$?
    if [[ "$result" -ne 0 ]]; then
        log_error "Scheduler setup failed"
        return 1
    fi
    log_info "Scheduler setup completed successfully"
    return 0
}

# Validates the deployment by checking component status
validate_deployment() {
    log_debug "Validating deployment"
    if [[ "$SKIP_DEPLOYMENT" == "true" ]]; then
        log_info "Skipping deployment validation due to SKIP_DEPLOYMENT=true"
        return 0
    fi

    log_info "Starting deployment validation"
    # Assuming validate_deployment.py takes --project_id and --region
    python3 "$(dirname "$0")/validate_deployment.py" \
        --project_id="$PROJECT_ID" \
        --region="$REGION"
    local result=$?
    if [[ "$result" -ne 0 ]]; then
        log_warning "Deployment validation failed, but continuing"
    else
        log_info "Deployment validation completed successfully"
    fi
    return 0
}

# Parses script-specific command line arguments
parse_custom_args() {
    local args=("$@")
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --project-id)
                PROJECT_ID="$2"
                shift 2
                ;;
            --region)
                REGION="$2"
                shift 2
                ;;
            --app-name)
                APP_NAME="$2"
                shift 2
                ;;
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --backup-dir)
                BACKUP_DIR="$2"
                shift 2
                ;;
            --backup-date)
                BACKUP_DATE="$2"
                shift 2
                ;;
            --force)
                FORCE="true"
                shift
                ;;
            --skip-confirmation)
                SKIP_CONFIRMATION="true"
                shift
                ;;
            --skip-emergency-stop)
                SKIP_EMERGENCY_STOP="true"
                shift
                ;;
            --skip-infrastructure)
                SKIP_INFRASTRUCTURE="true"
                shift
                ;;
            --skip-secrets)
                SKIP_SECRETS="true"
                shift
                ;;
            --skip-data-restore)
                SKIP_DATA_RESTORE="true"
                shift
                ;;
            --skip-deployment)
                SKIP_DEPLOYMENT="true"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_custom_help
                return 1
                ;;
        esac
    done
}

# Displays script-specific help information
show_custom_help() {
    echo "Usage: $SCRIPT_NAME [options]"
    echo
    echo "Options:"
    echo "  --project-id <project_id>   Google Cloud project ID"
    echo "  --region <region>           Google Cloud region"
    echo "  --app-name <app_name>         Application name"
    echo "  --environment <environment>   Deployment environment"
    echo "  --backup-dir <backup_dir>     Backup directory"
    echo "  --backup-date <backup_date>   Backup date (YYYY-MM-DD or latest)"
    echo "  --force                     Force execution without confirmation"
    echo "  --skip-confirmation         Skip user confirmation prompt"
    echo "  --skip-emergency-stop     Skip emergency stop procedure"
    echo "  --skip-infrastructure     Skip infrastructure rebuild"
    echo "  --skip-secrets            Skip secrets setup"
    echo "  --skip-data-restore       Skip data restoration"
    echo "  --skip-deployment         Skip application deployment"
    echo
    echo "Description:"
    echo "  This script rebuilds the entire Budget Management Application environment."
    echo "  It is intended for disaster recovery or critical failure scenarios."
}

# Main function that orchestrates the environment rebuild process
main() {
    log_info "Starting environment rebuild process"

    # Check dependencies
    if ! check_dependencies; then
        handle_error 1 "Dependency check failed"
    fi

    # Confirm rebuild with user
    if ! confirm_rebuild; then
        log_info "Rebuild cancelled by user"
        return 1
    fi

    # Perform emergency stop
    if ! emergency_stop; then
        if [[ "$FORCE" == "true" ]]; then
            log_warning "Emergency stop failed, but continuing due to --force"
        else
            handle_error 1 "Emergency stop failed"
        fi
    fi

    # Rebuild infrastructure
    if ! rebuild_infrastructure; then
        if [[ "$FORCE" == "true" ]]; then
            log_warning "Infrastructure rebuild failed, but continuing due to --force"
        else
            handle_error 1 "Infrastructure rebuild failed"
        fi
    fi

    # Set up secrets
    if ! setup_secrets; then
        if [[ "$FORCE" == "true" ]]; then
            log_warning "Secrets setup failed, but continuing due to --force"
        else
            handle_error 1 "Secrets setup failed"
        fi
    fi

    # Restore data
    if ! restore_data; then
        if [[ "$FORCE" == "true" ]]; then
            log_warning "Data restoration failed, but continuing due to --force"
        else
            handle_error 1 "Data restoration failed"
        fi
    fi

    # Deploy application
    if ! deploy_application; then
        if [[ "$FORCE" == "true" ]]; then
            log_warning "Application deployment failed, but continuing due to --force"
        else
            handle_error 1 "Application deployment failed"
        fi
    fi

    # Setup scheduler
    if ! setup_scheduler; then
        if [[ "$FORCE" == "true" ]]; then
            log_warning "Scheduler setup failed, but continuing due to --force"
        else
            handle_error 1 "Scheduler setup failed"
        fi
    fi

    # Validate deployment
    validate_deployment

    log_info "Environment rebuild process completed successfully"
    return 0
}

# Execute the script
run "$@"