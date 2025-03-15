"""
Initialization module for the test utilities package that exposes key testing functions, classes, and constants from the utility modules. 
This file makes common testing utilities easily accessible to test files throughout the Budget Management Application test suite.
"""

import logging  # standard library
from typing import List  # standard library

from .fixture_loader import (  # Internal import
    load_fixture, load_transaction_fixture, load_budget_fixture, load_category_fixture,
    load_api_response_fixture, load_expected_result_fixture, convert_to_transaction_objects,
    convert_to_category_objects, FixtureLoader, GenericFixtureLoader,
    FIXTURE_BASE_DIR, JSON_FIXTURE_DIR, TRANSACTION_FIXTURE_DIR, BUDGET_FIXTURE_DIR,
    API_RESPONSE_FIXTURE_DIR, EXPECTED_FIXTURE_DIR, TEST_DATA_DIR
)
from .assertion_helpers import (  # Internal import
    assert_decimal_equal, assert_datetime_equal, assert_transaction_equal,
    assert_transactions_equal, assert_budget_equal, assert_category_equal,
    assert_categories_equal, assert_dict_subset, assert_api_response_valid,
    assert_api_error_response, assert_matches_fixture, assert_contains_transaction,
    assert_budget_variance_correct, assert_transfer_amount_valid,
    assert_email_content_valid, assert_categorization_correct,
    BudgetAssertions, TransactionAssertions, APIAssertions,
    DEFAULT_DECIMAL_PRECISION, DEFAULT_DATE_TOLERANCE
)
from .mock_factory import (  # Internal import
    MockFactory, GenericMockFactory, create_mock_capital_one_client,
    create_mock_google_sheets_client, create_mock_gemini_client,
    create_mock_gmail_client, create_mock
)
from .test_helpers import (  # Internal import
    load_test_fixture, create_test_transaction, create_test_transactions,
    create_test_category, create_test_categories, create_test_budget,
    setup_test_environment, teardown_test_environment, with_test_environment,
    create_temp_file, set_environment_variables, mock_api_response,
    compare_decimal_values, generate_test_data, TestEnvironment, TestDataGenerator
)

# Configure logging for test utilities
logger = logging.getLogger(__name__)


def configure_logging():
    """Configure logging for test utilities"""
    # Configure logging format for test utilities
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_format)

    # Set logging level to INFO by default
    logger.setLevel(logging.INFO)

    # Add console handler for logging output
    console_handler = logging.StreamHandler()
    logger.addHandler(console_handler)


__all__ = [  # List of all exported names
    # Fixture loading utilities
    'load_fixture', 'load_transaction_fixture', 'load_budget_fixture', 'load_category_fixture',
    'load_api_response_fixture', 'load_expected_result_fixture', 'convert_to_transaction_objects',
    'convert_to_category_objects', 'FixtureLoader', 'GenericFixtureLoader',

    # Fixture directory constants
    'FIXTURE_BASE_DIR', 'JSON_FIXTURE_DIR', 'TRANSACTION_FIXTURE_DIR', 'BUDGET_FIXTURE_DIR',
    'API_RESPONSE_FIXTURE_DIR', 'EXPECTED_FIXTURE_DIR', 'TEST_DATA_DIR',

    # Assertion helpers
    'assert_decimal_equal', 'assert_datetime_equal', 'assert_transaction_equal',
    'assert_transactions_equal', 'assert_budget_equal', 'assert_category_equal',
    'assert_categories_equal', 'assert_dict_subset', 'assert_api_response_valid',
    'assert_api_error_response', 'assert_matches_fixture', 'assert_contains_transaction',
    'assert_budget_variance_correct', 'assert_transfer_amount_valid',
    'assert_email_content_valid', 'assert_categorization_correct',

    # Assertion classes
    'BudgetAssertions', 'TransactionAssertions', 'APIAssertions',

    # Constants
    'DEFAULT_DECIMAL_PRECISION', 'DEFAULT_DATE_TOLERANCE',

    # Mock factory utilities
    'MockFactory', 'GenericMockFactory', 'create_mock_capital_one_client',
    'create_mock_google_sheets_client', 'create_mock_gemini_client',
    'create_mock_gmail_client', 'create_mock',

    # Test helpers
    'load_test_fixture', 'create_test_transaction', 'create_test_transactions',
    'create_test_category', 'create_test_categories', 'create_test_budget',
    'setup_test_environment', 'teardown_test_environment', 'with_test_environment',
    'create_temp_file', 'set_environment_variables', 'mock_api_response',
    'compare_decimal_values', 'generate_test_data', 'TestEnvironment', 'TestDataGenerator'
]