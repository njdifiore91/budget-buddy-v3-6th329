"""
Initialization file for the integration test package that exposes key testing components, fixtures, and utilities specifically for integration testing of the Budget Management Application.
This file makes integration test utilities and fixtures easily accessible to all integration test modules.
"""

import os  # standard library: Provides functions for interacting with the operating system
import pytest  # pytest 7.4.0+: The pytest framework for writing and running tests

# Internal imports: Import specific functions and classes from other modules within the project
from src.test.utils.test_helpers import with_test_environment  # Import context manager for setting up and tearing down test environment
from src.test.utils.test_helpers import create_test_transactions  # Import function to create test transaction data for testing
from src.test.utils.test_helpers import load_test_fixture  # Import function to load test fixtures for expected data
from src.test.mocks.capital_one_client import MockCapitalOneClient  # Import mock implementation of Capital One API client
from src.test.mocks.google_sheets_client import MockGoogleSheetsClient  # Import mock implementation of Google Sheets API client
from src.test.mocks.gemini_client import MockGeminiClient  # Import mock implementation of Gemini AI client
from src.test.mocks.gmail_client import MockGmailClient  # Import mock implementation of Gmail API client
from src.test.utils.assertion_helpers import TransactionAssertions  # Import specialized assertions for transaction testing
from src.test.utils.assertion_helpers import BudgetAssertions  # Import specialized assertions for budget testing
from src.test.utils.assertion_helpers import assert_transactions_equal  # Import function to assert equality of transaction lists
from src.test.utils.assertion_helpers import assert_api_response_valid  # Import function to assert API response validity
from src.test.utils.assertion_helpers import assert_budget_variance_correct  # Import function to assert budget variance calculations are correct
from src.test.utils.assertion_helpers import assert_transfer_amount_valid  # Import function to assert transfer amount calculation is valid
from src.test.utils.assertion_helpers import assert_email_content_valid  # Import function to assert email content contains expected information
from src.test.utils.fixture_loader import load_fixture  # Import function to load test fixtures from JSON files
from src.test.utils.fixture_loader import load_transaction_fixture  # Import function to load transaction fixtures from JSON files
from src.test.utils.fixture_loader import load_budget_fixture  # Import function to load budget fixtures from JSON files
from src.test.utils.fixture_loader import load_api_response_fixture  # Import function to load API response fixtures from JSON files
from src.test.utils.mock_factory import MockFactory  # Import factory for creating and managing mock objects

__version__ = "0.1.0"  # Version of the integration test package
INTEGRATION_TEST_DIR = os.path.dirname(os.path.abspath(__file__))  # Base directory path for the integration test package

__all__ = [  # Define the public API of the integration test package
    # Test utilities
    'with_test_environment', 'create_test_transactions', 'load_test_fixture',
    # Mock clients
    'MockCapitalOneClient', 'MockGoogleSheetsClient', 'MockGeminiClient', 'MockGmailClient',
    # Assertion helpers
    'TransactionAssertions', 'BudgetAssertions', 'assert_transactions_equal',
    'assert_api_response_valid', 'assert_budget_variance_correct', 'assert_transfer_amount_valid',
    'assert_email_content_valid',
    # Fixture loaders
    'load_fixture', 'load_transaction_fixture', 'load_budget_fixture', 'load_api_response_fixture',
    # Mock factory
    'MockFactory'
]