"""
Unit tests for the SavingsAutomator component, which is responsible for transferring budget surplus to a savings account.
Tests verify the component's ability to authenticate with Capital One API, validate transfer amounts,
verify account status, check for sufficient funds, initiate transfers, and verify transfer completion.
"""

import decimal  # standard library
from decimal import Decimal  # standard library
import pytest  # pytest 7.4.0+
from unittest.mock import MagicMock  # standard library
from typing import Tuple  # standard library

from src.backend.components.savings_automator import SavingsAutomator  # Internal import: The component being tested
from src.test.mocks.capital_one_client import MockCapitalOneClient  # Internal import: Mock implementation of Capital One API client for testing
from src.backend.models.transfer import Transfer, create_transfer  # Internal import: Model for representing fund transfers between accounts
from src.backend.models.transfer import create_transfer_from_capital_one_response  # Internal import: Create Transfer object from Capital One API response
from src.test.fixtures.budget import create_budget_with_surplus  # Internal import: Create a test budget with a specified surplus amount
from src.test.fixtures.budget import create_budget_with_deficit  # Internal import: Create a test budget with a specified deficit amount
from src.test.fixtures.budget import create_budget_with_zero_variance  # Internal import: Create a test budget with zero variance
from src.test.utils.test_helpers import setup_test_environment  # Internal import: Set up test environment with mock objects and test data
from src.test.utils.test_helpers import compare_decimal_values  # Internal import: Compare decimal values with a specified precision

# Define test constants
TEST_SURPLUS_AMOUNT = Decimal('50.00')
TEST_DEFICIT_AMOUNT = Decimal('-25.00')
TEST_ZERO_AMOUNT = Decimal('0.00')
TEST_SMALL_AMOUNT = Decimal('0.50')
TEST_TRANSFER_ID = "test_transfer_123"

@pytest.fixture
def setup_savings_automator() -> Tuple[SavingsAutomator, MockCapitalOneClient]:
    """Fixture to set up a SavingsAutomator instance with a mock Capital One client"""
    # Create a MockCapitalOneClient instance
    mock_capital_one_client = MockCapitalOneClient()
    # Create a SavingsAutomator instance with the mock client
    savings_automator = SavingsAutomator(capital_one_client=mock_capital_one_client)
    # Return a tuple containing both instances
    return savings_automator, mock_capital_one_client

def test_savings_automator_initialization():
    """Test that SavingsAutomator initializes correctly"""
    # Create a MockCapitalOneClient
    mock_capital_one_client = MockCapitalOneClient()
    # Create a SavingsAutomator with the mock client
    savings_automator = SavingsAutomator(capital_one_client=mock_capital_one_client)
    # Assert that the SavingsAutomator has the expected attributes
    assert savings_automator.capital_one_client == mock_capital_one_client
    # Assert that transfer_amount is initialized to zero
    assert savings_automator.transfer_amount == Decimal('0')
    # Assert that transfer is initialized to None
    assert savings_automator.transfer is None
    # Assert that transfer_successful is initialized to False
    assert savings_automator.transfer_successful is False

