"""
A development utility script that enables local execution of the Budget Management Application for testing and development purposes.
It sets up a local environment with mock API services, configures logging, and runs the application's main process with appropriate development settings.
"""

import os  # standard library
import sys  # standard library
import argparse  # standard library
import signal  # standard library
import time  # standard library

from python_dotenv import load_dotenv  # python-dotenv 1.0.0+

from src.scripts.config.script_settings import DEVELOPMENT_SETTINGS  # Access development-specific settings
from src.scripts.config.logging_setup import get_script_logger  # Get configured logger for the local run script
from src.scripts.development.mock_api_server import run_server, stop_server  # Start/stop the mock API server
from src.backend.main import main as app_main  # Import the main application entry point with an alias

# Global variables
logger = get_script_logger('local_run')  # Logger instance for this script
mock_server_thread = None  # Thread for the mock API server


def setup_environment(args: argparse.Namespace) -> bool:
    """
    Set up the local development environment with appropriate settings

    Args:
        args (argparse.Namespace): Parsed command line arguments

    Returns:
        bool: True if setup successful, False otherwise
    """
    try:
        # Load environment variables from .env.development file
        load_dotenv(dotenv_path=".env.development")

        # Set environment variable to indicate development environment
        os.environ['ENVIRONMENT'] = 'development'

        # Set environment variable to use mock APIs if specified in args
        if args.no_mocks:
            os.environ['USE_LOCAL_MOCKS'] = 'False'
        else:
            os.environ['USE_LOCAL_MOCKS'] = 'True'

        # Configure logging level based on args.verbose
        if args.verbose:
            os.environ['SCRIPT_LOG_LEVEL'] = 'DEBUG'

        # Log environment setup information
        logger.info("Local development environment setup complete", extra={
            "use_mocks": not args.no_mocks,
            "verbose_logging": args.verbose
        })
        return True
    except Exception as e:
        logger.error(f"Error setting up environment: {e}")
        return False


def start_mock_services(port: int) -> bool:
    """
    Start mock API services for local testing

    Args:
        port (int): Port number for the mock API server

    Returns:
        bool: True if mock services started successfully, False otherwise
    """
    global mock_server_thread
    try:
        logger.info("Starting mock API services", extra={"port": port})
        mock_server_thread = run_server(port=port)
        time.sleep(1)  # Give the server a moment to start

        if mock_server_thread and mock_server_thread.is_alive():
            logger.info("Mock API services started successfully")
            return True
        else:
            logger.error("Failed to start mock API services")
            return False
    except Exception as e:
        logger.error(f"Error starting mock API services: {e}")
        return False


def stop_mock_services() -> bool:
    """
    Stop running mock API services

    Returns:
        bool: True if mock services stopped successfully, False otherwise
    """
    global mock_server_thread
    try:
        if mock_server_thread is not None:
            logger.info("Stopping mock API services")
            stop_server()
            mock_server_thread = None
            logger.info("Mock API services stopped successfully")
            return True
        else:
            logger.info("No mock API services to stop")
            return False
    except Exception as e:
        logger.error(f"Error stopping mock API services: {e}")
        return False


def signal_handler(sig: int, frame: object) -> None:
    """
    Handle termination signals for graceful shutdown

    Args:
        sig (int): Signal number
        frame (frame): Frame object
    """
    logger.info(f"Received termination signal: {sig}")
    stop_mock_services()
    logger.info("Shutdown complete")
    sys.exit(0)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments for local run configuration

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(description="Run the Budget Management Application locally")
    parser.add_argument("--no-mocks", action="store_true", help="Disable mock API services")
    parser.add_argument("--port", type=int, default=DEVELOPMENT_SETTINGS['LOCAL_PORT'], help="Port for the mock API server")
    parser.add_argument("--check-health", action="store_true", help="Run system health check")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()


def run_application(args: argparse.Namespace) -> int:
    """
    Run the Budget Management Application locally

    Args:
        args (argparse.Namespace): Parsed command line arguments

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        logger.info("Starting local application run")

        # Set environment variables based on args
        if args.debug:
            os.environ['DEBUG'] = 'True'
        else:
            os.environ['DEBUG'] = 'False'

        # Call the main application function
        exit_code = app_main()

        logger.info(f"Application run completed with status: {exit_code}")
        return exit_code
    except Exception as e:
        logger.error(f"Error running application: {e}")
        return 1


def main() -> int:
    """
    Main entry point for local run script

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Parse command line arguments
    args = parse_arguments()

    # Register signal handlers for SIGINT and SIGTERM
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Set up environment
    if not setup_environment(args):
        logger.error("Environment setup failed")
        return 1

    # Start mock services if not disabled
    if not args.no_mocks:
        if not start_mock_services(args.port):
            logger.error("Mock services failed to start")
            return 1

    # Run the application
    exit_code = run_application(args)

    # Stop mock services if they were started
    if not args.no_mocks:
        stop_mock_services()

    # Return application exit code
    return exit_code


if __name__ == "__main__":
    sys.exit(main())