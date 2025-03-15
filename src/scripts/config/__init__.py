"""
Initialization module for the Budget Management Application's configuration package.

This module exports path constants, script settings, and logging setup functions
to provide a unified configuration interface for all utility scripts. It serves
as the central entry point for accessing configuration components throughout the
application.
"""

__version__ = '1.0.0'
__author__ = 'Nick DiFiore'
__email__ = 'njdifiore@gmail.com'

# Import path constants
from .path_constants import *

# Import script settings
from .script_settings import *

# Import logging setup
from .logging_setup import setup_logging, get_logger, generate_correlation_id, LoggingContext

import time

def get_script_logger(script_name):
    """
    Convenience function to get a configured logger for a script.
    
    Args:
        script_name: Name of the script requesting the logger
        
    Returns:
        Configured logger for the script
    """
    return get_logger(script_name)


def log_script_start(logger, script_name, args):
    """
    Logs the start of a script execution with context information.
    
    Args:
        logger: Configured logger
        script_name: Name of the script being executed
        args: Arguments passed to the script
        
    Returns:
        Correlation ID for the script execution
    """
    correlation_id = generate_correlation_id()
    logger.info(
        f"Starting script {script_name}",
        extra={
            'correlation_id': correlation_id,
            'context': {'args': args}
        }
    )
    return correlation_id


def log_script_end(logger, script_name, start_time, correlation_id, success=True):
    """
    Logs the end of a script execution with execution time.
    
    Args:
        logger: Configured logger
        script_name: Name of the script being executed
        start_time: Script start time (from time.time())
        correlation_id: Correlation ID from log_script_start
        success: Whether the script executed successfully
    """
    execution_time = time.time() - start_time
    status = "successfully" if success else "with errors"
    logger.info(
        f"Script {script_name} completed {status} in {execution_time:.2f} seconds",
        extra={
            'correlation_id': correlation_id,
            'context': {
                'execution_time': execution_time,
                'success': success
            }
        }
    )


def initialize_script_environment(script_name, args, log_level=None):
    """
    Initializes the script environment with standard configuration.
    
    Args:
        script_name: Name of the script being executed
        args: Arguments passed to the script
        log_level: Optional log level override
        
    Returns:
        Tuple containing (logger, correlation_id, start_time)
    """
    # Set up logging with specified log level
    setup_logging(log_level=log_level)
    
    # Get a logger for this script
    logger = get_script_logger(script_name)
    
    # Log script start
    start_time = time.time()
    correlation_id = log_script_start(logger, script_name, args)
    
    # Create necessary directories
    create_directory_structure()
    
    return logger, correlation_id, start_time