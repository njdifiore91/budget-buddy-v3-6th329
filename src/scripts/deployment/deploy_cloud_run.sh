#!/bin/bash
#
# Deploy to Google Cloud Run Script
#
# This script deploys the Budget Management Application to Google Cloud Run jobs,
# configures environment variables, mounts secrets, and sets appropriate resource
# allocations for reliable execution.
#
# Usage:
#   ./deploy_cloud_run.sh [options]
#
# For detailed usage information, run:
#   ./deploy_cloud_run.sh -h

# Get script directory
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Source the shell template
source "$SCRIPT_DIR/../../templates/shell_template.sh"

# Global variables with defaults
PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
REGION=${REGION:-us-east1}
ENVIRONMENT=${ENVIRONMENT:-dev}
APP_NAME=${APP_NAME:-budget-management}
SERVICE_ACCOUNT=${SERVICE_ACCOUNT:-${APP_NAME}-service@${PROJECT_ID}.iam.gserviceaccount.com}
CONTAINER_IMAGE=${CONTAINER_IMAGE:-gcr.io/${PROJECT_ID}/${APP_NAME}:latest}
CPU=${CPU:-1}
MEMORY=${MEMORY:-2Gi}
TIMEOUT_SECONDS=${TIMEOUT_SECONDS:-600}
MAX_RETRIES=${MAX_RETRIES:-3}
TERRAFORM_DIR=${TERRAFORM_DIR:-$ROOT_DIR/src/backend/deploy/terraform}
TERRAFORM_VARS_DIR=${TERRAFORM_VARS_DIR:-$ROOT_DIR/infrastructure/environments}
TERRAFORM_VARS_FILE=${TERRAFORM_VARS_FILE:-$TERRAFORM_VARS_DIR/$ENVIRONMENT.tfvars}
BUILD_IMAGE=${BUILD_IMAGE:-false}
SETUP_SCHEDULER=${SETUP_SCHEDULER:-true}
VALIDATE_DEPLOYMENT=${VALIDATE_DEPLOYMENT:-true}

#
# Functions
#

# Checks if gcloud CLI is installed and configured
check_gcloud_installed() {
    log_debug "Checking if gcloud CLI is installed..."
    
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
    local current_project=$(gcloud config get-value project 2>/dev/null)
    if [[ -z "$current_project" || "$current_project" == "(unset)" ]]; then
        log_error "No Google Cloud project is configured. Please run 'gcloud init' or set PROJECT_ID."
        return 1
    fi
    
    local gcloud_version=$(gcloud --version | head -n 1)
    log_info "gcloud CLI is installed: $gcloud_version"
    log_info "Using Google Cloud project: $current_project"
    
    return 0
}

