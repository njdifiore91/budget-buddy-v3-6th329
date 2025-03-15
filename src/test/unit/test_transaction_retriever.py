import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from decimal import Decimal

from src.backend.components.transaction_retriever import TransactionRetriever
from src.backend.models.transaction import Transaction
from src.test.utils.test_helpers import create_test_transaction, create_test_transactions, load_fixture
from src.test.utils.assertion_helpers import assert_transactions_equal
from src.backend.utils.error_handlers import APIError

# Define test functions for TransactionRetriever
def test_transaction_retriever_init():
    """Test that TransactionRetriever initializes correctly with provided clients"""
    # Step 1: Create mock Capital One client
    mock_capital_one_client = MagicMock()
    # Step 2: Create mock Google Sheets client
    mock_sheets_client = MagicMock()
    # Step 3: Create TransactionRetriever with mock clients
    retriever = TransactionRetriever(capital_one_client=mock_capital_one_client, sheets_client=mock_sheets_client)
    # Step 4: Assert that the retriever's clients are the ones provided
    assert retriever.capital_one_client == mock_capital_one_client
    assert retriever.sheets_client == mock_sheets_client
    # Step 5: Assert that the retriever is properly initialized
    assert retriever.auth_service is not None

@patch('src.backend.components.transaction_retriever.CapitalOneClient')
@patch('src.backend.components.transaction_retriever.GoogleSheetsClient')
@patch('src.backend.components.transaction_retriever.AuthenticationService')
def test_transaction_retriever_init_default(MockAuthenticationService, MockGoogleSheetsClient, MockCapitalOneClient):
    """Test that TransactionRetriever initializes correctly with default clients"""
    # Step 1: Mock the default client classes
    mock_capital_one_client = MagicMock()
    MockCapitalOneClient.return_value = mock_capital_one_client
    mock_sheets_client = MagicMock()
    MockGoogleSheetsClient.return_value = mock_sheets_client
    mock_auth_service = MagicMock()
    MockAuthenticationService.return_value = mock_auth_service

    # Step 2: Create TransactionRetriever without providing clients
    retriever = TransactionRetriever()

    # Step 3: Assert that the retriever creates default clients
    assert isinstance(retriever.capital_one_client, MagicMock)
    assert isinstance(retriever.sheets_client, MagicMock)
    assert isinstance(retriever.auth_service, MagicMock)

    # Step 4: Assert that the retriever is properly initialized
    assert retriever.capital_one_client == mock_capital_one_client
    assert retriever.sheets_client == mock_sheets_client
    assert retriever.auth_service == mock_auth_service

def test_authenticate_success():
    """Test successful authentication with both APIs"""
    # Step 1: Create mock Capital One client that returns True for authenticate()
    mock_capital_one_client = MagicMock()
    mock_capital_one_client.authenticate.return_value = True
    # Step 2: Create mock Google Sheets client that returns True for authenticate()
    mock_sheets_client = MagicMock()
    mock_sheets_client.authenticate.return_value = True
    # Step 3: Create TransactionRetriever with mock clients
    retriever = TransactionRetriever(capital_one_client=mock_capital_one_client, sheets_client=mock_sheets_client)
    # Step 4: Call authenticate() method
    result = retriever.authenticate()
    # Step 5: Assert that the method returns True
    assert result is True
    # Step 6: Assert that both client authenticate methods were called
    mock_capital_one_client.authenticate.assert_called_once()
    mock_sheets_client.authenticate.assert_called_once()

def test_authenticate_capital_one_failure():
    """Test authentication failure with Capital One API"""
    # Step 1: Create mock Capital One client that returns False for authenticate()
    mock_capital_one_client = MagicMock()
    mock_capital_one_client.authenticate.return_value = False
    # Step 2: Create mock Google Sheets client that returns True for authenticate()
    mock_sheets_client = MagicMock()
    mock_sheets_client.authenticate.return_value = True
    # Step 3: Create TransactionRetriever with mock clients
    retriever = TransactionRetriever(capital_one_client=mock_capital_one_client, sheets_client=mock_sheets_client)
    # Step 4: Call authenticate() method
    result = retriever.authenticate()
    # Step 5: Assert that the method returns False
    assert result is False
    # Step 6: Assert that Capital One authenticate method was called
    mock_capital_one_client.authenticate.assert_called_once()
    # Step 7: Assert that Google Sheets authenticate method was not called
    mock_sheets_client.authenticate.assert_not_called()

