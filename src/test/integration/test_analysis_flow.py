import pytest
from decimal import Decimal
from typing import List, Dict, Any

from src.backend.components.budget_analyzer import BudgetAnalyzer
from src.test.mocks.google_sheets_client import MockGoogleSheetsClient
from src.backend.models.budget import Budget
from src.test.utils.fixture_loader import load_fixture, load_budget_fixture, load_transaction_fixture, load_expected_result_fixture
from src.test.utils.assertion_helpers import assert_budget_variance_correct, assert_transfer_amount_valid, assert_dict_subset
from src.test.utils.assertion_helpers import BudgetAssertions


@pytest.fixture
def budget_analyzer_fixture():
    """Pytest fixture that provides a configured BudgetAnalyzer instance with mock dependencies"""
    mock_sheets_client = MockGoogleSheetsClient()
    weekly_spending_data = load_fixture("sheets/weekly_spending.json")
    master_budget_data = load_fixture("sheets/master_budget.json")
    mock_sheets_client.set_sheet_data("Weekly Spending", weekly_spending_data)
    mock_sheets_client.set_sheet_data("Master Budget", master_budget_data)
    budget_analyzer = BudgetAnalyzer(sheets_client=mock_sheets_client)
    return budget_analyzer


def test_budget_analyzer_authentication(budget_analyzer_fixture):
    """Test that BudgetAnalyzer can authenticate with Google Sheets API"""
    budget_analyzer = budget_analyzer_fixture
    budget_analyzer.authenticate()
    assert budget_analyzer.sheets_client.authenticated
    sheets_client = budget_analyzer.sheets_client
    assert sheets_client.authenticated is True


def test_budget_analyzer_authentication_failure():
    """Test that BudgetAnalyzer handles authentication failures correctly"""
    mock_sheets_client = MockGoogleSheetsClient(authentication_should_fail=True)
    budget_analyzer = BudgetAnalyzer(sheets_client=mock_sheets_client)
    result = budget_analyzer.authenticate()
    assert result is False
    assert budget_analyzer.sheets_client.authenticated is False


def test_get_transactions_and_budget(budget_analyzer_fixture):
    """Test that BudgetAnalyzer can retrieve transactions and budget data"""
    budget_analyzer = budget_analyzer_fixture
    budget_analyzer.authenticate()
    transactions, budget = budget_analyzer.get_transactions_and_budget()
    assert isinstance(transactions, list)
    assert isinstance(budget, Budget)
    assert len(transactions) > 0
    assert len(budget.categories) > 0


def test_analyze_budget(budget_analyzer_fixture):
    """Test that BudgetAnalyzer can analyze budget data correctly"""
    budget_analyzer = budget_analyzer_fixture
    budget_analyzer.authenticate()
    transactions, budget = budget_analyzer.get_transactions_and_budget()
    budget = budget
    analysis_results = budget_analyzer.analyze_budget(budget)
    assert isinstance(analysis_results, dict)
    assert 'total_budget' in analysis_results
    assert 'total_spent' in analysis_results
    assert 'total_variance' in analysis_results
    BudgetAssertions.assert_variance_calculation(budget)
    expected_budget_analysis = load_expected_result_fixture("budget_analysis_results")
    assert_dict_subset(analysis_results, expected_budget_analysis)


def test_budget_variance_calculation(budget_analyzer_fixture):
    """Test that budget variance calculations are mathematically correct"""
    budget_analyzer = budget_analyzer_fixture
    budget_analyzer.authenticate()
    transactions, budget = budget_analyzer.get_transactions_and_budget()
    budget.analyze()
    assert budget.is_analyzed is True
    assert_budget_variance_correct(budget)
    total_budget = sum(category.weekly_amount for category in budget.categories)
    total_spent = sum(budget.actual_spending.values())
    total_variance = total_budget - total_spent
    assert budget.total_budget == total_budget
    assert budget.total_spent == total_spent
    assert budget.total_variance == total_variance
    for category in budget.categories:
        category_name = category.name
        budget_amount = category.weekly_amount
        actual_amount = budget.actual_spending.get(category_name, Decimal('0'))
        expected_variance = budget_amount - actual_amount
        assert category.name in budget.category_variances
        assert budget.category_variances[category_name] == expected_variance


def test_transfer_amount_calculation(budget_analyzer_fixture):
    """Test that transfer amount is correctly calculated based on budget surplus"""
    budget_analyzer = budget_analyzer_fixture
    budget_analyzer.authenticate()
    transactions, budget = budget_analyzer.get_transactions_and_budget()
    budget.analyze()
    transfer_amount = budget.get_transfer_amount()
    expected_budget_analysis = load_expected_result_fixture("budget_analysis_results")
    expected_transfer_amount = expected_budget_analysis.get('transfer_amount')
    assert_transfer_amount_valid(transfer_amount, budget.total_variance)
    if budget.total_variance > 0:
        assert transfer_amount == budget.total_variance
    else:
        assert transfer_amount == 0


def test_execute_end_to_end(budget_analyzer_fixture):
    """Test the complete budget analysis flow from end to end"""
    budget_analyzer = budget_analyzer_fixture
    previous_status = {'correlation_id': 'test_correlation_id'}
    result = budget_analyzer.execute(previous_status)
    assert result['status'] == 'success'
    assert 'analysis_results' in result
    assert 'transfer_amount' in result
    expected_budget_analysis = load_expected_result_fixture("budget_analysis_results")
    assert_dict_subset(result['analysis_results'], expected_budget_analysis)
    assert result['correlation_id'] == 'test_correlation_id'


def test_execute_with_empty_data():
    """Test that BudgetAnalyzer handles empty data gracefully"""
    mock_sheets_client = MockGoogleSheetsClient()
    mock_sheets_client.set_sheet_data("Weekly Spending", [])
    mock_sheets_client.set_sheet_data("Master Budget", [])
    budget_analyzer = BudgetAnalyzer(sheets_client=mock_sheets_client)
    result = budget_analyzer.execute({})
    assert result['status'] != 'success'
    assert 'error' in result['message'].lower()


def test_execute_with_authentication_failure():
    """Test that BudgetAnalyzer handles authentication failures during execution"""
    mock_sheets_client = MockGoogleSheetsClient(authentication_should_fail=True)
    budget_analyzer = BudgetAnalyzer(sheets_client=mock_sheets_client)
    result = budget_analyzer.execute({})
    assert result['status'] != 'success'
    assert 'authentication' in result['message'].lower()