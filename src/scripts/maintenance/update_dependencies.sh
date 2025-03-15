#!/bin/bash
#
# Update Dependencies Script
#
# This script updates Python dependencies for the Budget Management Application.
# It checks for outdated packages, updates them to their latest compatible versions,
# and ensures the application remains functional after updates.

# Source shell template for common functions
source "$(dirname "${BASH_SOURCE[0]}")/../../templates/shell_template.sh"

# Global variables
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../../.." && pwd)
BACKEND_DIR="$ROOT_DIR/src/backend"
SCRIPTS_DIR="$ROOT_DIR/src/scripts"
BACKEND_REQUIREMENTS="$BACKEND_DIR/requirements.txt"
SCRIPTS_REQUIREMENTS="$SCRIPTS_DIR/requirements.txt"
BACKUP_DIR="$ROOT_DIR/data/backups/dependencies"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
PYTHON_VENV="$ROOT_DIR/venv"
REQUIRED_COMMANDS=("python3" "pip" "virtualenv")

# Script-specific flags
CHECK_ONLY=false
BACKEND_ONLY=false
SCRIPTS_ONLY=false
SKIP_BACKUP=false
SKIP_TESTS=false

#
# Parse script-specific command line arguments
#
parse_custom_args() {
    local args=("$@")
    
    for arg in "${args[@]}"; do
        case $arg in
            --check-only)
                CHECK_ONLY=true
                shift
                ;;
            --backend-only)
                BACKEND_ONLY=true
                shift
                ;;
            --scripts-only)
                SCRIPTS_ONLY=true
                shift
                ;;
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            *)
                # Unknown argument
                ;;
        esac
    done
    
    # Validate arguments
    if [[ "$BACKEND_ONLY" == "true" && "$SCRIPTS_ONLY" == "true" ]]; then
        log_error "Cannot use both --backend-only and --scripts-only flags."
        return 1
    fi
    
    return 0
}

#
# Display script-specific help information
#
show_custom_help() {
    echo "CUSTOM OPTIONS:"
    echo "  --check-only      Only check for outdated packages without updating"
    echo "  --backend-only    Only update backend dependencies"
    echo "  --scripts-only    Only update script dependencies"
    echo "  --skip-backup     Skip backing up requirements files"
    echo "  --skip-tests      Skip running tests after update"
    echo
    echo "DESCRIPTION:"
    echo "  This script updates Python dependencies for the Budget Management Application."
    echo "  It checks for outdated packages, updates them to their latest compatible versions,"
    echo "  and ensures the application remains functional after updates."
}

#
# Create backups of requirements files before updating
#
backup_requirements() {
    log_info "Backing up requirements files..."
    
    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"
    
    # Backup backend requirements if it exists
    if [[ -f "$BACKEND_REQUIREMENTS" ]]; then
        cp "$BACKEND_REQUIREMENTS" "$BACKUP_DIR/backend_requirements_${TIMESTAMP}.txt"
        log_debug "Backed up backend requirements to $BACKUP_DIR/backend_requirements_${TIMESTAMP}.txt"
    else
        log_warning "Backend requirements file not found: $BACKEND_REQUIREMENTS"
    fi
    
    # Backup scripts requirements if it exists
    if [[ -f "$SCRIPTS_REQUIREMENTS" ]]; then
        cp "$SCRIPTS_REQUIREMENTS" "$BACKUP_DIR/scripts_requirements_${TIMESTAMP}.txt"
        log_debug "Backed up scripts requirements to $BACKUP_DIR/scripts_requirements_${TIMESTAMP}.txt"
    else
        log_warning "Scripts requirements file not found: $SCRIPTS_REQUIREMENTS"
    fi
    
    log_info "Backup completed."
    return 0
}

#
# Check for outdated packages in the specified requirements file
#
check_outdated_packages() {
    local requirements_file="$1"
    local file_name=$(basename "$requirements_file")
    
    log_info "Checking for outdated packages in $file_name..."
    
    # Ensure the requirements file exists
    if [[ ! -f "$requirements_file" ]]; then
        log_error "Requirements file not found: $requirements_file"
        return 1
    fi
    
    # Activate virtual environment if it exists
    if [[ -d "$PYTHON_VENV" ]]; then
        source "$PYTHON_VENV/bin/activate"
    fi
    
    # Get a list of installed packages from the requirements file
    local installed_packages=$(grep -v '^\s*#' "$requirements_file" | sed 's/[<>=].*//' | tr -d ' ' | xargs)
    
    # Check for outdated packages
    local outdated_output=$(pip list --outdated --format=columns)
    local has_outdated=false
    
    # Display outdated packages that are in the requirements file
    echo "Outdated packages in $file_name:"
    
    for package in $installed_packages; do
        # Check if the package is in the outdated list
        if echo "$outdated_output" | grep -q "^$package "; then
            has_outdated=true
            local line=$(echo "$outdated_output" | grep "^$package ")
            local current_version=$(echo "$line" | awk '{print $2}')
            local latest_version=$(echo "$line" | awk '{print $3}')
            echo "  $package: $current_version -> $latest_version"
        fi
    done
    
    if [[ "$has_outdated" == "false" ]]; then
        echo "  No outdated packages found."
        log_info "No outdated packages found in $file_name."
        return 1  # Return 1 to indicate no updates needed
    else
        log_info "Found outdated packages in $file_name."
        return 0  # Return 0 to indicate updates needed
    fi
}