def test_authenticate_google_sheets_failure():
    """Test authentication failure with Google Sheets API"""
    # Step 1: Create mock Capital One client that returns True for authenticate()
    mock_capital_one_client = MagicMock()
    mock_capital_one_client.authenticate.return_value = True
    # Step 2: Create mock Google Sheets client that returns False for authenticate()
    mock_sheets_client = MagicMock()
    mock_sheets_client.authenticate.return_value = False
    # Step 3: Create TransactionRetriever with mock clients
    retriever = TransactionRetriever(capital_one_client=mock_capital_one_client, sheets_client=mock_sheets_client)
    # Step 4: Call authenticate() method
    result = retriever.authenticate()
    # Step 5: Assert that the method returns False
    assert result is False
    # Step 6: Assert that both client authenticate methods were called
    mock_capital_one_client.authenticate.assert_called_once()
    mock_sheets_client.authenticate.assert_called_once()

def test_retrieve_transactions_success():
    """Test successful transaction retrieval"""
    # Step 1: Create test transactions
    test_transactions = create_test_transactions(3)
    # Step 2: Create mock Capital One client that returns test transactions
    mock_capital_one_client = MagicMock()
    mock_capital_one_client.retrieve_transactions.return_value = test_transactions
    # Step 3: Create TransactionRetriever with mock client
    retriever = TransactionRetriever(capital_one_client=mock_capital_one_client)
    # Step 4: Call retrieve_transactions() method
    result = retriever.retrieve_transactions()
    # Step 5: Assert that the method returns the test transactions
    assert_transactions_equal(result, test_transactions)
    # Step 6: Assert that Capital One get_weekly_transactions method was called
    mock_capital_one_client.get_weekly_transactions.assert_called_once()

def test_retrieve_transactions_empty():
    """Test transaction retrieval with empty result"""
    # Step 1: Create mock Capital One client that returns empty list
    mock_capital_one_client = MagicMock()
    mock_capital_one_client.retrieve_transactions.return_value = []
    # Step 2: Create TransactionRetriever with mock client
    retriever = TransactionRetriever(capital_one_client=mock_capital_one_client)
    # Step 3: Call retrieve_transactions() method
    result = retriever.retrieve_transactions()
    # Step 4: Assert that the method returns an empty list
    assert result == []
    # Step 5: Assert that Capital One get_weekly_transactions method was called
    mock_capital_one_client.get_weekly_transactions.assert_called_once()

def test_retrieve_transactions_error():
    """Test transaction retrieval with API error"""
    # Step 1: Create mock Capital One client that raises APIError
    mock_capital_one_client = MagicMock()
    mock_capital_one_client.retrieve_transactions.side_effect = APIError("Test API Error", "Capital One", "retrieve_transactions")
    # Step 2: Create TransactionRetriever with mock client
    retriever = TransactionRetriever(capital_one_client=mock_capital_one_client)
    # Step 3: Call retrieve_transactions() method
    with pytest.raises(APIError):
        retriever.retrieve_transactions()
    # Step 4: Assert that Capital One get_weekly_transactions method was called
    mock_capital_one_client.get_weekly_transactions.assert_called_once()

def test_store_transactions_success():
    """Test successful transaction storage"""
    # Step 1: Create test transactions
    test_transactions = create_test_transactions(3)
    # Step 2: Create mock Google Sheets client that returns transaction count
    mock_sheets_client = MagicMock()
    mock_sheets_client.append_transactions.return_value = len(test_transactions)
    # Step 3: Create TransactionRetriever with mock client
    retriever = TransactionRetriever(sheets_client=mock_sheets_client)
    # Step 4: Call store_transactions() method with test transactions
    result = retriever.store_transactions(test_transactions)
    # Step 5: Assert that the method returns the correct transaction count
    assert result == len(test_transactions)
    # Step 6: Assert that Google Sheets append_transactions method was called with test transactions
    mock_sheets_client.append_transactions.assert_called_once_with(test_transactions)

