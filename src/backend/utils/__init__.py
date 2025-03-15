"""
__init__.py - Package initialization for utility modules in the Budget Management Application

This module exposes commonly used utility functions and classes from various utility modules
to simplify imports throughout the application. Functions are imported from date_utils,
validation, formatters, and error_handlers modules.
"""

# Import all utilities from their respective modules
from .date_utils import *
from .validation import *
from .formatters import *
from .error_handlers import *

# Define what gets imported with "from backend.utils import *"
__all__ = [
    # Date and time utilities (from date_utils)
    'get_transaction_date_range',
    'parse_capital_one_date',
    'format_date_for_sheets',
    'parse_sheets_date',
    'get_current_week_start',
    'get_current_week_end',
    'is_date_in_current_week',
    'format_iso_date',
    'format_iso_datetime',
    'convert_to_est',
    'EST_TIMEZONE',
    'UTC_TIMEZONE',
    
    # Validation utilities (from validation)
    'is_valid_transaction',
    'validate_transactions',
    'is_valid_category',
    'validate_categorization_results',
    'is_categorization_successful',
    'is_valid_amount',
    'parse_amount',
    'is_valid_email',
    'validate_email_list',
    'is_valid_transfer_amount',
    'validate_budget_data',
    'validate_api_response',
    'is_duplicate_transaction',
    'filter_duplicates',
    'validate_calculation_results',
    
    # Formatting utilities (from formatters)
    'format_currency',
    'format_percentage',
    'format_variance',
    'format_budget_status',
    'format_email_subject',
    'format_category_for_sheets',
    'format_transaction_for_sheets',
    'format_transactions_for_sheets',
    'format_budget_analysis_for_ai',
    'truncate_text',
    'clean_html',
    'format_list_for_html',
    'format_dict_for_sheets',
    
    # Error handling utilities (from error_handlers)
    'retry_with_backoff',
    'is_retriable_error',
    'handle_api_error',
    'handle_validation_error',
    'handle_auth_error',
    'format_exception_for_log',
    'safe_execute',
    
    # Custom exceptions (from error_handlers)
    'APIError',
    'ValidationError',
    'AuthenticationError'
]