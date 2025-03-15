"""
JSON fixtures module for the Budget Management Application.

This module provides standardized access to JSON test data including transactions,
budget information, API responses, and expected results. It defines directory paths
and helper functions to access fixture files in a consistent manner.
"""

import os
from pathlib import Path

# Directory paths for JSON fixtures
JSON_DIR = os.path.dirname(os.path.abspath(__file__))
TRANSACTIONS_DIR = os.path.join(JSON_DIR, 'transactions')
BUDGET_DIR = os.path.join(JSON_DIR, 'budget')
API_RESPONSES_DIR = os.path.join(JSON_DIR, 'api_responses')
EXPECTED_DIR = os.path.join(JSON_DIR, 'expected')

# API-specific response directories
CAPITAL_ONE_RESPONSES_DIR = os.path.join(API_RESPONSES_DIR, 'capital_one')
GOOGLE_SHEETS_RESPONSES_DIR = os.path.join(API_RESPONSES_DIR, 'google_sheets')
GEMINI_RESPONSES_DIR = os.path.join(API_RESPONSES_DIR, 'gemini')
GMAIL_RESPONSES_DIR = os.path.join(API_RESPONSES_DIR, 'gmail')


def get_transaction_fixture_path(fixture_name):
    """
    Get the full path to a transaction fixture file.

    Args:
        fixture_name (str): The name of the transaction fixture file

    Returns:
        str: Full path to the transaction fixture file
    """
    return os.path.join(TRANSACTIONS_DIR, fixture_name)


def get_budget_fixture_path(fixture_name):
    """
    Get the full path to a budget fixture file.

    Args:
        fixture_name (str): The name of the budget fixture file

    Returns:
        str: Full path to the budget fixture file
    """
    return os.path.join(BUDGET_DIR, fixture_name)


def get_api_response_fixture_path(service_name, fixture_name):
    """
    Get the full path to an API response fixture file.

    Args:
        service_name (str): The name of the service (capital_one, google_sheets, gemini, gmail)
        fixture_name (str): The name of the API response fixture file

    Returns:
        str: Full path to the API response fixture file
    """
    service_dir_map = {
        'capital_one': CAPITAL_ONE_RESPONSES_DIR,
        'google_sheets': GOOGLE_SHEETS_RESPONSES_DIR,
        'gemini': GEMINI_RESPONSES_DIR,
        'gmail': GMAIL_RESPONSES_DIR
    }
    
    service_dir = service_dir_map.get(service_name.lower(), API_RESPONSES_DIR)
    return os.path.join(service_dir, fixture_name)


def get_expected_fixture_path(fixture_name):
    """
    Get the full path to an expected result fixture file.

    Args:
        fixture_name (str): The name of the expected result fixture file

    Returns:
        str: Full path to the expected result fixture file
    """
    return os.path.join(EXPECTED_DIR, fixture_name)