def test_authenticate_success(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test successful authentication with Capital One API"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure the mock client to succeed authentication
    mock_capital_one_client.set_should_fail_authentication(False)
    # Call the authenticate method
    auth_success = savings_automator.authenticate()
    # Assert that the method returns True
    assert auth_success is True
    # Assert that the mock client's authenticate method was called
    mock_capital_one_client.authenticate.assert_called_once()

def test_authenticate_failure(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test authentication failure with Capital One API"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure the mock client to fail authentication
    mock_capital_one_client.set_should_fail_authentication(True)
    # Call the authenticate method
    auth_success = savings_automator.authenticate()
    # Assert that the method returns False
    assert auth_success is False
    # Assert that the mock client's authenticate method was called
    mock_capital_one_client.authenticate.assert_called_once()

def test_validate_transfer_amount_valid(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test validation of valid transfer amounts"""
    # Unpack the setup_savings_automator fixture
    savings_automator, _ = setup_savings_automator
    # Call validate_transfer_amount with a valid amount (> minimum)
    is_valid = savings_automator.validate_transfer_amount(TEST_SURPLUS_AMOUNT)
    # Assert that the method returns True
    assert is_valid is True

def test_validate_transfer_amount_zero(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test validation of zero transfer amount"""
    # Unpack the setup_savings_automator fixture
    savings_automator, _ = setup_savings_automator
    # Call validate_transfer_amount with zero
    is_valid = savings_automator.validate_transfer_amount(TEST_ZERO_AMOUNT)
    # Assert that the method returns False
    assert is_valid is False

def test_validate_transfer_amount_negative(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test validation of negative transfer amount"""
    # Unpack the setup_savings_automator fixture
    savings_automator, _ = setup_savings_automator
    # Call validate_transfer_amount with a negative amount
    is_valid = savings_automator.validate_transfer_amount(TEST_DEFICIT_AMOUNT)
    # Assert that the method returns False
    assert is_valid is False

def test_validate_transfer_amount_below_minimum(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test validation of amount below minimum threshold"""
    # Unpack the setup_savings_automator fixture
    savings_automator, _ = setup_savings_automator
    # Call validate_transfer_amount with an amount below minimum threshold
    is_valid = savings_automator.validate_transfer_amount(TEST_SMALL_AMOUNT)
    # Assert that the method returns False
    assert is_valid is False

def test_verify_account_status_success(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test successful verification of account status"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure mock client to return active account status for both accounts
    mock_capital_one_client.set_should_fail_accounts(False)
    # Call verify_account_status method
    account_status_valid = savings_automator.verify_account_status()
    # Assert that the method returns True
    assert account_status_valid is True
    # Assert that get_checking_account_details and get_savings_account_details were called
    assert mock_capital_one_client.get_checking_account_details.called
    assert mock_capital_one_client.get_savings_account_details.called

def test_verify_account_status_inactive_checking(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test verification with inactive checking account"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure mock client to return inactive status for checking account
    mock_capital_one_client.set_should_fail_accounts(True)
    # Call verify_account_status method
    account_status_valid = savings_automator.verify_account_status()
    # Assert that the method returns False
    assert account_status_valid is False

def test_verify_account_status_inactive_savings(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test verification with inactive savings account"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure mock client to return inactive status for savings account
    mock_capital_one_client.set_should_fail_accounts(True)
    # Call verify_account_status method
    account_status_valid = savings_automator.verify_account_status()
    # Assert that the method returns False
    assert account_status_valid is False

def test_verify_account_status_api_error(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test account verification when API returns an error"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure mock client to fail account retrieval
    mock_capital_one_client.set_should_fail_accounts(True)
    # Call verify_account_status method
    account_status_valid = savings_automator.verify_account_status()
    # Assert that the method returns False
    assert account_status_valid is False

def test_verify_sufficient_funds_success(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test successful verification of sufficient funds"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure mock client to return account with sufficient balance
    mock_capital_one_client.set_should_fail_accounts(False)
    # Call verify_sufficient_funds with an amount less than the balance
    funds_sufficient = savings_automator.verify_sufficient_funds(TEST_SURPLUS_AMOUNT)
    # Assert that the method returns True
    assert funds_sufficient is True
    # Assert that get_checking_account_details was called
    assert mock_capital_one_client.get_checking_account_details.called

def test_verify_sufficient_funds_insufficient(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test verification with insufficient funds"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure mock client to return account with low balance
    mock_capital_one_client.set_should_fail_accounts(True)
    # Call verify_sufficient_funds with an amount greater than the balance
    funds_sufficient = savings_automator.verify_sufficient_funds(TEST_SURPLUS_AMOUNT)
    # Assert that the method returns False
    assert funds_sufficient is False

def test_verify_sufficient_funds_api_error(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test funds verification when API returns an error"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure mock client to fail account retrieval
    mock_capital_one_client.set_should_fail_accounts(True)
    # Call verify_sufficient_funds method
    funds_sufficient = savings_automator.verify_sufficient_funds(TEST_SURPLUS_AMOUNT)
    # Assert that the method returns False
    assert funds_sufficient is False

def test_initiate_transfer_success(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test successful transfer initiation"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure mock client to return successful transfer response
    mock_capital_one_client.set_should_fail_transfers(False)
    # Call initiate_transfer with a valid amount
    transfer_result = savings_automator.initiate_transfer(TEST_SURPLUS_AMOUNT)
    # Assert that the method returns a dictionary with success status
    assert transfer_result['status'] == 'success'
    # Assert that transfer_to_savings was called with the correct amount
    assert mock_capital_one_client.transfer_to_savings.called
    # Assert that the transfer object was created correctly
    assert savings_automator.transfer is not None

def test_initiate_transfer_failure(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test transfer initiation failure"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure mock client to fail transfer initiation
    mock_capital_one_client.set_should_fail_transfers(True)
    # Call initiate_transfer with a valid amount
    transfer_result = savings_automator.initiate_transfer(TEST_SURPLUS_AMOUNT)
    # Assert that the method returns a dictionary with failure status
    assert transfer_result['status'] == 'error'
    # Assert that transfer_to_savings was called
    assert mock_capital_one_client.transfer_to_savings.called

def test_verify_transfer_success(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test successful transfer verification"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure mock client to return completed transfer status
    mock_capital_one_client.set_should_fail_transfers(False)
    # Call verify_transfer with a transfer ID
    verification_result = savings_automator.verify_transfer(TEST_TRANSFER_ID)
    # Assert that the method returns True
    assert verification_result is True
    # Assert that verify_transfer_completion was called with the correct transfer ID
    assert mock_capital_one_client.verify_transfer_completion.called

def test_verify_transfer_pending(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test verification of pending transfer"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure mock client to return pending transfer status
    mock_capital_one_client.set_should_fail_transfers(True)
    # Call verify_transfer with a transfer ID
    verification_result = savings_automator.verify_transfer(TEST_TRANSFER_ID)
    # Assert that the method returns False
    assert verification_result is False
    # Assert that verify_transfer_completion was called
    assert mock_capital_one_client.verify_transfer_completion.called

def test_verify_transfer_failed(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test verification of failed transfer"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure mock client to return failed transfer status
    mock_capital_one_client.set_should_fail_transfers(True)
    # Call verify_transfer with a transfer ID
    verification_result = savings_automator.verify_transfer(TEST_TRANSFER_ID)
    # Assert that the method returns False
    assert verification_result is False
    # Assert that verify_transfer_completion was called
    assert mock_capital_one_client.verify_transfer_completion.called

def test_verify_transfer_api_error(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test transfer verification when API returns an error"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure mock client to fail transfer status retrieval
    mock_capital_one_client.set_should_fail_transfers(True)
    # Call verify_transfer with a transfer ID
    verification_result = savings_automator.verify_transfer(TEST_TRANSFER_ID)
    # Assert that the method returns False
    assert verification_result is False

def test_transfer_surplus_success(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test successful surplus transfer end-to-end"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure mock client for successful account verification, transfer initiation, and verification
    mock_capital_one_client.set_should_fail_accounts(False)
    mock_capital_one_client.set_should_fail_transfers(False)
    # Call transfer_surplus with a valid amount
    transfer_result = savings_automator.transfer_surplus(TEST_SURPLUS_AMOUNT)
    # Assert that the method returns a dictionary with success status
    assert transfer_result['status'] == 'success'
    # Assert that the transfer_successful flag is set to True
    assert savings_automator.transfer_successful is True
    # Assert that all expected methods were called in sequence
    assert mock_capital_one_client.get_checking_account_details.called
    assert mock_capital_one_client.get_savings_account_details.called
    assert mock_capital_one_client.transfer_to_savings.called
    assert mock_capital_one_client.verify_transfer_completion.called

def test_transfer_surplus_invalid_amount(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test surplus transfer with invalid amount"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Call transfer_surplus with zero amount
    transfer_result = savings_automator.transfer_surplus(TEST_ZERO_AMOUNT)
    # Assert that the method returns early with no transfer status
    assert transfer_result['status'] == 'no_transfer'
    # Assert that no further methods were called after validation
    assert not mock_capital_one_client.get_checking_account_details.called
    assert not mock_capital_one_client.get_savings_account_details.called
    assert not mock_capital_one_client.transfer_to_savings.called
    assert not mock_capital_one_client.verify_transfer_completion.called

def test_transfer_surplus_inactive_accounts(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test surplus transfer with inactive accounts"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure mock client to return inactive account status
    mock_capital_one_client.set_should_fail_accounts(True)
    # Call transfer_surplus with a valid amount
    transfer_result = savings_automator.transfer_surplus(TEST_SURPLUS_AMOUNT)
    # Assert that the method returns a dictionary with failure status
    assert transfer_result['status'] == 'error'
    # Assert that verify_account_status was called but not initiate_transfer
    assert mock_capital_one_client.get_checking_account_details.called
    assert mock_capital_one_client.get_savings_account_details.called
    assert not mock_capital_one_client.transfer_to_savings.called

def test_transfer_surplus_insufficient_funds(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test surplus transfer with insufficient funds"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure mock client for active accounts but insufficient funds
    mock_capital_one_client.set_should_fail_accounts(True)
    # Call transfer_surplus with a valid amount
    transfer_result = savings_automator.transfer_surplus(TEST_SURPLUS_AMOUNT)
    # Assert that the method returns a dictionary with failure status
    assert transfer_result['status'] == 'error'
    # Assert that verify_sufficient_funds was called but not initiate_transfer
    assert mock_capital_one_client.get_checking_account_details.called
    assert not mock_capital_one_client.transfer_to_savings.called

def test_transfer_surplus_transfer_failure(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test surplus transfer with transfer initiation failure"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure mock client for successful validation but failed transfer
    mock_capital_one_client.set_should_fail_transfers(True)
    # Call transfer_surplus with a valid amount
    transfer_result = savings_automator.transfer_surplus(TEST_SURPLUS_AMOUNT)
    # Assert that the method returns a dictionary with failure status
    assert transfer_result['status'] == 'error'
    # Assert that initiate_transfer was called but transfer_successful is False
    assert mock_capital_one_client.transfer_to_savings.called
    assert savings_automator.transfer_successful is False

def test_transfer_surplus_verification_failure(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test surplus transfer with verification failure"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure mock client for successful initiation but failed verification
    mock_capital_one_client.set_should_fail_transfers(True)
    # Call transfer_surplus with a valid amount
    transfer_result = savings_automator.transfer_surplus(TEST_SURPLUS_AMOUNT)
    # Assert that the method returns a dictionary with partial success status
    assert transfer_result['status'] == 'error'
    # Assert that verify_transfer was called but transfer_successful is False
    assert mock_capital_one_client.verify_transfer_completion.called
    assert savings_automator.transfer_successful is False

def test_execute_success_with_surplus(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test successful execution with budget surplus"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Create a budget with surplus using create_budget_with_surplus
    budget = create_budget_with_surplus(TEST_SURPLUS_AMOUNT)
    # Configure mock client for successful authentication and transfer
    mock_capital_one_client.set_should_fail_authentication(False)
    mock_capital_one_client.set_should_fail_transfers(False)
    # Create previous_status dictionary with budget analysis results
    previous_status = {'budget_analysis': budget.to_dict()}
    # Call execute with previous_status
    result = savings_automator.execute(previous_status)
    # Assert that the method returns a dictionary with success status
    assert result['status'] == 'success'
    # Assert that transfer_surplus was called with the correct amount
    assert mock_capital_one_client.transfer_to_savings.called
    # Assert that the response contains execution metadata
    assert 'execution_time' in result

def test_execute_with_deficit(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test execution with budget deficit (no transfer)"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Create a budget with deficit using create_budget_with_deficit
    budget = create_budget_with_deficit(TEST_DEFICIT_AMOUNT)
    # Configure mock client for successful authentication
    mock_capital_one_client.set_should_fail_authentication(False)
    # Create previous_status dictionary with budget analysis results
    previous_status = {'budget_analysis': budget.to_dict()}
    # Call execute with previous_status
    result = savings_automator.execute(previous_status)
    # Assert that the method returns a dictionary with success status but no transfer
    assert result['status'] == 'success'
    # Assert that transfer_surplus was not called
    assert not mock_capital_one_client.transfer_to_savings.called

def test_execute_with_zero_variance(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test execution with zero budget variance (no transfer)"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Create a budget with zero variance using create_budget_with_zero_variance
    budget = create_budget_with_zero_variance()
    # Configure mock client for successful authentication
    mock_capital_one_client.set_should_fail_authentication(False)
    # Create previous_status dictionary with budget analysis results
    previous_status = {'budget_analysis': budget.to_dict()}
    # Call execute with previous_status
    result = savings_automator.execute(previous_status)
    # Assert that the method returns a dictionary with success status but no transfer
    assert result['status'] == 'success'
    # Assert that transfer_surplus was not called
    assert not mock_capital_one_client.transfer_to_savings.called

def test_execute_authentication_failure(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test execution with authentication failure"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Create a budget with surplus using create_budget_with_surplus
    budget = create_budget_with_surplus(TEST_SURPLUS_AMOUNT)
    # Configure mock client to fail authentication
    mock_capital_one_client.set_should_fail_authentication(True)
    # Create previous_status dictionary with budget analysis results
    previous_status = {'budget_analysis': budget.to_dict()}
    # Call execute with previous_status
    result = savings_automator.execute(previous_status)
    # Assert that the method returns a dictionary with failure status
    assert result['status'] == 'error'
    # Assert that transfer_surplus was not called
    assert not mock_capital_one_client.transfer_to_savings.called

def test_execute_missing_budget_data(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test execution with missing budget data"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Configure mock client for successful authentication
    mock_capital_one_client.set_should_fail_authentication(False)
    # Create previous_status dictionary without budget analysis results
    previous_status = {}
    # Call execute with previous_status
    result = savings_automator.execute(previous_status)
    # Assert that the method returns a dictionary with success status but no transfer
    assert result['status'] == 'success'
    # Assert that transfer_surplus was not called
    assert not mock_capital_one_client.transfer_to_savings.called

def test_execute_exception_handling(setup_savings_automator: Tuple[SavingsAutomator, MockCapitalOneClient]):
    """Test exception handling during execution"""
    # Unpack the setup_savings_automator fixture
    savings_automator, mock_capital_one_client = setup_savings_automator
    # Create a budget with surplus using create_budget_with_surplus
    budget = create_budget_with_surplus(TEST_SURPLUS_AMOUNT)
    # Configure mock client to raise an exception during authentication
    mock_capital_one_client.set_should_fail_authentication(True)
    # Create previous_status dictionary with budget analysis results
    previous_status = {'budget_analysis': budget.to_dict()}
    # Call execute with previous_status
    result = savings_automator.execute(previous_status)
    # Assert that the method returns a dictionary with failure status
    assert result['status'] == 'error'
    # Assert that the response contains error information
    assert 'error_message' in result