def test_store_transactions_empty():
    """Test transaction storage with empty list"""
    # Step 1: Create mock Google Sheets client
    mock_sheets_client = MagicMock()
    # Step 2: Create TransactionRetriever with mock client
    retriever = TransactionRetriever(sheets_client=mock_sheets_client)
    # Step 3: Call store_transactions() method with empty list
    result = retriever.store_transactions([])
    # Step 4: Assert that the method returns 0
    assert result == 0
    # Step 5: Assert that Google Sheets append_transactions method was called with empty list
    mock_sheets_client.append_transactions.assert_called_once_with([])

def test_store_transactions_error():
    """Test transaction storage with API error"""
    # Step 1: Create test transactions
    test_transactions = create_test_transactions(3)
    # Step 2: Create mock Google Sheets client that raises APIError
    mock_sheets_client = MagicMock()
    mock_sheets_client.append_transactions.side_effect = APIError("Test API Error", "Google Sheets", "store_transactions")
    # Step 3: Create TransactionRetriever with mock client
    retriever = TransactionRetriever(sheets_client=mock_sheets_client)
    # Step 4: Call store_transactions() method with test transactions
    with pytest.raises(APIError):
        retriever.store_transactions(test_transactions)
    # Step 5: Assert that Google Sheets append_transactions method was called
    mock_sheets_client.append_transactions.assert_called_once_with(test_transactions)

def test_execute_success():
    """Test successful execution of the complete retrieval and storage process"""
    # Step 1: Create test transactions
    test_transactions = create_test_transactions(3)
    # Step 2: Create mock Capital One client that returns test transactions
    mock_capital_one_client = MagicMock()
    mock_capital_one_client.retrieve_transactions.return_value = test_transactions
    # Step 3: Create mock Google Sheets client that returns transaction count
    mock_sheets_client = MagicMock()
    mock_sheets_client.append_transactions.return_value = len(test_transactions)
    # Step 4: Create TransactionRetriever with mock clients
    retriever = TransactionRetriever(capital_one_client=mock_capital_one_client, sheets_client=mock_sheets_client)
    # Step 5: Call execute() method
    result = retriever.execute()
    # Step 6: Assert that the method returns success status with correct transaction count
    assert result["status"] == "success"
    assert result["transaction_count"] == len(test_transactions)
    # Step 7: Assert that authenticate, retrieve_transactions, and store_transactions methods were called
    mock_capital_one_client.authenticate.assert_called_once()
    mock_sheets_client.authenticate.assert_called_once()
    mock_capital_one_client.get_weekly_transactions.assert_called_once()
    mock_sheets_client.append_transactions.assert_called_once_with(test_transactions)

def test_execute_authentication_failure():
    """Test execution with authentication failure"""
    # Step 1: Create mock clients where authenticate returns False
    mock_capital_one_client = MagicMock()
    mock_capital_one_client.authenticate.return_value = False
    mock_sheets_client = MagicMock()
    mock_sheets_client.authenticate.return_value = False
    # Step 2: Create TransactionRetriever with mock clients
    retriever = TransactionRetriever(capital_one_client=mock_capital_one_client, sheets_client=mock_sheets_client)
    # Step 3: Call execute() method
    result = retriever.execute()
    # Step 4: Assert that the method returns error status with authentication failure
    assert result["status"] == "error"
    assert "Authentication failed" in result["error"]
    # Step 5: Assert that authenticate method was called
    mock_capital_one_client.authenticate.assert_called_once()
    mock_sheets_client.authenticate.assert_called_once()
    # Step 6: Assert that retrieve_transactions and store_transactions methods were not called
    mock_capital_one_client.get_weekly_transactions.assert_not_called()
    mock_sheets_client.append_transactions.assert_not_called()

