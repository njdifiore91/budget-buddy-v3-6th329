#!/bin/bash
#
# setup_cloud_scheduler.sh
#
# This script sets up a Google Cloud Scheduler job to trigger the 
# Budget Management Application's Cloud Run job on a weekly schedule.
# It configures the scheduler with appropriate cron expression, timezone,
# and authentication settings to ensure reliable execution of the budget 
# management workflow every Sunday at 12 PM EST.

# Source the shell template
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/../../templates/shell_template.sh"

# Default configuration
PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
REGION=${REGION:-us-east1}
ENVIRONMENT=${ENVIRONMENT:-dev}
APP_NAME=${APP_NAME:-budget-management}
SERVICE_ACCOUNT=${SERVICE_ACCOUNT:-${APP_NAME}-service@${PROJECT_ID}.iam.gserviceaccount.com}
CLOUD_RUN_JOB_NAME=${CLOUD_RUN_JOB_NAME:-${APP_NAME}-job}
SCHEDULER_NAME=${SCHEDULER_NAME:-${APP_NAME}-scheduler}
SCHEDULE_CRON=${SCHEDULE_CRON:-0 12 * * 0}  # Sunday at 12 PM
SCHEDULE_TIMEZONE=${SCHEDULE_TIMEZONE:-America/New_York}  # EST/EDT
RETRY_COUNT=${RETRY_COUNT:-3}
MIN_BACKOFF=${MIN_BACKOFF:-1s}
MAX_BACKOFF=${MAX_BACKOFF:-60s}
MAX_RETRY_DURATION=${MAX_RETRY_DURATION:-300s}
MAX_DOUBLINGS=${MAX_DOUBLINGS:-3}
USE_TERRAFORM=${USE_TERRAFORM:-false}
TERRAFORM_DIR=${TERRAFORM_DIR:-$ROOT_DIR/src/backend/deploy/terraform}
TERRAFORM_VARS_DIR=${TERRAFORM_VARS_DIR:-$ROOT_DIR/infrastructure/environments}
TERRAFORM_VARS_FILE=${TERRAFORM_VARS_FILE:-$TERRAFORM_VARS_DIR/$ENVIRONMENT.tfvars}

# Check if gcloud CLI is installed and configured
check_gcloud_installed() {
    log_info "Checking if gcloud CLI is installed and configured..."
    
    if ! check_command_exists "gcloud"; then
        log_error "gcloud CLI is not installed. Please install the Google Cloud SDK."
        return 1
    fi
    
    # Check if gcloud is properly configured
    if ! gcloud --version > /dev/null 2>&1; then
        log_error "gcloud CLI is installed but not properly configured."
        return 1
    fi
    
    # Check if project ID is set
    local current_project=$(gcloud config get-value project 2>/dev/null)
    if [[ -z "$current_project" ]]; then
        log_error "No Google Cloud project is set. Please run 'gcloud config set project YOUR_PROJECT_ID'"
        return 1
    fi
    
    log_debug "gcloud CLI is installed and configured with project: $current_project"
    return 0
}

# Check if jq is installed for JSON parsing
check_jq_installed() {
    log_info "Checking if jq is installed for JSON parsing..."
    
    if ! check_command_exists "jq"; then
        log_error "jq is not installed. Please install jq for JSON parsing."
        return 1
    fi
    
    # Check if jq is working properly
    if ! jq --version > /dev/null 2>&1; then
        log_error "jq is installed but not properly configured."
        return 1
    fi
    
    log_debug "jq is installed: $(jq --version)"
    return 0
}

# Check if the service account exists and has required permissions
check_service_account() {
    log_info "Checking if service account $SERVICE_ACCOUNT exists..."
    
    # Check if service account exists
    if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT" --project "$PROJECT_ID" > /dev/null 2>&1; then
        log_error "Service account $SERVICE_ACCOUNT does not exist."
        log_error "Please create it with: gcloud iam service-accounts create ${SERVICE_ACCOUNT%%@*} --project $PROJECT_ID"
        return 1
    fi
    
    # TODO: Check if service account has required roles
    # This would require listing roles and checking them, but we'll simplify for now
    
    log_debug "Service account $SERVICE_ACCOUNT exists"
    return 0
}

