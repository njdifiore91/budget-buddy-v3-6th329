import os
import uuid
from decimal import Decimal
from typing import Dict, List, Any, Tuple

import pytest
from mock import MagicMock

from ..mocks.capital_one_client import MockCapitalOneClient
from ..mocks.google_sheets_client import MockGoogleSheetsClient
from ..mocks.gemini_client import MockGeminiClient
from ..mocks.gmail_client import MockGmailClient
from ..utils.fixture_loader import load_fixture
from ...backend.main import run_budget_management_process
from ...backend.utils.error_handlers import APIError, ValidationError, AuthenticationError
from ...backend.services.error_handling_service import with_error_handling, with_circuit_breaker, reset_circuit

TEST_CORRELATION_ID = "test-error-handling-e2e-001"


def setup_test_environment() -> Tuple[MockCapitalOneClient, MockGoogleSheetsClient, MockGeminiClient, MockGmailClient, Dict[str, Any]]:
    """
    Set up the test environment with mock clients and test data for error handling tests
    """
    # Create mock clients
    capital_one_client = MockCapitalOneClient()
    sheets_client = MockGoogleSheetsClient()
    gemini_client = MockGeminiClient()
    gmail_client = MockGmailClient()

    # Load test fixtures
    transactions = load_fixture("transactions/valid_transactions.json")
    budget_data = load_fixture("budget/valid_budget.json")
    api_responses = load_fixture("api_responses/capital_one/transactions.json")

    # Configure mock clients with test data
    capital_one_client.set_transactions(transactions)
    sheets_client.set_sheet_data("Weekly Spending", [["Location", "Amount", "Timestamp", "Category"]])  # Header row
    sheets_client.set_sheet_data("Master Budget", [["Category", "Weekly Amount"]])  # Header row

    # Reset any circuit breaker states from previous tests
    reset_circuit('capital_one')
    reset_circuit('google_sheets')
    reset_circuit('gemini')
    reset_circuit('gmail')

    return capital_one_client, sheets_client, gemini_client, gmail_client, {
        "transactions": transactions,
        "budget_data": budget_data,
        "api_responses": api_responses
    }


def teardown_test_environment(capital_one_client: MockCapitalOneClient, sheets_client: MockGoogleSheetsClient,
                             gemini_client: MockGeminiClient, gmail_client: MockGmailClient) -> None:
    """
    Clean up the test environment after test execution
    """
    # Reset all mock clients to their initial state
    capital_one_client.reset()
    sheets_client.reset()
    gemini_client.reset()
    gmail_client.reset()

    # Reset any circuit breaker states
    reset_circuit('capital_one')
    reset_circuit('google_sheets')
    reset_circuit('gemini')
    reset_circuit('gmail')

    # Clear any test data or state
    pass


def assert_graceful_degradation(result: Dict[str, Any], expected_error_type: str, expected_component: str) -> None:
    """
    Verify that the system gracefully degrades when encountering errors
    """
    # Assert that result contains status key with value 'partial_success' or 'error'
    assert result.get('status') in ['partial_success', 'error']

    # Assert that result contains errors list
    assert 'errors' in result

    # Assert that at least one error in errors list has type matching expected_error_type
    assert any(error.get('error_type') == expected_error_type for error in result['errors'])

    # Assert that at least one error in errors list has component matching expected_component
    assert any(error.get('component') == expected_component for error in result['errors'])

    # Assert that result contains completed_steps list showing which steps completed successfully
    assert 'completed_steps' in result


def test_authentication_failure_capital_one():
    """Test error handling when Capital One authentication fails"""
    capital_one_client, sheets_client, gemini_client, gmail_client, test_config = setup_test_environment()
    capital_one_client.set_should_fail_authentication(True)
    result = run_budget_management_process(TEST_CORRELATION_ID)
    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)
    assert result['retriever']['status'] == 'error'
    assert "Authentication failed" in result['retriever']['error']


def test_authentication_failure_google_sheets():
    """Test error handling when Google Sheets authentication fails"""
    capital_one_client, sheets_client, gemini_client, gmail_client, test_config = setup_test_environment()
    sheets_client.set_authentication_failure(True)
    result = run_budget_management_process(TEST_CORRELATION_ID)
    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)
    assert result['categorizer']['status'] == 'error'
    assert "Authentication failed" in result['categorizer']['error']


def test_authentication_failure_gemini():
    """Test error handling when Gemini API authentication fails"""
    capital_one_client, sheets_client, gemini_client, gmail_client, test_config = setup_test_environment()
    gemini_client.set_failure_mode(True, 'authentication')
    result = run_budget_management_process(TEST_CORRELATION_ID)
    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)
    assert result['insight']['status'] == 'error'
    assert "Authentication required" in result['insight']['error']


def test_transaction_retrieval_failure():
    """Test error handling when transaction retrieval from Capital One fails"""
    capital_one_client, sheets_client, gemini_client, gmail_client, test_config = setup_test_environment()
    capital_one_client.set_should_fail_transactions(True)
    result = run_budget_management_process(TEST_CORRELATION_ID)
    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)
    assert result['retriever']['status'] == 'error'
    assert "Transaction retrieval failed" in result['retriever']['error']


