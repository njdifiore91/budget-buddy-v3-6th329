"""
Initialization module for the configuration package.

This module centralizes access to application settings, logging configuration,
and environment variables. It serves as the entry point for all configuration-related
functionality in the Budget Management Application.
"""

# Import settings and configuration from internal modules
from .settings import (
    APP_SETTINGS,
    API_SETTINGS,
    RETRY_SETTINGS,
    get_env_var,
    get_secret,
    get_api_credentials,
    initialize_settings
)

# Import logging utilities
from .logging_config import (
    setup_logging,
    get_logger
)

# Define exported package members
__all__ = [
    "APP_SETTINGS",
    "API_SETTINGS", 
    "RETRY_SETTINGS", 
    "get_env_var", 
    "get_secret", 
    "get_api_credentials", 
    "initialize_settings", 
    "setup_logging", 
    "get_logger",
    "initialize"
]


def initialize(log_level=None, use_cloud_logging=None):
    """
    Initializes both settings and logging configuration.
    
    Args:
        log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_cloud_logging (bool): Whether to use Google Cloud Logging
        
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    # Initialize settings
    settings_success = initialize_settings()
    
    # Setup logging system
    logging_success = setup_logging(log_level, use_cloud_logging)
    
    # Return overall success status
    return settings_success and logging_success