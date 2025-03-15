"""
Unit tests for the BudgetAnalyzer component, which is responsible for comparing
actual spending to budgeted amounts, calculating variances, and determining the 
overall budget status.
"""

import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal

from ...components.budget_analyzer import BudgetAnalyzer
from ...models.budget import Budget
from ...utils.error_handlers import APIError, ValidationError
from ..mocks.mock_google_sheets_client import MockGoogleSheetsClient
from ..fixtures.budget import (
    create_test_budget, create_analyzed_budget, create_budget_with_surplus,
    create_budget_with_deficit, get_expected_analysis_results
)
from ..fixtures.transactions import create_categorized_transactions


class TestBudgetAnalyzer:
    """Test class for BudgetAnalyzer component"""
    
    def setup_method(self, method):
        """Set up test fixtures before each test method"""
        # Create a mock GoogleSheetsClient
        self.mock_client = MockGoogleSheetsClient()
        
        # Create test transactions and budget data
        self.test_transactions = create_categorized_transactions()
        self.test_budget_data = create_test_budget().to_dict()
        
        # Set up the mock client with test data
        self.mock_client.set_sheet_data("Weekly Spending", [
            [transaction.location, str(transaction.amount), str(transaction.timestamp), transaction.category]
            for transaction in self.test_transactions
        ])
        self.mock_client.set_sheet_data("Master Budget", [
            [category, amount] for category, amount in self.test_budget_data.get('category_analysis', {}).items()
        ])
        
        # Create a BudgetAnalyzer with the mock client
        self.analyzer = BudgetAnalyzer(sheets_client=self.mock_client)
    
    def test_init(self):
        """Test initialization of BudgetAnalyzer"""
        # Verify that sheets_client is correctly assigned
        assert self.analyzer.sheets_client == self.mock_client
        
        # Verify that correlation_id is initialized to None
        assert self.analyzer.correlation_id is None
        
        # Verify that budget is initialized to None
        assert self.analyzer.budget is None
        
        # Verify that category_totals is initialized to empty dictionary
        assert self.analyzer.category_totals == {}
        
        # Verify that transfer_amount is initialized to Decimal('0')
        assert self.analyzer.transfer_amount == Decimal('0')
    
    def test_authenticate(self):
        """Test authentication with Google Sheets API"""
        # Call authenticate method
        result = self.analyzer.authenticate()
        # Verify that it returns True
        assert result is True
        
        # Set mock client's auth_success to False
        self.mock_client.auth_success = False
        # Call authenticate method again
        result = self.analyzer.authenticate()
        # Verify that it returns False
        assert result is False
    
    def test_get_transactions_and_budget(self):
        """Test retrieval of transactions and budget data"""
        # Call get_transactions_and_budget method
        transactions, budget = self.analyzer.get_transactions_and_budget()
        
        # Verify that it returns a tuple of (transactions, budget)
        assert isinstance(transactions, list)
        assert isinstance(budget, Budget)
        
        # Verify that transactions list is not empty
        assert len(transactions) > 0
        
        # Verify that budget is a Budget object
        assert isinstance(budget, Budget)
        
        # Verify that category_totals is populated
        assert len(self.analyzer.category_totals) > 0
    
    def test_analyze_budget(self):
        """Test budget analysis functionality"""
        # Create a test budget
        test_budget = create_test_budget()
        
        # Call analyze_budget method with the test budget
        analysis_results = self.analyzer.analyze_budget(test_budget)
        
        # Verify that analysis results match expected values
        expected_results = get_expected_analysis_results()
        assert analysis_results['total_budget'] == expected_results['total_budget']
        assert analysis_results['total_spent'] == expected_results['total_spent']
        assert analysis_results['total_variance'] == expected_results['total_variance']
        assert analysis_results['is_surplus'] == expected_results['is_surplus']
        
        # Verify that transfer_amount is calculated correctly
        if analysis_results['total_variance'] > 0:
            assert self.analyzer.transfer_amount > 0
        else:
            assert self.analyzer.transfer_amount == Decimal('0')
    
    def test_format_analysis_results(self):
        """Test formatting of analysis results"""
        # Create a test budget and analyze it
        test_budget = create_analyzed_budget()
        analysis_results = test_budget.to_dict()
        
        # Call format_analysis_results with the analysis results
        formatted_results = self.analyzer.format_analysis_results(analysis_results)
        
        # Verify that formatted results contain all required fields
        assert 'total_budget' in formatted_results
        assert 'total_spent' in formatted_results
        assert 'total_variance' in formatted_results
        assert 'category_variances' in formatted_results
        assert 'transfer_amount' in formatted_results
        assert 'budget_status' in formatted_results
        
        # Verify that budget_status is correct based on total_variance
        if analysis_results['total_variance'] > 0:
            assert formatted_results['budget_status'] == 'surplus'
        else:
            assert formatted_results['budget_status'] == 'deficit'
    
    def test_execute_success(self):
        """Test successful execution of the complete process"""
        # Call execute method with empty previous_status
        result = self.analyzer.execute({})
        
        # Verify that result contains 'status': 'success'
        assert result['status'] == 'success'
        
        # Verify that result contains expected analysis data
        assert 'analysis_results' in result
        assert 'transfer_amount' in result
        
        # Verify that execution_time is included
        assert 'execution_time' in result
    
    def test_execute_with_correlation_id(self):
        """Test execution with correlation ID passed from previous component"""
        # Create previous_status with correlation_id
        previous_status = {'correlation_id': 'test-correlation-id'}
        
        # Call execute method with this previous_status
        result = self.analyzer.execute(previous_status)
        
        # Verify that correlation_id is preserved in the result
        assert result['correlation_id'] == 'test-correlation-id'
    
    def test_execute_api_error(self):
        """Test execution with API errors"""
        # Set mock client to raise API errors
        self.mock_client.set_api_error(True)
        
        # Call execute method
        result = self.analyzer.execute({})
        
        # Verify that result contains 'status': 'error'
        assert result['status'] == 'error'
        
        # Verify that error details are included
        assert 'message' in result
    
    def test_check_health(self):
        """Test health check functionality"""
        # Call check_health method
        result = self.analyzer.check_health()
        
        # Verify that result contains health status for Google Sheets
        assert 'google_sheets' in result
        assert result['google_sheets'] == 'healthy'
        
        # Set mock client to raise API errors
        self.mock_client.set_api_error(True)
        
        # Call check_health method again
        result = self.analyzer.check_health()
        
        # Verify that result indicates unhealthy status
        assert result['google_sheets'] == 'unhealthy'