# Checks if Terraform is installed and accessible
check_terraform_installed() {
    log_debug "Checking if Terraform is installed..."
    
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

# Checks if Docker is installed and accessible if building image
check_docker_installed() {
    # Skip check if not building image
    if [[ "$BUILD_IMAGE" != "true" ]]; then
        return 0
    fi
    
    log_debug "Checking if Docker is installed..."
    
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

# Checks if the service account exists and has required permissions
check_service_account() {
    log_info "Checking service account: $SERVICE_ACCOUNT"
    
    # Check if service account exists
    if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT" --project="$PROJECT_ID" &>/dev/null; then
        log_error "Service account $SERVICE_ACCOUNT does not exist."
        log_error "Please create it with: gcloud iam service-accounts create ${SERVICE_ACCOUNT%%@*} --project=$PROJECT_ID"
        return 1
    fi
    
    # Check if service account has necessary roles
    # This is a basic check and may need to be enhanced based on your specific requirements
    local required_roles=("roles/run.invoker" "roles/secretmanager.secretAccessor")
    local missing_roles=0
    
    for role in "${required_roles[@]}"; do
        log_debug "Checking if service account has role: $role"
        
        # This is a simplified check and might need a more robust implementation
        # for production environments
        if ! gcloud projects get-iam-policy "$PROJECT_ID" --format=json | \
             jq -e ".bindings[] | select(.role == \"$role\") | .members[] | select(. == \"serviceAccount:$SERVICE_ACCOUNT\")" &>/dev/null; then
            log_warning "Service account $SERVICE_ACCOUNT may not have the required role: $role"
            ((missing_roles++))
        fi
    done
    
    if [[ $missing_roles -gt 0 ]]; then
        log_warning "Service account may be missing some required roles. Please verify permissions manually."
    else
        log_info "Service account $SERVICE_ACCOUNT exists and appears to have required roles."
    fi
    
    return 0
}

# Builds the Docker image for the application if requested
build_application_image() {
    if [[ "$BUILD_IMAGE" != "true" ]]; then
        log_info "Skipping Docker image build (BUILD_IMAGE=false)"
        return 0
    fi
    
    log_info "Building Docker image: $CONTAINER_IMAGE"
    
    # Set environment variables for build_docker_image.sh
    export PROJECT_ID="$PROJECT_ID"
    export APP_NAME="$APP_NAME"
    export PUSH_IMAGE="true"
    
    # Determine image tag from CONTAINER_IMAGE
    local image_tag="${CONTAINER_IMAGE##*:}"
    if [[ "$image_tag" == "$CONTAINER_IMAGE" ]]; then
        image_tag="latest"
    fi
    
    export VERSION="$image_tag"
    
    # Execute build_docker_image.sh
    if ! "$SCRIPT_DIR/build_docker_image.sh" --push; then
        log_error "Failed to build and push Docker image."
        return 1
    fi
    
    log_info "Docker image built and pushed successfully: $CONTAINER_IMAGE"
    return 0
}

# Deploys the application to Cloud Run using Terraform
deploy_cloud_run_job() {
    log_info "Deploying application to Cloud Run using Terraform..."
    
    # Check if Terraform directory exists
    if [[ ! -d "$TERRAFORM_DIR" ]]; then
        log_error "Terraform directory not found: $TERRAFORM_DIR"
        return 1
    fi
    
    # Create a temporary Terraform variables file with Cloud Run job configuration
    local temp_vars_file="/tmp/cloud_run_vars_$(date +%s).tfvars"
    
    cat > "$temp_vars_file" << EOF
project_id         = "$PROJECT_ID"
region             = "$REGION"
environment        = "$ENVIRONMENT"
app_name           = "$APP_NAME"
service_account    = "$SERVICE_ACCOUNT"
container_image    = "$CONTAINER_IMAGE"
cpu                = "$CPU"
memory             = "$MEMORY"
timeout_seconds    = $TIMEOUT_SECONDS
max_retries        = $MAX_RETRIES
EOF
    
    log_debug "Created temporary Terraform variables file: $temp_vars_file"
    
    # Set environment variables for apply_terraform.sh
    export TERRAFORM_DIR="$TERRAFORM_DIR"
    export TFVARS_FILE="$temp_vars_file"
    export AUTO_APPROVE="true"
    
    # Execute apply_terraform.sh
    if ! "$SCRIPT_DIR/apply_terraform.sh" --auto-approve; then
        log_error "Failed to deploy to Cloud Run using Terraform."
        rm -f "$temp_vars_file"
        return 1
    fi
    
    # Clean up temporary variables file
    rm -f "$temp_vars_file"
    
    log_info "Application deployed to Cloud Run successfully."
    return 0
}

# Sets up the Cloud Scheduler job to trigger the Cloud Run job
setup_cloud_scheduler() {
    if [[ "$SETUP_SCHEDULER" != "true" ]]; then
        log_info "Skipping Cloud Scheduler setup (SETUP_SCHEDULER=false)"
        return 0
    fi
    
    log_info "Setting up Cloud Scheduler for weekly job execution..."
    
    # Cloud Scheduler job name
    local scheduler_name="${APP_NAME}-weekly-scheduler"
    
    # Create or update Cloud Scheduler job
    # Schedule for Sunday at 12 PM EST (17:00 UTC)
    if ! gcloud scheduler jobs create http "$scheduler_name" \
         --project="$PROJECT_ID" \
         --location="$REGION" \
         --schedule="0 17 * * 0" \
         --time-zone="America/New_York" \
         --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${APP_NAME}:run" \
         --http-method="POST" \
         --oauth-service-account-email="$SERVICE_ACCOUNT" \
         --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform" 2>/dev/null; then
         
        log_info "Cloud Scheduler job already exists, updating..."
        
        if ! gcloud scheduler jobs update http "$scheduler_name" \
             --project="$PROJECT_ID" \
             --location="$REGION" \
             --schedule="0 17 * * 0" \
             --time-zone="America/New_York" \
             --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${APP_NAME}:run" \
             --http-method="POST" \
             --oauth-service-account-email="$SERVICE_ACCOUNT" \
             --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform"; then
            log_error "Failed to update Cloud Scheduler job."
            return 1
        fi
    fi
    
    log_info "Cloud Scheduler job setup successfully: $scheduler_name"
    log_info "Schedule: Every Sunday at 12 PM EST"
    
    return 0
}

# Validates that the Cloud Run job was deployed correctly
validate_deployment() {
    if [[ "$VALIDATE_DEPLOYMENT" != "true" ]]; then
        log_info "Skipping deployment validation (VALIDATE_DEPLOYMENT=false)"
        return 0
    fi
    
    log_info "Validating Cloud Run job deployment..."
    
    # Get Cloud Run job details
    local job_details
    job_details=$(gcloud run jobs describe "$APP_NAME" \
                 --project="$PROJECT_ID" \
                 --region="$REGION" \
                 --format=json)
    
    if [[ $? -ne 0 ]]; then
        log_error "Failed to retrieve Cloud Run job details. Deployment may have failed."
        return 1
    fi
    
    # Validate container image
    local deployed_image
    deployed_image=$(echo "$job_details" | jq -r '.template.template.containers[0].image')
    
    if [[ "$deployed_image" != "$CONTAINER_IMAGE" ]]; then
        log_warning "Deployed container image ($deployed_image) does not match expected image ($CONTAINER_IMAGE)."
    else
        log_info "Container image validation: PASSED"
    fi
    
    # Validate CPU and memory
    local deployed_cpu
    deployed_cpu=$(echo "$job_details" | jq -r '.template.template.containers[0].resources.limits.cpu')
    
    local deployed_memory
    deployed_memory=$(echo "$job_details" | jq -r '.template.template.containers[0].resources.limits.memory')
    
    if [[ "$deployed_cpu" != "$CPU" ]]; then
        log_warning "Deployed CPU allocation ($deployed_cpu) does not match expected value ($CPU)."
    else
        log_info "CPU allocation validation: PASSED"
    fi
    
    if [[ "$deployed_memory" != "$MEMORY" ]]; then
        log_warning "Deployed memory allocation ($deployed_memory) does not match expected value ($MEMORY)."
    else
        log_info "Memory allocation validation: PASSED"
    fi
    
    # Validate service account
    local deployed_service_account
    deployed_service_account=$(echo "$job_details" | jq -r '.template.serviceAccount')
    
    if [[ "$deployed_service_account" != "$SERVICE_ACCOUNT" ]]; then
        log_warning "Deployed service account ($deployed_service_account) does not match expected service account ($SERVICE_ACCOUNT)."
    else
        log_info "Service account validation: PASSED"
    fi
    
    log_info "Deployment validation completed successfully."
    return 0
}

# Parses script-specific command line arguments
parse_custom_args() {
    local args=("$@")
    
    for ((i=0; i<${#args[@]}; i++)); do
        case "${args[$i]}" in
            --project-id=*)
                PROJECT_ID="${args[$i]#*=}"
                ;;
            --project-id)
                ((i++))
                PROJECT_ID="${args[$i]}"
                ;;
            --region=*)
                REGION="${args[$i]#*=}"
                ;;
            --region)
                ((i++))
                REGION="${args[$i]}"
                ;;
            --environment=*)
                ENVIRONMENT="${args[$i]#*=}"
                ;;
            --environment)
                ((i++))
                ENVIRONMENT="${args[$i]}"
                ;;
            --app-name=*)
                APP_NAME="${args[$i]#*=}"
                ;;
            --app-name)
                ((i++))
                APP_NAME="${args[$i]}"
                ;;
            --service-account=*)
                SERVICE_ACCOUNT="${args[$i]#*=}"
                ;;
            --service-account)
                ((i++))
                SERVICE_ACCOUNT="${args[$i]}"
                ;;
            --container-image=*)
                CONTAINER_IMAGE="${args[$i]#*=}"
                ;;
            --container-image)
                ((i++))
                CONTAINER_IMAGE="${args[$i]}"
                ;;
            --cpu=*)
                CPU="${args[$i]#*=}"
                ;;
            --cpu)
                ((i++))
                CPU="${args[$i]}"
                ;;
            --memory=*)
                MEMORY="${args[$i]#*=}"
                ;;
            --memory)
                ((i++))
                MEMORY="${args[$i]}"
                ;;
            --timeout=*)
                TIMEOUT_SECONDS="${args[$i]#*=}"
                ;;
            --timeout)
                ((i++))
                TIMEOUT_SECONDS="${args[$i]}"
                ;;
            --max-retries=*)
                MAX_RETRIES="${args[$i]#*=}"
                ;;
            --max-retries)
                ((i++))
                MAX_RETRIES="${args[$i]}"
                ;;
            --build-image)
                BUILD_IMAGE="true"
                ;;
            --no-scheduler)
                SETUP_SCHEDULER="false"
                ;;
            --no-validate)
                VALIDATE_DEPLOYMENT="false"
                ;;
            *)
                log_error "Unknown option: ${args[$i]}"
                show_help
                return 1
                ;;
        esac
    done
    
    return 0
}

