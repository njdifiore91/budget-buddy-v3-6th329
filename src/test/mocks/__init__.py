"""
__init__.py - Initialization file for the test mocks package that exports all mock client
implementations for testing the Budget Management Application.

This file makes all mock clients available through a single import, simplifying test setup
and improving code organization. It provides centralized access to all mock implementations
of external services used by the Budget Management Application.
"""

# Capital One API mock client and utilities
from .capital_one_client import (
    MockCapitalOneClient,
    format_date_for_api,
    get_date_range,
)

# Google Sheets API mock client
from .google_sheets_client import MockGoogleSheetsClient

# Gemini AI API mock client and utilities
from .gemini_client import (
    MockGeminiClient,
    MockGeminiClientFactory,
    parse_categorization_text,
)

# Gmail API mock client and utilities
from .gmail_client import (
    MockGmailClient,
    validate_email_addresses,
    create_message,
    add_attachment,
)

# Cloud Scheduler mock client and utilities
from .cloud_scheduler import (
    MockCloudScheduler,
    MockCloudSchedulerJob,
    parse_cron_expression,
    calculate_next_execution,
)

# Secret Manager mock client and utilities
from .secret_manager import (
    MockSecretManagerServiceClient,
    MockSecretManagerClient,
    MockSecretVersion,
    create_secret_version_response,
)

# Export all mock classes and utilities
__all__ = [
    # Capital One mocks
    'MockCapitalOneClient',
    'format_date_for_api',
    'get_date_range',
    
    # Google Sheets mocks
    'MockGoogleSheetsClient',
    
    # Gemini AI mocks
    'MockGeminiClient',
    'MockGeminiClientFactory',
    'parse_categorization_text',
    
    # Gmail mocks
    'MockGmailClient',
    'validate_email_addresses',
    'create_message',
    'add_attachment',
    
    # Cloud Scheduler mocks
    'MockCloudScheduler',
    'MockCloudSchedulerJob',
    'parse_cron_expression',
    'calculate_next_execution',
    
    # Secret Manager mocks
    'MockSecretManagerServiceClient',
    'MockSecretManagerClient',
    'MockSecretVersion',
    'create_secret_version_response',
]