# Standalone tests

def test_budget_analyzer_init():
    """Test BudgetAnalyzer initialization with default and custom parameters"""
    # Create a BudgetAnalyzer with default parameters
    analyzer = BudgetAnalyzer()
    
    # Verify that sheets_client and auth_service are initialized
    assert analyzer.sheets_client is not None
    assert analyzer.auth_service is not None
    
    # Create a mock GoogleSheetsClient
    mock_client = MockGoogleSheetsClient()
    
    # Create a BudgetAnalyzer with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Verify that the provided sheets_client is used
    assert analyzer.sheets_client == mock_client


def test_authenticate_success():
    """Test successful authentication with Google Sheets API"""
    # Create a mock GoogleSheetsClient with auth_success=True
    mock_client = MockGoogleSheetsClient(auth_success=True)
    
    # Create a BudgetAnalyzer with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Call authenticate method
    result = analyzer.authenticate()
    
    # Verify that authentication returns True
    assert result is True


def test_authenticate_failure():
    """Test failed authentication with Google Sheets API"""
    # Create a mock GoogleSheetsClient with auth_success=False
    mock_client = MockGoogleSheetsClient(auth_success=False)
    
    # Create a BudgetAnalyzer with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Call authenticate method
    result = analyzer.authenticate()
    
    # Verify that authentication returns False
    assert result is False


def test_get_transactions_and_budget_success():
    """Test successful retrieval of transactions and budget data"""
    # Create a mock GoogleSheetsClient
    mock_client = MockGoogleSheetsClient()
    
    # Set up mock sheet data for Weekly Spending and Master Budget
    mock_client.set_sheet_data("Weekly Spending", [
        ["Grocery Store", "50.00", "2023-07-16T12:00:00.000Z", "Groceries"],
        ["Starbucks", "5.45", "2023-07-15T08:15:22.456Z", "Dining Out"],
        ["Amazon", "29.99", "2023-07-14T14:22:11.789Z", "Shopping"]
    ])
    
    mock_client.set_sheet_data("Master Budget", [
        ["Groceries", "100.00"],
        ["Dining Out", "50.00"],
        ["Shopping", "40.00"]
    ])
    
    # Create a BudgetAnalyzer with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Call get_transactions_and_budget method
    transactions, budget = analyzer.get_transactions_and_budget()
    
    # Verify that transactions and budget are returned correctly
    assert len(transactions) == 3
    assert isinstance(budget, Budget)
    
    # Verify that category_totals is calculated correctly
    assert analyzer.category_totals.get("Groceries") == Decimal("50.00")
    assert analyzer.category_totals.get("Dining Out") == Decimal("5.45")
    assert analyzer.category_totals.get("Shopping") == Decimal("29.99")


def test_get_transactions_and_budget_api_error():
    """Test handling of API errors during data retrieval"""
    # Create a mock GoogleSheetsClient with api_error=True
    mock_client = MockGoogleSheetsClient(api_error=True)
    
    # Create a BudgetAnalyzer with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Call get_transactions_and_budget method with pytest.raises(APIError)
    with pytest.raises(APIError):
        analyzer.get_transactions_and_budget()