#
# Update packages in the specified requirements file
#
update_packages() {
    local requirements_file="$1"
    local file_name=$(basename "$requirements_file")
    
    log_info "Updating packages in $file_name..."
    
    # Ensure the requirements file exists
    if [[ ! -f "$requirements_file" ]]; then
        log_error "Requirements file not found: $requirements_file"
        return 1
    fi
    
    # Activate virtual environment if it exists
    if [[ -d "$PYTHON_VENV" ]]; then
        source "$PYTHON_VENV/bin/activate"
    fi
    
    # Update packages
    log_debug "Running: pip install --upgrade -r $requirements_file"
    if ! pip install --upgrade -r "$requirements_file"; then
        log_error "Failed to update packages in $file_name"
        return 1
    fi
    
    log_info "Successfully updated packages in $file_name."
    return 0
}

#
# Run tests to ensure application functionality after updates
#
run_tests() {
    log_info "Running tests to verify functionality..."
    
    # Activate virtual environment if it exists
    if [[ -d "$PYTHON_VENV" ]]; then
        source "$PYTHON_VENV/bin/activate"
    fi
    
    # Change to backend directory to run tests
    pushd "$BACKEND_DIR" > /dev/null
    
    # Run tests
    log_debug "Running: pytest"
    if ! python -m pytest; then
        log_error "Tests failed after dependency update."
        popd > /dev/null
        return 1
    fi
    
    popd > /dev/null
    log_info "All tests passed successfully."
    return 0
}

#
# Update the requirements file with the current package versions
#
update_requirements_file() {
    local requirements_file="$1"
    local file_name=$(basename "$requirements_file")
    
    log_info "Updating $file_name with current package versions..."
    
    # Ensure the requirements file exists
    if [[ ! -f "$requirements_file" ]]; then
        log_error "Requirements file not found: $requirements_file"
        return 1
    fi
    
    # Activate virtual environment if it exists
    if [[ -d "$PYTHON_VENV" ]]; then
        source "$PYTHON_VENV/bin/activate"
    fi
    
    # Create a temporary file
    local temp_file=$(mktemp)
    
    # Get current installed packages and versions for packages in the requirements file
    local package_names=$(grep -v '^\s*#' "$requirements_file" | sed 's/[<>=].*//' | tr -d ' ' | xargs)
    
    for package in $package_names; do
        if pip show "$package" > /dev/null 2>&1; then
            local version=$(pip show "$package" | grep "^Version" | cut -d' ' -f2)
            echo "$package==$version" >> "$temp_file"
        else
            log_warning "Package $package is in requirements but not installed, skipping."
        fi
    done
    
    # Replace the requirements file with the new one
    mv "$temp_file" "$requirements_file"
    
    log_info "Successfully updated $file_name with current package versions."
    return 0
}

#
# Restore requirements files from backup if update fails
#
restore_backup() {
    local backup_timestamp="$1"
    
    log_info "Restoring requirements files from backup (timestamp: $backup_timestamp)..."
    
    # Restore backend requirements if backup exists
    local backend_backup="$BACKUP_DIR/backend_requirements_${backup_timestamp}.txt"
    if [[ -f "$backend_backup" ]]; then
        cp "$backend_backup" "$BACKEND_REQUIREMENTS"
        log_debug "Restored backend requirements from $backend_backup"
    else
        log_warning "Backend requirements backup not found: $backend_backup"
    fi
    
    # Restore scripts requirements if backup exists
    local scripts_backup="$BACKUP_DIR/scripts_requirements_${backup_timestamp}.txt"
    if [[ -f "$scripts_backup" ]]; then
        cp "$scripts_backup" "$SCRIPTS_REQUIREMENTS"
        log_debug "Restored scripts requirements from $scripts_backup"
    else
        log_warning "Scripts requirements backup not found: $scripts_backup"
    fi
    
    log_info "Backup restoration completed."
    return 0
}

