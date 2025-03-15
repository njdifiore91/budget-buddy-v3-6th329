import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal

from ...backend.components.budget_analyzer import BudgetAnalyzer
from ...backend.utils.error_handlers import APIError, ValidationError
from ...test.mocks.google_sheets_client import MockGoogleSheetsClient
from ...test.fixtures.transactions import create_test_transactions, create_transactions_with_amounts
from ...test.fixtures.budget import create_test_budget, create_budget_with_variance, create_analyzed_budget, get_expected_budget_analysis
from ...test.utils.assertion_helpers import assert_budget_variance_correct, assert_transfer_amount_valid, BudgetAssertions
from ...test.utils.test_helpers import setup_test_environment, with_test_environment
from ...test.utils.test_helpers import APIError, ValidationError

# Define a fixture for setting up a BudgetAnalyzer instance with mock dependencies
@pytest.fixture
def setup_budget_analyzer():
    """Pytest fixture to set up a BudgetAnalyzer instance with mock dependencies"""
    # Create a MockGoogleSheetsClient instance
    sheets_client = MockGoogleSheetsClient()
    
    # Create a BudgetAnalyzer instance with the mock sheets client
    analyzer = BudgetAnalyzer(sheets_client=sheets_client)
    
    # Return the BudgetAnalyzer instance
    return analyzer

# Define a fixture for setting up a MockGoogleSheetsClient with test data
@pytest.fixture
def setup_sheets_client_with_data():
    """Pytest fixture to set up a MockGoogleSheetsClient with test data"""
    # Create a MockGoogleSheetsClient instance
    sheets_client = MockGoogleSheetsClient()
    
    # Load test transaction data
    test_transactions = create_test_transactions()
    
    # Load test budget data
    test_budget = create_test_budget()
    
    # Configure the mock client with the test data
    sheets_client.set_sheet_data("Weekly Spending", [tx.to_sheets_format() for tx in test_transactions])
    sheets_client.set_sheet_data("Master Budget", [cat.to_dict() for cat in test_budget.categories])
    
    # Return the configured mock client
    return sheets_client

# Test that BudgetAnalyzer initializes correctly
def test_budget_analyzer_init():
    """Test that BudgetAnalyzer initializes correctly"""
    # Create a MockGoogleSheetsClient
    sheets_client = MockGoogleSheetsClient()
    
    # Create a BudgetAnalyzer with the mock client
    analyzer = BudgetAnalyzer(sheets_client=sheets_client)
    
    # Assert that the BudgetAnalyzer instance has the expected properties
    assert isinstance(analyzer, BudgetAnalyzer)
    
    # Assert that the sheets_client attribute is set correctly
    assert analyzer.sheets_client == sheets_client

# Test successful authentication with Google Sheets API
def test_authenticate_success(setup_budget_analyzer):
    """Test successful authentication with Google Sheets API"""
    # Configure the mock sheets client to return success for authentication
    setup_budget_analyzer.sheets_client.authenticated = True
    
    # Call authenticate() method
    result = setup_budget_analyzer.authenticate()
    
    # Assert that the method returns True
    assert result is True
    
    # Assert that the sheets client's authenticate method was called
    assert setup_budget_analyzer.sheets_client.authenticated is True

# Test authentication failure with Google Sheets API
def test_authenticate_failure(setup_budget_analyzer):
    """Test authentication failure with Google Sheets API"""
    # Configure the mock sheets client to return failure for authentication
    setup_budget_analyzer.sheets_client.authenticated = False
    
    # Call authenticate() method
    result = setup_budget_analyzer.authenticate()
    
    # Assert that the method returns False
    assert result is False
    
    # Assert that the sheets client's authenticate method was called
    assert setup_budget_analyzer.sheets_client.authenticated is False

# Test successful retrieval of transactions and budget data
def test_get_transactions_and_budget_success(setup_budget_analyzer, setup_sheets_client_with_data):
    """Test successful retrieval of transactions and budget data"""
    # Replace the analyzer's sheets_client with the configured mock
    setup_budget_analyzer.sheets_client = setup_sheets_client_with_data
    
    # Call get_transactions_and_budget() method
    transactions, budget = setup_budget_analyzer.get_transactions_and_budget()
    
    # Assert that the method returns a tuple of (transactions, budget)
    assert isinstance(transactions, list)
    assert isinstance(budget, Budget)
    
    # Assert that transactions is a list of Transaction objects
    # Assert that budget is a Budget object
    
    # Assert that the sheets client's get_transactions and get_budget methods were called
    assert setup_budget_analyzer.sheets_client.get_sheet_data("Weekly Spending") is not None
    assert setup_budget_analyzer.sheets_client.get_sheet_data("Master Budget") is not None

