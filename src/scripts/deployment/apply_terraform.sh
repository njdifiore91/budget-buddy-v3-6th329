#!/bin/bash
#
# Apply Terraform Configuration Script
#
# This script applies Terraform configurations to deploy the Budget Management Application
# infrastructure to Google Cloud Platform.

# Source the shell template
source "$(dirname "$0")/../../templates/shell_template.sh"

# Default settings
TERRAFORM_DIR="${TERRAFORM_DIR:-$ROOT_DIR/src/backend/deploy/terraform}"
ENVIRONMENTS_DIR="${ENVIRONMENTS_DIR:-$ROOT_DIR/infrastructure/environments}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
TFVARS_FILE="${TFVARS_FILE:-$ENVIRONMENTS_DIR/$ENVIRONMENT.tfvars}"
AUTO_APPROVE="${AUTO_APPROVE:-false}"
INIT_RECONFIGURE="${INIT_RECONFIGURE:-false}"
BACKEND_CONFIG="${BACKEND_CONFIG:-}"
PLAN_FILE="${PLAN_FILE:-terraform.tfplan}"

# Check if Terraform is installed and has the required version
check_terraform_installed() {
    if ! check_command_exists "terraform"; then
        log_error "Terraform is not installed. Please install Terraform >= 1.0.0"
        return 1
    fi
    
    if ! terraform version &>/dev/null; then
        log_error "Failed to run 'terraform version'. Please check your Terraform installation."
        return 1
    fi
    
    local tf_version=$(terraform version -json | grep -o '"terraform_version":"[^"]*"' | cut -d'"' -f4)
    local major_version=$(echo "$tf_version" | cut -d'.' -f1)
    local minor_version=$(echo "$tf_version" | cut -d'.' -f2)
    
    if [[ "$major_version" -lt 1 ]]; then
        log_error "Terraform version must be >= 1.0.0, found $tf_version"
        return 1
    fi
    
    log_info "Terraform version $tf_version is installed"
    return 0
}

# Check if gcloud CLI is installed and configured
check_gcloud_installed() {
    if ! check_command_exists "gcloud"; then
        log_error "Google Cloud SDK (gcloud) is not installed. Please install gcloud CLI."
        return 1
    fi
    
    if ! gcloud --version &>/dev/null; then
        log_error "Failed to run 'gcloud --version'. Please check your gcloud installation."
        return 1
    fi
    
    local project_id=$(gcloud config get-value project 2>/dev/null)
    if [[ -z "$project_id" || "$project_id" == "(unset)" ]]; then
        log_error "Google Cloud project is not set. Please run 'gcloud config set project YOUR_PROJECT_ID'."
        return 1
    fi
    
    log_info "Google Cloud SDK is installed and project is set to '$project_id'"
    return 0
}

# Check if the Terraform variables file exists
check_tfvars_file() {
    if [[ ! -f "$TFVARS_FILE" ]]; then
        log_error "Terraform variables file not found: $TFVARS_FILE"
        return 1
    fi
    
    log_info "Using Terraform variables file: $TFVARS_FILE"
    return 0
}

# Initialize the Terraform working directory
terraform_init() {
    log_info "Initializing Terraform..."
    
    cd "$TERRAFORM_DIR" || {
        log_error "Failed to change directory to $TERRAFORM_DIR"
        return 1
    }
    
    local init_cmd="terraform init"
    
    # Add reconfigure flag if requested
    if [[ "$INIT_RECONFIGURE" == "true" ]]; then
        init_cmd="$init_cmd -reconfigure"
    fi
    
    # Add backend configuration if provided
    if [[ -n "$BACKEND_CONFIG" ]]; then
        init_cmd="$init_cmd -backend-config=\"$BACKEND_CONFIG\""
    fi
    
    # Run terraform init with retry
    if ! retry_command "$init_cmd"; then
        log_error "Terraform initialization failed"
        return 1
    fi
    
    log_info "Terraform initialization completed successfully"
    return 0
}

# Validate the Terraform configuration
terraform_validate() {
    log_info "Validating Terraform configuration..."
    
    cd "$TERRAFORM_DIR" || {
        log_error "Failed to change directory to $TERRAFORM_DIR"
        return 1
    }
    
    # Run terraform validate with retry
    if ! retry_command "terraform validate"; then
        log_error "Terraform validation failed"
        return 1
    fi
    
    log_info "Terraform validation completed successfully"
    return 0
}

