import os
from decimal import Decimal
from typing import Dict, List, Any, Tuple
import uuid
import pytest

from ..mocks.capital_one_client import MockCapitalOneClient
from ..mocks.google_sheets_client import MockGoogleSheetsClient
from ..mocks.gemini_client import MockGeminiClient
from ..mocks.gmail_client import MockGmailClient
from ..utils.fixture_loader import load_fixture
from ...backend.main import run_budget_management_process
from ...backend.components.transaction_retriever import TransactionRetriever
from ...backend.components.transaction_categorizer import TransactionCategorizer
from ...backend.components.budget_analyzer import BudgetAnalyzer
from ...backend.components.insight_generator import InsightGenerator
from ...backend.components.report_distributor import ReportDistributor
from ...backend.components.savings_automator import SavingsAutomator

TEST_CORRELATION_ID = "test-weekly-process-e2e-001"

def setup_test_environment() -> Tuple[MockCapitalOneClient, MockGoogleSheetsClient, MockGeminiClient, MockGmailClient]:
    """Set up the test environment with mock clients and test data"""
    # Create mock clients
    capital_one_client = MockCapitalOneClient()
    sheets_client = MockGoogleSheetsClient()
    gemini_client = MockGeminiClient()
    gmail_client = MockGmailClient()

    # Load test fixtures
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

    return capital_one_client, sheets_client, gemini_client, gmail_client

def teardown_test_environment(capital_one_client: MockCapitalOneClient, sheets_client: MockGoogleSheetsClient, gemini_client: MockGeminiClient, gmail_client: MockGmailClient) -> None:
    """Clean up the test environment after test execution"""
    capital_one_client.reset()
    sheets_client.reset()
    gemini_client.reset()
    gmail_client.reset()

def test_successful_weekly_process():
    """Test the complete weekly budget management process with successful execution"""
    capital_one_client, sheets_client, gemini_client, gmail_client = setup_test_environment()

    # Execute the main function
    results = run_budget_management_process(TEST_CORRELATION_ID)

    # Assert that the process completed successfully
    assert results["status"] == "success"
    assert results["retriever"]["status"] == "success"
    assert results["categorizer"]["status"] == "success"
    assert results["analyzer"]["status"] == "success"
    assert results["insight"]["status"] == "success"
    assert results["report"]["status"] == "success"
    assert gmail_client.get_sent_email_count() == 1

    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)

def test_weekly_process_with_budget_surplus():
    """Test the weekly process with a budget surplus that triggers savings transfer"""
    capital_one_client, sheets_client, gemini_client, gmail_client = setup_test_environment()

    # Modify the budget to create a surplus
    sheets_client.set_sheet_data("Master Budget", [["Category", "Weekly Amount"], ["Groceries", "200"], ["Transportation", "150"], ["Dining Out", "100"]])

    # Execute the main function
    results = run_budget_management_process(TEST_CORRELATION_ID)

    # Assert that the process completed successfully
    assert results["status"] == "success"
    assert results["savings"]["transfer_result"]["status"] == "success"
    assert capital_one_client.get_initiated_transfers()

    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)

def test_weekly_process_with_budget_deficit():
    """Test the weekly process with a budget deficit that doesn't trigger savings transfer"""
    capital_one_client, sheets_client, gemini_client, gmail_client = setup_test_environment()

    # Modify the budget to create a deficit
    sheets_client.set_sheet_data("Master Budget", [["Category", "Weekly Amount"], ["Groceries", "50"], ["Transportation", "30"], ["Dining Out", "20"]])

    # Execute the main function
    results = run_budget_management_process(TEST_CORRELATION_ID)

    # Assert that the process completed successfully
    assert results["status"] == "success"
    assert results["savings"]["transfer_result"]["status"] == "no_transfer"
    assert not capital_one_client.get_initiated_transfers()

    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)

