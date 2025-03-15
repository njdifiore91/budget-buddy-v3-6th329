#!/bin/bash
# Shell script that sets up the complete environment for the Budget Management Application.
# It creates the necessary directory structure, installs dependencies, configures credentials for all external APIs,
# initializes Google Sheets, and verifies API access to ensure the application is ready for execution.

# Define script directory
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Define root directory
ROOT_DIR=$(cd "$SCRIPT_DIR/../../.." && pwd)

# Define data directory
DATA_DIR="$ROOT_DIR/data"

# Define logs directory
LOGS_DIR="$DATA_DIR/logs"

# Define backups directory
BACKUP_DIR="$DATA_DIR/backups"

# Define credentials directory
CREDENTIALS_DIR="$ROOT_DIR/credentials"

# Define .env file path
ENV_FILE="$ROOT_DIR/.env"

# Define .env.example file path
ENV_EXAMPLE_FILE="$ROOT_DIR/src/backend/.env.example"

# Define Python virtual environment directory
PYTHON_VENV="$ROOT_DIR/venv"

# Function to print a banner with application information
print_banner() {
  echo "------------------------------------------------------------------"
  echo "  Budget Management Application - Environment Setup"
  echo "------------------------------------------------------------------"
  echo "  This script will set up the necessary environment for the application."
  echo "  Script location: $SCRIPT_DIR"
  echo "  Version: 1.0"
  echo "  Date: $(date)"
  echo "------------------------------------------------------------------"
}

# Function to print a section header
print_section() {
  section_name="$1"
  echo ""
  echo "=================================================================="
  echo "  $section_name"
  echo "=================================================================="
}

# Function to check if prerequisites are installed
check_prerequisites() {
  print_section "Checking Prerequisites"

  # Check if Python 3.11+ is installed
  if ! command -v python3.11 &> /dev/null; then
    echo "Error: Python 3.11 or higher is required."
    return 1
  else
    echo "Python 3.11+ is installed."
  fi

  # Check if pip is installed
  if ! command -v pip3 &> /dev/null; then
    echo "Error: pip is required."
    return 1
  else
    echo "pip is installed."
  fi

  # Check if virtualenv is installed
  if ! command -v virtualenv &> /dev/null; then
    echo "Error: virtualenv is required."
    return 1
  else
    echo "virtualenv is installed."
  fi

  # Check if git is installed
  if ! command -v git &> /dev/null; then
    echo "Error: git is required."
    return 1
  else
    echo "git is installed."
  fi

  return 0
}

# Function to create the directory structure
create_directory_structure() {
  print_section "Creating Directory Structure"

  # Create data directory if it doesn't exist
  if [ ! -d "$DATA_DIR" ]; then
    mkdir -p "$DATA_DIR"
    echo "Created data directory: $DATA_DIR"
  else
    echo "Data directory already exists: $DATA_DIR"
  fi

  # Create logs directory if it doesn't exist
  if [ ! -d "$LOGS_DIR" ]; then
    mkdir -p "$LOGS_DIR"
    echo "Created logs directory: $LOGS_DIR"
  else
    echo "Logs directory already exists: $LOGS_DIR"
  fi

  # Create backups directory if it doesn't exist
  if [ ! -d "$BACKUP_DIR" ]; then
    mkdir -p "$BACKUP_DIR"
    echo "Created backups directory: $BACKUP_DIR"
  else
    echo "Backups directory already exists: $BACKUP_DIR"
  fi

  # Create credentials directory with secure permissions if it doesn't exist
  if [ ! -d "$CREDENTIALS_DIR" ]; then
    mkdir -p "$CREDENTIALS_DIR"
    chmod 700 "$CREDENTIALS_DIR"
    echo "Created credentials directory: $CREDENTIALS_DIR"
  else
    echo "Credentials directory already exists: $CREDENTIALS_DIR"
  fi

  return 0
}