def test_execute_retrieval_failure():
    """Test execution with transaction retrieval failure"""
    # Step 1: Create mock Capital One client that raises APIError on get_weekly_transactions
    mock_capital_one_client = MagicMock()
    mock_capital_one_client.get_weekly_transactions.side_effect = APIError("Test API Error", "Capital One", "retrieve_transactions")
    # Step 2: Create mock Google Sheets client
    mock_sheets_client = MagicMock()
    # Step 3: Create TransactionRetriever with mock clients
    retriever = TransactionRetriever(capital_one_client=mock_capital_one_client, sheets_client=mock_sheets_client)
    # Step 4: Call execute() method
    result = retriever.execute()
    # Step 5: Assert that the method returns error status with retrieval failure
    assert result["status"] == "error"
    assert "Test API Error" in result["error"]
    # Step 6: Assert that authenticate and retrieve_transactions methods were called
    mock_capital_one_client.authenticate.assert_called_once()
    mock_sheets_client.authenticate.assert_called_once()
    mock_capital_one_client.get_weekly_transactions.assert_called_once()
    # Step 7: Assert that store_transactions method was not called
    mock_sheets_client.append_transactions.assert_not_called()

def test_execute_storage_failure():
    """Test execution with transaction storage failure"""
    # Step 1: Create test transactions
    test_transactions = create_test_transactions(3)
    # Step 2: Create mock Capital One client that returns test transactions
    mock_capital_one_client = MagicMock()
    mock_capital_one_client.retrieve_transactions.return_value = test_transactions
    # Step 3: Create mock Google Sheets client that raises APIError on append_transactions
    mock_sheets_client = MagicMock()
    mock_sheets_client.append_transactions.side_effect = APIError("Test API Error", "Google Sheets", "store_transactions")
    # Step 4: Create TransactionRetriever with mock clients
    retriever = TransactionRetriever(capital_one_client=mock_capital_one_client, sheets_client=mock_sheets_client)
    # Step 5: Call execute() method
    result = retriever.execute()
    # Step 6: Assert that the method returns error status with storage failure
    assert result["status"] == "error"
    assert "Test API Error" in result["error"]
    # Step 7: Assert that authenticate, retrieve_transactions, and store_transactions methods were called
    mock_capital_one_client.authenticate.assert_called_once()
    mock_sheets_client.authenticate.assert_called_once()
    mock_capital_one_client.get_weekly_transactions.assert_called_once()
    mock_sheets_client.append_transactions.assert_called_once_with(test_transactions)

def test_execute_no_transactions():
    """Test execution with no transactions retrieved"""
    # Step 1: Create mock Capital One client that returns empty list
    mock_capital_one_client = MagicMock()
    mock_capital_one_client.retrieve_transactions.return_value = []
    # Step 2: Create mock Google Sheets client
    mock_sheets_client = MagicMock()
    # Step 3: Create TransactionRetriever with mock clients
    retriever = TransactionRetriever(capital_one_client=mock_capital_one_client, sheets_client=mock_sheets_client)
    # Step 4: Call execute() method
    result = retriever.execute()
    # Step 5: Assert that the method returns success status with no transactions
    assert result["status"] == "success"
    assert result["transaction_count"] == 0
    # Step 6: Assert that authenticate and retrieve_transactions methods were called
    mock_capital_one_client.authenticate.assert_called_once()
    mock_sheets_client.authenticate.assert_called_once()
    mock_capital_one_client.get_weekly_transactions.assert_called_once()
    # Step 7: Assert that store_transactions method was not called
    mock_sheets_client.append_transactions.assert_not_called()

def test_check_health():
    """Test health check functionality"""
    # Step 1: Create mock Capital One client with test_connectivity returning True
    mock_capital_one_client = MagicMock()
    mock_capital_one_client.test_connectivity.return_value = True
    # Step 2: Create mock Google Sheets client with authenticate returning True
    mock_sheets_client = MagicMock()
    mock_sheets_client.authenticate.return_value = True
    # Step 3: Create TransactionRetriever with mock clients
    retriever = TransactionRetriever(capital_one_client=mock_capital_one_client, sheets_client=mock_sheets_client)
    # Step 4: Call check_health() method
    health_status = retriever.check_health()
    # Step 5: Assert that the method returns healthy status for both APIs
    assert health_status["capital_one"] == "healthy"
    assert health_status["google_sheets"] == "healthy"
    # Step 6: Assert that Capital One test_connectivity and Google Sheets authenticate methods were called
    mock_capital_one_client.test_connectivity.assert_called_once()
    mock_sheets_client.authenticate.assert_called_once()