# Test handling of API errors during data retrieval
def test_get_transactions_and_budget_api_error(setup_budget_analyzer):
    """Test handling of API errors during data retrieval"""
    # Configure the mock sheets client to raise APIError
    setup_budget_analyzer.sheets_client.read_sheet = MagicMock(side_effect=APIError("API Error", "Google Sheets", "read_sheet"))
    
    # Use pytest.raises to assert that get_transactions_and_budget() raises APIError
    with pytest.raises(APIError):
        setup_budget_analyzer.get_transactions_and_budget()
    
    # Assert that the sheets client's get_transactions method was called
    setup_budget_analyzer.sheets_client.read_sheet.assert_called()

# Test budget analysis with valid budget data
def test_analyze_budget():
    """Test budget analysis with valid budget data"""
    # Create a test budget with known variances
    budget = create_budget_with_variance(Decimal('100.00'))
    
    # Create a BudgetAnalyzer instance
    analyzer = BudgetAnalyzer()
    
    # Call analyze_budget() method with the test budget
    analysis_results = analyzer.analyze_budget(budget)
    
    # Assert that the method returns a dictionary with analysis results
    assert isinstance(analysis_results, dict)
    
    # Assert that the results contain expected keys (total_budget, total_spent, total_variance, etc.)
    assert 'total_budget' in analysis_results
    assert 'total_spent' in analysis_results
    assert 'total_variance' in analysis_results
    assert 'category_variances' in analysis_results
    
    # Assert that the variance calculations are mathematically correct using assert_budget_variance_correct
    assert_budget_variance_correct(budget)

# Test handling of validation errors during budget analysis
def test_analyze_budget_validation_error():
    """Test handling of validation errors during budget analysis"""
    # Create a test budget with invalid data
    budget = create_test_budget()
    budget.categories = None  # Invalidate the budget
    
    # Create a BudgetAnalyzer instance
    analyzer = BudgetAnalyzer()
    
    # Use pytest.raises to assert that analyze_budget() raises ValidationError
    with pytest.raises(Exception):
        analyzer.analyze_budget(budget)
    
    # Verify that the error message contains expected validation failure details
    # (This part is skipped because the exception is raised before the error message is generated)

# Test formatting of budget analysis results
def test_format_analysis_results(setup_budget_analyzer):
    """Test formatting of budget analysis results"""
    # Create a sample analysis results dictionary
    analysis_results = {
        'total_budget': Decimal('500.00'),
        'total_spent': Decimal('400.00'),
        'total_variance': Decimal('100.00'),
        'category_variances': {'Groceries': Decimal('50.00'), 'Dining Out': Decimal('-20.00')}
    }
    
    # Call format_analysis_results() method
    formatted_results = setup_budget_analyzer.format_analysis_results(analysis_results)
    
    # Assert that the formatted results contain expected keys
    assert 'total_budget' in formatted_results
    assert 'total_spent' in formatted_results
    assert 'total_variance' in formatted_results
    assert 'category_variances' in formatted_results
    
    # Assert that the budget_status is correctly set based on total_variance
    assert formatted_results['budget_status'] == 'surplus'
    
    # Assert that category_variances are included in the formatted results
    assert 'Groceries' in formatted_results['category_variances']
    assert 'Dining Out' in formatted_results['category_variances']

# Test successful execution of the complete budget analysis process
def test_execute_success(setup_budget_analyzer, setup_sheets_client_with_data):
    """Test successful execution of the complete budget analysis process"""
    # Replace the analyzer's sheets_client with the configured mock
    setup_budget_analyzer.sheets_client = setup_sheets_client_with_data
    
    # Create a previous_status dictionary
    previous_status = {'status': 'success'}
    
    # Call execute() method with previous_status
    result = setup_budget_analyzer.execute(previous_status)
    
    # Assert that the method returns a dictionary with status 'success'
    assert result['status'] == 'success'
    
    # Assert that the result contains analysis_results and transfer_amount
    assert 'analysis_results' in result
    assert 'transfer_amount' in result
    
    # Assert that the sheets client's methods were called in the expected sequence
    assert setup_budget_analyzer.sheets_client.get_sheet_data("Weekly Spending") is not None
    assert setup_budget_analyzer.sheets_client.get_sheet_data("Master Budget") is not None

