#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../../.." && pwd)
BACKEND_DIR="$ROOT_DIR/src/backend"
TEST_DIR="$ROOT_DIR/src/test"
VENV_DIR="$ROOT_DIR/venv"
REPORT_DIR="$ROOT_DIR/test-reports"
COVERAGE_DIR="$REPORT_DIR/coverage"

# Source the shell template for common functions
source "$SCRIPT_DIR/../../templates/shell_template.sh"

check_test_dependencies() {
    local dependencies=("python" "pytest")
    check_dependencies "${dependencies[@]}"
    return $?
}

setup_test_environment() {
    log_info "Setting up test environment..."
    
    # Check if virtual environment exists
    if [[ ! -d "$VENV_DIR" ]]; then
        log_info "Creating virtual environment at $VENV_DIR"
        python -m venv "$VENV_DIR"
        if [[ $? -ne 0 ]]; then
            log_error "Failed to create virtual environment"
            return 1
        fi
    fi
    
    # Activate virtual environment
    if [[ -f "$VENV_DIR/bin/activate" ]]; then
        source "$VENV_DIR/bin/activate"
    else
        log_error "Virtual environment activation script not found"
        return 1
    fi
    
    # Install test dependencies
    log_info "Installing test dependencies..."
    if [[ -f "$ROOT_DIR/requirements-dev.txt" ]]; then
        pip install -r "$ROOT_DIR/requirements-dev.txt"
    else
        log_warning "requirements-dev.txt not found, installing pytest directly"
        pip install pytest pytest-cov pytest-mock
    fi
    
    # Create test report directories if they don't exist
    mkdir -p "$REPORT_DIR"
    mkdir -p "$COVERAGE_DIR"
    
    log_info "Test environment setup completed"
    return 0
}

run_unit_tests() {
    log_info "Running unit tests..."
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Run pytest with unit test marker
    python -m pytest "$TEST_DIR/unit" -v \
        --junitxml="$REPORT_DIR/unit-tests.xml" \
        --cov="$BACKEND_DIR" \
        --cov-report=term \
        -m "unit"
    
    local exit_code=$?
    
    log_info "Unit tests completed with exit code $exit_code"
    return $exit_code
}

run_integration_tests() {
    log_info "Running integration tests..."
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Run pytest with integration test marker
    python -m pytest "$TEST_DIR/integration" -v \
        --junitxml="$REPORT_DIR/integration-tests.xml" \
        --cov="$BACKEND_DIR" \
        --cov-report=term \
        --cov-append \
        -m "integration"
    
    local exit_code=$?
    
    log_info "Integration tests completed with exit code $exit_code"
    return $exit_code
}

run_e2e_tests() {
    log_info "Running end-to-end tests..."
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Run pytest with e2e test marker
    python -m pytest "$TEST_DIR/e2e" -v \
        --junitxml="$REPORT_DIR/e2e-tests.xml" \
        --cov="$BACKEND_DIR" \
        --cov-report=term \
        --cov-append \
        -m "e2e"
    
    local exit_code=$?
    
    log_info "End-to-end tests completed with exit code $exit_code"
    return $exit_code
}

run_all_tests() {
    log_info "Running all tests..."
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Run all tests with coverage
    python -m pytest "$TEST_DIR" -v \
        --junitxml="$REPORT_DIR/all-tests.xml" \
        --cov="$BACKEND_DIR" \
        --cov-report=term
    
    local exit_code=$?
    
    log_info "All tests completed with exit code $exit_code"
    return $exit_code
}

generate_coverage_report() {
    log_info "Generating coverage report..."
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Generate coverage reports
    python -m coverage html -d "$COVERAGE_DIR/html"
    python -m coverage xml -o "$COVERAGE_DIR/coverage.xml"
    
    if [[ $? -eq 0 ]]; then
        log_info "Coverage report generated at $COVERAGE_DIR"
        return 0
    else
        log_error "Failed to generate coverage report"
        return 1
    fi
}

parse_custom_args() {
    local args=("$@")
    
    # Default values
    RUN_UNIT_TESTS=false
    RUN_INTEGRATION_TESTS=false
    RUN_E2E_TESTS=false
    RUN_ALL_TESTS=false
    GENERATE_COVERAGE=false
    
    # No arguments means run all tests
    if [[ ${#args[@]} -eq 0 ]]; then
        RUN_ALL_TESTS=true
        GENERATE_COVERAGE=true
        return 0
    fi
    
    # Parse arguments
    while (( "$#" )); do
        case "$1" in
            --unit)
                RUN_UNIT_TESTS=true
                shift
                ;;
            --integration)
                RUN_INTEGRATION_TESTS=true
                shift
                ;;
            --e2e)
                RUN_E2E_TESTS=true
                shift
                ;;
            --all)
                RUN_ALL_TESTS=true
                shift
                ;;
            --coverage)
                GENERATE_COVERAGE=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                return 1
                ;;
        esac
    done
    
    return 0
}

show_custom_help() {
    echo "TEST OPTIONS:"
    echo "  --unit          Run unit tests only"
    echo "  --integration   Run integration tests only"
    echo "  --e2e           Run end-to-end tests only"
    echo "  --all           Run all tests (default if no options provided)"
    echo "  --coverage      Generate coverage report"
    echo
    echo "EXAMPLES:"
    echo "  $SCRIPT_NAME --unit                # Run only unit tests"
    echo "  $SCRIPT_NAME --unit --integration  # Run unit and integration tests"
    echo "  $SCRIPT_NAME --all --coverage      # Run all tests and generate coverage report"
    echo "  $SCRIPT_NAME                       # Equivalent to --all --coverage"
}

main() {
    local exit_code=0
    
    # Check test dependencies
    if ! check_test_dependencies; then
        log_error "Missing required dependencies"
        return 1
    fi
    
    # Setup test environment
    if ! setup_test_environment; then
        log_error "Failed to set up test environment"
        return 1
    fi
    
    # Run tests based on arguments
    if [[ "$RUN_UNIT_TESTS" == "true" ]]; then
        run_unit_tests
        exit_code=$((exit_code + $?))
    fi
    
    if [[ "$RUN_INTEGRATION_TESTS" == "true" ]]; then
        run_integration_tests
        exit_code=$((exit_code + $?))
    fi
    
    if [[ "$RUN_E2E_TESTS" == "true" ]]; then
        run_e2e_tests
        exit_code=$((exit_code + $?))
    fi
    
    if [[ "$RUN_ALL_TESTS" == "true" ]]; then
        run_all_tests
        exit_code=$?
    fi
    
    # Generate coverage report if requested
    if [[ "$GENERATE_COVERAGE" == "true" ]]; then
        generate_coverage_report
    fi
    
    if [[ $exit_code -eq 0 ]]; then
        log_info "All tests passed successfully!"
    else
        log_error "Tests completed with errors (exit code: $exit_code)"
    fi
    
    return $exit_code
}

# Execute the script if it's run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    run "$@"
fi