# Create a Terraform execution plan
terraform_plan() {
    log_info "Creating Terraform execution plan..."
    
    cd "$TERRAFORM_DIR" || {
        log_error "Failed to change directory to $TERRAFORM_DIR"
        return 1
    }
    
    local plan_cmd="terraform plan -var-file=\"$TFVARS_FILE\" -out=\"$PLAN_FILE\""
    
    # Run terraform plan with retry
    if ! retry_command "$plan_cmd"; then
        log_error "Terraform plan creation failed"
        return 1
    fi
    
    log_info "Terraform plan created successfully: $PLAN_FILE"
    return 0
}

# Apply the Terraform execution plan
terraform_apply() {
    log_info "Applying Terraform configuration..."
    
    cd "$TERRAFORM_DIR" || {
        log_error "Failed to change directory to $TERRAFORM_DIR"
        return 1
    }
    
    local apply_cmd="terraform apply"
    
    # Add auto-approve flag if requested
    if [[ "$AUTO_APPROVE" == "true" ]]; then
        apply_cmd="$apply_cmd -auto-approve"
    fi
    
    # Use plan file if it exists, otherwise use var-file
    if [[ -f "$PLAN_FILE" ]]; then
        apply_cmd="$apply_cmd \"$PLAN_FILE\""
    else
        apply_cmd="$apply_cmd -var-file=\"$TFVARS_FILE\""
    fi
    
    # Run terraform apply with retry
    if ! retry_command "$apply_cmd"; then
        log_error "Terraform apply failed"
        return 1
    fi
    
    log_info "Terraform apply completed successfully"
    return 0
}

# Display Terraform outputs after successful apply
terraform_output() {
    log_info "Retrieving Terraform outputs..."
    
    cd "$TERRAFORM_DIR" || {
        log_error "Failed to change directory to $TERRAFORM_DIR"
        return 1
    }
    
    if ! terraform output; then
        log_warning "Failed to retrieve Terraform outputs. This is not critical."
    fi
    
    return 0
}

# Parse script-specific command line arguments
parse_custom_args() {
    local args=("$@")
    
    for ((i=0; i<${#args[@]}; i++)); do
        case "${args[$i]}" in
            --environment=*)
                ENVIRONMENT="${args[$i]#*=}"
                TFVARS_FILE="$ENVIRONMENTS_DIR/$ENVIRONMENT.tfvars"
                ;;
            --environment)
                ((i++))
                ENVIRONMENT="${args[$i]}"
                TFVARS_FILE="$ENVIRONMENTS_DIR/$ENVIRONMENT.tfvars"
                ;;
            --tfvars-file=*)
                TFVARS_FILE="${args[$i]#*=}"
                ;;
            --tfvars-file)
                ((i++))
                TFVARS_FILE="${args[$i]}"
                ;;
            --auto-approve)
                AUTO_APPROVE="true"
                ;;
            --init-reconfigure)
                INIT_RECONFIGURE="true"
                ;;
            --backend-config=*)
                BACKEND_CONFIG="${args[$i]#*=}"
                ;;
            --backend-config)
                ((i++))
                BACKEND_CONFIG="${args[$i]}"
                ;;
            --plan-file=*)
                PLAN_FILE="${args[$i]#*=}"
                ;;
            --plan-file)
                ((i++))
                PLAN_FILE="${args[$i]}"
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

# Display script-specific help information
show_custom_help() {
    echo "DESCRIPTION:"
    echo "  This script applies Terraform configurations to deploy the Budget Management"
    echo "  Application infrastructure to Google Cloud Platform."
    echo
    echo "CUSTOM OPTIONS:"
    echo "  --environment=ENV        Set the deployment environment (default: dev)"
    echo "  --tfvars-file=FILE       Specify the Terraform variables file to use"
    echo "  --auto-approve           Skip interactive approval before applying"
    echo "  --init-reconfigure       Force reconfiguration of Terraform backend"
    echo "  --backend-config=CONFIG  Specify additional backend configuration"
    echo "  --plan-file=FILE         Specify the name of the plan file (default: terraform.tfplan)"
    echo
    echo "EXAMPLES:"
    echo "  $SCRIPT_NAME --environment=prod"
    echo "  $SCRIPT_NAME --tfvars-file=/path/to/custom.tfvars"
    echo "  $SCRIPT_NAME --auto-approve"
}

# Main function that orchestrates the Terraform apply process
main() {
    # Check prerequisites
    if ! check_terraform_installed; then
        return 1
    fi
    
    if ! check_gcloud_installed; then
        return 1
    fi
    
    if ! check_tfvars_file; then
        return 1
    fi
    
    # Run Terraform operations
    if ! terraform_init; then
        return 1
    fi
    
    if ! terraform_validate; then
        return 1
    fi
    
    if ! terraform_plan; then
        return 1
    fi
    
    if ! terraform_apply; then
        return 1
    fi
    
    # Display outputs
    terraform_output
    
    log_info "Terraform apply process completed successfully for environment: $ENVIRONMENT"
    return 0
}