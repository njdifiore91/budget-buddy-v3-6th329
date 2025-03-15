import pytest  # pytest 7.4.0+
from decimal import Decimal  # standard library

# Internal imports
from ..conftest import mock_capital_one_client, budget_with_surplus, budget_with_deficit  # src/backend/tests/conftest.py
from ..conftest import create_budget_with_surplus, create_budget_with_deficit  # src/backend/tests/conftest.py
from ...components.budget_analyzer import BudgetAnalyzer  # src/backend/components/budget_analyzer.py
from ...components.savings_automator import SavingsAutomator  # src/backend/components/savings_automator.py
from ...models.transfer import Transfer  # src/backend/models/transfer.py


def test_savings_flow_with_surplus(mock_capital_one_client):
    """Tests the complete savings flow when there is a budget surplus"""
    # Step 1: Create a budget with surplus using create_budget_with_surplus
    budget = create_budget_with_surplus()

    # Step 2: Set up mock_capital_one_client with sufficient account balance
    mock_capital_one_client.set_account_balance(
        mock_capital_one_client.checking_account_id, Decimal("2000.00")
    )

    # Step 3: Create a BudgetAnalyzer instance with the mock client
    budget_analyzer = BudgetAnalyzer(sheets_client=None)

    # Step 4: Execute the budget analysis to calculate surplus
    analysis_results = budget_analyzer.analyze_budget(budget)

    # Step 5: Create a SavingsAutomator instance with the mock client
    savings_automator = SavingsAutomator(capital_one_client=mock_capital_one_client)

    # Step 6: Execute the savings automation with the budget analysis results
    transfer_result = savings_automator.transfer_surplus(analysis_results['total_variance'])

    # Step 7: Verify that a transfer was initiated
    assert mock_capital_one_client.transfer_initiated is True

    # Step 8: Verify that the transfer amount matches the budget surplus
    assert mock_capital_one_client.transfer_amount == budget.total_variance

    # Step 9: Verify that the transfer was completed successfully
    assert transfer_result.get('status') == 'success'


def test_savings_flow_with_deficit(mock_capital_one_client):
    """Tests the savings flow when there is a budget deficit (no transfer should occur)"""
    # Step 1: Create a budget with deficit using create_budget_with_deficit
    budget = create_budget_with_deficit()

    # Step 2: Set up mock_capital_one_client with account balance
    mock_capital_one_client.set_account_balance(
        mock_capital_one_client.checking_account_id, Decimal("2000.00")
    )

    # Step 3: Create a BudgetAnalyzer instance with the mock client
    budget_analyzer = BudgetAnalyzer(sheets_client=None)

    # Step 4: Execute the budget analysis to calculate deficit
    analysis_results = budget_analyzer.analyze_budget(budget)

    # Step 5: Create a SavingsAutomator instance with the mock client
    savings_automator = SavingsAutomator(capital_one_client=mock_capital_one_client)

    # Step 6: Execute the savings automation with the budget analysis results
    transfer_result = savings_automator.transfer_surplus(analysis_results['total_variance'])

    # Step 7: Verify that no transfer was initiated (transfer_initiated should be False)
    assert mock_capital_one_client.transfer_initiated is False

    # Step 8: Verify that the transfer amount is zero
    assert transfer_result.get('status') == 'no_transfer'


def test_savings_flow_with_api_error(mock_capital_one_client):
    """Tests the savings flow error handling when the Capital One API fails"""
    # Step 1: Create a budget with surplus using create_budget_with_surplus
    budget = create_budget_with_surplus()

    # Step 2: Set up mock_capital_one_client with sufficient account balance
    mock_capital_one_client.set_account_balance(
        mock_capital_one_client.checking_account_id, Decimal("2000.00")
    )

    # Step 3: Set API error flag on mock_capital_one_client
    mock_capital_one_client.set_api_error(True)

    # Step 4: Create a BudgetAnalyzer instance with the mock client
    budget_analyzer = BudgetAnalyzer(sheets_client=None)

    # Step 5: Execute the budget analysis to calculate surplus
    analysis_results = budget_analyzer.analyze_budget(budget)

    # Step 6: Create a SavingsAutomator instance with the mock client
    savings_automator = SavingsAutomator(capital_one_client=mock_capital_one_client)

    # Step 7: Execute the savings automation with the budget analysis results
    transfer_result = savings_automator.transfer_surplus(analysis_results['total_variance'])

    # Step 8: Verify that the execution status indicates an error
    assert transfer_result.get('status') == 'error'

    # Step 9: Verify that no transfer was initiated
    assert mock_capital_one_client.transfer_initiated is False


