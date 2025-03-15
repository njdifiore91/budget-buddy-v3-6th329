"""
Integration tests for the transaction flow in the Budget Management Application.

This file tests the end-to-end process of retrieving transactions from Capital One 
and storing them in Google Sheets, verifying that the components work together correctly.
"""

import pytest

from ...components.transaction_retriever import TransactionRetriever
from ..mocks.mock_capital_one_client import MockCapitalOneClient
from ..mocks.mock_google_sheets_client import MockGoogleSheetsClient
from ..fixtures.transactions import create_test_transactions
from ...utils.error_handlers import APIError


def test_transaction_retriever_initialization():
    """Test that the TransactionRetriever initializes correctly with mock clients."""
    # Create mock clients
    capital_one_client = MockCapitalOneClient()
    sheets_client = MockGoogleSheetsClient()
    
    # Initialize TransactionRetriever with mock clients
    retriever = TransactionRetriever(
        capital_one_client=capital_one_client,
        sheets_client=sheets_client
    )
    
    # Assert that the retriever's clients are correctly set
    assert retriever.capital_one_client == capital_one_client
    assert retriever.sheets_client == sheets_client


def test_transaction_retriever_authentication():
    """Test that the TransactionRetriever authenticates with both APIs successfully."""
    # Create mock clients with auth_success=True
    capital_one_client = MockCapitalOneClient(auth_success=True)
    sheets_client = MockGoogleSheetsClient(auth_success=True)
    
    retriever = TransactionRetriever(
        capital_one_client=capital_one_client,
        sheets_client=sheets_client
    )
    
    # Test authentication success
    result = retriever.authenticate()
    assert result is True
    
    # Create mock clients with auth_success=False
    capital_one_client = MockCapitalOneClient(auth_success=False)
    sheets_client = MockGoogleSheetsClient(auth_success=True)
    
    retriever = TransactionRetriever(
        capital_one_client=capital_one_client,
        sheets_client=sheets_client
    )
    
    # Test authentication failure
    result = retriever.authenticate()
    assert result is False


def test_transaction_retrieval():
    """Test that the TransactionRetriever retrieves transactions from Capital One API."""
    # Create test transactions
    test_transactions = create_test_transactions()
    
    # Create mock Capital One client and set test transactions
    capital_one_client = MockCapitalOneClient()
    capital_one_client.set_transactions([tx.to_dict() for tx in test_transactions])
    
    # Initialize TransactionRetriever with mock client
    retriever = TransactionRetriever(capital_one_client=capital_one_client)
    
    # Call retrieve_transactions method
    retrieved_transactions = retriever.retrieve_transactions()
    
    # Assert that returned transactions match test transactions
    assert len(retrieved_transactions) == len(test_transactions)
    
    # Compare transaction attributes since the objects will not be equal
    for i, tx in enumerate(retrieved_transactions):
        assert tx.location == test_transactions[i].location
        assert tx.amount == test_transactions[i].amount
        # Timestamps may have timezone differences, so check year, month, day
        assert tx.timestamp.date() == test_transactions[i].timestamp.date()


def test_transaction_storage():
    """Test that the TransactionRetriever stores transactions in Google Sheets."""
    # Create test transactions
    test_transactions = create_test_transactions()
    
    # Create mock Google Sheets client
    sheets_client = MockGoogleSheetsClient()
    
    # Initialize TransactionRetriever with mock client
    retriever = TransactionRetriever(sheets_client=sheets_client)
    
    # Call store_transactions method with test transactions
    stored_count = retriever.store_transactions(test_transactions)
    
    # Assert that transactions were stored in Weekly Spending sheet
    assert stored_count == len(test_transactions)
    
    # Verify the number of transactions stored matches expected count
    sheet_data = sheets_client.get_sheet_data("Weekly Spending")
    assert len(sheet_data) == len(test_transactions)


def test_transaction_flow_success():
    """Test the complete transaction flow from retrieval to storage."""
    # Create test transactions
    test_transactions = create_test_transactions()
    
    # Create mock Capital One client and set test transactions
    capital_one_client = MockCapitalOneClient(auth_success=True)
    capital_one_client.set_transactions([tx.to_dict() for tx in test_transactions])
    
    # Create mock Google Sheets client
    sheets_client = MockGoogleSheetsClient(auth_success=True)
    
    # Initialize TransactionRetriever with both mock clients
    retriever = TransactionRetriever(
        capital_one_client=capital_one_client,
        sheets_client=sheets_client
    )
    
    # Call execute method to run the complete flow
    result = retriever.execute()
    
    # Assert that the result status is 'success'
    assert result['status'] == 'success'
    
    # Verify that transactions were retrieved and stored correctly
    assert result['transaction_count'] > 0
    assert result['transaction_count'] == len(test_transactions)
    
    # Check that the transaction count in the result matches expected count
    sheet_data = sheets_client.get_sheet_data("Weekly Spending")
    assert len(sheet_data) == len(test_transactions)