# Check if the Cloud Run job exists to be triggered by the scheduler
check_cloud_run_job() {
    log_info "Checking if Cloud Run job $CLOUD_RUN_JOB_NAME exists in $REGION region..."
    
    # Check if Cloud Run job exists
    if ! gcloud run jobs describe "$CLOUD_RUN_JOB_NAME" --region "$REGION" --project "$PROJECT_ID" > /dev/null 2>&1; then
        log_error "Cloud Run job $CLOUD_RUN_JOB_NAME does not exist in region $REGION."
        log_error "Please create the Cloud Run job first before setting up the scheduler."
        return 1
    fi
    
    log_debug "Cloud Run job $CLOUD_RUN_JOB_NAME exists in region $REGION"
    return 0
}

# Set up Cloud Scheduler using Terraform configuration
setup_scheduler_terraform() {
    log_info "Setting up Cloud Scheduler using Terraform..."
    
    # Check if Terraform directory exists
    if [[ ! -d "$TERRAFORM_DIR" ]]; then
        log_error "Terraform directory $TERRAFORM_DIR does not exist."
        return 1
    fi
    
    # Check if terraform command exists
    if ! check_command_exists "terraform"; then
        log_error "terraform command not found. Please install Terraform."
        return 1
    fi
    
    # Create or update Terraform variables
    local tf_vars=(
        "-var=project_id=$PROJECT_ID"
        "-var=region=$REGION"
        "-var=environment=$ENVIRONMENT"
        "-var=app_name=$APP_NAME"
        "-var=service_account=$SERVICE_ACCOUNT"
        "-var=cloud_run_job_name=$CLOUD_RUN_JOB_NAME"
        "-var=scheduler_name=$SCHEDULER_NAME"
        "-var=schedule_cron=\"$SCHEDULE_CRON\""
        "-var=schedule_timezone=$SCHEDULE_TIMEZONE"
        "-var=retry_count=$RETRY_COUNT"
        "-var=min_backoff=$MIN_BACKOFF"
        "-var=max_backoff=$MAX_BACKOFF"
        "-var=max_retry_duration=$MAX_RETRY_DURATION"
        "-var=max_doublings=$MAX_DOUBLINGS"
    )
    
    # If vars file exists, include it
    if [[ -f "$TERRAFORM_VARS_FILE" ]]; then
        tf_vars+=("-var-file=$TERRAFORM_VARS_FILE")
    fi
    
    log_debug "Running terraform apply with variables: ${tf_vars[*]}"
    
    # Initialize Terraform
    (cd "$TERRAFORM_DIR" && terraform init) || {
        log_error "Failed to initialize Terraform"
        return 1
    }
    
    # Apply Terraform configuration
    if ! (cd "$TERRAFORM_DIR" && terraform apply -auto-approve "${tf_vars[@]}"); then
        log_error "Failed to apply Terraform configuration"
        return 1
    fi
    
    # Get scheduler job name from Terraform output
    local scheduler_job=$(cd "$TERRAFORM_DIR" && terraform output -raw scheduler_job_name 2>/dev/null || echo "$SCHEDULER_NAME")
    
    log_info "Successfully set up Cloud Scheduler job $scheduler_job using Terraform"
    return 0
}

