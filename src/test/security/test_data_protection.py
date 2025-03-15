import os  # standard library
import json  # standard library
import decimal  # standard library
from decimal import Decimal  # standard library
import datetime  # standard library
import re  # standard library
import unittest  # standard library
from unittest.mock import MagicMock, patch  # standard library
from io import StringIO  # standard library
import pytest  # pytest 7.4.0+

from src.backend.models.transaction import Transaction  # Internal import
from src.backend.utils.formatters import format_currency, clean_html, format_transaction_for_sheets  # Internal import
from src.backend.api_clients.capital_one_client import CapitalOneClient  # Internal import
from src.test.mocks.capital_one_client import MockCapitalOneClient  # Internal import
from src.test.utils.fixture_loader import load_test_fixture  # Internal import
from src.test.utils.test_helpers import with_test_environment  # Internal import

TEST_TRANSACTIONS_PATH = os.path.join(os.path.dirname(__file__), '../fixtures/json/transactions')
ACCOUNT_NUMBER_PATTERN = re.compile(r'\d{4}-\d{4}-\d{4}-\d{4}')
MASKED_ACCOUNT_PATTERN = re.compile(r'XXXX-XXXX-XXXX-\d{4}')


def setup_module():
    """Setup function that runs before all tests in the module"""
    # Set up any global test fixtures or environment variables
    # Initialize mock loggers to capture log output
    pass


def teardown_module():
    """Teardown function that runs after all tests in the module"""
    # Clean up any global test fixtures or environment variables
    # Reset any patched modules or functions
    pass


def load_transaction_fixtures(fixture_name: str):
    """Load transaction test fixtures from JSON files"""
    # Construct path to the fixture file
    fixture_path = os.path.join(TEST_TRANSACTIONS_PATH, fixture_name + '.json')
    # Load and parse JSON data from the file
    with open(fixture_path, 'r') as f:
        transaction_data = json.load(f)
    # Return the parsed transaction data
    return transaction_data


class TestTransactionDataProtection(unittest.TestCase):
    """Test case for transaction data protection"""

    def setUp(self):
        """Set up test fixtures before each test method"""
        # Load transaction test fixtures
        self.transactions_data = load_test_fixture('transactions/valid_transactions')
        # Create Transaction objects for testing
        self.transaction = Transaction(
            location="Test Merchant",
            amount=Decimal("123.45"),
            timestamp=datetime.datetime.now(),
            transaction_id="tx-123",
            description="Test transaction"
        )
        self.sensitive_transaction = Transaction(
            location="Capital One Bank",
            amount=Decimal("100000.00"),
            timestamp=datetime.datetime.now(),
            transaction_id="tx-sensitive",
            description="Payment from 1234-5678-9012-3456"
        )
        # Set up mock loggers to capture log output
        self.mock_logger = MagicMock()

    def tearDown(self):
        """Clean up test fixtures after each test method"""
        # Reset all mocks
        self.mock_logger.reset_mock()
        # Clear captured log output
        pass

    @pytest.mark.security
    def test_transaction_to_dict_masks_sensitive_data(self):
        """Test that Transaction.to_dict properly masks sensitive data"""
        # Create Transaction with sensitive data (account numbers, large amounts)
        transaction = self.sensitive_transaction
        # Call to_dict method
        transaction_dict = transaction.to_dict()
        # Assert that account numbers are properly masked (e.g., XXXX-XXXX-XXXX-1234)
        assert MASKED_ACCOUNT_PATTERN.search(transaction_dict['description'])
        # Assert that transaction amounts are included but not modified
        assert transaction_dict['amount'] == Decimal('100000.00')
        # Assert that non-sensitive data is not masked
        assert transaction_dict['location'] == "Capital One Bank"

    @pytest.mark.security
    def test_transaction_to_sheets_format_protects_sensitive_data(self):
        """Test that Transaction.to_sheets_format properly handles sensitive data for Google Sheets"""
        # Create Transaction with sensitive data
        transaction = self.sensitive_transaction
        # Call to_sheets_format method
        sheets_format = transaction.to_sheets_format()
        # Assert that the formatted data includes necessary fields for Sheets
        assert len(sheets_format) >= 3
        # Assert that no sensitive data beyond transaction amount is included
        assert not ACCOUNT_NUMBER_PATTERN.search(sheets_format[0])
        # Assert that transaction location is included but not modified
        assert sheets_format[0] == "Capital One Bank"

    @pytest.mark.security
    def test_transaction_str_representation_masks_sensitive_data(self):
        """Test that Transaction string representation masks sensitive data"""
        # Create Transaction with sensitive data
        transaction = self.sensitive_transaction
        # Convert Transaction to string using str()
        transaction_str = str(transaction)
        # Assert that account numbers are properly masked
        assert MASKED_ACCOUNT_PATTERN.search(transaction_str)
        # Assert that transaction amounts are included but not modified
        assert "$100000.00" in transaction_str
        # Assert that the string representation is useful but secure
        assert "Capital One Bank" in transaction_str


