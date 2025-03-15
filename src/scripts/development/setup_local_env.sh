#!/bin/bash
# Shell script that sets up a local development environment for the Budget Management Application.
# It creates the necessary directory structure, installs dependencies, configures environment variables,
# sets up mock API servers, and prepares the environment for local testing and development.

# Source common environment setup functions
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/../../setup/setup_environment.sh"

# Define root directory
ROOT_DIR=$(cd "$SCRIPT_DIR/../../.." && pwd)

# Define backend directory
BACKEND_DIR="$ROOT_DIR/src/backend"

# Define scripts directory
SCRIPTS_DIR="$ROOT_DIR/src/scripts"

# Define data directory
DATA_DIR="$ROOT_DIR/data"

# Define logs directory
LOGS_DIR="$DATA_DIR/logs"

# Define credentials directory
CREDENTIALS_DIR="$ROOT_DIR/credentials"

# Define .env file path
ENV_FILE="$ROOT_DIR/.env"

# Define .env.example file path
ENV_EXAMPLE_FILE="$BACKEND_DIR/.env.example"

# Define Python virtual environment directory
PYTHON_VENV="$ROOT_DIR/venv"

# Define mock server PID file
MOCK_SERVER_PID_FILE="$DATA_DIR/mock_server.pid"

# Function to set up the .env file with development-specific configuration
setup_dev_env_file() {
  print_section "Setting Up Development .env File"

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

  # Update .env file with development-specific settings
  echo "Setting ENVIRONMENT=development"
  echo "ENVIRONMENT=development" >> "$ENV_FILE"

  echo "Setting DEBUG=true"
  echo "DEBUG=true" >> "$ENV_FILE"

  echo "Setting USE_LOCAL_MOCKS=true"
  echo "USE_LOCAL_MOCKS=true" >> "$ENV_FILE"

  # Set DRY_RUN=true for safety in development
  echo "Setting DRY_RUN=true"
  echo "DRY_RUN=true" >> "$ENV_FILE"

  return 0
}

# Function to install development-specific dependencies
install_dev_dependencies() {
  print_section "Installing Development Dependencies"

  # Activate virtual environment
  source "$PYTHON_VENV/bin/activate"

  # Install development dependencies from requirements-dev.txt if it exists
  if [ -f "$ROOT_DIR/requirements-dev.txt" ]; then
    echo "Installing development dependencies from requirements-dev.txt"
    "$PYTHON_VENV/bin/pip3" install --no-cache-dir -r "$ROOT_DIR/requirements-dev.txt" || return 1
  fi

  # Install testing dependencies
  echo "Installing testing dependencies"
  "$PYTHON_VENV/bin/pip3" install --no-cache-dir pytest pytest-mock pytest-cov freezegun || return 1

  # Install mock server dependencies (Flask)
  echo "Installing mock server dependencies (Flask)"
  "$PYTHON_VENV/bin/pip3" install --no-cache-dir Flask || return 1

  # Install development tools (pytest, black, flake8)
  echo "Installing development tools (pytest, black, flake8)"
  "$PYTHON_VENV/bin/pip3" install --no-cache-dir black flake8 || return 1

  return 0
}

# Function to set up mock credentials for development
setup_mock_credentials() {
  print_section "Setting Up Mock Credentials"

  # Create mock credentials directory if it doesn't exist
  if [ ! -d "$CREDENTIALS_DIR" ]; then
    mkdir -p "$CREDENTIALS_DIR"
    chmod 700 "$CREDENTIALS_DIR"
    echo "Created credentials directory: $CREDENTIALS_DIR"
  fi

  # Create mock Capital One credentials file with test values
  echo "Creating mock Capital One credentials file"
  cat > "$CREDENTIALS_DIR/capital_one_credentials.json" <<EOL
{
  "client_id": "mock_capital_one_client_id",
  "client_secret": "mock_capital_one_client_secret"
}
EOL
  chmod 600 "$CREDENTIALS_DIR/capital_one_credentials.json"

  # Create mock Google Sheets credentials file with test values
  echo "Creating mock Google Sheets credentials file"
  cat > "$CREDENTIALS_DIR/sheets_credentials.json" <<EOL
{
  "type": "service_account",
  "project_id": "mock-project-id",
  "private_key_id": "mock_private_key_id",
  "private_key": "mock_private_key",
  "client_email": "mock@example.com",
  "client_id": "mock_client_id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/certs",
  "client_x509_cert_url": "https://www.googleapis.com/oauth2/certs"
}
EOL
  chmod 600 "$CREDENTIALS_DIR/sheets_credentials.json"

  # Create mock Gmail credentials file with test values
  echo "Creating mock Gmail credentials file"
  cat > "$CREDENTIALS_DIR/gmail_credentials.json" <<EOL
{
  "type": "service_account",
  "project_id": "mock-project-id",
  "private_key_id": "mock_private_key_id",
  "private_key": "mock_private_key",
  "client_email": "mock@example.com",
  "client_id": "mock_client_id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/certs",
  "client_x509_cert_url": "https://www.googleapis.com/oauth2/certs"
}
EOL
  chmod 600 "$CREDENTIALS_DIR/gmail_credentials.json"

  # Set Gemini API key in .env file to a test value
  echo "Setting GEMINI_API_KEY=mock_gemini_api_key in .env file"
  echo "GEMINI_API_KEY=mock_gemini_api_key" >> "$ENV_FILE"

  return 0
}

