"""
Defines configuration settings and environment variable utilities for the Budget Management Application's utility scripts.

This module centralizes script-specific settings, API configurations, and environment variable
handling to ensure consistent behavior across all utility scripts.

Functions:
    get_env_var: Gets an environment variable with a default value if not set.
    get_boolean_env_var: Gets a boolean environment variable with a default value.
    get_int_env_var: Gets an integer environment variable with a default value.
    get_float_env_var: Gets a float environment variable with a default value.
    get_list_env_var: Gets a list environment variable with a default value.
    get_dict_env_var: Gets a dictionary environment variable with a default value.
    update_settings: Updates script settings with values from environment variables.
    get_credential_path: Gets the path to a credential file in the credentials directory.

Constants:
    SCRIPT_SETTINGS: Default settings for all scripts.
    API_TEST_SETTINGS: Settings for API testing scripts.
    MAINTENANCE_SETTINGS: Settings for maintenance scripts.
    DEVELOPMENT_SETTINGS: Settings for development scripts.
"""

import os
from typing import Any, Dict, Optional, Union
import dotenv  # python-dotenv 1.0.0+

from .path_constants import ROOT_DIR, LOGS_DIR, CREDENTIALS_DIR

# Load environment variables from .env file
dotenv.load_dotenv(os.path.join(ROOT_DIR, '.env'))

def get_env_var(var_name: str, default: Any = None) -> Any:
    """
    Gets an environment variable with a default value if not set.
    
    Args:
        var_name: The name of the environment variable.
        default: The default value to return if the environment variable is not set.
        
    Returns:
        The environment variable value or the default value.
    """
    value = os.getenv(var_name)
    return value if value is not None else default


def get_boolean_env_var(var_name: str, default: bool = False) -> bool:
    """
    Gets a boolean environment variable with a default value.
    
    Args:
        var_name: The name of the environment variable.
        default: The default boolean value to return if the environment variable is not set.
        
    Returns:
        The boolean value of the environment variable.
    """
    value = get_env_var(var_name, default)
    if isinstance(value, str):
        value = value.lower()
        if value in ('true', 'yes', 'y', '1'):
            return True
        elif value in ('false', 'no', 'n', '0'):
            return False
    return bool(default)


def get_int_env_var(var_name: str, default: int = 0) -> int:
    """
    Gets an integer environment variable with a default value.
    
    Args:
        var_name: The name of the environment variable.
        default: The default integer value to return if the environment variable is not set.
        
    Returns:
        The integer value of the environment variable.
    """
    value = get_env_var(var_name, default)
    try:
        return int(value)
    except (ValueError, TypeError):
        print(f"Warning: Could not convert environment variable {var_name} to integer. Using default value {default}.")
        return default


def get_float_env_var(var_name: str, default: float = 0.0) -> float:
    """
    Gets a float environment variable with a default value.
    
    Args:
        var_name: The name of the environment variable.
        default: The default float value to return if the environment variable is not set.
        
    Returns:
        The float value of the environment variable.
    """
    value = get_env_var(var_name, default)
    try:
        return float(value)
    except (ValueError, TypeError):
        print(f"Warning: Could not convert environment variable {var_name} to float. Using default value {default}.")
        return default


def get_list_env_var(var_name: str, default: list = None, separator: str = ',') -> list:
    """
    Gets a list environment variable with a default value.
    
    Args:
        var_name: The name of the environment variable.
        default: The default list value to return if the environment variable is not set.
        separator: The separator used to split the environment variable value into a list.
        
    Returns:
        The list value of the environment variable.
    """
    if default is None:
        default = []
    
    value = get_env_var(var_name)
    if value is None:
        return default
    
    if isinstance(value, str):
        return [item.strip() for item in value.split(separator)]
    
    return default


def get_dict_env_var(var_name: str, default: dict = None, item_separator: str = ',', key_value_separator: str = '=') -> dict:
    """
    Gets a dictionary environment variable with a default value.
    
    Args:
        var_name: The name of the environment variable.
        default: The default dictionary value to return if the environment variable is not set.
        item_separator: The separator used to split the environment variable value into items.
        key_value_separator: The separator used to split each item into key-value pairs.
        
    Returns:
        The dictionary value of the environment variable.
    """
    if default is None:
        default = {}
    
    value = get_env_var(var_name)
    if value is None:
        return default
    
    if isinstance(value, str):
        result = {}
        try:
            items = value.split(item_separator)
            for item in items:
                if key_value_separator in item:
                    key, val = item.split(key_value_separator, 1)
                    result[key.strip()] = val.strip()
            return result
        except Exception:
            print(f"Warning: Could not convert environment variable {var_name} to dictionary. Using default value.")
            return default
    
    return default