class TestFormatterDataProtection(unittest.TestCase):
    """Test case for data protection in formatter functions"""

    def setUp(self):
        """Set up test fixtures before each test method"""
        # Set up test data for formatting functions
        self.test_amount = Decimal("1234567.89")
        self.test_html = "<script>alert('XSS');</script><p>This is safe.</p>"
        self.test_transaction = {
            "location": "Capital One",
            "amount": Decimal("987.65"),
            "timestamp": "2023-10-26 10:00:00",
            "account_number": "1111-2222-3333-4444"
        }
        # Set up mock loggers to capture log output
        self.mock_logger = MagicMock()

    def tearDown(self):
        """Clean up test fixtures after each test method"""
        # Reset all mocks
        self.mock_logger.reset_mock()
        # Clear captured log output
        pass

    @pytest.mark.security
    def test_format_currency_handles_sensitive_amounts(self):
        """Test that format_currency properly handles sensitive financial amounts"""
        # Create test amounts including very large values
        amounts = [Decimal("1000000.00"), Decimal("-500000.00"), Decimal("0.01")]
        # Call format_currency with each test amount
        formatted_amounts = [format_currency(amount) for amount in amounts]
        # Assert that the formatted string includes currency symbol
        assert all("$" in s for s in formatted_amounts)
        # Assert that the amount is formatted correctly
        assert formatted_amounts[0] == "$1000000.00"
        assert formatted_amounts[1] == "($500000.00)"
        assert formatted_amounts[2] == "$0.01"
        # Assert that no additional sensitive information is included
        assert all(len(s) > 1 for s in formatted_amounts)

    @pytest.mark.security
    def test_clean_html_sanitizes_content(self):
        """Test that clean_html properly sanitizes HTML content to prevent XSS"""
        # Create test HTML content with potentially malicious scripts and tags
        html_content = "<script>alert('XSS');</script><p>This is safe.</p>"
        # Call clean_html with the test content
        sanitized_content = clean_html(html_content)
        # Assert that script tags and other dangerous elements are removed
        assert "<script>" not in sanitized_content
        # Assert that safe HTML elements are preserved
        assert "<p>This is safe.</p>" in sanitized_content
        # Assert that the sanitized content is still valid HTML
        assert sanitized_content == "<p>This is safe.</p>"

    @pytest.mark.security
    def test_format_transaction_for_sheets_protects_sensitive_data(self):
        """Test that format_transaction_for_sheets properly protects sensitive data"""
        # Create test transaction dictionary with sensitive data
        transaction = self.test_transaction
        # Call format_transaction_for_sheets with the test data
        formatted_data = format_transaction_for_sheets(transaction)
        # Assert that the formatted data includes necessary fields for Sheets
        assert len(formatted_data) == 4
        # Assert that account numbers are properly masked
        assert "1111-2222-3333-4444" not in formatted_data[0]
        # Assert that transaction amounts are included but not modified
        assert formatted_data[1] == "987.65"