# Function to start the mock API server for local development
start_mock_api_server() {
  print_section "Starting Mock API Server"

  # Check if mock server is already running
  if [ -f "$MOCK_SERVER_PID_FILE" ]; then
    pid=$(cat "$MOCK_SERVER_PID_FILE")
    if ps -p "$pid" > /dev/null; then
      echo "Mock server is already running with PID: $pid"
      read -p "Do you want to restart it? (y/n): " -n 1 -r
      echo    # (optional) move to a new line
      if [[ $REPLY =~ ^[Yy]$ ]]
      then
        echo "Stopping existing mock server..."
        kill "$pid" || true
        wait "$pid" 2>/dev/null || true
        rm -f "$MOCK_SERVER_PID_FILE"
      else
        echo "Keeping existing mock server running."
        return 0
      fi
    fi
  fi

  # Activate virtual environment
  source "$PYTHON_VENV/bin/activate"

  # Start mock_api_server.py in background
  echo "Starting mock_api_server.py in background"
  "$PYTHON_VENV/bin/python3" "$BACKEND_DIR/mock_api_server.py" > "$LOGS_DIR/mock_server.log" 2>&1 &
  mock_server_pid=$!

  # Save PID to file for later management
  echo "$mock_server_pid" > "$MOCK_SERVER_PID_FILE"
  echo "Mock server PID saved to: $MOCK_SERVER_PID_FILE"

  # Wait for server to start up (crude check)
  echo "Waiting for mock server to start up..."
  sleep 5

  # Verify server is responding (replace with a proper health check)
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:8081 | grep -q "200"; then
    echo "Mock server is responding."
  else
    echo "Error: Mock server is not responding."
    return 1
  fi

  return 0
}

# Function to set up test data for local development
setup_test_data() {
  print_section "Setting Up Test Data"

  # Activate virtual environment
  source "$PYTHON_VENV/bin/activate"

  # Run generate_test_data.py script to create sample transactions
  echo "Running generate_test_data.py script"
  "$PYTHON_VENV/bin/python3" "$SCRIPTS_DIR/generate_test_data.py" || return 1

  # Create test budget categories in mock Google Sheets response
  echo "Creating test budget categories in mock Google Sheets response"
  # (Implementation depends on how mock responses are managed)

  return 0
}

# Function to set up Git hooks for development workflow
setup_git_hooks() {
  print_section "Setting Up Git Hooks"

  # Create pre-commit hook to run linting and tests
  echo "Creating pre-commit hook"
  cat > "$ROOT_DIR/.git/hooks/pre-commit" <<EOL
#!/bin/sh
echo "Running pre-commit checks..."
source "$PYTHON_VENV/bin/activate"
black .
flake8 .
pytest
EOL
  chmod +x "$ROOT_DIR/.git/hooks/pre-commit"

  # Create pre-push hook to run full test suite
  echo "Creating pre-push hook"
  cat > "$ROOT_DIR/.git/hooks/pre-push" <<EOL
#!/bin/sh
echo "Running pre-push checks..."
source "$PYTHON_VENV/bin/activate"
pytest --cov=src --cov-report term-missing
EOL
  chmod +x "$ROOT_DIR/.git/hooks/pre-push"

  # Make hooks executable
  echo "Making hooks executable"
  chmod +x "$ROOT_DIR/.git/hooks/*"

  return 0
}

# Main function that orchestrates the local development environment setup
main() {
  # Print banner with application information
  print_banner

  # Check prerequisites (Python, pip, git)
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

  # Install development-specific dependencies
  if install_dev_dependencies; then
    echo "Development dependencies installed successfully."
  else
    echo "Error: Failed to install development dependencies."
    return 1
  fi

  # Setup development-specific .env file
  if setup_dev_env_file; then
    echo ".env file setup successfully."
  else
    echo "Error: Failed to setup .env file."
    return 1
  fi

  # Setup mock credentials for development
  if setup_mock_credentials; then
    echo "Mock credentials configured successfully."
  else
    echo "Error: Failed to configure mock credentials."
    return 1
  fi

  # Setup test data for local development
  if setup_test_data; then
    echo "Test data setup successfully."
  else
    echo "Error: Failed to setup test data."
    return 1
  fi

  # Start mock API server
  if start_mock_api_server; then
    echo "Mock API server started successfully."
  else
    echo "Error: Failed to start mock API server."
    return 1
  fi

  # Setup Git hooks
  if setup_git_hooks; then
    echo "Git hooks setup successfully."
  else
    echo "Error: Failed to setup Git hooks."
    return 1
  fi

  # Print setup completion message with instructions for local development
  echo ""
  echo "------------------------------------------------------------------"
  echo "  Local development environment setup complete!"
  echo "  - Activate the virtual environment: source venv/bin/activate"
  echo "  - Run the application: python src/backend/main.py"
  echo "  - Access mock API server at http://localhost:8081"
  echo "------------------------------------------------------------------"

  return 0
}

# Execute main function
exit_code=$(main)
exit $exit_code