# Displays script-specific help information
show_custom_help() {
    echo "DESCRIPTION:"
    echo "  Deploys the Budget Management Application to Google Cloud Run jobs,"
    echo "  configures environment variables, mounts secrets, and sets appropriate"
    echo "  resource allocations for reliable execution."
    echo
    echo "CUSTOM OPTIONS:"
    echo "  --project-id VALUE      Set the Google Cloud project ID (default: from gcloud config)"
    echo "  --region VALUE          Set the deployment region (default: us-east1)"
    echo "  --environment VALUE     Set the deployment environment (default: dev)"
    echo "  --app-name VALUE        Set the application name (default: budget-management)"
    echo "  --service-account VALUE Set the service account email (default: \${APP_NAME}-service@\${PROJECT_ID}.iam.gserviceaccount.com)"
    echo "  --container-image VALUE Set the container image to deploy (default: gcr.io/\${PROJECT_ID}/\${APP_NAME}:latest)"
    echo "  --cpu VALUE             Set the CPU allocation (default: 1)"
    echo "  --memory VALUE          Set the memory allocation (default: 2Gi)"
    echo "  --timeout VALUE         Set the execution timeout in seconds (default: 600)"
    echo "  --max-retries VALUE     Set the maximum number of retries (default: 3)"
    echo "  --build-image           Build and push the container image before deployment"
    echo "  --no-scheduler          Skip Cloud Scheduler setup"
    echo "  --no-validate           Skip deployment validation"
    echo
    echo "EXAMPLES:"
    echo "  # Deploy with default settings"
    echo "  $SCRIPT_NAME"
    echo
    echo "  # Deploy to production environment"
    echo "  $SCRIPT_NAME --environment=prod"
    echo
    echo "  # Deploy with custom resource allocations"
    echo "  $SCRIPT_NAME --cpu=2 --memory=4Gi --timeout=1200"
    echo
    echo "  # Build image and deploy"
    echo "  $SCRIPT_NAME --build-image"
}