def update_settings(settings_dict: Dict[str, Any], prefix: str = '') -> Dict[str, Any]:
    """
    Updates script settings with values from environment variables.
    
    This function checks for environment variables with names prefixed by the given
    prefix followed by the settings key, and updates the settings dictionary with
    those values.
    
    Args:
        settings_dict: The settings dictionary to update.
        prefix: The prefix for environment variable names.
        
    Returns:
        The updated settings dictionary.
    """
    updated_settings = settings_dict.copy()
    
    for key in settings_dict:
        env_var_name = f"{prefix}{key}" if prefix else key
        if os.getenv(env_var_name) is not None:
            # Get the environment variable with the appropriate type
            if isinstance(settings_dict[key], bool):
                updated_settings[key] = get_boolean_env_var(env_var_name)
            elif isinstance(settings_dict[key], int):
                updated_settings[key] = get_int_env_var(env_var_name)
            elif isinstance(settings_dict[key], float):
                updated_settings[key] = get_float_env_var(env_var_name)
            elif isinstance(settings_dict[key], list):
                updated_settings[key] = get_list_env_var(env_var_name)
            elif isinstance(settings_dict[key], dict):
                updated_settings[key] = get_dict_env_var(env_var_name)
            else:
                updated_settings[key] = get_env_var(env_var_name)
                
    return updated_settings


def get_credential_path(credential_name: str) -> Optional[str]:
    """
    Gets the path to a credential file in the credentials directory.
    
    Args:
        credential_name: The name of the credential file.
        
    Returns:
        The path to the credential file, or None if the file does not exist.
    """
    cred_path = os.path.join(CREDENTIALS_DIR, credential_name)
    if os.path.exists(cred_path):
        return cred_path
    else:
        print(f"Warning: Credential file {credential_name} not found in {CREDENTIALS_DIR}")
        return None


# Default script settings
SCRIPT_SETTINGS = {
    'LOG_LEVEL': os.getenv('SCRIPT_LOG_LEVEL', 'INFO'),
    'DEBUG': get_boolean_env_var('SCRIPT_DEBUG', False),
    'VERBOSE': get_boolean_env_var('SCRIPT_VERBOSE', False),
    'TIMEOUT': get_int_env_var('SCRIPT_TIMEOUT', 30),
    'MAX_RETRIES': get_int_env_var('SCRIPT_MAX_RETRIES', 3),
    'BACKOFF_FACTOR': get_float_env_var('SCRIPT_BACKOFF_FACTOR', 0.5),
    'USE_JSON_LOGS': get_boolean_env_var('SCRIPT_USE_JSON_LOGS', False)
}

# API test settings
API_TEST_SETTINGS = {
    'CAPITAL_ONE_TEST_ACCOUNT': os.getenv('CAPITAL_ONE_TEST_ACCOUNT', ''),
    'SHEETS_TEST_SPREADSHEET_ID': os.getenv('SHEETS_TEST_SPREADSHEET_ID', ''),
    'SHEETS_TEST_RANGE': os.getenv('SHEETS_TEST_RANGE', 'Sheet1!A1:D10'),
    'GEMINI_TEST_PROMPT': os.getenv('GEMINI_TEST_PROMPT', 'Generate a test response'),
    'GMAIL_TEST_RECIPIENT': os.getenv('GMAIL_TEST_RECIPIENT', 'njdifiore@gmail.com'),
    'GMAIL_TEST_SUBJECT': os.getenv('GMAIL_TEST_SUBJECT', 'Budget Management - API Test'),
    'GMAIL_TEST_BODY': os.getenv('GMAIL_TEST_BODY', 'This is a test email from the Budget Management Application.'),
    'USE_MOCK_RESPONSES': get_boolean_env_var('USE_MOCK_RESPONSES', False),
    'MOCK_RESPONSE_DIR': os.getenv('MOCK_RESPONSE_DIR', os.path.join(ROOT_DIR, 'src', 'test', 'fixtures', 'json', 'api_responses'))
}

# Maintenance script settings
MAINTENANCE_SETTINGS = {
    'HEALTH_CHECK_INTERVAL': get_int_env_var('HEALTH_CHECK_INTERVAL', 24),  # Hours
    'CREDENTIAL_ROTATION_INTERVAL': get_int_env_var('CREDENTIAL_ROTATION_INTERVAL', 90),  # Days
    'BACKUP_INTERVAL': get_int_env_var('BACKUP_INTERVAL', 7),  # Days
    'LOG_RETENTION_DAYS': get_int_env_var('LOG_RETENTION_DAYS', 30),
    'ALERT_EMAIL': os.getenv('ALERT_EMAIL', 'njdifiore@gmail.com'),
    'ALERT_ON_WARNING': get_boolean_env_var('ALERT_ON_WARNING', True),
    'ALERT_ON_ERROR': get_boolean_env_var('ALERT_ON_ERROR', True)
}

# Development script settings
DEVELOPMENT_SETTINGS = {
    'LOCAL_PORT': get_int_env_var('LOCAL_PORT', 8080),
    'MOCK_SERVER_PORT': get_int_env_var('MOCK_SERVER_PORT', 8081),
    'GENERATE_TEST_DATA_COUNT': get_int_env_var('GENERATE_TEST_DATA_COUNT', 50),
    'USE_LOCAL_MOCKS': get_boolean_env_var('USE_LOCAL_MOCKS', True),
    'AUTO_RELOAD': get_boolean_env_var('AUTO_RELOAD', True)
}