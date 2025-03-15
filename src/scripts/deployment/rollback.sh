#!/bin/bash
#
# Rollback Script for Budget Management Application
#
# This script handles rollback procedures for the Budget Management Application deployment.
# It reverts the application to a previous known-good state in case of deployment failures
# or issues, ensuring service reliability and providing disaster recovery capabilities.
#
# Usage:
#   ./rollback.sh [options]
#
# For detailed usage information, run:
#   ./rollback.sh -h

# Source the shell template
source "$(dirname "$0")/../../templates/shell_template.sh"

# Global variables with defaults
PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
REGION=${REGION:-us-east1}
ENVIRONMENT=${ENVIRONMENT:-dev}
APP_NAME=${APP_NAME:-budget-management}
PREVIOUS_VERSION=${PREVIOUS_VERSION:-}
ROLLBACK_TYPE=${ROLLBACK_TYPE:-full}
TERRAFORM_DIR=${TERRAFORM_DIR:-$ROOT_DIR/src/backend/deploy/terraform}
TERRAFORM_VARS_DIR=${TERRAFORM_VARS_DIR:-$ROOT_DIR/infrastructure/environments}
TERRAFORM_VARS_FILE=${TERRAFORM_VARS_FILE:-$TERRAFORM_VARS_DIR/$ENVIRONMENT.tfvars}
FORCE=${FORCE:-false}
SKIP_VALIDATION=${SKIP_VALIDATION:-false}
DEPLOYMENT_HISTORY_FILE=${DEPLOYMENT_HISTORY_FILE:-$ROOT_DIR/data/deployment_history.json}

# Checks if gcloud CLI is installed and configured
check_gcloud_installed() {
    if ! check_command_exists "gcloud"; then
        log_error "gcloud CLI is not installed or not in PATH. Please install Google Cloud SDK."
        return 1
    fi
    
    # Verify gcloud is properly installed by checking version
    if ! gcloud --version > /dev/null 2>&1; then
        log_error "gcloud CLI is installed but not accessible."
        return 1
    fi
    
    # Check if project is configured
    local project_id=$(gcloud config get-value project 2>/dev/null)
    if [[ -z "$project_id" || "$project_id" == "(unset)" ]]; then
        log_error "No Google Cloud project is configured. Please run 'gcloud init' or set PROJECT_ID."
        return 1
    fi
    
    local gcloud_version=$(gcloud --version | head -n 1)
    log_info "gcloud CLI is installed: $gcloud_version"
    log_info "Using Google Cloud project: $project_id"
    
    return 0
}

# Checks if Terraform is installed and accessible
check_terraform_installed() {
    if ! check_command_exists "terraform"; then
        log_error "Terraform is not installed or not in PATH. Please install Terraform."
        return 1
    fi
    
    # Verify Terraform is properly installed by checking version
    if ! terraform --version > /dev/null 2>&1; then
        log_error "Terraform is installed but not accessible."
        return 1
    fi
    
    local tf_version=$(terraform version -json | grep -o '"terraform_version":"[^"]*"' | cut -d'"' -f4)
    log_info "Terraform is installed: v$tf_version"
    
    return 0
}

# Checks if Docker is installed and accessible
check_docker_installed() {
    if ! check_command_exists "docker"; then
        log_error "Docker is not installed or not in PATH. Please install Docker."
        return 1
    fi
    
    # Verify Docker is running by checking version
    if ! docker --version > /dev/null 2>&1; then
        log_error "Docker is installed but not running or not accessible."
        return 1
    fi
    
    local docker_version=$(docker --version)
    log_info "Docker is installed: $docker_version"
    
    return 0
}

