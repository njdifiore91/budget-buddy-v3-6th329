"""Package initialization file for the development utilities in the Budget Management Application.

This module exposes development-specific functions and classes to simplify imports and provide a clean interface for local development, testing, and debugging.
"""

import subprocess  # standard library
from typing import List  # typing
from .setup_local_env import main as setup_local_env  # Import function to set up local development environment
from .mock_api_server import run_server, stop_server, app as mock_api_app  # Import Flask application instance for the mock API server with an alias
from .local_run import main as local_run_main  # Import main function from local_run module with an alias
from .create_fixtures import create_fixtures  # Import function to create test fixtures
from .generate_test_data import generate_test_data  # Import function to generate test data

__all__ = ["setup_local_environment", "run_mock_server", "stop_mock_server", "local_run", "create_test_fixtures", "generate_test_data", "run_tests"]


def setup_local_environment(force_reset: bool) -> bool:
    """Set up the local development environment with mock services and test data

    Args:
        force_reset (bool): If True, reset the environment even if it already exists

    Returns:
        bool: True if setup was successful, False otherwise
    """
    # Call setup_local_env script to set up the environment
    result = setup_local_env(force_reset=force_reset)
    # Return True if setup was successful, False otherwise
    return result


def run_mock_server(host: str, port: int, debug: bool) -> threading.Thread:
    """Start the mock API server for local development

    Args:
        host (str): Hostname to bind the server to
        port (int): Port number to listen on
        debug (bool): Enable debug mode

    Returns:
        threading.Thread: Thread running the mock API server
    """
    # Import threading
    import threading
    # Call run_server from mock_api_server module with provided parameters
    thread = run_server(host=host, port=port, debug=debug)
    # Return the thread object running the server
    return thread


def stop_mock_server() -> bool:
    """Stop the running mock API server

    Returns:
        bool: True if server was stopped, False if not running
    """
    # Call stop_server from mock_api_server module
    result = stop_server()
    # Return True if server was stopped, False if not running
    return result


def local_run(args: List[str]) -> int:
    """Run the Budget Management Application locally for development and testing

    Args:
        args (List[str]): Command line arguments to pass to the application

    Returns:
        int: Exit code from the application run
    """
    # Call local_run_main from local_run module with provided arguments
    exit_code = local_run_main(args=args)
    # Return the exit code from the application run
    return exit_code


def create_test_fixtures(output_dir: str) -> bool:
    """Create test fixtures for development and testing

    Args:
        output_dir (str): Directory to store the generated fixtures

    Returns:
        bool: True if fixtures were created successfully, False otherwise
    """
    # Call create_fixtures function with provided output directory
    result = create_fixtures(output_dir=output_dir)
    # Return True if fixtures were created successfully, False otherwise
    return result


def generate_test_data(output_dir: str) -> bool:
    """Generate test data for development and testing

    Args:
        output_dir (str): Directory to store the generated test data

    Returns:
        bool: True if test data was generated successfully, False otherwise
    """
    # Call generate_test_data function with provided output directory
    result = generate_test_data(output_dir=output_dir)
    # Return True if test data was generated successfully, False otherwise
    return result


def run_tests(test_type: str, verbose: bool) -> int:
    """Run tests for the Budget Management Application

    Args:
        test_type (str): Type of tests to run (unit, integration, all)
        verbose (bool): Enable verbose output

    Returns:
        int: Exit code from the test run
    """
    # Import subprocess module
    import subprocess
    # Determine test command based on test_type (unit, integration, all)
    if test_type == "unit":
        test_command = ["pytest", "src/test/unit"]
    elif test_type == "integration":
        test_command = ["pytest", "src/test/integration"]
    else:
        test_command = ["pytest", "src/test"]
    # Add verbose flag if verbose is True
    if verbose:
        test_command.append("-v")
    # Execute test command using subprocess.run
    result = subprocess.run(test_command)
    # Return exit code from the test run
    return result.returncode