# Main function that orchestrates the Cloud Run deployment process
main() {
    log_info "Starting deployment to Google Cloud Run..."
    
    # Check if gcloud is installed
    if ! check_gcloud_installed; then
        return 1
    fi
    
    # Check if Terraform is installed
    if ! check_terraform_installed; then
        return 1
    fi
    
    # Check if Docker is installed (if building image)
    if [[ "$BUILD_IMAGE" == "true" ]] && ! check_docker_installed; then
        return 1
    fi
    
    # Check service account
    if ! check_service_account; then
        return 1
    fi
    
    # Build and push container image if requested
    if [[ "$BUILD_IMAGE" == "true" ]]; then
        if ! build_application_image; then
            return 1
        fi
    fi
    
    # Deploy to Cloud Run using Terraform
    if ! deploy_cloud_run_job; then
        return 1
    fi
    
    # Set up Cloud Scheduler if enabled
    if [[ "$SETUP_SCHEDULER" == "true" ]]; then
        if ! setup_cloud_scheduler; then
            log_warning "Failed to set up Cloud Scheduler. The application is deployed but will need to be triggered manually."
            # Continue despite scheduler setup failure
        fi
    fi
    
    # Validate deployment if enabled
    if [[ "$VALIDATE_DEPLOYMENT" == "true" ]]; then
        if ! validate_deployment; then
            log_warning "Deployment validation found issues. Please check the logs for details."
            # Continue despite validation warnings
        fi
    fi
    
    log_info "Deployment to Google Cloud Run completed successfully."
    log_info "Job Name: $APP_NAME"
    log_info "Project: $PROJECT_ID"
    log_info "Region: $REGION"
    log_info "Environment: $ENVIRONMENT"
    
    return 0
}

# Script execution is handled by the template's run function