# Gets the previous version from deployment history if not specified
get_previous_version() {
    # If previous version is already specified, return it
    if [[ -n "$PREVIOUS_VERSION" ]]; then
        echo "$PREVIOUS_VERSION"
        return 0
    fi
    
    # Try to get previous version from deployment history
    if [[ ! -f "$DEPLOYMENT_HISTORY_FILE" ]]; then
        log_warning "Deployment history file not found: $DEPLOYMENT_HISTORY_FILE"
        return 1
    fi
    
    # Parse deployment history to get the previous version
    # This assumes the deployment history is a JSON array with the most recent version first
    local prev_version=$(jq -r 'if length > 1 then .[1].version else "" end' "$DEPLOYMENT_HISTORY_FILE" 2>/dev/null)
    
    if [[ -z "$prev_version" || "$prev_version" == "null" ]]; then
        log_warning "No previous version found in deployment history."
        return 1
    fi
    
    log_info "Found previous version in deployment history: $prev_version"
    echo "$prev_version"
    return 0
}

# Confirms with the user before proceeding with rollback
confirm_rollback() {
    # Skip confirmation if FORCE is true
    if [[ "$FORCE" == "true" ]]; then
        return 0
    fi
    
    local prev_version=$(get_previous_version)
    local current_version=$(jq -r '.[0].version' "$DEPLOYMENT_HISTORY_FILE" 2>/dev/null || echo "unknown")
    
    log_warning "WARNING: You are about to roll back the deployment from version $current_version to $prev_version."
    log_warning "This operation is potentially destructive and may result in data loss."
    log_warning "Please make sure you understand the consequences before proceeding."
    
    echo
    echo "To confirm this rollback, type 'ROLLBACK' and press Enter:"
    read -r confirmation
    
    if [[ "$confirmation" == "ROLLBACK" ]]; then
        log_info "Rollback confirmed by user."
        return 0
    else
        log_info "Rollback cancelled by user."
        return 1
    fi
}

# Rolls back to a previous container image version
rollback_container_image() {
    log_info "Starting container image rollback..."
    
    # Get previous version if not specified
    local prev_version=$(get_previous_version)
    if [[ -z "$prev_version" ]]; then
        log_error "No previous version found for rollback. Please specify a version with --previous-version."
        return 1
    fi
    
    # Construct previous container image tag
    local prev_image="gcr.io/$PROJECT_ID/$APP_NAME:$prev_version"
    log_info "Rolling back to container image: $prev_image"
    
    # Check if previous container image exists
    if ! gcloud container images describe "$prev_image" --project="$PROJECT_ID" &>/dev/null; then
        log_error "Previous container image not found: $prev_image"
        return 1
    fi
    
    # Update Cloud Run job to use previous container image
    log_info "Updating Cloud Run job to use previous container image..."
    
    if ! gcloud run jobs update "$APP_NAME" \
         --project="$PROJECT_ID" \
         --region="$REGION" \
         --image="$prev_image"; then
        log_error "Failed to update Cloud Run job to use previous container image."
        return 1
    fi
    
    log_info "Container image rollback completed successfully."
    return 0
}

# Rolls back infrastructure changes using Terraform
rollback_infrastructure() {
    log_info "Starting infrastructure rollback..."
    
    # Check if Terraform state has previous state
    cd "$TERRAFORM_DIR" || {
        log_error "Failed to change directory to $TERRAFORM_DIR"
        return 1
    }
    
    # Initialize Terraform
    log_debug "Initializing Terraform..."
    if ! terraform init -reconfigure &>/dev/null; then
        log_error "Failed to initialize Terraform."
        return 1
    fi
    
    # Check if there's a previous state
    if ! terraform state list &>/dev/null; then
        log_error "No Terraform state found for rollback."
        return 1
    fi
    
    # Execute terraform apply with auto-approve to restore previous state
    log_info "Applying Terraform to restore previous infrastructure state..."
    
    # Set environment variables for apply_terraform.sh
    export TERRAFORM_DIR="$TERRAFORM_DIR"
    export TFVARS_FILE="$TERRAFORM_VARS_FILE"
    export AUTO_APPROVE="true"
    export INIT_RECONFIGURE="true"
    
    # Execute apply_terraform.sh
    if ! "$(dirname "$0")/apply_terraform.sh" --auto-approve; then
        log_error "Failed to roll back infrastructure using Terraform."
        return 1
    fi
    
    log_info "Infrastructure rollback completed successfully."
    return 0
}