# Function to set up the virtual environment
setup_virtual_environment() {
  print_section "Setting Up Virtual Environment"

  # Check if virtual environment already exists
  if [ -d "$PYTHON_VENV" ]; then
    echo "Virtual environment already exists: $PYTHON_VENV"
  else
    # Create virtual environment if it doesn't exist
    echo "Creating virtual environment: $PYTHON_VENV"
    virtualenv "$PYTHON_VENV" || return 1
  fi

  # Activate virtual environment
  source "$PYTHON_VENV/bin/activate"

  # Upgrade pip to latest version
  echo "Upgrading pip"
  "$PYTHON_VENV/bin/pip3" install --upgrade pip || return 1

  # Install dependencies from requirements.txt
  echo "Installing dependencies from requirements.txt"
  "$PYTHON_VENV/bin/pip3" install --no-cache-dir -r "$ROOT_DIR/requirements.txt" || return 1

  return 0
}

# Function to set up the .env file
setup_env_file() {
  print_section "Setting Up .env File"

  # Check if .env file already exists
  if [ -f "$ENV_FILE" ]; then
    echo ".env file already exists: $ENV_FILE"
  else
    # If it doesn't exist, copy from .env.example
    if [ -f "$ENV_EXAMPLE_FILE" ]; then
      echo "Copying .env.example to .env"
      cp "$ENV_EXAMPLE_FILE" "$ENV_FILE" || return 1
    else
      # If .env.example doesn't exist, create a basic .env file with default settings
      echo "Creating basic .env file"
      cat > "$ENV_FILE" <<EOL
# Basic .env file for Budget Management Application
# Add your API keys and other configuration settings here
EOL
    fi
  fi

  return 0
}

# Function to run a Python script in the virtual environment
run_python_script() {
  script_path="$1"
  args="$2"

  # Activate virtual environment
  source "$PYTHON_VENV/bin/activate"

  # Run the specified Python script with provided arguments
  echo "Running Python script: $script_path $args"
  "$PYTHON_VENV/bin/python3" "$script_path" $args
  script_exit_code=$?

  return $script_exit_code
}

# Function to configure API credentials
configure_api_credentials() {
  print_section "Configuring API Credentials"

  # Run configure_credentials.py script
  run_python_script "$SCRIPT_DIR/configure_credentials.py"
  api_credentials_exit_code=$?

  return $api_credentials_exit_code
}

# Function to initialize Google Sheets
initialize_google_sheets() {
  print_section "Initializing Google Sheets"

  # Run initialize_sheets.py script
  run_python_script "$SCRIPT_DIR/initialize_sheets.py"
  initialize_sheets_exit_code=$?

  return $initialize_sheets_exit_code
}

# Function to verify API access
verify_api_access() {
  print_section "Verifying API Access"

  # Run verify_api_access.py script
  run_python_script "$SCRIPT_DIR/verify_api_access.py"
  verify_api_exit_code=$?

  return $verify_api_exit_code
}

# Main function that orchestrates the entire setup process
main() {
  # Print banner with application information
  print_banner

  # Check prerequisites
  if check_prerequisites; then
    echo "Prerequisites check passed."
  else
    echo "Error: Prerequisites check failed."
    return 1
  fi

  # Create directory structure
  if create_directory_structure; then
    echo "Directory structure created successfully."
  else
    echo "Error: Failed to create directory structure."
    return 1
  fi

  # Setup virtual environment and install dependencies
  if setup_virtual_environment; then
    echo "Virtual environment setup and dependencies installed successfully."
  else
    echo "Error: Failed to setup virtual environment and install dependencies."
    return 1
  fi

  # Setup .env file with default configuration
  if setup_env_file; then
    echo ".env file setup successfully."
  else
    echo "Error: Failed to setup .env file."
    return 1
  fi

  # Configure API credentials for all external services
  if configure_api_credentials; then
    echo "API credentials configured successfully."
  else
    echo "Error: Failed to configure API credentials."
    return 1
  fi

  # Initialize Google Sheets for budget and transaction data
  if initialize_google_sheets; then
    echo "Google Sheets initialized successfully."
  else
    echo "Error: Failed to initialize Google Sheets."
    return 1
  fi

  # Verify access to all required external APIs
  if verify_api_access; then
    echo "API access verified successfully."
  else
    echo "Error: Failed to verify API access."
    return 1
  fi

  # Print setup completion message
  echo ""
  echo "------------------------------------------------------------------"
  echo "  Environment setup complete!"
  echo "  You can now run the Budget Management Application."
  echo "------------------------------------------------------------------"

  return 0
}

# Execute main function
exit_code=$(main)
exit $exit_code