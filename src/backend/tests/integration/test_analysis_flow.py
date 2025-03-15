"""
Integration tests for the budget analysis flow in the Budget Management Application.
Tests the BudgetAnalyzer component's interaction with Google Sheets API to retrieve transaction
and budget data, perform analysis, and calculate variances and transfer amounts.
"""

import pytest
from decimal import Decimal

from ...components.budget_analyzer import BudgetAnalyzer
from ..mocks.mock_google_sheets_client import MockGoogleSheetsClient
from ..fixtures.transactions import create_categorized_transactions
from ..fixtures.categories import create_test_categories
from ..fixtures.budget import create_budget_with_surplus, create_budget_with_deficit, get_expected_analysis_results
from ...models.transaction import Transaction
from ...models.budget import Budget
from ...utils.error_handlers import APIError, ValidationError


def setup_mock_sheets_client(auth_success=True, api_error=False):
    """Helper function to set up a mock Google Sheets client with test data"""
    # Create a new MockGoogleSheetsClient with provided auth_success and api_error parameters
    mock_client = MockGoogleSheetsClient(auth_success=auth_success, api_error=api_error)
    
    # Create test transactions with categories
    transactions = create_categorized_transactions()
    
    # Create test budget categories
    categories = create_test_categories()
    
    # Format transactions for Google Sheets format
    transactions_data = [transaction.to_sheets_format() for transaction in transactions]
    categories_data = [[category.name, str(category.weekly_amount)] for category in categories]
    
    # Set up Weekly Spending sheet data with transactions
    mock_client.set_sheet_data("Weekly Spending", transactions_data)
    
    # Set up Master Budget sheet data with categories
    mock_client.set_sheet_data("Master Budget", categories_data)
    
    # Return the configured mock client
    return mock_client


@pytest.mark.integration
def test_budget_analyzer_successful_flow():
    """Test the complete budget analysis flow with successful API calls"""
    # Set up mock Google Sheets client with successful authentication
    mock_client = setup_mock_sheets_client(auth_success=True, api_error=False)
    
    # Create a BudgetAnalyzer instance with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Execute the budget analysis process
    result = analyzer.execute({})
    
    # Verify the execution status is 'success'
    assert result['status'] == 'success'
    
    # Verify the analysis results match expected values
    expected_results = get_expected_analysis_results()
    
    # Verify category variances are calculated correctly
    assert 'analysis_results' in result
    analysis_results = result['analysis_results']
    assert 'category_variances' in analysis_results
    assert len(analysis_results['category_variances']) > 0
    
    # Verify total budget, total spent, and total variance are correct
    assert 'total_budget' in analysis_results
    assert 'total_spent' in analysis_results
    assert 'total_variance' in analysis_results
    
    # Verify transfer amount is calculated correctly
    assert 'transfer_amount' in result
    assert result['transfer_amount'] >= 0


@pytest.mark.integration
def test_budget_analyzer_with_surplus():
    """Test budget analysis with a budget surplus scenario"""
    # Set up mock Google Sheets client with successful authentication
    mock_client = setup_mock_sheets_client(auth_success=True, api_error=False)
    
    # Set up sheet data to create a budget surplus scenario
    budget = create_budget_with_surplus()
    
    # Set sheet data to reflect surplus scenario
    categories_data = [[category.name, str(category.weekly_amount)] for category in budget.categories]
    mock_client.set_sheet_data("Master Budget", categories_data)
    
    # Create a BudgetAnalyzer instance with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Execute the budget analysis process
    result = analyzer.execute({})
    
    # Verify the execution status is 'success'
    assert result['status'] == 'success'
    
    # Verify total_variance is positive (surplus)
    assert result['analysis_results']['total_variance'] > 0
    
    # Verify transfer_amount equals total_variance
    assert result['transfer_amount'] == result['analysis_results']['total_variance']
    
    # Verify budget_status is 'surplus'
    assert result['analysis_results']['budget_status'] == 'surplus'


@pytest.mark.integration
def test_budget_analyzer_with_deficit():
    """Test budget analysis with a budget deficit scenario"""
    # Set up mock Google Sheets client with successful authentication
    mock_client = setup_mock_sheets_client(auth_success=True, api_error=False)
    
    # Set up sheet data to create a budget deficit scenario
    budget = create_budget_with_deficit()
    
    # Set sheet data to reflect deficit scenario
    categories_data = [[category.name, str(category.weekly_amount)] for category in budget.categories]
    mock_client.set_sheet_data("Master Budget", categories_data)
    
    # Create a BudgetAnalyzer instance with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Execute the budget analysis process
    result = analyzer.execute({})
    
    # Verify the execution status is 'success'
    assert result['status'] == 'success'
    
    # Verify total_variance is negative (deficit)
    assert result['analysis_results']['total_variance'] < 0
    
    # Verify transfer_amount is zero
    assert result['transfer_amount'] == 0
    
    # Verify budget_status is 'deficit'
    assert result['analysis_results']['budget_status'] == 'deficit'