# Rolls back the Cloud Run job configuration
rollback_cloud_run_job() {
    log_info "Starting Cloud Run job rollback..."
    
    # Get previous version if not specified
    local prev_version=$(get_previous_version)
    if [[ -z "$prev_version" ]]; then
        log_error "No previous version found for rollback. Please specify a version with --previous-version."
        return 1
    fi
    
    # Construct previous container image tag
    local prev_image="gcr.io/$PROJECT_ID/$APP_NAME:$prev_version"
    log_info "Rolling back to container image: $prev_image"
    
    # Set environment variables for deploy_cloud_run.sh
    export PROJECT_ID="$PROJECT_ID"
    export REGION="$REGION"
    export ENVIRONMENT="$ENVIRONMENT"
    export APP_NAME="$APP_NAME"
    export CONTAINER_IMAGE="$prev_image"
    export SETUP_SCHEDULER="false"
    export VALIDATE_DEPLOYMENT="false"
    
    # Execute deploy_cloud_run.sh
    if ! "$(dirname "$0")/deploy_cloud_run.sh"; then
        log_error "Failed to roll back Cloud Run job."
        return 1
    fi
    
    log_info "Cloud Run job rollback completed successfully."
    return 0
}

# Validates that the rollback was successful
validate_rollback() {
    # Skip validation if requested
    if [[ "$SKIP_VALIDATION" == "true" ]]; then
        log_info "Skipping rollback validation as requested."
        return 0
    fi
    
    log_info "Validating rollback..."
    
    # Get previous version
    local prev_version=$(get_previous_version)
    if [[ -z "$prev_version" ]]; then
        log_warning "No previous version found for validation. Skipping detailed validation."
        return 0
    fi
    
    # Construct previous container image tag
    local prev_image="gcr.io/$PROJECT_ID/$APP_NAME:$prev_version"
    
    # Check if Cloud Run job is using the correct container image
    log_debug "Checking if Cloud Run job is using the correct container image..."
    
    local current_image
    current_image=$(gcloud run jobs describe "$APP_NAME" \
                  --project="$PROJECT_ID" \
                  --region="$REGION" \
                  --format="value(template.template.containers[0].image)")
    
    if [[ "$current_image" != "$prev_image" ]]; then
        log_warning "Cloud Run job is not using the expected container image."
        log_warning "Expected: $prev_image"
        log_warning "Actual: $current_image"
        return 1
    fi
    
    # Check if the job is in a healthy state
    log_debug "Checking if Cloud Run job is in a healthy state..."
    
    local job_status
    job_status=$(gcloud run jobs describe "$APP_NAME" \
               --project="$PROJECT_ID" \
               --region="$REGION" \
               --format="value(status.conditions[0].status)")
    
    if [[ "$job_status" != "True" ]]; then
        log_warning "Cloud Run job may not be in a healthy state."
        return 1
    fi
    
    # If full rollback, verify infrastructure state
    if [[ "$ROLLBACK_TYPE" == "full" ]]; then
        log_debug "Checking infrastructure state..."
        
        cd "$TERRAFORM_DIR" || {
            log_warning "Failed to change directory to $TERRAFORM_DIR for infrastructure validation."
            return 1
        }
        
        if ! terraform validate &>/dev/null; then
            log_warning "Terraform validation failed after infrastructure rollback."
            return 1
        fi
    fi
    
    log_info "Rollback validation completed successfully."
    return 0
}