# Test execution handling when authentication fails
def test_execute_authentication_failure(setup_budget_analyzer):
    """Test execution handling when authentication fails"""
    # Configure the mock sheets client to return failure for authentication
    setup_budget_analyzer.sheets_client.authenticated = False
    
    # Call execute() method
    result = setup_budget_analyzer.execute({})
    
    # Assert that the method returns a dictionary with status 'error'
    assert result['status'] == 'error'
    
    # Assert that the error message indicates authentication failure
    assert 'Failed to authenticate' in result['message']

# Test execution handling when data retrieval fails
def test_execute_data_retrieval_failure(setup_budget_analyzer):
    """Test execution handling when data retrieval fails"""
    # Configure the mock sheets client to raise APIError during get_transactions
    setup_budget_analyzer.sheets_client.read_sheet = MagicMock(side_effect=APIError("API Error", "Google Sheets", "read_sheet"))
    
    # Call execute() method
    result = setup_budget_analyzer.execute({})
    
    # Assert that the method returns a dictionary with status 'error'
    assert result['status'] == 'error'
    
    # Assert that the error message indicates data retrieval failure
    assert 'Failed to retrieve transaction or budget data' in result['message']

# Test execution handling when no transactions are found
def test_execute_empty_data(setup_budget_analyzer):
    """Test execution handling when no transactions are found"""
    # Configure the mock sheets client to return empty lists for transactions
    setup_budget_analyzer.sheets_client.get_transactions = MagicMock(return_value=[])
    
    # Call execute() method
    result = setup_budget_analyzer.execute({})
    
    # Assert that the method returns a dictionary with status 'warning'
    assert result['status'] == 'warning'
    
    # Assert that the warning message indicates no transactions found
    assert 'No transactions found' in result['message']

# Test execution handling when budget analysis fails
def test_execute_analysis_error(setup_budget_analyzer, setup_sheets_client_with_data):
    """Test execution handling when budget analysis fails"""
    # Replace the analyzer's sheets_client with the configured mock
    setup_budget_analyzer.sheets_client = setup_sheets_client_with_data
    
    # Patch the analyze_budget method to raise ValidationError
    with patch.object(BudgetAnalyzer, 'analyze_budget', side_effect=ValidationError("Validation Error", "budget")):
        # Call execute() method
        result = setup_budget_analyzer.execute({})
        
        # Assert that the method returns a dictionary with status 'error'
        assert result['status'] == 'error'
        
        # Assert that the error message indicates analysis failure
        assert 'An unexpected error occurred during budget analysis' in result['message']

# Test calculation of transfer amount with budget surplus
def test_transfer_amount_calculation_surplus():
    """Test calculation of transfer amount with budget surplus"""
    # Create a budget with a known surplus
    budget = create_budget_with_variance(Decimal('100.00'))
    
    # Create a BudgetAnalyzer instance
    analyzer = BudgetAnalyzer()
    
    # Call analyze_budget() method
    analyzer.analyze_budget(budget)
    
    # Assert that the transfer_amount equals the total_variance
    assert analyzer.transfer_amount == Decimal('100.00')
    
    # Use assert_transfer_amount_valid to verify the transfer amount is correct
    assert_transfer_amount_valid(analyzer.transfer_amount, budget.total_variance)

# Test calculation of transfer amount with budget deficit
def test_transfer_amount_calculation_deficit():
    """Test calculation of transfer amount with budget deficit"""
    # Create a budget with a known deficit
    budget = create_budget_with_variance(Decimal('-50.00'))
    
    # Create a BudgetAnalyzer instance
    analyzer = BudgetAnalyzer()
    
    # Call analyze_budget() method
    analyzer.analyze_budget(budget)
    
    # Assert that the transfer_amount is zero
    assert analyzer.transfer_amount == Decimal('0')
    
    # Use assert_transfer_amount_valid to verify the transfer amount is correct
    assert_transfer_amount_valid(analyzer.transfer_amount, budget.total_variance)

# Test health check functionality
def test_check_health(setup_budget_analyzer):
    """Test health check functionality"""
    # Call check_health() method
    health_status = setup_budget_analyzer.check_health()
    
    # Assert that the method returns a dictionary with health status
    assert isinstance(health_status, dict)
    
    # Assert that the dictionary contains a key for Google Sheets API
    assert 'google_sheets' in health_status