def test_check_health_capital_one_unhealthy():
    """Test health check with unhealthy Capital One API"""
    # Step 1: Create mock Capital One client with test_connectivity returning False
    mock_capital_one_client = MagicMock()
    mock_capital_one_client.test_connectivity.return_value = False
    # Step 2: Create mock Google Sheets client with authenticate returning True
    mock_sheets_client = MagicMock()
    mock_sheets_client.authenticate.return_value = True
    # Step 3: Create TransactionRetriever with mock clients
    retriever = TransactionRetriever(capital_one_client=mock_capital_one_client, sheets_client=mock_sheets_client)
    # Step 4: Call check_health() method
    health_status = retriever.check_health()
    # Step 5: Assert that the method returns unhealthy status for Capital One API
    assert health_status["capital_one"] == "unhealthy"
    assert health_status["google_sheets"] == "healthy"
    # Step 6: Assert that Capital One test_connectivity and Google Sheets authenticate methods were called
    mock_capital_one_client.test_connectivity.assert_called_once()
    mock_sheets_client.authenticate.assert_called_once()

def test_check_health_google_sheets_unhealthy():
    """Test health check with unhealthy Google Sheets API"""
    # Step 1: Create mock Capital One client with test_connectivity returning True
    mock_capital_one_client = MagicMock()
    mock_capital_one_client.test_connectivity.return_value = True
    # Step 2: Create mock Google Sheets client with authenticate returning False
    mock_sheets_client = MagicMock()
    mock_sheets_client.authenticate.return_value = False
    # Step 3: Create TransactionRetriever with mock clients
    retriever = TransactionRetriever(capital_one_client=mock_capital_one_client, sheets_client=mock_sheets_client)
    # Step 4: Call check_health() method
    health_status = retriever.check_health()
    # Step 5: Assert that the method returns unhealthy status for Google Sheets API
    assert health_status["capital_one"] == "healthy"
    assert health_status["google_sheets"] == "unhealthy"
    # Step 6: Assert that Capital One test_connectivity and Google Sheets authenticate methods were called
    mock_capital_one_client.test_connectivity.assert_called_once()
    mock_sheets_client.authenticate.assert_called_once()

def test_check_health_both_unhealthy():
    """Test health check with both APIs unhealthy"""
    # Step 1: Create mock Capital One client with test_connectivity returning False
    mock_capital_one_client = MagicMock()
    mock_capital_one_client.test_connectivity.return_value = False
    # Step 2: Create mock Google Sheets client with authenticate returning False
    mock_sheets_client = MagicMock()
    mock_sheets_client.authenticate.return_value = False
    # Step 3: Create TransactionRetriever with mock clients
    retriever = TransactionRetriever(capital_one_client=mock_capital_one_client, sheets_client=mock_sheets_client)
    # Step 4: Call check_health() method
    health_status = retriever.check_health()
    # Step 5: Assert that the method returns unhealthy status for both APIs
    assert health_status["capital_one"] == "unhealthy"
    assert health_status["google_sheets"] == "unhealthy"
    # Step 6: Assert that Capital One test_connectivity and Google Sheets authenticate methods were called
    mock_capital_one_client.test_connectivity.assert_called_once()
    mock_sheets_client.authenticate.assert_called_once()

def test_check_health_capital_one_error():
    """Test health check with Capital One API error"""
    # Step 1: Create mock Capital One client with test_connectivity raising exception
    mock_capital_one_client = MagicMock()
    mock_capital_one_client.test_connectivity.side_effect = Exception("Test Connectivity Error")
    # Step 2: Create mock Google Sheets client with authenticate returning True
    mock_sheets_client = MagicMock()
    mock_sheets_client.authenticate.return_value = True
    # Step 3: Create TransactionRetriever with mock clients
    retriever = TransactionRetriever(capital_one_client=mock_capital_one_client, sheets_client=mock_sheets_client)
    # Step 4: Call check_health() method
    health_status = retriever.check_health()
    # Step 5: Assert that the method returns unhealthy status for Capital One API with error message
    assert "unhealthy: Test Connectivity Error" in health_status["capital_one"]
    assert health_status["google_sheets"] == "healthy"
    # Step 6: Assert that Capital One test_connectivity and Google Sheets authenticate methods were called
    mock_capital_one_client.test_connectivity.assert_called_once()
    mock_sheets_client.authenticate.assert_called_once()