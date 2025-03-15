import os  # standard library
import pytest  # pytest 7.4.0+

from .test_weekly_process import *  # Import all test functions for weekly budget process
from .test_error_handling import *  # Import all test functions for error handling scenarios
from .test_performance import *  # Import all test functions and classes for performance testing
from .test_security import *  # Import all test functions for security testing
from ..utils.fixture_loader import load_fixture  # Import fixture loading utility for test data
from ..mocks.capital_one_client import MockCapitalOneClient  # Import mock implementation of Capital One API client
from ..mocks.google_sheets_client import MockGoogleSheetsClient  # Import mock implementation of Google Sheets API client
from ..mocks.gemini_client import MockGeminiClient  # Import mock implementation of Gemini AI API client
from ..mocks.gmail_client import MockGmailClient  # Import mock implementation of Gmail API client

__version__ = "1.0.0"
E2E_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
__all__ = [
    # Weekly process tests
    'test_successful_weekly_process', 'test_weekly_process_with_budget_surplus',
    'test_weekly_process_with_budget_deficit', 'test_weekly_process_with_transaction_retrieval_failure',
    'test_weekly_process_with_categorization_failure', 'test_weekly_process_with_email_failure',
    'test_weekly_process_with_transfer_failure', 'test_weekly_process_with_large_transaction_volume',
    'test_weekly_process_component_integration', 'test_weekly_process_data_consistency',
    # Error handling tests
    'test_authentication_failure_capital_one', 'test_authentication_failure_google_sheets',
    'test_authentication_failure_gemini', 'test_transaction_retrieval_failure',
    'test_transaction_categorization_failure', 'test_insight_generation_failure',
    'test_email_sending_failure', 'test_savings_transfer_failure',
    'test_retry_mechanism_authentication', 'test_retry_mechanism_api_calls',
    'test_circuit_breaker_pattern', 'test_fallback_mechanism',
    'test_graceful_degradation_critical_component', 'test_graceful_degradation_non_critical_component',
    'test_error_logging_and_reporting', 'test_multiple_concurrent_failures',
    # Performance tests
    'TestEndToEndPerformance', 'TestComponentPerformanceIntegration',
    'setup_mock_clients_with_volume', 'run_end_to_end_workflow', 'measure_workflow_performance',
    # Security tests
    'test_end_to_end_authentication_security', 'test_end_to_end_data_protection',
    'test_end_to_end_secure_transfer', 'test_end_to_end_authentication_failure_handling',
    'test_end_to_end_api_error_security', 'test_end_to_end_credential_storage',
    'test_end_to_end_email_content_security', 'test_end_to_end_log_security',
    'test_end_to_end_error_message_security',
    # Common utilities
    'setup_test_environment', 'teardown_test_environment',
    'MockCapitalOneClient', 'MockGoogleSheetsClient', 'MockGeminiClient', 'MockGmailClient',
    'load_fixture'
]

def setup_e2e_test_environment():
    """Set up the test environment for end-to-end tests with mock clients and test data"""
    # Create instances of all mock clients (Capital One, Google Sheets, Gemini, Gmail)
    capital_one_client = MockCapitalOneClient()
    sheets_client = MockGoogleSheetsClient()
    gemini_client = MockGeminiClient()
    gmail_client = MockGmailClient()

    # Load test fixtures for transactions, budget data, and API responses
    transactions = load_fixture("transactions/valid_transactions.json")
    budget_data = load_fixture("budget/valid_budget.json")
    categorization_response = load_fixture("api_responses/gemini/categorization.json")
    insight_response = load_fixture("api_responses/gemini/insights.json")

    # Configure mock clients with test data
    capital_one_client.set_transactions(transactions)
    sheets_client.set_sheet_data("Weekly Spending", [["Location", "Amount", "Timestamp", "Category"]])  # Header row
    sheets_client.set_sheet_data("Master Budget", [["Category", "Weekly Amount"]])  # Header row
    sheets_client.append_rows("Weekly Spending", [t.values() for t in transactions])
    sheets_client.set_sheet_data("Master Budget", [["Groceries", "150"], ["Transportation", "100"], ["Dining Out", "50"]])
    gemini_client.set_response("categorization", categorization_response)
    gemini_client.set_response("insights", insight_response)

    return {
        "capital_one_client": capital_one_client,
        "sheets_client": sheets_client,
        "gemini_client": gemini_client,
        "gmail_client": gmail_client,
        "transactions": transactions,
        "budget_data": budget_data,
        "categorization_response": categorization_response,
        "insight_response": insight_response
    }

def teardown_e2e_test_environment(test_env):
    """Clean up the test environment after end-to-end test execution"""
    # Extract mock clients from test_env dictionary
    capital_one_client = test_env["capital_one_client"]
    sheets_client = test_env["sheets_client"]
    gemini_client = test_env["gemini_client"]
    gmail_client = test_env["gmail_client"]

    # Reset all mock clients to their initial state
    capital_one_client.reset()
    sheets_client.reset()
    gemini_client.reset()
    gmail_client.reset()