def test_savings_flow_with_insufficient_funds(mock_capital_one_client):
    """Tests the savings flow when there are insufficient funds in the checking account"""
    # Step 1: Create a budget with surplus using create_budget_with_surplus
    budget = create_budget_with_surplus()

    # Step 2: Set up mock_capital_one_client with insufficient account balance (less than surplus)
    mock_capital_one_client.set_account_balance(
        mock_capital_one_client.checking_account_id, Decimal("10.00")
    )

    # Step 3: Create a BudgetAnalyzer instance with the mock client
    budget_analyzer = BudgetAnalyzer(sheets_client=None)

    # Step 4: Execute the budget analysis to calculate surplus
    analysis_results = budget_analyzer.analyze_budget(budget)

    # Step 5: Create a SavingsAutomator instance with the mock client
    savings_automator = SavingsAutomator(capital_one_client=mock_capital_one_client)

    # Step 6: Execute the savings automation with the budget analysis results
    transfer_result = savings_automator.transfer_surplus(analysis_results['total_variance'])

    # Step 7: Verify that the execution status indicates an error
    assert transfer_result.get('status') == 'error'

    # Step 8: Verify that no transfer was initiated
    assert mock_capital_one_client.transfer_initiated is False


def test_direct_transfer_surplus_method(mock_capital_one_client):
    """Tests the transfer_surplus method directly without going through execute"""
    # Step 1: Set up mock_capital_one_client with sufficient account balance
    mock_capital_one_client.set_account_balance(
        mock_capital_one_client.checking_account_id, Decimal("2000.00")
    )

    # Step 2: Create a SavingsAutomator instance with the mock client
    savings_automator = SavingsAutomator(capital_one_client=mock_capital_one_client)

    # Step 3: Call transfer_surplus method directly with a specific amount
    transfer_amount = Decimal("50.00")
    transfer_result = savings_automator.transfer_surplus(transfer_amount)

    # Step 4: Verify that a transfer was initiated
    assert mock_capital_one_client.transfer_initiated is True

    # Step 5: Verify that the transfer amount matches the specified amount
    assert mock_capital_one_client.transfer_amount == transfer_amount

    # Step 6: Verify that the transfer result contains the expected status and details
    assert transfer_result.get('status') == 'success'
    assert transfer_result.get('amount') == str(transfer_amount)


def test_end_to_end_savings_flow(mock_capital_one_client):
    """Tests the complete end-to-end savings flow from budget analysis to transfer"""
    # Step 1: Create a budget with surplus using create_budget_with_surplus
    budget = create_budget_with_surplus()

    # Step 2: Set up mock_capital_one_client with sufficient account balance
    mock_capital_one_client.set_account_balance(
        mock_capital_one_client.checking_account_id, Decimal("2000.00")
    )

    # Step 3: Create a BudgetAnalyzer instance with the mock client
    budget_analyzer = BudgetAnalyzer(sheets_client=None)

    # Step 4: Execute the budget analysis to calculate surplus
    analysis_results = budget_analyzer.analyze_budget(budget)

    # Step 5: Create a SavingsAutomator instance with the mock client
    savings_automator = SavingsAutomator(capital_one_client=mock_capital_one_client)

    # Step 6: Execute the savings automation with the budget analysis results
    transfer_result = savings_automator.transfer_surplus(analysis_results['total_variance'])

    # Step 7: Verify that a transfer was initiated
    assert mock_capital_one_client.transfer_initiated is True

    # Step 8: Verify that the transfer amount matches the budget surplus
    assert mock_capital_one_client.transfer_amount == budget.total_variance

    # Step 9: Verify that the execution status indicates success
    assert transfer_result.get('status') == 'success'

    # Step 10: Verify that the transfer was completed successfully
    assert transfer_result.get('verified') is True

    # Step 11: Verify that the account balances were updated correctly
    expected_checking_balance = Decimal("2000.00") - budget.total_variance
    assert Decimal(mock_capital_one_client.accounts[mock_capital_one_client.checking_account_id]['balance']) == expected_checking_balance