#
# Main function that orchestrates the dependency update process
#
main() {
    log_info "Starting dependency update process..."
    
    # Check if required commands are available
    log_debug "Checking for required commands..."
    if ! check_dependencies "${REQUIRED_COMMANDS[@]}"; then
        log_error "Missing required commands. Please install the required dependencies."
        return 1
    fi
    
    # Check if virtual environment exists
    if [[ ! -d "$PYTHON_VENV" ]]; then
        log_info "Creating virtual environment at $PYTHON_VENV..."
        if ! virtualenv -p python3 "$PYTHON_VENV"; then
            log_error "Failed to create virtual environment."
            return 1
        fi
    fi
    
    # Activate virtual environment
    source "$PYTHON_VENV/bin/activate"
    log_debug "Virtual environment activated: $PYTHON_VENV"
    
    # Backup requirements files if not skipped
    local backup_created=false
    if [[ "$SKIP_BACKUP" == "false" ]]; then
        if backup_requirements; then
            backup_created=true
        else
            log_warning "Failed to create backups. Continuing without backup."
        fi
    else
        log_info "Skipping backup as requested."
    fi
    
    # Check for outdated packages
    local backend_has_updates=false
    local scripts_has_updates=false
    
    # Check backend requirements if not scripts-only
    if [[ "$SCRIPTS_ONLY" == "false" && -f "$BACKEND_REQUIREMENTS" ]]; then
        if check_outdated_packages "$BACKEND_REQUIREMENTS"; then
            backend_has_updates=true
        fi
    fi
    
    # Check scripts requirements if not backend-only
    if [[ "$BACKEND_ONLY" == "false" && -f "$SCRIPTS_REQUIREMENTS" ]]; then
        if check_outdated_packages "$SCRIPTS_REQUIREMENTS"; then
            scripts_has_updates=true
        fi
    fi
    
    # Determine if updates are needed
    local update_needed=false
    if [[ "$backend_has_updates" == "true" || "$scripts_has_updates" == "true" ]]; then
        update_needed=true
    fi
    
    # If check-only flag is set, exit here
    if [[ "$CHECK_ONLY" == "true" ]]; then
        log_info "Check-only mode enabled. Not performing updates."
        return 0
    fi
    
    # Update packages if needed
    if [[ "$update_needed" == "true" ]]; then
        log_info "Updates are available. Proceeding with package updates..."
        
        # Update backend requirements if needed and not scripts-only
        if [[ "$backend_has_updates" == "true" && "$SCRIPTS_ONLY" == "false" ]]; then
            if ! update_packages "$BACKEND_REQUIREMENTS"; then
                log_error "Failed to update backend packages."
                if [[ "$backup_created" == "true" ]]; then
                    restore_backup "$TIMESTAMP"
                fi
                return 1
            fi
        fi
        
        # Update scripts requirements if needed and not backend-only
        if [[ "$scripts_has_updates" == "true" && "$BACKEND_ONLY" == "false" ]]; then
            if ! update_packages "$SCRIPTS_REQUIREMENTS"; then
                log_error "Failed to update script packages."
                if [[ "$backup_created" == "true" ]]; then
                    restore_backup "$TIMESTAMP"
                fi
                return 1
            fi
        fi
        
        # Run tests if not skipped and backend was updated
        if [[ "$SKIP_TESTS" == "false" && "$backend_has_updates" == "true" ]]; then
            if ! run_tests; then
                log_error "Tests failed after package updates. Restoring from backup..."
                if [[ "$backup_created" == "true" ]]; then
                    restore_backup "$TIMESTAMP"
                fi
                return 1
            fi
        elif [[ "$SKIP_TESTS" == "true" ]]; then
            log_info "Skipping tests as requested."
        elif [[ "$backend_has_updates" == "false" ]]; then
            log_info "Backend was not updated, skipping tests."
        fi
        
        # Update requirements files with current versions if they were updated
        if [[ "$backend_has_updates" == "true" && "$SCRIPTS_ONLY" == "false" ]]; then
            update_requirements_file "$BACKEND_REQUIREMENTS"
        fi
        
        if [[ "$scripts_has_updates" == "true" && "$BACKEND_ONLY" == "false" ]]; then
            update_requirements_file "$SCRIPTS_REQUIREMENTS"
        fi
        
        log_info "Dependency update process completed successfully."
    else
        log_info "No updates needed. All packages are up to date."
    fi
    
    return 0
}

#
# Cleanup function to perform cleanup operations before script exit
#
cleanup() {
    log_debug "Starting cleanup operations..."
    
    # Deactivate virtual environment if activated
    if [[ -n "$VIRTUAL_ENV" ]]; then
        deactivate
        log_debug "Virtual environment deactivated."
    fi
    
    # Remove any temporary files
    log_debug "Cleanup completed."
}

# Execute the script if it's run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    run "$@"
fi