"""
__init__.py - Initializes the fixtures package for the Budget Management Application test suite.

This module exports all test fixture data, factory functions, and utility methods from the various
fixture modules, providing a centralized access point for test data across unit, integration, and
end-to-end tests.
"""

# Import all fixtures from submodules
from .transactions import *
from .categories import *
from .budget import *
from .api_responses import *

# Define __all__ to explicitly specify what is exported from this package
__all__ = [
    # From transactions.py
    "VALID_TRANSACTIONS", "INVALID_TRANSACTIONS", "LARGE_VOLUME_TRANSACTIONS",
    "create_test_transaction", "create_test_transactions", "create_categorized_transactions",
    "create_transactions_with_amounts", "get_transaction_fixture_by_name", "TransactionFactory",
    
    # From categories.py
    "MASTER_BUDGET_CATEGORIES", "EMPTY_BUDGET_CATEGORIES", "DEFAULT_CATEGORIES",
    "create_test_category", "create_test_categories", "create_categories_with_amounts",
    "get_category_fixture_by_name", "get_category_mapping", "CategoryFactory",
    
    # From budget.py
    "MASTER_BUDGET", "WEEKLY_SPENDING", "EXPECTED_BUDGET_ANALYSIS",
    "create_test_budget", "create_budget_with_variance", "create_analyzed_budget",
    "create_budget_from_fixtures", "get_expected_budget_analysis",
    "create_budget_with_specific_categories", "create_budget_with_specific_spending",
    "BudgetFactory",
    
    # From api_responses.py
    "CAPITAL_ONE_TRANSACTIONS", "CAPITAL_ONE_ACCOUNTS", "CAPITAL_ONE_TRANSFER",
    "GOOGLE_SHEETS_BUDGET_DATA", "GOOGLE_SHEETS_TRANSACTION_DATA",
    "GEMINI_CATEGORIZATION", "GEMINI_INSIGHTS", "GMAIL_EMAIL_CONFIRMATION",
    "get_capital_one_response", "get_google_sheets_response", "get_gemini_response",
    "get_gmail_response", "get_api_response", "get_error_response",
    "create_custom_response", "MockAPIResponseFactory"
]