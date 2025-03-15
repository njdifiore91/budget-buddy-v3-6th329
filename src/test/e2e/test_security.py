import os  # standard library
import pytest  # pytest 7.4.0+
from unittest.mock import patch, MagicMock  # standard library
import logging  # standard library
from decimal import Decimal  # standard library

from ..mocks.capital_one_client import MockCapitalOneClient  # Mock implementation of Capital One API client for security testing
from ..mocks.google_sheets_client import MockGoogleSheetsClient  # Mock implementation of Google Sheets API client for security testing
from ..mocks.gemini_client import MockGeminiClient  # Mock implementation of Gemini AI API client for security testing
from ..mocks.gmail_client import MockGmailClient  # Mock implementation of Gmail API client for security testing
from ..utils.test_helpers import load_test_fixture, TestEnvironment  # Load test fixtures for security testing
from ..utils.assertion_helpers import assert_exception_contains  # Verify exception messages in security tests
from ..utils.assertion_helpers import assert_logs_contain  # Verify logs don't contain sensitive data
from src.backend.main import run_budget_management_process  # Main function that executes the complete budget management workflow
from src.backend.services.authentication_service import AuthenticationService, mask_sensitive_data  # Service being tested that manages authentication for external APIs
from src.backend.components.savings_automator import SavingsAutomator  # Component for automating the transfer of budget surplus to savings account

TEST_CORRELATION_ID = "test-security-e2e-001"
SENSITIVE_FIELDS = ['client_secret', 'api_key', 'access_token', 'refresh_token', 'account_number', 'card_number', 'routing_number', 'transfer_id']

def setup_security_test_environment():
    """Set up the test environment with mock clients and test data for security testing"""
    capital_one_client = MockCapitalOneClient()
    sheets_client = MockGoogleSheetsClient()
    gemini_client = MockGeminiClient()
    gmail_client = MockGmailClient()

    test_transactions = load_test_fixture("transactions/valid_transactions.json")
    test_budget = load_test_fixture("budget/valid_budget.json")
    test_api_responses = load_test_fixture("api_responses/capital_one/transactions.json")

    capital_one_client.set_transactions(test_transactions)
    sheets_client.set_sheet_data("Weekly Spending", [["Test Location", "10.00", "2024-01-01", ""]])
    sheets_client.set_sheet_data("Master Budget", [["Groceries", "100.00"]])

    return capital_one_client, sheets_client, gemini_client, gmail_client

def teardown_security_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client):
    """Clean up the test environment after security test execution"""
    capital_one_client.reset()
    sheets_client.reset()
    gemini_client.reset()
    gmail_client.reset()

