import pytest  # pytest 7.4.0+
from decimal import Decimal  # standard library
from typing import Dict, List, Any  # standard library

from src.backend.components.budget_analyzer import BudgetAnalyzer  # Internal import
from src.backend.components.savings_automator import SavingsAutomator  # Internal import
from src.test.mocks.capital_one_client import MockCapitalOneClient  # Internal import
from src.test.utils.fixture_loader import load_fixture  # Internal import
from src.test.utils.assertion_helpers import assert_transfer_amount_valid, assert_dict_subset  # Internal import

BUDGET_FIXTURE_PATH = "json/budget/master_budget.json"  # Global variable
TRANSACTION_FIXTURE_PATH = "json/transactions/valid_transactions.json"  # Global variable
EXPECTED_TRANSFER_FIXTURE_PATH = "json/expected/transfer_result.json"  # Global variable
MIN_TRANSFER_AMOUNT = Decimal('1.00')  # Global variable


@pytest.fixture
def setup_budget_analyzer() -> BudgetAnalyzer:
    """
    Pytest fixture that sets up a BudgetAnalyzer instance with mock data
    
    Returns:
        Configured BudgetAnalyzer instance
    """
    # Load budget fixture data using load_fixture with BUDGET_FIXTURE_PATH
    budget_data = load_fixture(BUDGET_FIXTURE_PATH)
    # Load transaction fixture data using load_fixture with TRANSACTION_FIXTURE_PATH
    transaction_data = load_fixture(TRANSACTION_FIXTURE_PATH)
    # Create a BudgetAnalyzer instance
    budget_analyzer = BudgetAnalyzer()
    # Mock the get_transactions_and_budget method to return the fixture data
    budget_analyzer.get_transactions_and_budget = lambda: (transaction_data, budget_data)
    # Return the configured BudgetAnalyzer instance
    return budget_analyzer


@pytest.fixture
def setup_capital_one_client() -> MockCapitalOneClient:
    """
    Pytest fixture that sets up a MockCapitalOneClient instance
    
    Returns:
        Configured MockCapitalOneClient instance
    """
    # Create a MockCapitalOneClient instance
    capital_one_client = MockCapitalOneClient()
    # Configure the mock client with appropriate test data
    capital_one_client.authenticate = lambda: True  # Mock successful authentication
    # Return the configured MockCapitalOneClient instance
    return capital_one_client


@pytest.fixture
def setup_savings_automator(capital_one_client: MockCapitalOneClient) -> SavingsAutomator:
    """
    Pytest fixture that sets up a SavingsAutomator instance with mock client
    
    Args:
        capital_one_client: 
    
    Returns:
        Configured SavingsAutomator instance
    """
    # Create a SavingsAutomator instance with the provided capital_one_client
    savings_automator = SavingsAutomator(capital_one_client=capital_one_client)
    # Return the configured SavingsAutomator instance
    return savings_automator


def test_successful_savings_transfer(setup_budget_analyzer: BudgetAnalyzer, setup_savings_automator: SavingsAutomator):
    """
    Test successful transfer of budget surplus to savings account
    """
    # Arrange
    budget_analyzer = setup_budget_analyzer
    savings_automator = setup_savings_automator
    
    # Mock budget analysis results with a surplus
    budget_analyzer.transfer_amount = Decimal('100.00')
    budget_analyzer.validate_transfer_amount = lambda amount: True
    savings_automator.verify_account_status = lambda: True
    savings_automator.verify_sufficient_funds = lambda amount: True
    savings_automator.initiate_transfer = lambda amount: {"status": "success", "transfer_id": "test_transfer_id"}
    savings_automator.verify_transfer = lambda transfer_id: True
    
    # Act
    transfer_result = savings_automator.transfer_surplus(budget_analyzer.transfer_amount)
    
    # Assert
    assert transfer_result["status"] == "success"
    assert transfer_result["transfer_id"] == "test_transfer_id"
    assert transfer_result["verified"] is True


