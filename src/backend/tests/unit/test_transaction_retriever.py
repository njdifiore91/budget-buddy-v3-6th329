"""
Unit tests for the TransactionRetriever component, responsible for retrieving
transactions from Capital One API and storing them in Google Sheets.

These tests verify correct behavior for API interactions, error handling,
and the complete transaction processing flow.
"""

import pytest
from unittest.mock import MagicMock, patch

from ...components.transaction_retriever import TransactionRetriever
from ..mocks.mock_capital_one_client import MockCapitalOneClient
from ..mocks.mock_google_sheets_client import MockGoogleSheetsClient
from ..fixtures.transactions import create_test_transactions
from ...models.transaction import Transaction
from ...utils.error_handlers import APIError


def test_transaction_retriever_init():
    """Test the initialization of TransactionRetriever with default and custom clients"""
    # Arrange - Create mock clients
    mock_capital_one = MockCapitalOneClient()
    mock_sheets = MockGoogleSheetsClient()
    
    # Act - Initialize with mock clients
    retriever = TransactionRetriever(
        capital_one_client=mock_capital_one,
        sheets_client=mock_sheets
    )
    
    # Assert - Verify clients are correctly assigned
    assert retriever.capital_one_client == mock_capital_one
    assert retriever.sheets_client == mock_sheets
    
    # Act - Initialize with no clients (should create default ones)
    retriever_default = TransactionRetriever()
    
    # Assert - Verify default clients are created
    assert retriever_default.capital_one_client is not None
    assert retriever_default.sheets_client is not None


def test_authenticate_success():
    """Test successful authentication with both APIs"""
    # Arrange - Create mock clients with authentication success
    mock_capital_one = MockCapitalOneClient(auth_success=True)
    mock_sheets = MockGoogleSheetsClient(auth_success=True)
    
    # Create the retriever with mock clients
    retriever = TransactionRetriever(
        capital_one_client=mock_capital_one,
        sheets_client=mock_sheets
    )
    
    # Act - Call authenticate method
    result = retriever.authenticate()
    
    # Assert - Verify authenticate returns True
    assert result is True


def test_authenticate_failure_capital_one():
    """Test authentication failure with Capital One API"""
    # Arrange - Create mock clients with Capital One failing
    mock_capital_one = MockCapitalOneClient(auth_success=False)
    mock_sheets = MockGoogleSheetsClient(auth_success=True)
    
    # Create the retriever with mock clients
    retriever = TransactionRetriever(
        capital_one_client=mock_capital_one,
        sheets_client=mock_sheets
    )
    
    # Act - Call authenticate method
    result = retriever.authenticate()
    
    # Assert - Verify authenticate returns False
    assert result is False


def test_authenticate_failure_google_sheets():
    """Test authentication failure with Google Sheets API"""
    # Arrange - Create mock clients with Google Sheets failing
    mock_capital_one = MockCapitalOneClient(auth_success=True)
    mock_sheets = MockGoogleSheetsClient(auth_success=False)
    
    # Create the retriever with mock clients
    retriever = TransactionRetriever(
        capital_one_client=mock_capital_one,
        sheets_client=mock_sheets
    )
    
    # Act - Call authenticate method
    result = retriever.authenticate()
    
    # Assert - Verify authenticate returns False
    assert result is False


def test_retrieve_transactions_success():
    """Test successful retrieval of transactions"""
    # Arrange - Create test transactions data
    test_transactions = create_test_transactions()
    
    # Create mock Capital One client that returns test transactions
    mock_capital_one = MockCapitalOneClient()
    mock_capital_one.set_transactions([tx.to_dict() for tx in test_transactions])
    
    # Create the retriever with mock client
    retriever = TransactionRetriever(capital_one_client=mock_capital_one)
    
    # Act - Call retrieve_transactions method
    transactions = retriever.retrieve_transactions()
    
    # Assert - Verify returned transactions match test data
    assert len(transactions) == len(test_transactions)
    assert all(isinstance(tx, Transaction) for tx in transactions)
    # Verify get_weekly_transactions was called on the client
    assert transactions is not None


def test_retrieve_transactions_api_error():
    """Test transaction retrieval with API error"""
    # Arrange - Create mock Capital One client with API error
    mock_capital_one = MockCapitalOneClient(api_error=True)
    
    # Create the retriever with mock client
    retriever = TransactionRetriever(capital_one_client=mock_capital_one)
    
    # Act & Assert - Verify APIError is raised
    with pytest.raises(APIError):
        retriever.retrieve_transactions()


def test_store_transactions_success():
    """Test successful storage of transactions in Google Sheets"""
    # Arrange - Create test transactions data
    test_transactions = create_test_transactions()
    
    # Create mock Google Sheets client
    mock_sheets = MockGoogleSheetsClient()
    
    # Create the retriever with mock client
    retriever = TransactionRetriever(sheets_client=mock_sheets)
    
    # Act - Call store_transactions method
    stored_count = retriever.store_transactions(test_transactions)
    
    # Assert - Verify append_transactions was called with test transactions
    assert stored_count == len(test_transactions)
    assert mock_sheets.append_count == 1  # Verify the append method was called once


def test_store_transactions_api_error():
    """Test transaction storage with API error"""
    # Arrange - Create test transactions data
    test_transactions = create_test_transactions()
    
    # Create mock Google Sheets client with API error
    mock_sheets = MockGoogleSheetsClient(api_error=True)
    
    # Create the retriever with mock client
    retriever = TransactionRetriever(sheets_client=mock_sheets)
    
    # Act & Assert - Verify APIError is raised
    with pytest.raises(APIError):
        retriever.store_transactions(test_transactions)