# Updates the deployment history with rollback information
update_deployment_history() {
    log_info "Updating deployment history..."
    
    # Get previous version
    local prev_version=$(get_previous_version)
    if [[ -z "$prev_version" ]]; then
        log_warning "No previous version found. Skipping deployment history update."
        return 1
    fi
    
    # Create deployment history directory if it doesn't exist
    mkdir -p "$(dirname "$DEPLOYMENT_HISTORY_FILE")"
    
    # Create new deployment history file if it doesn't exist
    if [[ ! -f "$DEPLOYMENT_HISTORY_FILE" ]]; then
        echo "[]" > "$DEPLOYMENT_HISTORY_FILE"
    fi
    
    # Create rollback entry
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local rollback_entry=$(cat <<EOF
{
  "timestamp": "$timestamp",
  "version": "$prev_version",
  "action": "rollback",
  "environment": "$ENVIRONMENT",
  "type": "$ROLLBACK_TYPE",
  "reason": "Manual rollback initiated by user"
}
EOF
)
    
    # Update deployment history file
    # Add new entry to the beginning of the array
    local updated_history
    updated_history=$(jq --argjson entry "$rollback_entry" '[$entry] + .' "$DEPLOYMENT_HISTORY_FILE")
    
    echo "$updated_history" > "$DEPLOYMENT_HISTORY_FILE"
    
    log_info "Deployment history updated successfully."
    return 0
}

# Parses script-specific command line arguments
parse_custom_args() {
    local args=("$@")
    local i=0
    
    while [[ $i -lt ${#args[@]} ]]; do
        arg="${args[$i]}"
        case "$arg" in
            --project-id=*)
                PROJECT_ID="${arg#*=}"
                ;;
            --project-id)
                ((i++))
                PROJECT_ID="${args[$i]}"
                ;;
            --region=*)
                REGION="${arg#*=}"
                ;;
            --region)
                ((i++))
                REGION="${args[$i]}"
                ;;
            --environment=*)
                ENVIRONMENT="${arg#*=}"
                TERRAFORM_VARS_FILE="$TERRAFORM_VARS_DIR/$ENVIRONMENT.tfvars"
                ;;
            --environment)
                ((i++))
                ENVIRONMENT="${args[$i]}"
                TERRAFORM_VARS_FILE="$TERRAFORM_VARS_DIR/$ENVIRONMENT.tfvars"
                ;;
            --app-name=*)
                APP_NAME="${arg#*=}"
                ;;
            --app-name)
                ((i++))
                APP_NAME="${args[$i]}"
                ;;
            --previous-version=*)
                PREVIOUS_VERSION="${arg#*=}"
                ;;
            --previous-version)
                ((i++))
                PREVIOUS_VERSION="${args[$i]}"
                ;;
            --rollback-type=*)
                ROLLBACK_TYPE="${arg#*=}"
                ;;
            --rollback-type)
                ((i++))
                ROLLBACK_TYPE="${args[$i]}"
                ;;
            --force)
                FORCE="true"
                ;;
            --skip-validation)
                SKIP_VALIDATION="true"
                ;;
            *)
                log_error "Unknown option: $arg"
                show_help
                return 1
                ;;
        esac
        ((i++))
    done
    
    # Validate rollback type
    if [[ "$ROLLBACK_TYPE" != "container" && "$ROLLBACK_TYPE" != "infrastructure" && "$ROLLBACK_TYPE" != "full" ]]; then
        log_error "Invalid rollback type: $ROLLBACK_TYPE"
        log_error "Valid options are: container, infrastructure, full"
        return 1
    fi
    
    return 0
}