def test_no_transfer_when_no_surplus(setup_budget_analyzer: BudgetAnalyzer, setup_savings_automator: SavingsAutomator):
    """
    Test that no transfer occurs when there is no budget surplus
    """
    # Arrange
    budget_analyzer = setup_budget_analyzer
    savings_automator = setup_savings_automator
    
    # Mock budget analysis results with no surplus
    budget_analyzer.transfer_amount = Decimal('0.00')
    
    # Act
    transfer_result = savings_automator.transfer_surplus(budget_analyzer.transfer_amount)
    
    # Assert
    assert transfer_result["status"] == "no_transfer"
    assert transfer_result["reason"] == "Invalid transfer amount"


def test_no_transfer_when_surplus_below_minimum(setup_budget_analyzer: BudgetAnalyzer, setup_savings_automator: SavingsAutomator):
    """
    Test that no transfer occurs when surplus is below minimum transfer amount
    """
    # Arrange
    budget_analyzer = setup_budget_analyzer
    savings_automator = setup_savings_automator
    
    # Mock budget analysis results with surplus below minimum
    budget_analyzer.transfer_amount = Decimal('0.50')
    
    # Act
    transfer_result = savings_automator.transfer_surplus(budget_analyzer.transfer_amount)
    
    # Assert
    assert transfer_result["status"] == "no_transfer"
    assert transfer_result["reason"] == "Invalid transfer amount"


def test_authentication_failure(setup_budget_analyzer: BudgetAnalyzer, setup_savings_automator: SavingsAutomator, setup_capital_one_client: MockCapitalOneClient):
    """
    Test handling of authentication failure with Capital One API
    """
    # Arrange
    budget_analyzer = setup_budget_analyzer
    savings_automator = setup_savings_automator
    capital_one_client = setup_capital_one_client
    
    # Mock authentication failure
    capital_one_client.set_should_fail_authentication(True)
    
    # Act
    transfer_result = savings_automator.transfer_surplus(budget_analyzer.transfer_amount)
    
    # Assert
    assert transfer_result["status"] == "error"
    assert "Authentication failed" in transfer_result["error_message"]


def test_account_status_failure(setup_budget_analyzer: BudgetAnalyzer, setup_savings_automator: SavingsAutomator, setup_capital_one_client: MockCapitalOneClient):
    """
    Test handling of account status retrieval failure
    """
    # Arrange
    budget_analyzer = setup_budget_analyzer
    savings_automator = setup_savings_automator
    capital_one_client = setup_capital_one_client
    
    # Mock account status retrieval failure
    capital_one_client.set_should_fail_accounts(True)
    
    # Act
    transfer_result = savings_automator.transfer_surplus(budget_analyzer.transfer_amount)
    
    # Assert
    assert transfer_result["status"] == "error"
    assert "Account status verification failed" in transfer_result["error_message"]


def test_transfer_failure(setup_budget_analyzer: BudgetAnalyzer, setup_savings_automator: SavingsAutomator, setup_capital_one_client: MockCapitalOneClient):
    """
    Test handling of transfer initiation failure
    """
    # Arrange
    budget_analyzer = setup_budget_analyzer
    savings_automator = setup_savings_automator
    capital_one_client = setup_capital_one_client
    
    # Mock transfer initiation failure
    capital_one_client.set_should_fail_transfers(True)
    
    # Act
    transfer_result = savings_automator.transfer_surplus(budget_analyzer.transfer_amount)
    
    # Assert
    assert transfer_result["status"] == "error"
    assert "transfer" in transfer_result["error_message"].lower()


def test_end_to_end_savings_flow(setup_budget_analyzer: BudgetAnalyzer, setup_savings_automator: SavingsAutomator, setup_capital_one_client: MockCapitalOneClient):
    """
    Test the complete end-to-end flow from budget analysis to savings transfer
    """
    # Arrange
    budget_analyzer = setup_budget_analyzer
    savings_automator = setup_savings_automator
    capital_one_client = setup_capital_one_client
    
    # Set a known transfer amount
    budget_analyzer.transfer_amount = Decimal('50.00')
    
    # Act
    transfer_result = savings_automator.transfer_surplus(budget_analyzer.transfer_amount)
    
    # Assert
    assert transfer_result["status"] == "success"
    assert transfer_result["transfer_result"]["transferId"] == "transfer123"
    assert transfer_result["transfer_result"]["status"] == "completed"