@pytest.mark.security
@pytest.mark.e2e
def test_end_to_end_authentication_security():
    """Test that the application securely handles authentication for all external APIs"""
    capital_one_client, sheets_client, gemini_client, gmail_client = setup_security_test_environment()

    with patch("src.backend.components.transaction_retriever.CapitalOneClient", return_value=capital_one_client), \
         patch("src.backend.components.transaction_categorizer.GoogleSheetsClient", return_value=sheets_client), \
         patch("src.backend.components.insight_generator.GeminiClient", return_value=gemini_client), \
         patch("src.backend.components.report_distributor.GmailClient", return_value=gmail_client):
        run_budget_management_process(TEST_CORRELATION_ID)

        assert capital_one_client.authenticated
        assert sheets_client.authenticated
        assert gemini_client.is_authenticated
        assert gmail_client.authenticated

        assert_logs_contain(logging.getLogger('capital_one_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('google_sheets_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('gemini_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('gmail_client').handlers[0].format, SENSITIVE_FIELDS)

    teardown_security_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)

@pytest.mark.security
@pytest.mark.e2e
def test_end_to_end_data_protection():
    """Test that sensitive data is protected throughout the entire application workflow"""
    capital_one_client, sheets_client, gemini_client, gmail_client = setup_security_test_environment()

    with patch("src.backend.components.transaction_retriever.CapitalOneClient", return_value=capital_one_client), \
         patch("src.backend.components.transaction_categorizer.GoogleSheetsClient", return_value=sheets_client), \
         patch("src.backend.components.insight_generator.GeminiClient", return_value=gemini_client), \
         patch("src.backend.components.report_distributor.GmailClient", return_value=gmail_client):
        run_budget_management_process(TEST_CORRELATION_ID)

        assert_logs_contain(logging.getLogger('capital_one_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('google_sheets_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('gemini_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('gmail_client').handlers[0].format, SENSITIVE_FIELDS)

        last_email = gmail_client.get_last_sent_email()
        if last_email:
            assert_logs_contain(last_email['html_content'], SENSITIVE_FIELDS)

    teardown_security_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)

@pytest.mark.security
@pytest.mark.e2e
def test_end_to_end_secure_transfer():
    """Test that financial transfers are performed securely with proper validation"""
    capital_one_client, sheets_client, gemini_client, gmail_client = setup_security_test_environment()

    with patch("src.backend.components.transaction_retriever.CapitalOneClient", return_value=capital_one_client), \
         patch("src.backend.components.transaction_categorizer.GoogleSheetsClient", return_value=sheets_client), \
         patch("src.backend.components.insight_generator.GeminiClient", return_value=gemini_client), \
         patch("src.backend.components.report_distributor.GmailClient", return_value=gmail_client):
        run_budget_management_process(TEST_CORRELATION_ID)

        initiated_transfers = capital_one_client.get_initiated_transfers()
        if initiated_transfers:
            for transfer in initiated_transfers:
                assert 'amount' in transfer
                assert 'sourceAccountId' in transfer
                assert 'destinationAccountId' in transfer
                assert_logs_contain(str(transfer), SENSITIVE_FIELDS)

    teardown_security_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)

@pytest.mark.security
@pytest.mark.e2e
def test_end_to_end_authentication_failure_handling():
    """Test that the application handles authentication failures securely"""
    capital_one_client, sheets_client, gemini_client, gmail_client = setup_security_test_environment()

    capital_one_client.set_should_fail_authentication(True)
    sheets_client.set_authentication_failure(True)
    gemini_client.set_failure_mode(True, 'authentication')
    gmail_client.set_should_fail_authentication(True)

    with patch("src.backend.components.transaction_retriever.CapitalOneClient", return_value=capital_one_client), \
         patch("src.backend.components.transaction_categorizer.GoogleSheetsClient", return_value=sheets_client), \
         patch("src.backend.components.insight_generator.GeminiClient", return_value=gemini_client), \
         patch("src.backend.components.report_distributor.GmailClient", return_value=gmail_client):
        run_budget_management_process(TEST_CORRELATION_ID)

        assert_logs_contain(logging.getLogger('capital_one_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('google_sheets_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('gemini_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('gmail_client').handlers[0].format, SENSITIVE_FIELDS)

    teardown_security_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)

@pytest.mark.security
@pytest.mark.e2e
def test_end_to_end_api_error_security():
    """Test that API errors are handled securely without exposing sensitive information"""
    capital_one_client, sheets_client, gemini_client, gmail_client = setup_security_test_environment()

    capital_one_client.set_should_fail_transactions(True)
    sheets_client.set_authentication_failure(True)
    gemini_client.set_failure_mode(True, 'completion')
    gmail_client.set_should_fail_sending(True)

    with patch("src.backend.components.transaction_retriever.CapitalOneClient", return_value=capital_one_client), \
         patch("src.backend.components.transaction_categorizer.GoogleSheetsClient", return_value=sheets_client), \
         patch("src.backend.components.insight_generator.GeminiClient", return_value=gemini_client), \
         patch("src.backend.components.report_distributor.GmailClient", return_value=gmail_client):
        run_budget_management_process(TEST_CORRELATION_ID)

        assert_logs_contain(logging.getLogger('capital_one_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('google_sheets_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('gemini_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('gmail_client').handlers[0].format, SENSITIVE_FIELDS)

    teardown_security_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)

@pytest.mark.security
@pytest.mark.e2e
def test_end_to_end_credential_storage():
    """Test that credentials are stored securely throughout application lifecycle"""
    capital_one_client, sheets_client, gemini_client, gmail_client = setup_security_test_environment()

    with patch("src.backend.components.transaction_retriever.CapitalOneClient", return_value=capital_one_client), \
         patch("src.backend.components.transaction_categorizer.GoogleSheetsClient", return_value=sheets_client), \
         patch("src.backend.components.insight_generator.GeminiClient", return_value=gemini_client), \
         patch("src.backend.components.report_distributor.GmailClient", return_value=gmail_client):
        run_budget_management_process(TEST_CORRELATION_ID)

        assert_logs_contain(logging.getLogger('capital_one_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('google_sheets_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('gemini_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('gmail_client').handlers[0].format, SENSITIVE_FIELDS)

    teardown_security_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)

@pytest.mark.security
@pytest.mark.e2e
def test_end_to_end_email_content_security():
    """Test that email content doesn't contain sensitive financial information"""
    capital_one_client, sheets_client, gemini_client, gmail_client = setup_security_test_environment()

    with patch("src.backend.components.transaction_retriever.CapitalOneClient", return_value=capital_one_client), \
         patch("src.backend.components.transaction_categorizer.GoogleSheetsClient", return_value=sheets_client), \
         patch("src.backend.components.insight_generator.GeminiClient", return_value=gemini_client), \
         patch("src.backend.components.report_distributor.GmailClient", return_value=gmail_client):
        run_budget_management_process(TEST_CORRELATION_ID)

        last_email = gmail_client.get_last_sent_email()
        if last_email:
            assert_logs_contain(last_email['html_content'], SENSITIVE_FIELDS)

    teardown_security_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)

@pytest.mark.security
@pytest.mark.e2e
def test_end_to_end_log_security():
    """Test that application logs don't contain sensitive information"""
    capital_one_client, sheets_client, gemini_client, gmail_client = setup_security_test_environment()

    with patch("src.backend.components.transaction_retriever.CapitalOneClient", return_value=capital_one_client), \
         patch("src.backend.components.transaction_categorizer.GoogleSheetsClient", return_value=sheets_client), \
         patch("src.backend.components.insight_generator.GeminiClient", return_value=gemini_client), \
         patch("src.backend.components.report_distributor.GmailClient", return_value=gmail_client):
        run_budget_management_process(TEST_CORRELATION_ID)

        assert_logs_contain(logging.getLogger('capital_one_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('google_sheets_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('gemini_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('gmail_client').handlers[0].format, SENSITIVE_FIELDS)

    teardown_security_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)

@pytest.mark.security
@pytest.mark.e2e
def test_end_to_end_error_message_security():
    """Test that error messages don't expose sensitive information"""
    capital_one_client, sheets_client, gemini_client, gmail_client = setup_security_test_environment()

    capital_one_client.set_should_fail_authentication(True)
    sheets_client.set_authentication_failure(True)
    gemini_client.set_failure_mode(True, 'completion')
    gmail_client.set_should_fail_sending(True)

    with patch("src.backend.components.transaction_retriever.CapitalOneClient", return_value=capital_one_client), \
         patch("src.backend.components.transaction_categorizer.GoogleSheetsClient", return_value=sheets_client), \
         patch("src.backend.components.insight_generator.GeminiClient", return_value=gemini_client), \
         patch("src.backend.components.report_distributor.GmailClient", return_value=gmail_client):
        run_budget_management_process(TEST_CORRELATION_ID)

        assert_logs_contain(logging.getLogger('capital_one_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('google_sheets_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('gemini_client').handlers[0].format, SENSITIVE_FIELDS)
        assert_logs_contain(logging.getLogger('gmail_client').handlers[0].format, SENSITIVE_FIELDS)

    teardown_security_test_environment(capital_one_client, sheets_client, gemini_client, gmail_client)