# Set up Cloud Scheduler using gcloud commands
setup_scheduler_gcloud() {
    log_info "Setting up Cloud Scheduler using gcloud commands..."
    
    # Check if scheduler already exists
    if gcloud scheduler jobs describe "$SCHEDULER_NAME" --location "$REGION" --project "$PROJECT_ID" > /dev/null 2>&1; then
        log_warning "Scheduler job $SCHEDULER_NAME already exists. Deleting it to create a fresh configuration."
        if ! gcloud scheduler jobs delete "$SCHEDULER_NAME" --location "$REGION" --project "$PROJECT_ID" --quiet; then
            log_error "Failed to delete existing scheduler job $SCHEDULER_NAME"
            return 1
        fi
    fi
    
    # Construct the Cloud Run job URI
    local job_uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/$CLOUD_RUN_JOB_NAME:run"
    
    # Construct retry configuration
    local retry_config="--retry-count=$RETRY_COUNT --min-backoff=$MIN_BACKOFF --max-backoff=$MAX_BACKOFF --max-retry-duration=$MAX_RETRY_DURATION --max-doublings=$MAX_DOUBLINGS"
    
    log_debug "Creating scheduler job with URI: $job_uri"
    log_debug "Retry configuration: $retry_config"
    
    # Create the scheduler job
    if ! gcloud scheduler jobs create http "$SCHEDULER_NAME" \
        --location "$REGION" \
        --project "$PROJECT_ID" \
        --schedule "$SCHEDULE_CRON" \
        --time-zone "$SCHEDULE_TIMEZONE" \
        --uri "$job_uri" \
        --http-method POST \
        --oauth-service-account-email "$SERVICE_ACCOUNT" \
        $retry_config \
        --message-body "{}" \
        --headers "Content-Type=application/json"; then
        log_error "Failed to create scheduler job $SCHEDULER_NAME"
        return 1
    fi
    
    # Verify the scheduler job was created
    if ! gcloud scheduler jobs describe "$SCHEDULER_NAME" --location "$REGION" --project "$PROJECT_ID" > /dev/null 2>&1; then
        log_error "Failed to verify scheduler job $SCHEDULER_NAME was created"
        return 1
    fi
    
    log_info "Successfully set up Cloud Scheduler job $SCHEDULER_NAME using gcloud"
    return 0
}

# Validate that the Cloud Scheduler job was set up correctly
validate_scheduler() {
    log_info "Validating Cloud Scheduler job configuration..."
    
    # Get scheduler job details
    local job_details
    job_details=$(gcloud scheduler jobs describe "$SCHEDULER_NAME" --location "$REGION" --project "$PROJECT_ID" --format=json 2>/dev/null)
    if [[ $? -ne 0 ]]; then
        log_error "Failed to retrieve details for scheduler job $SCHEDULER_NAME"
        return 1
    fi
    
    # Extract and validate schedule
    local schedule=$(echo "$job_details" | jq -r '.schedule')
    if [[ "$schedule" != "$SCHEDULE_CRON" ]]; then
        log_warning "Scheduler job has unexpected schedule: $schedule (expected: $SCHEDULE_CRON)"
    fi
    
    # Extract and validate timezone
    local timezone=$(echo "$job_details" | jq -r '.timeZone')
    if [[ "$timezone" != "$SCHEDULE_TIMEZONE" ]]; then
        log_warning "Scheduler job has unexpected timezone: $timezone (expected: $SCHEDULE_TIMEZONE)"
    fi
    
    # Extract and validate target
    local http_target=$(echo "$job_details" | jq -r '.httpTarget.uri')
    if [[ ! "$http_target" =~ .*"$CLOUD_RUN_JOB_NAME".* ]]; then
        log_warning "Scheduler job target does not contain expected Cloud Run job name: $http_target"
    fi
    
    # Extract and validate service account
    local service_account=$(echo "$job_details" | jq -r '.httpTarget.oauthToken.serviceAccountEmail')
    if [[ "$service_account" != "$SERVICE_ACCOUNT" ]]; then
        log_warning "Scheduler job has unexpected service account: $service_account (expected: $SERVICE_ACCOUNT)"
    fi
    
    log_info "Validation complete for scheduler job $SCHEDULER_NAME"
    return 0
}

