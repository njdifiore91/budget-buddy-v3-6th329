"""
Initializes the test fixtures package for the Budget Management Application, exposing
commonly used test data and utility functions. This module aggregates and re-exports
fixtures from the transactions, categories, budget, and API responses modules to provide
a centralized access point for test data.
"""

import os  # standard library
from typing import Dict, List, Any, Optional  # standard library

# Import transaction fixtures
from .transactions import (
    load_transaction_data,
    create_test_transaction,
    create_test_transactions,
    create_categorized_transactions,
    create_uncategorized_transactions,
    get_transaction_by_location,
    SAMPLE_TRANSACTIONS,
    CATEGORIZED_TRANSACTIONS,
)

# Import category fixtures
from .categories import (
    load_category_data,
    create_test_category,
    create_test_categories,
    get_category_by_name,
    create_custom_categories,
    create_categories_with_surplus,
    create_categories_with_deficit,
    SAMPLE_CATEGORIES,
)

# Import budget fixtures
from .budget import (
    load_budget_data,
    create_test_budget,
    create_analyzed_budget,
    create_budget_with_surplus,
    create_budget_with_deficit,
    create_budget_with_zero_balance,
    create_budget_from_test_sheet_data,
    get_expected_analysis_results,
    create_budget_with_transactions,
    SAMPLE_BUDGET,
    ANALYZED_BUDGET,
)

# Import API response fixtures
from .api_responses import (
    load_json_fixture,
    MockResponse,
    create_mock_api_response,
    create_mock_error_response,
    load_capital_one_transactions_response,
    load_capital_one_accounts_response,
    load_capital_one_transfer_response,
    load_capital_one_error_response,
    load_google_sheets_budget_response,
    load_google_sheets_transactions_response,
    load_google_sheets_error_response,
    load_gemini_categorization_response,
    load_gemini_insights_response,
    load_gemini_error_response,
    load_gmail_confirmation_response,
    load_gmail_error_response,
    CAPITAL_ONE_TRANSACTIONS_RESPONSE,
    CAPITAL_ONE_ACCOUNTS_RESPONSE,
    CAPITAL_ONE_TRANSFER_RESPONSE,
    GOOGLE_SHEETS_BUDGET_RESPONSE,
    GOOGLE_SHEETS_TRANSACTIONS_RESPONSE,
    GEMINI_CATEGORIZATION_RESPONSE,
    GEMINI_INSIGHTS_RESPONSE,
    GMAIL_CONFIRMATION_RESPONSE,
)

# Define common paths
FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(FIXTURES_DIR, 'data')

# Define exports
__all__ = [
    # Transaction fixtures
    "load_transaction_data",
    "create_test_transaction",
    "create_test_transactions",
    "create_categorized_transactions",
    "create_uncategorized_transactions",
    "get_transaction_by_location",
    "SAMPLE_TRANSACTIONS",
    "CATEGORIZED_TRANSACTIONS",
    
    # Category fixtures
    "load_category_data",
    "create_test_category",
    "create_test_categories",
    "get_category_by_name",
    "create_custom_categories",
    "create_categories_with_surplus",
    "create_categories_with_deficit",
    "SAMPLE_CATEGORIES",
    
    # Budget fixtures
    "load_budget_data",
    "create_test_budget",
    "create_analyzed_budget",
    "create_budget_with_surplus",
    "create_budget_with_deficit",
    "create_budget_with_zero_balance",
    "create_budget_from_test_sheet_data",
    "get_expected_analysis_results",
    "create_budget_with_transactions",
    "SAMPLE_BUDGET",
    "ANALYZED_BUDGET",
    
    # API response fixtures
    "load_json_fixture",
    "MockResponse",
    "create_mock_api_response",
    "create_mock_error_response",
    "load_capital_one_transactions_response",
    "load_capital_one_accounts_response",
    "load_capital_one_transfer_response",
    "load_capital_one_error_response",
    "load_google_sheets_budget_response",
    "load_google_sheets_transactions_response",
    "load_google_sheets_error_response",
    "load_gemini_categorization_response",
    "load_gemini_insights_response",
    "load_gemini_error_response",
    "load_gmail_confirmation_response",
    "load_gmail_error_response",
    "CAPITAL_ONE_TRANSACTIONS_RESPONSE",
    "CAPITAL_ONE_ACCOUNTS_RESPONSE",
    "CAPITAL_ONE_TRANSFER_RESPONSE",
    "GOOGLE_SHEETS_BUDGET_RESPONSE",
    "GOOGLE_SHEETS_TRANSACTIONS_RESPONSE",
    "GEMINI_CATEGORIZATION_RESPONSE",
    "GEMINI_INSIGHTS_RESPONSE",
    "GMAIL_CONFIRMATION_RESPONSE",
]