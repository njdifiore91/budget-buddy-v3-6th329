"""
settings.py - Central configuration module for the Budget Management Application

This module manages environment-specific settings, API credentials, and application parameters.
It provides functions for securely accessing environment variables and secrets.
"""

import os  # standard library
import json  # standard library
import logging  # standard library
import decimal  # standard library
from dotenv import load_dotenv  # python-dotenv 1.0.0+
from google.cloud import secretmanager  # google-cloud-secret-manager 2.16.0+

# Set up logger
logger = logging.getLogger(__name__)

# Environment settings
ENV = os.getenv('ENVIRONMENT', 'development')
DEBUG = ENV == 'development'
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')

# Application settings
APP_SETTINGS = {
    "DEBUG": DEBUG,
    "LOG_LEVEL": os.getenv('LOG_LEVEL', 'INFO'),
    "WEEKLY_SPENDING_SHEET_ID": os.getenv('WEEKLY_SPENDING_SHEET_ID'),
    "MASTER_BUDGET_SHEET_ID": os.getenv('MASTER_BUDGET_SHEET_ID'),
    "MIN_TRANSFER_AMOUNT": decimal.Decimal('1.00'),  # Minimum amount to transfer to savings
    "CATEGORIZATION_THRESHOLD": 0.95,  # Required threshold for transaction categorization
    "EMAIL_RECIPIENTS": ['njdifiore@gmail.com', 'nick@blitzy.com'],
    "EMAIL_SENDER": 'njdifiore@gmail.com'
}

# API integration settings
API_SETTINGS = {
    "CAPITAL_ONE": {
        "BASE_URL": os.getenv('CAPITAL_ONE_API_URL', 'https://api.capitalone.com'),
        "AUTH_URL": os.getenv('CAPITAL_ONE_AUTH_URL', 'https://api.capitalone.com/oauth2/token'),
        "CLIENT_ID_SECRET": 'capital-one-credentials',
        "CHECKING_ACCOUNT_ID": os.getenv('CAPITAL_ONE_CHECKING_ACCOUNT_ID'),
        "SAVINGS_ACCOUNT_ID": os.getenv('CAPITAL_ONE_SAVINGS_ACCOUNT_ID')
    },
    "GOOGLE_SHEETS": {
        "API_VERSION": 'v4',
        "SCOPES": ['https://www.googleapis.com/auth/spreadsheets'],
        "CREDENTIALS_SECRET": 'google-sheets-credentials'
    },
    "GEMINI": {
        "API_URL": 'https://generativelanguage.googleapis.com',
        "API_VERSION": 'v1',
        "MODEL": 'gemini-pro',
        "API_KEY_SECRET": 'gemini-api-key'
    },
    "GMAIL": {
        "API_VERSION": 'v1',
        "SCOPES": ['https://www.googleapis.com/auth/gmail.send'],
        "CREDENTIALS_SECRET": 'gmail-credentials'
    }
}

# Retry configuration for API calls
RETRY_SETTINGS = {
    "DEFAULT_MAX_RETRIES": 3,
    "DEFAULT_RETRY_DELAY": 1,  # Initial delay in seconds
    "DEFAULT_RETRY_BACKOFF_FACTOR": 2.0,  # Exponential backoff multiplier
    "DEFAULT_RETRY_JITTER": 0.1,  # Random jitter factor
    "RETRIABLE_STATUS_CODES": [429, 500, 502, 503, 504]  # HTTP status codes to retry
}


def get_env_var(var_name, default=None):
    """
    Retrieves an environment variable with fallback to default value.
    
    Args:
        var_name (str): Name of the environment variable
        default (str): Default value if variable is not found
        
    Returns:
        str: Value of the environment variable or default
    """
    # Ensure .env file is loaded in development environment
    if ENV == 'development':
        load_dotenv()
    
    value = os.getenv(var_name, default)
    if value is None:
        logger.warning(f"Environment variable {var_name} not found and no default provided")
    elif value == default and default is not None:
        logger.debug(f"Using default value for {var_name}")
    
    return value