# Displays script-specific help information
show_custom_help() {
    echo "DESCRIPTION:"
    echo "  This script handles rollback procedures for the Budget Management Application"
    echo "  deployment. It reverts the application to a previous known-good state in case"
    echo "  of deployment failures or issues."
    echo
    echo "CUSTOM OPTIONS:"
    echo "  --project-id VALUE       Set the Google Cloud project ID (default: from gcloud config)"
    echo "  --region VALUE           Set the deployment region (default: us-east1)"
    echo "  --environment VALUE      Set the deployment environment (default: dev)"
    echo "  --app-name VALUE         Set the application name (default: budget-management)"
    echo "  --previous-version VALUE Specify the version to roll back to (default: auto-detected from history)"
    echo "  --rollback-type VALUE    Specify what to roll back: container, infrastructure, or full (default: full)"
    echo "  --force                  Skip rollback confirmation prompt"
    echo "  --skip-validation        Skip post-rollback validation"
    echo
    echo "ROLLBACK TYPES:"
    echo "  container      - Roll back only the container image"
    echo "  infrastructure - Roll back only the infrastructure using Terraform"
    echo "  full           - Roll back both container image and infrastructure (default)"
    echo
    echo "EXAMPLES:"
    echo "  # Roll back to the previous version (auto-detected from history)"
    echo "  $SCRIPT_NAME"
    echo
    echo "  # Roll back to a specific version"
    echo "  $SCRIPT_NAME --previous-version=1.2.3"
    echo
    echo "  # Roll back only the container image, skipping infrastructure"
    echo "  $SCRIPT_NAME --rollback-type=container"
    echo
    echo "  # Force rollback without confirmation"
    echo "  $SCRIPT_NAME --force"
}

# Main function that orchestrates the rollback process
main() {
    log_info "Starting rollback process for Budget Management Application..."
    
    # Check if gcloud is installed
    if ! check_gcloud_installed; then
        return 1
    fi
    
    # Check if Terraform is installed if needed for rollback type
    if [[ "$ROLLBACK_TYPE" == "infrastructure" || "$ROLLBACK_TYPE" == "full" ]]; then
        if ! check_terraform_installed; then
            return 1
        fi
    fi
    
    # Check if Docker is installed
    if ! check_docker_installed; then
        return 1
    fi
    
    # Get previous version if not specified
    if [[ -z "$PREVIOUS_VERSION" ]]; then
        PREVIOUS_VERSION=$(get_previous_version)
        if [[ -z "$PREVIOUS_VERSION" && ("$ROLLBACK_TYPE" == "container" || "$ROLLBACK_TYPE" == "full") ]]; then
            log_error "No previous version found for rollback. Please specify a version with --previous-version."
            return 1
        fi
    fi
    
    # Confirm rollback with user
    if ! confirm_rollback; then
        log_info "Rollback cancelled by user."
        return 1
    fi
    
    # Roll back container image if rollback type is container or full
    if [[ "$ROLLBACK_TYPE" == "container" || "$ROLLBACK_TYPE" == "full" ]]; then
        if ! rollback_container_image; then
            log_error "Container image rollback failed."
            return 1
        fi
    fi
    
    # Roll back infrastructure if rollback type is infrastructure or full
    if [[ "$ROLLBACK_TYPE" == "infrastructure" || "$ROLLBACK_TYPE" == "full" ]]; then
        if ! rollback_infrastructure; then
            log_error "Infrastructure rollback failed."
            return 1
        fi
    fi
    
    # Roll back Cloud Run job if rollback type is container or full
    if [[ "$ROLLBACK_TYPE" == "container" || "$ROLLBACK_TYPE" == "full" ]]; then
        if ! rollback_cloud_run_job; then
            log_error "Cloud Run job rollback failed."
            return 1
        fi
    fi
    
    # Validate rollback
    if ! validate_rollback; then
        log_warning "Rollback validation failed. The application may not be in a fully restored state."
        # Continue despite validation failure
    fi
    
    # Update deployment history
    if ! update_deployment_history; then
        log_warning "Failed to update deployment history. This doesn't affect the rollback itself."
        # Continue despite history update failure
    fi
    
    log_info "Rollback process completed successfully."
    log_info "Application has been rolled back to version: $PREVIOUS_VERSION"
    
    return 0
}