def test_weekly_process_with_transaction_retrieval_failure():
    """Test error handling when transaction retrieval fails"""
    capital_one_client, sheets_client, gemini_client, gmail_client = setup_test_environment()

    # Configure Capital One client to simulate a failure
    capital_one_client.set_should_fail_transactions(True)

    # Execute the main function
    results = run_budget_management_process(TEST_CORRELATION_ID)

    # Assert that the process failed and the error was handled correctly
    assert results["status"] == "error"
    assert "Transaction retrieval failed" in results["error"]
    assert results["retriever"]["status"] == "error"

    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)

def test_weekly_process_with_categorization_failure():
    """Test error handling when transaction categorization fails"""
    capital_one_client, sheets_client, gemini_client, gmail_client = setup_test_environment()

    # Configure Gemini client to simulate a failure
    gemini_client.set_failure_mode(True, "categorization")

    # Execute the main function
    results = run_budget_management_process(TEST_CORRELATION_ID)

    # Assert that the process failed and the error was handled correctly
    assert results["status"] == "error"
    assert "Transaction categorization failed" in results["error"]
    assert results["categorizer"]["status"] == "error"

    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)

def test_weekly_process_with_email_failure():
    """Test graceful degradation when email delivery fails"""
    capital_one_client, sheets_client, gemini_client, gmail_client = setup_test_environment()

    # Configure Gmail client to simulate a failure
    gmail_client.set_should_fail_sending(True)

    # Execute the main function
    results = run_budget_management_process(TEST_CORRELATION_ID)

    # Assert that the process completed successfully, but the email delivery failed
    assert results["status"] == "success"
    assert results["report"]["status"] == "error"
    assert gmail_client.get_sent_email_count() == 0

    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)

def test_weekly_process_with_transfer_failure():
    """Test graceful degradation when savings transfer fails"""
    capital_one_client, sheets_client, gemini_client, gmail_client = setup_test_environment()

    # Configure Capital One client to simulate a transfer failure
    capital_one_client.set_should_fail_transfers(True)
    sheets_client.set_sheet_data("Master Budget", [["Category", "Weekly Amount"], ["Groceries", "200"], ["Transportation", "150"], ["Dining Out", "100"]])

    # Execute the main function
    results = run_budget_management_process(TEST_CORRELATION_ID)

    # Assert that the process completed successfully, but the transfer failed
    assert results["status"] == "success"
    assert results["savings"]["transfer_result"]["status"] == "error"
    assert capital_one_client.get_initiated_transfers()

    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)

def test_weekly_process_with_large_transaction_volume():
    """Test performance with a large number of transactions"""
    capital_one_client, sheets_client, gemini_client, gmail_client = setup_test_environment()

    # Load a large transaction fixture
    large_transactions = load_fixture("transactions/large_transaction_volume.json")
    capital_one_client.set_transactions(large_transactions)

    # Execute the main function
    results = run_budget_management_process(TEST_CORRELATION_ID)

    # Assert that the process completed successfully
    assert results["status"] == "success"
    assert results["retriever"]["transaction_count"] == len(large_transactions)

    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)

def test_weekly_process_component_integration():
    """Test integration between individual components in the workflow"""
    capital_one_client, sheets_client, gemini_client, gmail_client = setup_test_environment()

    # Execute the main function
    results = run_budget_management_process(TEST_CORRELATION_ID)

    # Assert that the components are integrated correctly by checking data flow
    assert sheets_client.get_sheet_data("Weekly Spending")  # Check that transactions were stored
    assert gemini_client.get_call_history("categorize_transactions")  # Check that Gemini was called
    assert gmail_client.get_sent_email_count() == 1  # Check that email was sent

    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)

def test_weekly_process_data_consistency():
    """Test data consistency throughout the entire process"""
    capital_one_client, sheets_client, gemini_client, gmail_client = setup_test_environment()

    # Execute the main function
    results = run_budget_management_process(TEST_CORRELATION_ID)

    # Assert that the data is consistent throughout the process
    transactions = capital_one_client.transaction_fixtures["transactions"]
    stored_transactions = sheets_client.get_sheet_data("Weekly Spending")
    assert len(transactions) == len(stored_transactions) - 1 # -1 to account for header row

    teardown_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)