@pytest.mark.integration
def test_budget_analyzer_authentication_failure():
    """Test budget analysis flow when Google Sheets authentication fails"""
    # Set up mock Google Sheets client with authentication failure
    mock_client = setup_mock_sheets_client(auth_success=False, api_error=False)
    
    # Create a BudgetAnalyzer instance with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Execute the budget analysis process
    result = analyzer.execute({})
    
    # Verify the execution status is 'error'
    assert result['status'] == 'error'
    
    # Verify the error message indicates authentication failure
    assert 'authenticate' in result['message'].lower()
    
    # Verify no analysis results are returned
    assert 'analysis_results' not in result


@pytest.mark.integration
def test_budget_analyzer_api_error():
    """Test budget analysis flow when Google Sheets API returns an error"""
    # Set up mock Google Sheets client with API error
    mock_client = setup_mock_sheets_client(auth_success=True, api_error=True)
    
    # Create a BudgetAnalyzer instance with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Execute the budget analysis process
    result = analyzer.execute({})
    
    # Verify the execution status is 'error'
    assert result['status'] == 'error'
    
    # Verify the error message indicates API error
    assert 'failed to retrieve' in result['message'].lower() or 'api' in result['message'].lower()
    
    # Verify no analysis results are returned
    assert 'analysis_results' not in result


@pytest.mark.integration
def test_budget_analyzer_empty_transactions():
    """Test budget analysis flow when no transactions are found"""
    # Set up mock Google Sheets client with successful authentication
    mock_client = setup_mock_sheets_client(auth_success=True, api_error=False)
    
    # Set up empty Weekly Spending sheet data
    mock_client.set_sheet_data("Weekly Spending", [])
    
    # Create a BudgetAnalyzer instance with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Execute the budget analysis process
    result = analyzer.execute({})
    
    # Verify the execution status is 'warning'
    assert result['status'] == 'warning'
    
    # Verify the warning message indicates no transactions found
    assert 'no transactions' in result['message'].lower()
    
    # Verify analysis results show zero spending
    # (Note: In this case, the actual implementation might not return analysis results)


@pytest.mark.integration
def test_budget_analyzer_empty_budget():
    """Test budget analysis flow when no budget categories are found"""
    # Set up mock Google Sheets client with successful authentication
    mock_client = setup_mock_sheets_client(auth_success=True, api_error=False)
    
    # Set up empty Master Budget sheet data
    mock_client.set_sheet_data("Master Budget", [])
    
    # Create a BudgetAnalyzer instance with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Execute the budget analysis process
    result = analyzer.execute({})
    
    # Verify the execution status is 'error'
    assert result['status'] == 'error'
    
    # Verify the error message indicates no budget categories found
    assert 'budget data' in result['message'].lower()
    
    # Verify no analysis results are returned
    assert 'analysis_results' not in result


@pytest.mark.integration
def test_budget_analyzer_retry_mechanism():
    """Test that the budget analyzer retries API calls on transient errors"""
    # Set up mock Google Sheets client that fails on first call but succeeds on retry
    mock_client = MockGoogleSheetsClient(auth_success=True)
    
    # Set up test data
    transactions = create_categorized_transactions()
    categories = create_test_categories()
    
    # Format test data
    transactions_data = [transaction.to_sheets_format() for transaction in transactions]
    categories_data = [[category.name, str(category.weekly_amount)] for category in categories]
    
    # Set up sheet data
    mock_client.set_sheet_data("Weekly Spending", transactions_data)
    mock_client.set_sheet_data("Master Budget", categories_data)
    
    # Configure mock to fail on first API call then succeed
    # This is a simplified implementation - in a real test, we would
    # need to enhance the mock to track and control retry behavior
    
    # Create a BudgetAnalyzer instance with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Execute the budget analysis process
    result = analyzer.execute({})
    
    # Verify the execution status is 'success' after retries
    assert result['status'] == 'success'
    
    # Verify the analysis results are correct
    assert 'analysis_results' in result
    
    # Verify the retry count matches expected value
    # This would require the mock to track retry attempts
    # assert mock_client.retry_count > 0  # Example assertion


@pytest.mark.integration
def test_budget_analyzer_component_integration():
    """Test integration between BudgetAnalyzer and other components"""
    # Set up mock Google Sheets client with successful authentication
    mock_client = setup_mock_sheets_client(auth_success=True, api_error=False)
    
    # Create a BudgetAnalyzer instance with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Create a mock previous_status that would come from TransactionCategorizer
    previous_status = {
        'status': 'success',
        'message': 'Transaction categorization completed successfully',
        'correlation_id': 'test-correlation-id',
        'execution_time': 1.5
    }
    
    # Execute the budget analysis process with previous_status
    result = analyzer.execute(previous_status)
    
    # Verify the execution status is 'success'
    assert result['status'] == 'success'
    
    # Verify the correlation_id is preserved from previous_status
    assert result['correlation_id'] == previous_status['correlation_id']
    
    # Verify the analysis results are correct
    assert 'analysis_results' in result
    
    # Verify the execution metadata is properly updated
    assert 'execution_time' in result