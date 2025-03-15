#!/bin/bash
#
# Shell Script Template
# 
# This template provides standardized structure, logging, error handling,
# and utility functions for shell scripts in the Budget Management Application.
#
# Usage: 
#   1. Copy this template to create a new script
#   2. Implement the main() and parse_custom_args() functions
#   3. Update show_custom_help() with script-specific help information
#   4. Use exported functions for consistent logging and error handling

# Exit immediately if a command exits with a non-zero status
set -e

# Get script directory
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Get root directory
ROOT_DIR=$(cd "$SCRIPT_DIR/../../.." && pwd)

# Script name
SCRIPT_NAME=$(basename "${BASH_SOURCE[0]}")

# Default settings
VERBOSE=${VERBOSE:-false}
DEBUG=${DEBUG:-false}
LOG_LEVEL=${LOG_LEVEL:-INFO}
MAX_RETRIES=${MAX_RETRIES:-3}
RETRY_DELAY=${RETRY_DELAY:-5}

# Log file setup
LOGS_DIR=${LOGS_DIR:-$ROOT_DIR/data/logs}
LOG_FILE=${LOG_FILE:-$LOGS_DIR/${SCRIPT_NAME%.sh}.log}

#
# Logging Functions
#

# Log a message with the specified level
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    local log_line="[$timestamp] [$SCRIPT_NAME] [$level] $message"
    
    # Ensure log directory exists
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Log to console
    if [[ "$level" == "ERROR" ]]; then
        echo -e "$log_line" >&2
    elif [[ "$VERBOSE" == "true" ]] || [[ "$level" == "ERROR" ]] || [[ "$level" == "WARNING" ]]; then
        echo -e "$log_line"
    fi
    
    # Log to file
    echo -e "$log_line" >> "$LOG_FILE"
}

# Log a debug message if DEBUG mode is enabled
log_debug() {
    if [[ "$DEBUG" == "true" ]]; then
        log_message "DEBUG" "$1"
    fi
}

# Log an info message
log_info() {
    log_message "INFO" "$1"
}

# Log a warning message
log_warning() {
    log_message "WARNING" "$1"
}

# Log an error message
log_error() {
    log_message "ERROR" "$1"
}

#
# Utility Functions
#

# Check if a command exists
check_command_exists() {
    command -v "$1" >/dev/null 2>&1
    return $?
}

# Check if all required dependencies are installed
check_dependencies() {
    local dependencies=("$@")
    local missing=false
    
    for cmd in "${dependencies[@]}"; do
        if ! check_command_exists "$cmd"; then
            log_error "Required dependency '$cmd' is not installed."
            missing=true
        fi
    done
    
    if [[ "$missing" == "true" ]]; then
        return 1
    fi
    
    return 0
}

# Execute a command with retry logic
retry_command() {
    local cmd="$1"
    local retry_count=0
    local exit_code=0
    
    while [[ $retry_count -lt $MAX_RETRIES ]]; do
        log_debug "Executing command: $cmd"
        
        # Execute the command
        eval "$cmd"
        exit_code=$?
        
        if [[ $exit_code -eq 0 ]]; then
            if [[ $retry_count -gt 0 ]]; then
                log_info "Command succeeded after $retry_count retries."
            fi
            return $exit_code
        fi
        
        retry_count=$((retry_count + 1))
        
        if [[ $retry_count -lt $MAX_RETRIES ]]; then
            log_warning "Command failed (exit code $exit_code). Retrying in $RETRY_DELAY seconds... (attempt $retry_count/$MAX_RETRIES)"
            sleep $RETRY_DELAY
        else
            log_error "Command failed after $MAX_RETRIES attempts (exit code $exit_code)."
            return $exit_code
        fi
    done
    
    return $exit_code
}

# Perform cleanup operations before script exit
cleanup() {
    log_debug "Starting cleanup operations..."
    
    # Implement cleanup logic here
    # Examples:
    # - Remove temporary files
    # - Reset configurations
    # - Release resources
    
    log_debug "Cleanup completed."
}

# Handle errors and perform cleanup
handle_error() {
    local exit_code="$1"
    local error_message="$2"
    
    log_error "$error_message (exit code: $exit_code)"
    cleanup
    exit "$exit_code"
}

#
# Argument Parsing Functions
#

# Parse command line arguments
parse_args() {
    OPTIND=1
    
    while getopts ":vdh" opt; do
        case $opt in
            v)
                VERBOSE=true
                ;;
            d)
                DEBUG=true
                ;;
            h)
                show_help
                exit 0
                ;;
            \?)
                log_error "Invalid option: -$OPTARG"
                show_help
                return 1
                ;;
            :)
                log_error "Option -$OPTARG requires an argument."
                show_help
                return 1
                ;;
        esac
    done
    
    # Shift processed options
    shift $((OPTIND-1))
    
    # Call script-specific argument parsing
    parse_custom_args "$@"
    return $?
}

# Parse script-specific command line arguments
# To be implemented by scripts using this template
parse_custom_args() {
    # Implement custom argument parsing in derived scripts
    return 0
}

#
# Help Information
#

# Display help information
show_help() {
    echo "NAME:"
    echo "  $SCRIPT_NAME - Script description goes here"
    echo
    echo "USAGE:"
    echo "  $SCRIPT_NAME [options] [arguments]"
    echo
    echo "OPTIONS:"
    echo "  -v              Enable verbose mode"
    echo "  -d              Enable debug mode (includes verbose)"
    echo "  -h              Show this help message"
    echo
    
    # Display script-specific help
    show_custom_help
}

# Display script-specific help information
# To be implemented by scripts using this template
show_custom_help() {
    echo "CUSTOM OPTIONS:"
    echo "  No custom options available for this script template."
    echo
    echo "DESCRIPTION:"
    echo "  This is a template script. Replace this help text with"
    echo "  information specific to your script implementation."
}

#
# Main Function (to be implemented by derived scripts)
#

main() {
    log_warning "The main() function must be implemented by the script using this template."
    return 0
}

#
# Script Execution
#

# Entry point function
run() {
    local start_time=$(date +%s)
    local exit_code=0
    
    # Parse command line arguments
    if ! parse_args "$@"; then
        exit 1
    fi
    
    # Set up trap for error handling
    trap 'handle_error $? "Unexpected error occurred"' ERR
    
    # Ensure log directory exists
    mkdir -p "$LOGS_DIR"
    
    log_info "Starting script execution"
    
    if [[ "$DEBUG" == "true" ]]; then
        log_debug "Debug mode enabled"
    fi
    
    # Execute main function
    main
    exit_code=$?
    
    # Calculate execution time
    local end_time=$(date +%s)
    local execution_time=$((end_time - start_time))
    
    log_info "Script completed with exit code $exit_code (execution time: ${execution_time}s)"
    
    return $exit_code
}

# Execute the script if it's run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    run "$@"
fi