def get_secret(secret_name, version_id=None, project_id=None):
    """
    Retrieves a secret from Google Cloud Secret Manager.
    
    Args:
        secret_name (str): Name of the secret
        version_id (str): Version of the secret, defaults to 'latest'
        project_id (str): Google Cloud project ID, defaults to PROJECT_ID
        
    Returns:
        str: Secret value as string
    """
    if project_id is None:
        project_id = PROJECT_ID
    
    if version_id is None:
        version_id = 'latest'
    
    try:
        # Create the Secret Manager client
        client = secretmanager.SecretManagerServiceClient()
        
        # Build the resource name of the secret version
        name = f"projects/{project_id}/secrets/{secret_name}/versions/{version_id}"
        
        # Access the secret version
        response = client.access_secret_version(request={"name": name})
        
        # Return the decoded payload
        return response.payload.data.decode('UTF-8')
    
    except Exception as e:
        logger.error(f"Error retrieving secret {secret_name}: {str(e)}")
        
        # In development mode, attempt to use environment variables as fallback
        if ENV == 'development':
            env_var_name = secret_name.replace('-', '_').upper()
            logger.warning(f"Attempting to use environment variable {env_var_name} as fallback")
            return os.getenv(env_var_name, '')
        
        raise


def load_json_secret(secret_name, version_id=None, project_id=None):
    """
    Loads a JSON-formatted secret from Secret Manager.
    
    Args:
        secret_name (str): Name of the secret
        version_id (str): Version of the secret, defaults to 'latest'
        project_id (str): Google Cloud project ID, defaults to PROJECT_ID
        
    Returns:
        dict: Parsed JSON secret as dictionary
    """
    try:
        secret_value = get_secret(secret_name, version_id, project_id)
        return json.loads(secret_value)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON secret {secret_name}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error loading JSON secret {secret_name}: {str(e)}")
        raise


def get_api_credentials(service_name):
    """
    Retrieves API credentials for a specific service.
    
    Args:
        service_name (str): Name of the service (CAPITAL_ONE, GOOGLE_SHEETS, GEMINI, GMAIL)
        
    Returns:
        dict: API credentials for the specified service
    """
    if service_name not in API_SETTINGS:
        logger.error(f"Unknown service: {service_name}")
        raise ValueError(f"Unknown service: {service_name}")
    
    try:
        service_config = API_SETTINGS[service_name]
        
        # Determine which secret to retrieve based on service
        if service_name == "GEMINI":
            # For Gemini, we just need the API key
            secret_name = service_config['API_KEY_SECRET']
            return get_secret(secret_name)
        else:
            # For OAuth services, we need the full credentials JSON
            secret_name = service_config['CREDENTIALS_SECRET']
            return load_json_secret(secret_name)
    
    except Exception as e:
        logger.error(f"Error retrieving credentials for {service_name}: {str(e)}")
        raise


def initialize_settings():
    """
    Initializes application settings and validates required configuration.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    logger.info("Initializing application settings")
    
    # Validate required environment variables
    required_env_vars = [
        'WEEKLY_SPENDING_SHEET_ID',
        'MASTER_BUDGET_SHEET_ID'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not APP_SETTINGS.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    # Validate required secrets are accessible in non-development environments
    if ENV != 'development':
        required_secrets = [
            API_SETTINGS['CAPITAL_ONE']['CLIENT_ID_SECRET'],
            API_SETTINGS['GOOGLE_SHEETS']['CREDENTIALS_SECRET'],
            API_SETTINGS['GEMINI']['API_KEY_SECRET'],
            API_SETTINGS['GMAIL']['CREDENTIALS_SECRET']
        ]
        
        for secret_name in required_secrets:
            try:
                # Just check if we can access the secret
                get_secret(secret_name)
            except Exception as e:
                logger.error(f"Unable to access required secret {secret_name}: {str(e)}")
                return False
    
    logger.info("Application settings initialized successfully")
    return True