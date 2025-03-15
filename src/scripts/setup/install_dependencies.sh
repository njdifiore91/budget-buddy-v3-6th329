#!/bin/bash
# Script to install all dependencies required for the Budget Management Application
# This includes Python, required libraries, and development tools

# Global variables
PYTHON_VERSION="3.11"
REQUIRED_PACKAGES="google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2 pandas matplotlib seaborn requests python-dotenv pytest pytest-mock pytest-cov freezegun"
LOG_FILE="./dependency_install.log"

# Function to log messages to console and log file
log_message() {
    local message="$1"
    local level="${2:-INFO}"
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    
    echo "[$timestamp] [$level] $message"
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Function to check if Python version meets requirements
check_python_version() {
    if command -v python3 &>/dev/null; then
        local python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
        local major=$(echo "$python_version" | cut -d. -f1)
        local minor=$(echo "$python_version" | cut -d. -f2)
        
        log_message "Found Python version: $python_version"
        
        if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
            return 0
        else
            log_message "Python version $PYTHON_VERSION or higher is required, found $python_version" "WARNING"
            return 1
        fi
    else
        log_message "Python 3 not found" "WARNING"
        return 1
    fi
}

# Function to install Python if not present
install_python() {
    log_message "Installing Python $PYTHON_VERSION..."
    
    # Detect OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &>/dev/null; then
            # Debian/Ubuntu
            log_message "Detected Debian/Ubuntu system"
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv
        elif command -v yum &>/dev/null; then
            # CentOS/RHEL
            log_message "Detected CentOS/RHEL system"
            sudo yum install -y python3 python3-pip
        elif command -v dnf &>/dev/null; then
            # Fedora
            log_message "Detected Fedora system"
            sudo dnf install -y python3 python3-pip
        else
            log_message "Unsupported Linux distribution" "ERROR"
            return 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        log_message "Detected macOS system"
        if command -v brew &>/dev/null; then
            brew install python@3.11
        else
            log_message "Homebrew not found. Please install Homebrew first: https://brew.sh/" "ERROR"
            return 1
        fi
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Windows
        log_message "Detected Windows system"
        log_message "Please install Python $PYTHON_VERSION manually from https://www.python.org/downloads/" "ERROR"
        return 1
    else
        log_message "Unsupported operating system: $OSTYPE" "ERROR"
        return 1
    fi
    
    # Verify installation
    if check_python_version; then
        log_message "Python $PYTHON_VERSION installed successfully"
        return 0
    else
        log_message "Failed to install Python $PYTHON_VERSION" "ERROR"
        return 1
    fi
}

# Function to set up virtual environment
setup_virtual_env() {
    log_message "Setting up virtual environment..."
    
    # Check if venv module is available
    python3 -m venv --help &>/dev/null
    if [ $? -ne 0 ]; then
        log_message "Python venv module not available, installing..." "WARNING"
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            if command -v apt-get &>/dev/null; then
                sudo apt-get install -y python3-venv
            elif command -v yum &>/dev/null; then
                sudo yum install -y python3-venv
            elif command -v dnf &>/dev/null; then
                sudo dnf install -y python3-venv
            fi
        fi
    fi
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        if [ $? -ne 0 ]; then
            log_message "Failed to create virtual environment" "ERROR"
            return 1
        fi
    else
        log_message "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        log_message "To activate the virtual environment, run: .\\venv\\Scripts\\activate"
        # Since we can't activate the venv in the script for Windows, we return success
        return 0
    else
        log_message "Activating virtual environment"
        source venv/bin/activate
        if [ $? -ne 0 ]; then
            log_message "Failed to activate virtual environment" "ERROR"
            return 1
        fi
        log_message "Virtual environment activated"
        return 0
    fi
}

# Function to install dependencies
install_dependencies() {
    log_message "Installing required packages..."
    
    # Upgrade pip
    python -m pip install --upgrade pip
    
    # Install required packages
    python -m pip install $REQUIRED_PACKAGES
    
    if [ $? -ne 0 ]; then
        log_message "Failed to install some dependencies" "ERROR"
        return 1
    fi
    
    log_message "Required packages installed successfully"
    return 0
}

# Function to install development dependencies
install_development_dependencies() {
    log_message "Installing development dependencies..."
    
    # Install development packages
    python -m pip install pytest pytest-mock pytest-cov freezegun pre-commit
    
    if [ $? -ne 0 ]; then
        log_message "Failed to install some development dependencies" "ERROR"
        return 1
    fi
    
    # Setup pre-commit hooks if configuration exists
    if [ -f ".pre-commit-config.yaml" ]; then
        log_message "Setting up pre-commit hooks..."
        pre-commit install
    fi
    
    log_message "Development dependencies installed successfully"
    return 0
}

# Function to set up Google Cloud SDK
setup_gcp_cli() {
    log_message "Checking Google Cloud SDK..."
    
    if command -v gcloud &>/dev/null; then
        log_message "Google Cloud SDK already installed"
        return 0
    fi
    
    log_message "Installing Google Cloud SDK..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl https://sdk.cloud.google.com | bash
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &>/dev/null; then
            brew install --cask google-cloud-sdk
        else
            curl https://sdk.cloud.google.com | bash
        fi
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Windows
        log_message "Please install Google Cloud SDK manually from: https://cloud.google.com/sdk/docs/install" "WARNING"
        return 0
    else
        log_message "Unsupported operating system for Google Cloud SDK installation" "ERROR"
        return 1
    fi
    
    if command -v gcloud &>/dev/null; then
        log_message "Google Cloud SDK installed successfully"
        log_message "Please run 'gcloud init' to initialize the SDK"
        return 0
    else
        log_message "Failed to install Google Cloud SDK" "WARNING"
        return 1
    fi
}

# Main function
main() {
    # Clear or create log file
    > "$LOG_FILE"
    
    log_message "Starting installation of dependencies for Budget Management Application"
    
    # Check if running in development mode
    DEV_MODE=0
    if [ "$1" == "--dev" ]; then
        DEV_MODE=1
        log_message "Running in development mode"
    fi
    
    # Check Python version
    if ! check_python_version; then
        install_python
        if [ $? -ne 0 ]; then
            log_message "Failed to install required Python version" "ERROR"
            return 1
        fi
    fi
    
    # Setup virtual environment
    setup_virtual_env
    if [ $? -ne 0 ]; then
        log_message "Failed to setup virtual environment" "ERROR"
        return 1
    fi
    
    # Install dependencies
    install_dependencies
    if [ $? -ne 0 ]; then
        log_message "Failed to install dependencies" "ERROR"
        return 1
    fi
    
    # Install development dependencies if in dev mode
    if [ $DEV_MODE -eq 1 ]; then
        install_development_dependencies
        if [ $? -ne 0 ]; then
            log_message "Failed to install development dependencies" "ERROR"
            return 1
        fi
    fi
    
    # Setup Google Cloud SDK
    setup_gcp_cli
    
    log_message "Installation completed successfully"
    return 0
}

# Execute main function
main "$@"
exit $?