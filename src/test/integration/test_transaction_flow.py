"""
Integration test module for testing the transaction flow in the Budget Management Application.
Tests the end-to-end process of retrieving transactions from Capital One API and storing them in Google Sheets,
focusing on the integration between the TransactionRetriever component and its dependencies.
"""

import pytest
from typing import List, Dict, Any
from datetime import datetime
from decimal import Decimal

# Internal imports
from ..utils.test_helpers import with_test_environment, create_test_transactions, load_test_fixture
from ..utils.assertion_helpers import TransactionAssertions, assert_transactions_equal
from ..utils.fixture_loader import load_fixture, convert_to_transaction_objects
from ..mocks.capital_one_client import MockCapitalOneClient
from ..mocks.google_sheets_client import MockGoogleSheetsClient
from ...backend.components.transaction_retriever import TransactionRetriever

# Constants
TRANSACTION_FIXTURE_PATH = 'transactions/valid_transactions.json'
WEEKLY_SPENDING_SHEET_NAME = 'Weekly Spending'


class TestTransactionFlow:
    """Test class for transaction flow integration tests"""

    def setup_method(self):
        """Set up test fixtures before each test method"""
        self.transactions = load_test_fixture(TRANSACTION_FIXTURE_PATH)
        self.test_data = {
            'transactions': self.transactions
        }

    def teardown_method(self):
        """Clean up after each test method"""
        pass

    def test_transaction_retrieval_success(self):
        """Test successful retrieval of transactions from Capital One API"""
        with with_test_environment() as test_env:
            # Arrange
            mock_capital_one_client = test_env['mocks']['capital_one']
            mock_google_sheets_client = test_env['mocks']['google_sheets']
            transactions = test_env['test_data']['transactions']

            mock_capital_one_client.set_transactions(transactions)
            transaction_retriever = TransactionRetriever(
                capital_one_client=mock_capital_one_client,
                sheets_client=mock_google_sheets_client
            )

            # Act
            retrieved_transactions = transaction_retriever.retrieve_transactions()

            # Assert
            assert_transactions_equal(
                retrieved_transactions,
                convert_to_transaction_objects(transactions),
                check_order=True,
                check_category=False
            )
            assert mock_capital_one_client.get_transactions_called

    def test_transaction_storage_success(self):
        """Test successful storage of transactions in Google Sheets"""
        with with_test_environment() as test_env:
            # Arrange
            mock_capital_one_client = test_env['mocks']['capital_one']
            mock_google_sheets_client = test_env['mocks']['google_sheets']
            transactions = test_env['test_data']['transactions']
            transaction_retriever = TransactionRetriever(
                capital_one_client=mock_capital_one_client,
                sheets_client=mock_google_sheets_client
            )
            transactions = convert_to_transaction_objects(transactions)

            # Act
            stored_count = transaction_retriever.store_transactions(transactions)

            # Assert
            assert stored_count == len(transactions)
            assert mock_google_sheets_client.append_rows_called
            assert mock_google_sheets_client.get_sheet_data(WEEKLY_SPENDING_SHEET_NAME)

    def test_transaction_flow_end_to_end(self):
        """Test the complete transaction retrieval and storage flow"""
        with with_test_environment() as test_env:
            # Arrange
            mock_capital_one_client = test_env['mocks']['capital_one']
            mock_google_sheets_client = test_env['mocks']['google_sheets']
            transactions = test_env['test_data']['transactions']

            mock_capital_one_client.set_transactions(transactions)
            transaction_retriever = TransactionRetriever(
                capital_one_client=mock_capital_one_client,
                sheets_client=mock_google_sheets_client
            )

            # Act
            execution_status = transaction_retriever.execute()

            # Assert
            assert execution_status['status'] == 'success'
            assert mock_capital_one_client.get_transactions_called
            assert mock_google_sheets_client.append_rows_called
            stored_transactions = mock_google_sheets_client.get_sheet_data(WEEKLY_SPENDING_SHEET_NAME)
            assert len(stored_transactions) == len(transactions)

    def test_capital_one_authentication_failure(self):
        """Test handling of Capital One API authentication failure"""
        with with_test_environment() as test_env:
            # Arrange
            mock_capital_one_client = test_env['mocks']['capital_one']
            mock_google_sheets_client = test_env['mocks']['google_sheets']
            mock_capital_one_client.set_should_fail_authentication(True)
            transaction_retriever = TransactionRetriever(
                capital_one_client=mock_capital_one_client,
                sheets_client=mock_google_sheets_client
            )

            # Act
            execution_status = transaction_retriever.execute()

            # Assert
            assert execution_status['status'] == 'error'
            assert 'Authentication failed' in execution_status['error']
            assert not mock_google_sheets_client.append_rows_called

    def test_google_sheets_authentication_failure(self):
        """Test handling of Google Sheets API authentication failure"""
        with with_test_environment() as test_env:
            # Arrange
            mock_capital_one_client = test_env['mocks']['capital_one']
            mock_google_sheets_client = test_env['mocks']['google_sheets']
            mock_google_sheets_client.set_authentication_failure(True)
            transaction_retriever = TransactionRetriever(
                capital_one_client=mock_capital_one_client,
                sheets_client=mock_google_sheets_client
            )

            # Act
            execution_status = transaction_retriever.execute()

            # Assert
            assert execution_status['status'] == 'error'
            assert 'Authentication failed' in execution_status['error']
            assert not mock_google_sheets_client.append_rows_called

    def test_transaction_retrieval_failure(self):
        """Test handling of transaction retrieval failure"""
        with with_test_environment() as test_env:
            # Arrange
            mock_capital_one_client = test_env['mocks']['capital_one']
            mock_google_sheets_client = test_env['mocks']['google_sheets']
            mock_capital_one_client.set_should_fail_transactions(True)
            transaction_retriever = TransactionRetriever(
                capital_one_client=mock_capital_one_client,
                sheets_client=mock_google_sheets_client
            )

            # Act
            execution_status = transaction_retriever.execute()

            # Assert
            assert execution_status['status'] == 'error'
            assert 'Transaction retrieval failed' in execution_status['error']
            assert not mock_google_sheets_client.append_rows_called

    def test_empty_transactions_handling(self):
        """Test handling of empty transaction list"""
        with with_test_environment() as test_env:
            # Arrange
            mock_capital_one_client = test_env['mocks']['capital_one']
            mock_google_sheets_client = test_env['mocks']['google_sheets']
            mock_capital_one_client.set_transactions([])
            transaction_retriever = TransactionRetriever(
                capital_one_client=mock_capital_one_client,
                sheets_client=mock_google_sheets_client
            )

            # Act
            execution_status = transaction_retriever.execute()

            # Assert
            assert execution_status['status'] == 'success'
            assert 'No transactions retrieved' in execution_status['message']
            assert not mock_google_sheets_client.append_rows_called

    def test_retry_on_api_failure(self):
        """Test retry mechanism on transient API failures"""
        with with_test_environment() as test_env:
            # Arrange
            mock_capital_one_client = test_env['mocks']['capital_one']
            mock_google_sheets_client = test_env['mocks']['google_sheets']
            transactions = test_env['test_data']['transactions']

            # Configure mock Capital One client to fail initially then succeed
            mock_capital_one_client.set_should_fail_transactions(True)
            mock_capital_one_client.set_transactions(transactions)
            transaction_retriever = TransactionRetriever(
                capital_one_client=mock_capital_one_client,
                sheets_client=mock_google_sheets_client
            )

            # Act
            execution_status = transaction_retriever.execute()

            # Assert
            assert execution_status['status'] == 'success'
            assert mock_capital_one_client.get_transactions_called
            assert mock_google_sheets_client.append_rows_called