def test_execute_success():
    """Test successful execution of the complete retrieval and storage process"""
    # Arrange - Create test transactions data
    test_transactions = create_test_transactions()
    
    # Create mock clients
    mock_capital_one = MockCapitalOneClient(auth_success=True)
    mock_capital_one.set_transactions([tx.to_dict() for tx in test_transactions])
    
    mock_sheets = MockGoogleSheetsClient(auth_success=True)
    
    # Create the retriever with mock clients
    retriever = TransactionRetriever(
        capital_one_client=mock_capital_one,
        sheets_client=mock_sheets
    )
    
    # Act - Call execute method
    result = retriever.execute()
    
    # Assert - Verify successful execution
    assert result["status"] == "success"
    assert result["transaction_count"] == len(test_transactions)
    assert mock_sheets.append_count == 1  # Verify transactions were stored


def test_execute_authentication_failure():
    """Test execution with authentication failure"""
    # Arrange - Create mock clients with authentication failure
    mock_capital_one = MockCapitalOneClient(auth_success=False)
    mock_sheets = MockGoogleSheetsClient(auth_success=True)
    
    # Create the retriever with mock clients
    retriever = TransactionRetriever(
        capital_one_client=mock_capital_one,
        sheets_client=mock_sheets
    )
    
    # Act - Call execute method
    result = retriever.execute()
    
    # Assert - Verify execution failed due to authentication
    assert result["status"] == "error"
    assert "Authentication failed" in result["error"]
    assert mock_sheets.append_count == 0  # Verify no transactions were stored


def test_execute_retrieval_failure():
    """Test execution with transaction retrieval failure"""
    # Arrange - Create mock clients with API error for retrieval
    mock_capital_one = MockCapitalOneClient(auth_success=True, api_error=True)
    mock_sheets = MockGoogleSheetsClient(auth_success=True)
    
    # Create the retriever with mock clients
    retriever = TransactionRetriever(
        capital_one_client=mock_capital_one,
        sheets_client=mock_sheets
    )
    
    # Act - Call execute method
    result = retriever.execute()
    
    # Assert - Verify execution failed due to retrieval error
    assert result["status"] == "error"
    assert mock_sheets.append_count == 0  # Verify no transactions were stored


def test_execute_storage_failure():
    """Test execution with transaction storage failure"""
    # Arrange - Create test transactions data
    test_transactions = create_test_transactions()
    
    # Create mock clients with API error for storage
    mock_capital_one = MockCapitalOneClient(auth_success=True)
    mock_capital_one.set_transactions([tx.to_dict() for tx in test_transactions])
    
    mock_sheets = MockGoogleSheetsClient(auth_success=True, api_error=True)
    
    # Create the retriever with mock clients
    retriever = TransactionRetriever(
        capital_one_client=mock_capital_one,
        sheets_client=mock_sheets
    )
    
    # Act - Call execute method
    result = retriever.execute()
    
    # Assert - Verify execution failed due to storage error
    assert result["status"] == "error"


def test_execute_no_transactions():
    """Test execution when no transactions are retrieved"""
    # Arrange - Create mock clients with empty transaction list
    mock_capital_one = MockCapitalOneClient(auth_success=True)
    mock_capital_one.set_transactions([])  # Empty transaction list
    
    mock_sheets = MockGoogleSheetsClient(auth_success=True)
    
    # Create the retriever with mock clients
    retriever = TransactionRetriever(
        capital_one_client=mock_capital_one,
        sheets_client=mock_sheets
    )
    
    # Act - Call execute method
    result = retriever.execute()
    
    # Assert - Verify execution succeeded with no transactions
    assert result["status"] == "success"
    assert "No transactions" in result["message"]
    assert result["transaction_count"] == 0
    assert mock_sheets.append_count == 0  # Verify no append was attempted


def test_check_health():
    """Test health check functionality"""
    # Arrange - Create mock clients
    mock_capital_one = MockCapitalOneClient(auth_success=True)
    mock_sheets = MockGoogleSheetsClient(auth_success=True)
    
    # Create the retriever with mock clients
    retriever = TransactionRetriever(
        capital_one_client=mock_capital_one,
        sheets_client=mock_sheets
    )
    
    # Act - Call check_health method
    health_status = retriever.check_health()
    
    # Assert - Verify health status contains entries for both APIs
    assert 'capital_one' in health_status
    assert 'google_sheets' in health_status
    assert health_status['capital_one'] == 'healthy'
    assert health_status['google_sheets'] == 'healthy'


def test_check_health_with_errors():
    """Test health check with connectivity errors"""
    # Arrange - Create mock clients with connectivity errors
    mock_capital_one = MockCapitalOneClient(api_error=True)
    mock_sheets = MockGoogleSheetsClient(api_error=True)
    
    # Create the retriever with mock clients
    retriever = TransactionRetriever(
        capital_one_client=mock_capital_one,
        sheets_client=mock_sheets
    )
    
    # Act - Call check_health method
    health_status = retriever.check_health()
    
    # Assert - Verify health status contains entries for both APIs
    assert 'capital_one' in health_status
    assert 'google_sheets' in health_status
    assert health_status['capital_one'] == 'unhealthy'
    assert health_status['google_sheets'] == 'unhealthy'