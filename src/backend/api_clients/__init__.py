"""
API clients module for the Budget Management Application.

This module provides client classes for interacting with external services
used by the application, including Capital One API, Google Sheets API,
Gmail API, and Gemini AI API.

Each client handles authentication, request formatting, error handling, and
response parsing for its respective API.
"""

# Capital One API client
from .capital_one_client import (
    CapitalOneClient,
    format_date_for_api,
    get_date_range
)

# Google Sheets API client
from .google_sheets_client import (
    GoogleSheetsClient,
    build_sheets_service,
    parse_sheet_range,
    format_sheet_range
)

# Gmail API client
from .gmail_client import (
    GmailClient,
    create_message,
    add_attachment,
    validate_email_addresses
)

# Gemini AI API client
from .gemini_client import (
    GeminiClient,
    load_prompt_template
)

# Export all classes and functions
__all__ = [
    # Client classes
    'CapitalOneClient',
    'GoogleSheetsClient',
    'GmailClient',
    'GeminiClient',
    
    # Utility functions
    'format_date_for_api',
    'get_date_range',
    'build_sheets_service',
    'parse_sheet_range',
    'format_sheet_range',
    'create_message',
    'add_attachment',
    'validate_email_addresses',
    'load_prompt_template'
]