def test_transaction_categorization_failure():
    """Test error handling when transaction categorization with Gemini AI fails"""
    capital_one_client, sheets_client, gemini_client, gmail_client, test_config = setup_test_environment()
    gemini_client.set_failure_mode(True, 'categorization')
    result = run_budget_management_process(TEST_CORRELATION_ID)
    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)
    assert result['categorizer']['status'] == 'error'
    assert "Simulated categorization failure" in result['categorizer']['error']


def test_insight_generation_failure():
    """Test error handling when insight generation with Gemini AI fails"""
    capital_one_client, sheets_client, gemini_client, gmail_client, test_config = setup_test_environment()
    gemini_client.set_failure_mode(True, 'insights')
    result = run_budget_management_process(TEST_CORRELATION_ID)
    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)
    assert result['insight']['status'] == 'error'
    assert "Simulated insights generation failure" in result['insight']['error']


def test_email_sending_failure():
    """Test error handling when email sending via Gmail fails"""
    capital_one_client, sheets_client, gemini_client, gmail_client, test_config = setup_test_environment()
    gmail_client.set_should_fail_sending(True)
    result = run_budget_management_process(TEST_CORRELATION_ID)
    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)
    assert result['report']['status'] == 'error'
    assert "Failed to send email" in result['report']['error']


def test_savings_transfer_failure():
    """Test error handling when savings transfer via Capital One fails"""
    capital_one_client, sheets_client, gemini_client, gmail_client, test_config = setup_test_environment()
    capital_one_client.set_should_fail_transfers(True)
    result = run_budget_management_process(TEST_CORRELATION_ID)
    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)
    assert result['savings']['transfer_result']['status'] == 'error'
    assert "transfer_error" in result['savings']['transfer_result']['error_message']


def test_retry_mechanism_authentication():
    """Test retry mechanism for authentication failures"""
    capital_one_client, sheets_client, gemini_client, gmail_client, test_config = setup_test_environment()
    capital_one_client.set_should_fail_authentication(True)
    result = run_budget_management_process(TEST_CORRELATION_ID)
    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)
    assert capital_one_client.retry_count > 0
    assert result['retriever']['status'] == 'error'


def test_retry_mechanism_api_calls():
    """Test retry mechanism for transient API failures"""
    capital_one_client, sheets_client, gemini_client, gmail_client, test_config = setup_test_environment()
    capital_one_client.set_should_fail_transactions(True)
    result = run_budget_management_process(TEST_CORRELATION_ID)
    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)
    assert capital_one_client.retry_count > 0
    assert result['retriever']['status'] == 'error'


def test_circuit_breaker_pattern():
    """Test circuit breaker pattern for preventing repeated calls to failing services"""
    capital_one_client, sheets_client, gemini_client, gmail_client, test_config = setup_test_environment()
    capital_one_client.set_should_fail_authentication(True)
    result = run_budget_management_process(TEST_CORRELATION_ID)
    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)
    assert result['retriever']['status'] == 'error'
    assert "Circuit breaker for capital_one is open" in result['retriever']['error']


def test_fallback_mechanism():
    """Test fallback mechanism when primary operations fail"""
    capital_one_client, sheets_client, gemini_client, gmail_client, test_config = setup_test_environment()
    gmail_client.set_should_fail_sending(True)
    result = run_budget_management_process(TEST_CORRELATION_ID)
    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)
    assert result['report']['status'] == 'error'
    assert "Weekly Budget Update" in result['report']['message']


def test_graceful_degradation_critical_component():
    """Test graceful degradation when a critical component fails"""
    capital_one_client, sheets_client, gemini_client, gmail_client, test_config = setup_test_environment()
    capital_one_client.set_should_fail_authentication(True)
    result = run_budget_management_process(TEST_CORRELATION_ID)
    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)
    assert result['retriever']['status'] == 'error'


def test_graceful_degradation_non_critical_component():
    """Test graceful degradation when a non-critical component fails"""
    capital_one_client, sheets_client, gemini_client, gmail_client, test_config = setup_test_environment()
    gmail_client.set_should_fail_sending(True)
    result = run_budget_management_process(TEST_CORRELATION_ID)
    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)
    assert result['report']['status'] == 'error'


def test_error_logging_and_reporting():
    """Test error logging and reporting mechanisms"""
    capital_one_client, sheets_client, gemini_client, gmail_client, test_config = setup_test_environment()
    capital_one_client.set_should_fail_authentication(True)
    result = run_budget_management_process(TEST_CORRELATION_ID)
    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)
    assert result['retriever']['status'] == 'error'
    assert 'stack_trace' in result['retriever']


def test_multiple_concurrent_failures():
    """Test handling of multiple concurrent failures across different components"""
    capital_one_client, sheets_client, gemini_client, gmail_client, test_config = setup_test_environment()
    capital_one_client.set_should_fail_authentication(True)
    gmail_client.set_should_fail_sending(True)
    result = run_budget_management_process(TEST_CORRELATION_ID)
    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)
    assert result['retriever']['status'] == 'error'
    assert result['report']['status'] == 'success'