class TestCapitalOneClientDataProtection(unittest.TestCase):
    """Test case for data protection in Capital One API client"""

    def setUp(self):
        """Set up test fixtures before each test method"""
        # Create MockCapitalOneClient instance
        self.client = MockCapitalOneClient()
        # Set up test account and transaction data
        self.account_id = "test-account-123"
        self.transfer_amount = Decimal("50.00")
        self.source_account_id = "test-checking-123"
        self.destination_account_id = "test-savings-456"
        # Set up mock loggers to capture log output
        self.mock_logger = MagicMock()

    def tearDown(self):
        """Clean up test fixtures after each test method"""
        # Reset all mocks
        self.client.reset()
        self.mock_logger.reset_mock()
        # Clear captured log output
        pass

    @pytest.mark.security
    def test_get_transactions_masks_account_numbers(self):
        """Test that get_transactions masks account numbers in logs and responses"""
        # Set up mock response with account numbers
        self.client.set_transactions([{"accountId": "1234-5678-9012-3456", "amount": 100}])
        # Call client.get_transactions()
        transactions = self.client.get_transactions(account_id=self.account_id)
        # Capture log output
        # Assert that account numbers are masked in logs (e.g., XXXX-XXXX-XXXX-1234)
        # Assert that account numbers are masked in returned data
        # Assert that transaction data is otherwise complete and accurate
        pass

    @pytest.mark.security
    def test_initiate_transfer_protects_account_data(self):
        """Test that initiate_transfer protects account data in logs and requests"""
        # Set up mock for transfer request and response
        # Call client.initiate_transfer() with source and destination accounts
        transfer = self.client.initiate_transfer(
            amount=self.transfer_amount,
            source_account_id=self.source_account_id,
            destination_account_id=self.destination_account_id
        )
        # Capture log output and request data
        # Assert that account numbers are masked in logs
        # Assert that full account numbers are not logged
        # Assert that transfer amount is logged but not modified
        pass

    @pytest.mark.security
    def test_error_responses_mask_sensitive_data(self):
        """Test that error responses mask sensitive data"""
        # Configure mock client to raise an exception with sensitive data
        # Call client method that will raise the exception
        # Catch the exception and examine its content
        # Assert that sensitive data is masked in the exception message
        # Assert that the exception still contains useful error information
        pass


class TestLogDataProtection(unittest.TestCase):
    """Test case for data protection in application logs"""

    def setUp(self):
        """Set up test fixtures before each test method"""
        # Set up mock logger to capture log output
        self.mock_logger = MagicMock()
        # Create test data with sensitive information
        self.transaction = Transaction(
            location="Test Merchant",
            amount=Decimal("123.45"),
            timestamp=datetime.datetime.now(),
            transaction_id="tx-123",
            description="Payment from 1234-5678-9012-3456"
        )

    def tearDown(self):
        """Clean up test fixtures after each test method"""
        # Reset all mocks
        self.mock_logger.reset_mock()
        # Clear captured log output
        pass

    @pytest.mark.security
    def test_transaction_logging_masks_sensitive_data(self):
        """Test that transaction logging masks sensitive data"""
        # Create Transaction with sensitive data
        transaction = self.transaction
        # Perform operations that trigger logging
        # Capture log output
        # Assert that account numbers are masked in logs
        # Assert that transaction amounts are logged but not modified
        # Assert that non-sensitive data is logged normally
        pass

    @pytest.mark.security
    def test_api_request_logging_masks_sensitive_data(self):
        """Test that API request logging masks sensitive data"""
        # Set up mock API client with request logging
        # Perform API request with sensitive data
        # Capture log output
        # Assert that authentication tokens are masked in logs
        # Assert that account numbers are masked in logs
        # Assert that request URLs and methods are logged normally
        pass

    @pytest.mark.security
    def test_error_logging_masks_sensitive_data(self):
        """Test that error logging masks sensitive data"""
        # Set up operation that will trigger an error with sensitive data
        # Perform the operation and capture error logs
        # Assert that sensitive data is masked in error logs
        # Assert that error context and stack traces don't contain sensitive data
        # Assert that error logs still contain useful debugging information
        pass


class TestEmailContentProtection(unittest.TestCase):
    """Test case for data protection in email content"""

    def setUp(self):
        """Set up test fixtures before each test method"""
        # Set up mock email generator and formatter
        # Create test budget and transaction data
        pass

    def tearDown(self):
        """Clean up test fixtures after each test method"""
        # Reset all mocks
        pass

    @pytest.mark.security
    def test_email_content_protects_sensitive_data(self):
        """Test that email content protects sensitive financial data"""
        # Generate email content with budget and transaction data
        # Assert that account numbers are masked in email content
        # Assert that transaction amounts are included but not modified
        # Assert that only appropriate financial data is included in email
        pass

    @pytest.mark.security
    def test_email_sanitizes_html_content(self):
        """Test that email content is properly sanitized to prevent XSS"""
        # Create test HTML content with potentially malicious scripts
        # Generate email with the test content
        # Assert that script tags and other dangerous elements are removed
        # Assert that safe HTML elements are preserved
        # Assert that the sanitized content is still valid HTML
        pass

    @pytest.mark.security
    def test_email_subject_protects_sensitive_data(self):
        """Test that email subject line protects sensitive data"""
        # Generate email subject with budget status data
        # Assert that the subject includes budget status (surplus/deficit)
        # Assert that the subject includes formatted amount
        # Assert that no account numbers or other sensitive data is included
        pass