def test_analyze_budget_success():
    """Test successful budget analysis with valid data"""
    # Create a test budget with known values
    test_budget = create_test_budget()
    
    # Create a BudgetAnalyzer
    analyzer = BudgetAnalyzer()
    
    # Call analyze_budget method with the test budget
    analysis_results = analyzer.analyze_budget(test_budget)
    
    # Verify that analysis results match expected values
    expected_results = get_expected_analysis_results()
    assert analysis_results['total_budget'] == expected_results['total_budget']
    assert analysis_results['total_spent'] == expected_results['total_spent']
    assert analysis_results['total_variance'] == expected_results['total_variance']
    
    # Verify that total_budget, total_spent, and total_variance are calculated correctly
    assert analysis_results['total_budget'] == sum(category.weekly_amount for category in test_budget.categories)
    assert analysis_results['total_spent'] == sum(test_budget.actual_spending.values())
    assert analysis_results['total_variance'] == analysis_results['total_budget'] - analysis_results['total_spent']
    
    # Verify that category_variances contains correct values
    for category in test_budget.categories:
        actual_spent = test_budget.actual_spending.get(category.name, Decimal('0'))
        expected_variance = category.weekly_amount - actual_spent
        assert category.name in analysis_results['category_variances']
        assert analysis_results['category_variances'][category.name] == expected_variance


@patch('src.backend.utils.validation.validate_calculation_results')
def test_analyze_budget_validation_error(mock_validate):
    """Test handling of validation errors during budget analysis"""
    # Mock validate_calculation_results to raise ValidationError
    mock_validate.side_effect = ValidationError("Validation failed", "calculation")
    
    # Create a test budget
    test_budget = create_test_budget()
    
    # Create a BudgetAnalyzer
    analyzer = BudgetAnalyzer()
    
    # Call analyze_budget method with pytest.raises(ValidationError)
    with pytest.raises(ValidationError):
        analyzer.analyze_budget(test_budget)


def test_format_analysis_results():
    """Test formatting of analysis results for reporting"""
    # Create a sample analysis results dictionary
    analysis_results = {
        'total_budget': Decimal('295.00'),
        'total_spent': Decimal('220.99'),
        'total_variance': Decimal('74.01'),
        'category_variances': {
            'Groceries': Decimal('24.68'),
            'Dining Out': Decimal('4.33'),
            'Transportation': Decimal('45.00')
        },
        'is_surplus': True
    }
    
    # Create a BudgetAnalyzer
    analyzer = BudgetAnalyzer()
    
    # Call format_analysis_results method
    formatted_results = analyzer.format_analysis_results(analysis_results)
    
    # Verify that formatted results contain expected keys
    assert 'total_budget' in formatted_results
    assert 'total_spent' in formatted_results
    assert 'total_variance' in formatted_results
    assert 'category_variances' in formatted_results
    assert 'transfer_amount' in formatted_results
    assert 'budget_status' in formatted_results
    
    # Verify that total_budget, total_spent, total_variance are included
    assert formatted_results['total_budget'] == Decimal('295.00')
    assert formatted_results['total_spent'] == Decimal('220.99')
    assert formatted_results['total_variance'] == Decimal('74.01')
    
    # Verify that category_variances is included
    assert formatted_results['category_variances'] == analysis_results['category_variances']
    
    # Verify that transfer_amount is included
    assert 'transfer_amount' in formatted_results
    
    # Verify that budget_status is 'surplus' or 'deficit' as expected
    assert formatted_results['budget_status'] == 'surplus'


def test_execute_success():
    """Test successful execution of the complete budget analysis process"""
    # Create a mock GoogleSheetsClient with test data
    mock_client = MockGoogleSheetsClient()
    mock_client.set_sheet_data("Weekly Spending", [
        ["Grocery Store", "50.00", "2023-07-16T12:00:00.000Z", "Groceries"],
        ["Starbucks", "5.45", "2023-07-15T08:15:22.456Z", "Dining Out"],
        ["Amazon", "29.99", "2023-07-14T14:22:11.789Z", "Shopping"]
    ])
    mock_client.set_sheet_data("Master Budget", [
        ["Groceries", "100.00"],
        ["Dining Out", "50.00"],
        ["Shopping", "40.00"]
    ])
    
    # Create a BudgetAnalyzer with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Call execute method with empty previous_status
    result = analyzer.execute({})
    
    # Verify that result contains 'status': 'success'
    assert result['status'] == 'success'
    
    # Verify that result contains analysis_results with expected data
    assert 'analysis_results' in result
    analysis_results = result['analysis_results']
    assert analysis_results['total_budget'] > 0
    assert analysis_results['total_spent'] > 0
    assert analysis_results['budget_status'] in ['surplus', 'deficit']
    
    # Verify that result contains transfer_amount
    assert 'transfer_amount' in result
    
    # Verify that result contains execution_time
    assert 'execution_time' in result