def test_transaction_flow_authentication_failure():
    """Test transaction flow when authentication fails."""
    # Create mock Capital One client with auth_success=False
    capital_one_client = MockCapitalOneClient(auth_success=False)
    
    # Create mock Google Sheets client
    sheets_client = MockGoogleSheetsClient(auth_success=True)
    
    # Initialize TransactionRetriever with both mock clients
    retriever = TransactionRetriever(
        capital_one_client=capital_one_client,
        sheets_client=sheets_client
    )
    
    # Call execute method
    result = retriever.execute()
    
    # Assert that the result status is 'error'
    assert result['status'] == 'error'
    
    # Verify that the error message indicates authentication failure
    assert 'Authentication failed' in result['error']


def test_transaction_flow_retrieval_failure():
    """Test transaction flow when transaction retrieval fails."""
    # Create mock Capital One client and set API error
    capital_one_client = MockCapitalOneClient(auth_success=True, api_error=True)
    
    # Create mock Google Sheets client
    sheets_client = MockGoogleSheetsClient(auth_success=True)
    
    # Initialize TransactionRetriever with both mock clients
    retriever = TransactionRetriever(
        capital_one_client=capital_one_client,
        sheets_client=sheets_client
    )
    
    # Call execute method
    result = retriever.execute()
    
    # Assert that the result status is 'error'
    assert result['status'] == 'error'
    
    # Verify that the error message indicates retrieval failure
    assert 'error_type' in result


def test_transaction_flow_storage_failure():
    """Test transaction flow when transaction storage fails."""
    # Create test transactions
    test_transactions = create_test_transactions()
    
    # Create mock Capital One client and set test transactions
    capital_one_client = MockCapitalOneClient(auth_success=True)
    capital_one_client.set_transactions([tx.to_dict() for tx in test_transactions])
    
    # Create mock Google Sheets client and set API error
    sheets_client = MockGoogleSheetsClient(auth_success=True, api_error=True)
    
    # Initialize TransactionRetriever with both mock clients
    retriever = TransactionRetriever(
        capital_one_client=capital_one_client,
        sheets_client=sheets_client
    )
    
    # Call execute method
    result = retriever.execute()
    
    # Assert that the result status is 'error'
    assert result['status'] == 'error'
    
    # Verify that the error message indicates storage failure
    assert 'error_type' in result


def test_transaction_flow_empty_transactions():
    """Test transaction flow when no transactions are retrieved."""
    # Create mock Capital One client and set empty transaction list
    capital_one_client = MockCapitalOneClient(auth_success=True)
    capital_one_client.set_transactions([])
    
    # Create mock Google Sheets client
    sheets_client = MockGoogleSheetsClient(auth_success=True)
    
    # Initialize TransactionRetriever with both mock clients
    retriever = TransactionRetriever(
        capital_one_client=capital_one_client,
        sheets_client=sheets_client
    )
    
    # Call execute method
    result = retriever.execute()
    
    # Assert that the result status is 'success' (per the implementation)
    assert result['status'] == 'success'
    
    # Verify that the warning message indicates no transactions found
    assert 'No transactions retrieved' in result['message']
    assert result['transaction_count'] == 0


def test_transaction_flow_retry_logic():
    """Test that retry logic works when API calls fail temporarily."""
    # Create test transactions
    test_transactions = create_test_transactions()
    
    # Create mock Capital One client and set test transactions
    capital_one_client = MockCapitalOneClient(auth_success=True)
    capital_one_client.set_transactions([tx.to_dict() for tx in test_transactions])
    
    # Keep track of call count
    call_count = 0
    
    # Store the original method to restore it later
    original_get_weekly_transactions = capital_one_client.get_weekly_transactions
    
    # Define a function that will fail the first 2 times, then use the original
    def temporary_failure_get_weekly_transactions():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise APIError("Temporary failure", "Capital One", "get_weekly_transactions")
        return original_get_weekly_transactions()
    
    # Replace the method with our temporary failure version
    capital_one_client.get_weekly_transactions = temporary_failure_get_weekly_transactions
    
    # Create mock Google Sheets client
    sheets_client = MockGoogleSheetsClient(auth_success=True)
    
    # Initialize TransactionRetriever with both mock clients
    retriever = TransactionRetriever(
        capital_one_client=capital_one_client,
        sheets_client=sheets_client
    )
    
    try:
        # Call execute method
        result = retriever.execute()
        
        # Assert that the result status is 'success' after retries
        assert result['status'] == 'success'
        
        # Verify that the expected number of retries occurred
        assert call_count > 1
    finally:
        # Restore the original method to avoid affecting other tests
        capital_one_client.get_weekly_transactions = original_get_weekly_transactions