# Parse script-specific command line arguments
parse_custom_args() {
    local args=("$@")
    local i=0
    
    while [[ $i -lt ${#args[@]} ]]; do
        case "${args[$i]}" in
            --project-id)
                i=$((i+1))
                PROJECT_ID="${args[$i]}"
                ;;
            --region)
                i=$((i+1))
                REGION="${args[$i]}"
                ;;
            --environment)
                i=$((i+1))
                ENVIRONMENT="${args[$i]}"
                ;;
            --app-name)
                i=$((i+1))
                APP_NAME="${args[$i]}"
                ;;
            --service-account)
                i=$((i+1))
                SERVICE_ACCOUNT="${args[$i]}"
                ;;
            --cloud-run-job)
                i=$((i+1))
                CLOUD_RUN_JOB_NAME="${args[$i]}"
                ;;
            --scheduler-name)
                i=$((i+1))
                SCHEDULER_NAME="${args[$i]}"
                ;;
            --schedule)
                i=$((i+1))
                SCHEDULE_CRON="${args[$i]}"
                ;;
            --timezone)
                i=$((i+1))
                SCHEDULE_TIMEZONE="${args[$i]}"
                ;;
            --retry-count)
                i=$((i+1))
                RETRY_COUNT="${args[$i]}"
                ;;
            --use-terraform)
                USE_TERRAFORM=true
                ;;
            *)
                log_error "Unknown argument: ${args[$i]}"
                show_help
                return 1
                ;;
        esac
        i=$((i+1))
    done
    
    return 0
}

# Display script-specific help information
show_custom_help() {
    echo "CUSTOM OPTIONS:"
    echo "  --project-id <id>       Google Cloud project ID (default: current gcloud project)"
    echo "  --region <region>       Google Cloud region (default: us-east1)"
    echo "  --environment <env>     Deployment environment (default: dev)"
    echo "  --app-name <name>       Application name (default: budget-management)"
    echo "  --service-account <sa>  Service account email (default: derived from app-name)"
    echo "  --cloud-run-job <job>   Cloud Run job name (default: derived from app-name)"
    echo "  --scheduler-name <name> Cloud Scheduler job name (default: derived from app-name)"
    echo "  --schedule <cron>       Cron schedule expression (default: '0 12 * * 0' for Sunday at 12PM)"
    echo "  --timezone <tz>         Timezone for the schedule (default: America/New_York)"
    echo "  --retry-count <count>   Number of retry attempts (default: 3)"
    echo "  --use-terraform         Use Terraform for setup instead of gcloud commands"
    echo
    echo "DESCRIPTION:"
    echo "  This script sets up a Google Cloud Scheduler job to trigger the Budget Management"
    echo "  Application's Cloud Run job on a weekly schedule. It configures the scheduler with"
    echo "  appropriate cron expression, timezone, and authentication settings to ensure"
    echo "  reliable execution of the budget management workflow every Sunday at 12 PM EST."
    echo
    echo "EXAMPLES:"
    echo "  $SCRIPT_NAME -v"
    echo "  $SCRIPT_NAME --project-id my-project --region us-central1"
    echo "  $SCRIPT_NAME --schedule \"0 8 * * 1\" --timezone America/Los_Angeles"
    echo "  $SCRIPT_NAME --use-terraform"
}

# Main function that orchestrates the Cloud Scheduler setup process
main() {
    # Check gcloud is installed and configured
    if ! check_gcloud_installed; then
        return 1
    fi
    
    # Check jq is installed
    if ! check_jq_installed; then
        return 1
    fi
    
    # Check service account exists
    if ! check_service_account; then
        return 1
    fi
    
    # Check Cloud Run job exists
    if ! check_cloud_run_job; then
        return 1
    fi
    
    # Set up the scheduler using Terraform or gcloud
    if [[ "$USE_TERRAFORM" == "true" ]]; then
        if ! setup_scheduler_terraform; then
            return 1
        fi
    else
        if ! setup_scheduler_gcloud; then
            return 1
        fi
    fi
    
    # Validate the scheduler configuration
    if ! validate_scheduler; then
        log_warning "Scheduler validation had issues, but continuing..."
    fi
    
    log_info "Cloud Scheduler setup completed successfully"
    log_info "Job '$SCHEDULER_NAME' will run '$CLOUD_RUN_JOB_NAME' every Sunday at 12 PM EST"
    return 0
}

# Script execution happens via the shell template