def test_execute_authentication_failure():
    """Test execution handling when authentication fails"""
    # Create a mock GoogleSheetsClient with auth_success=False
    mock_client = MockGoogleSheetsClient(auth_success=False)
    
    # Create a BudgetAnalyzer with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Call execute method
    result = analyzer.execute({})
    
    # Verify that result contains 'status': 'error'
    assert result['status'] == 'error'
    
    # Verify that result contains error message about authentication
    assert 'authentication' in result['message'].lower()


def test_execute_api_error():
    """Test execution handling when API calls fail"""
    # Create a mock GoogleSheetsClient with api_error=True
    mock_client = MockGoogleSheetsClient(api_error=True)
    
    # Create a BudgetAnalyzer with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Call execute method
    result = analyzer.execute({})
    
    # Verify that result contains 'status': 'error'
    assert result['status'] == 'error'
    
    # Verify that result contains error message about API failure
    assert 'failed to retrieve' in result['message'].lower()


def test_execute_empty_data():
    """Test execution handling when no transactions or budget data is found"""
    # Create a mock GoogleSheetsClient with empty sheet data
    mock_client = MockGoogleSheetsClient()
    mock_client.set_sheet_data("Weekly Spending", [])
    mock_client.set_sheet_data("Master Budget", [])
    
    # Create a BudgetAnalyzer with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Call execute method
    result = analyzer.execute({})
    
    # Verify that result contains 'status': 'warning'
    assert result['status'] == 'warning'
    
    # Verify that result contains warning message about empty data
    assert 'no transactions found' in result['message'].lower()


def test_execute_with_surplus():
    """Test execution with budget surplus scenario"""
    # Create a mock GoogleSheetsClient with data that will result in surplus
    mock_client = MockGoogleSheetsClient()
    mock_client.set_sheet_data("Weekly Spending", [
        ["Grocery Store", "50.00", "2023-07-16T12:00:00.000Z", "Groceries"],
        ["Starbucks", "5.45", "2023-07-15T08:15:22.456Z", "Dining Out"]
    ])
    mock_client.set_sheet_data("Master Budget", [
        ["Groceries", "100.00"],
        ["Dining Out", "50.00"]
    ])
    
    # Create a BudgetAnalyzer with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Call execute method
    result = analyzer.execute({})
    
    # Verify that result contains positive total_variance
    analysis_results = result['analysis_results']
    assert analysis_results['total_variance'] > 0
    
    # Verify that result contains positive transfer_amount
    assert result['transfer_amount'] > 0
    
    # Verify that budget_status is 'surplus'
    assert analysis_results['budget_status'] == 'surplus'


def test_execute_with_deficit():
    """Test execution with budget deficit scenario"""
    # Create a mock GoogleSheetsClient with data that will result in deficit
    mock_client = MockGoogleSheetsClient()
    mock_client.set_sheet_data("Weekly Spending", [
        ["Grocery Store", "150.00", "2023-07-16T12:00:00.000Z", "Groceries"],
        ["Starbucks", "75.45", "2023-07-15T08:15:22.456Z", "Dining Out"]
    ])
    mock_client.set_sheet_data("Master Budget", [
        ["Groceries", "100.00"],
        ["Dining Out", "50.00"]
    ])
    
    # Create a BudgetAnalyzer with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Call execute method
    result = analyzer.execute({})
    
    # Verify that result contains negative total_variance
    analysis_results = result['analysis_results']
    assert analysis_results['total_variance'] < 0
    
    # Verify that result contains zero transfer_amount
    assert result['transfer_amount'] == Decimal('0')
    
    # Verify that budget_status is 'deficit'
    assert analysis_results['budget_status'] == 'deficit'


def test_check_health():
    """Test health check functionality"""
    # Create a mock GoogleSheetsClient with test_connectivity returning True
    mock_client = MockGoogleSheetsClient()
    mock_client.test_connectivity = lambda: True
    
    # Create a BudgetAnalyzer with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Call check_health method
    result = analyzer.check_health()
    
    # Verify that result contains 'google_sheets': 'healthy'
    assert result['google_sheets'] == 'healthy'
    
    # Create a mock GoogleSheetsClient with test_connectivity returning False
    mock_client = MockGoogleSheetsClient()
    mock_client.test_connectivity = lambda: False
    
    # Create a BudgetAnalyzer with the mock client
    analyzer = BudgetAnalyzer(sheets_client=mock_client)
    
    # Call check_health method
    result = analyzer.check_health()
    
    # Verify that result contains 'google_sheets': 'unhealthy'
    assert result['google_sheets'] == 'unhealthy'