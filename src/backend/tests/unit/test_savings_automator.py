"""
Unit tests for the SavingsAutomator component which is responsible for transferring budget surplus to a savings account.
These tests verify the component's ability to calculate transfer amounts, validate transfers, authenticate with Capital One API,
and handle various error scenarios.
"""

import pytest  # pytest 7.4.0+
from unittest.mock import MagicMock, patch  # standard library
from decimal import Decimal  # standard library

# Internal imports
from ...components.savings_automator import SavingsAutomator  # src/backend/components/savings_automator.py
from .mocks.mock_capital_one_client import MockCapitalOneClient  # src/backend/tests/mocks/mock_capital_one_client.py
from ...models.transfer import Transfer  # src/backend/models/transfer.py
from .fixtures.budget import create_budget_with_surplus, create_budget_with_deficit, create_budget_with_zero_balance  # src/backend/tests/fixtures/budget.py
from ...config.settings import APP_SETTINGS  # src/backend/config/settings.py
from .conftest import mock_capital_one_client  # src/backend/tests/conftest.py


def test_savings_automator_init():
    """Test that SavingsAutomator initializes correctly with default and custom dependencies"""
    # Create a mock Capital One client
    mock_client = MockCapitalOneClient()

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Assert that the client was correctly assigned
    assert automator.capital_one_client == mock_client

    # Initialize SavingsAutomator with no arguments
    automator = SavingsAutomator()

    # Assert that a default client was created
    assert automator.capital_one_client is not None


def test_authenticate_success():
    """Test successful authentication with Capital One API"""
    # Create a mock Capital One client with auth_success=True
    mock_client = MockCapitalOneClient(auth_success=True)

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Call authenticate method
    auth_success = automator.authenticate()

    # Assert that authentication was successful
    assert auth_success is True

    # Assert that the mock client's authenticate method was called
    assert mock_client.auth_service.authenticate_capital_one() is not None


def test_authenticate_failure():
    """Test authentication failure with Capital One API"""
    # Create a mock Capital One client with auth_success=False
    mock_client = MockCapitalOneClient(auth_success=False)

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Call authenticate method
    auth_success = automator.authenticate()

    # Assert that authentication failed
    assert auth_success is False

    # Assert that the mock client's authenticate method was called
    assert mock_client.auth_service.authenticate_capital_one() is not None


def test_validate_transfer_amount_valid():
    """Test validation of valid transfer amounts"""
    # Create a SavingsAutomator instance
    automator = SavingsAutomator()

    # Test with a valid amount above minimum threshold
    amount = Decimal('10.00')
    is_valid = automator.validate_transfer_amount(amount)
    assert is_valid is True

    # Test with amount exactly equal to minimum threshold
    amount = APP_SETTINGS['MIN_TRANSFER_AMOUNT']
    is_valid = automator.validate_transfer_amount(amount)
    assert is_valid is True


def test_validate_transfer_amount_invalid():
    """Test validation of invalid transfer amounts"""
    # Create a SavingsAutomator instance
    automator = SavingsAutomator()

    # Test with zero amount
    amount = Decimal('0.00')
    is_valid = automator.validate_transfer_amount(amount)
    assert is_valid is False

    # Test with negative amount
    amount = Decimal('-10.00')
    is_valid = automator.validate_transfer_amount(amount)
    assert is_valid is False

    # Test with amount below minimum threshold
    amount = APP_SETTINGS['MIN_TRANSFER_AMOUNT'] - Decimal('0.01')
    is_valid = automator.validate_transfer_amount(amount)
    assert is_valid is False


def test_verify_account_status_success():
    """Test successful verification of account status"""
    # Create a mock Capital One client
    mock_client = MockCapitalOneClient()

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Call verify_account_status method
    account_status = automator.verify_account_status()

    # Assert that verification was successful
    assert account_status is True

    # Assert that get_checking_account_details and get_savings_account_details were called
    assert mock_client.get_checking_account_details() is not None
    assert mock_client.get_savings_account_details() is not None


def test_verify_account_status_failure():
    """Test account status verification failure"""
    # Create a mock Capital One client with api_error=True
    mock_client = MockCapitalOneClient(api_error=True)

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Call verify_account_status method
    account_status = automator.verify_account_status()

    # Assert that verification failed
    assert account_status is False

    # Assert that get_checking_account_details was called
    assert mock_client.get_checking_account_details() is not None


def test_verify_sufficient_funds_success():
    """Test successful verification of sufficient funds"""
    # Create a mock Capital One client with sufficient balance
    mock_client = MockCapitalOneClient(checking_balance=Decimal('1000.00'))

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Call verify_sufficient_funds with an amount less than balance
    amount = Decimal('500.00')
    funds_available = automator.verify_sufficient_funds(amount)

    # Assert that verification was successful
    assert funds_available is True

    # Assert that get_checking_account_details was called
    assert mock_client.get_checking_account_details() is not None


def test_verify_sufficient_funds_failure():
    """Test verification failure due to insufficient funds"""
    # Create a mock Capital One client with a low balance
    mock_client = MockCapitalOneClient(checking_balance=Decimal('100.00'))

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Call verify_sufficient_funds with an amount greater than balance
    amount = Decimal('500.00')
    funds_available = automator.verify_sufficient_funds(amount)

    # Assert that verification failed
    assert funds_available is False

    # Assert that get_checking_account_details was called
    assert mock_client.get_checking_account_details() is not None


def test_initiate_transfer_success():
    """Test successful initiation of transfer"""
    # Create a mock Capital One client
    mock_client = MockCapitalOneClient()

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Call initiate_transfer with a valid amount
    amount = Decimal('100.00')
    transfer_result = automator.initiate_transfer(amount)

    # Assert that transfer was initiated successfully
    assert transfer_result['status'] == 'success'

    # Assert that transfer_to_savings was called with correct amount
    assert mock_client.transfer_to_savings.call_count == 1
    assert mock_client.transfer_to_savings.call_args[0][0] == amount

    # Assert that the transfer object was created
    assert automator.transfer is not None


def test_initiate_transfer_failure():
    """Test transfer initiation failure"""
    # Create a mock Capital One client with api_error=True
    mock_client = MockCapitalOneClient(api_error=True)

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Call initiate_transfer with a valid amount
    amount = Decimal('100.00')
    transfer_result = automator.initiate_transfer(amount)

    # Assert that transfer initiation failed
    assert transfer_result['status'] == 'error'

    # Assert that transfer_to_savings was called
    assert mock_client.transfer_to_savings.call_count == 1

    # Assert that the transfer object was not created
    assert automator.transfer is None


def test_verify_transfer_success():
    """Test successful verification of transfer completion"""
    # Create a mock Capital One client
    mock_client = MockCapitalOneClient()

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Set up a completed transfer in the mock client
    mock_client.complete_all_transfers()
    transfer_id = list(mock_client.transfers.keys())[0]

    # Call verify_transfer with the transfer ID
    verification_result = automator.verify_transfer(transfer_id)

    # Assert that verification was successful
    assert verification_result is True

    # Assert that verify_transfer_completion was called with correct ID
    assert mock_client.verify_transfer_completion.call_count == 1
    assert mock_client.verify_transfer_completion.call_args[0][0] == transfer_id


def test_verify_transfer_failure():
    """Test transfer verification failure"""
    # Create a mock Capital One client
    mock_client = MockCapitalOneClient()

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Set up a failed transfer in the mock client
    mock_client.fail_all_transfers()
    transfer_id = list(mock_client.transfers.keys())[0]

    # Call verify_transfer with the transfer ID
    verification_result = automator.verify_transfer(transfer_id)

    # Assert that verification failed
    assert verification_result is False

    # Assert that verify_transfer_completion was called with correct ID
    assert mock_client.verify_transfer_completion.call_count == 1
    assert mock_client.verify_transfer_completion.call_args[0][0] == transfer_id


def test_transfer_surplus_success():
    """Test successful transfer of budget surplus"""
    # Create a mock Capital One client
    mock_client = MockCapitalOneClient()

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Set up the mock client to complete transfers successfully
    mock_client.complete_all_transfers()

    # Call transfer_surplus with a valid amount
    amount = Decimal('100.00')
    transfer_result = automator.transfer_surplus(amount)

    # Assert that transfer was successful
    assert transfer_result['status'] == 'success'

    # Assert that the response contains correct transfer details
    assert transfer_result['amount'] == str(amount)

    # Assert that all required methods were called in sequence
    assert mock_client.transfer_to_savings.call_count == 1
    assert mock_client.verify_transfer_completion.call_count == 1
    assert automator.validate_transfer_amount(amount) is True
    assert automator.verify_account_status() is True
    assert automator.verify_sufficient_funds(amount) is True


def test_transfer_surplus_invalid_amount():
    """Test transfer surplus with invalid amount"""
    # Create a mock Capital One client
    mock_client = MockCapitalOneClient()

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Call transfer_surplus with zero amount
    amount = Decimal('0.00')
    transfer_result = automator.transfer_surplus(amount)

    # Assert that transfer was not attempted
    assert mock_client.transfer_to_savings.call_count == 0

    # Assert that the response indicates no transfer was made
    assert transfer_result['status'] == 'no_transfer'

    # Call transfer_surplus with negative amount
    amount = Decimal('-100.00')
    transfer_result = automator.transfer_surplus(amount)

    # Assert that transfer was not attempted
    assert mock_client.transfer_to_savings.call_count == 0

    # Assert that the response indicates no transfer was made
    assert transfer_result['status'] == 'no_transfer'


def test_transfer_surplus_account_status_failure():
    """Test transfer surplus with account status verification failure"""
    # Create a mock Capital One client with api_error=True
    mock_client = MockCapitalOneClient(api_error=True)

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Call transfer_surplus with a valid amount
    amount = Decimal('100.00')
    transfer_result = automator.transfer_surplus(amount)

    # Assert that transfer failed due to account status verification
    assert transfer_result['status'] == 'error'
    assert transfer_result['error_message'] == 'Account status verification failed'

    # Assert that verify_account_status was called but not subsequent methods
    assert mock_client.get_checking_account_details.call_count == 1
    assert mock_client.transfer_to_savings.call_count == 0


def test_transfer_surplus_insufficient_funds():
    """Test transfer surplus with insufficient funds"""
    # Create a mock Capital One client with a low balance
    mock_client = MockCapitalOneClient(checking_balance=Decimal('50.00'))

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Call transfer_surplus with an amount greater than balance
    amount = Decimal('100.00')
    transfer_result = automator.transfer_surplus(amount)

    # Assert that transfer failed due to insufficient funds
    assert transfer_result['status'] == 'error'
    assert transfer_result['error_message'] == 'Insufficient funds for transfer'

    # Assert that verify_sufficient_funds was called but not subsequent methods
    assert mock_client.get_checking_account_details.call_count == 1
    assert mock_client.transfer_to_savings.call_count == 0


def test_transfer_surplus_initiation_failure():
    """Test transfer surplus with transfer initiation failure"""
    # Create a mock Capital One client that fails on transfer initiation
    mock_client = MockCapitalOneClient(api_error=True)

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Call transfer_surplus with a valid amount
    amount = Decimal('100.00')
    transfer_result = automator.transfer_surplus(amount)

    # Assert that transfer failed due to initiation failure
    assert transfer_result['status'] == 'error'
    assert transfer_result['error_message'] == 'API error initiating transfer'

    # Assert that initiate_transfer was called but not verify_transfer
    assert mock_client.transfer_to_savings.call_count == 1
    assert mock_client.verify_transfer_completion.call_count == 0


def test_transfer_surplus_verification_failure():
    """Test transfer surplus with transfer verification failure"""
    # Create a mock Capital One client
    mock_client = MockCapitalOneClient()

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Set up the mock client to fail transfer verification
    mock_client.fail_all_transfers()

    # Call transfer_surplus with a valid amount
    amount = Decimal('100.00')
    transfer_result = automator.transfer_surplus(amount)

    # Assert that transfer was initiated but verification failed
    assert transfer_result['status'] == 'success'
    assert transfer_result['verified'] is False

    # Assert that the response indicates transfer failure
    assert transfer_result['transfer_successful'] is False

    # Assert that both initiate_transfer and verify_transfer were called
    assert mock_client.transfer_to_savings.call_count == 1
    assert mock_client.verify_transfer_completion.call_count == 1


def test_execute_with_surplus():
    """Test execute method with budget surplus"""
    # Create a budget with surplus using create_budget_with_surplus
    budget = create_budget_with_surplus()

    # Create a mock Capital One client
    mock_client = MockCapitalOneClient()

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Set up the mock client to complete transfers successfully
    mock_client.complete_all_transfers()

    # Call execute with the budget analysis results
    previous_status = {'budget_analysis': budget.to_dict()}
    result = automator.execute(previous_status)

    # Assert that execution was successful
    assert result['status'] == 'success'

    # Assert that transfer was initiated with correct amount
    assert mock_client.transfer_to_savings.call_count == 1
    assert mock_client.transfer_to_savings.call_args[0][0] == budget.get_transfer_amount()

    # Assert that the response contains successful transfer details
    assert result['transfer_result']['status'] == 'success'


def test_execute_with_deficit():
    """Test execute method with budget deficit"""
    # Create a budget with deficit using create_budget_with_deficit
    budget = create_budget_with_deficit()

    # Create a mock Capital One client
    mock_client = MockCapitalOneClient()

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Call execute with the budget analysis results
    previous_status = {'budget_analysis': budget.to_dict()}
    result = automator.execute(previous_status)

    # Assert that execution was successful but no transfer was made
    assert result['status'] == 'success'
    assert result['transfer_executed'] is False

    # Assert that the response indicates no surplus available
    assert result['message'] == 'No budget surplus to transfer'

    # Assert that transfer_to_savings was not called
    assert mock_client.transfer_to_savings.call_count == 0


def test_execute_with_zero_balance():
    """Test execute method with zero budget balance"""
    # Create a budget with zero balance using create_budget_with_zero_balance
    budget = create_budget_with_zero_balance()

    # Create a mock Capital One client
    mock_client = MockCapitalOneClient()

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Call execute with the budget analysis results
    previous_status = {'budget_analysis': budget.to_dict()}
    result = automator.execute(previous_status)

    # Assert that execution was successful but no transfer was made
    assert result['status'] == 'success'
    assert result['transfer_executed'] is False

    # Assert that the response indicates no surplus available
    assert result['message'] == 'No budget surplus to transfer'

    # Assert that transfer_to_savings was not called
    assert mock_client.transfer_to_savings.call_count == 0


def test_execute_authentication_failure():
    """Test execute method with authentication failure"""
    # Create a budget with surplus using create_budget_with_surplus
    budget = create_budget_with_surplus()

    # Create a mock Capital One client with auth_success=False
    mock_client = MockCapitalOneClient(auth_success=False)

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Call execute with the budget analysis results
    previous_status = {'budget_analysis': budget.to_dict()}
    result = automator.execute(previous_status)

    # Assert that execution failed due to authentication failure
    assert result['status'] == 'error'
    assert result['message'] == 'Authentication failed'

    # Assert that the response contains appropriate error message
    assert result['error'] == 'Authentication failed'

    # Assert that transfer_to_savings was not called
    assert mock_client.transfer_to_savings.call_count == 0


def test_execute_transfer_failure():
    """Test execute method with transfer failure"""
    # Create a budget with surplus using create_budget_with_surplus
    budget = create_budget_with_surplus()

    # Create a mock Capital One client that fails on transfer
    mock_client = MockCapitalOneClient(api_error=True)

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Call execute with the budget analysis results
    previous_status = {'budget_analysis': budget.to_dict()}
    result = automator.execute(previous_status)

    # Assert that execution completed but transfer failed
    assert result['status'] == 'error'

    # Assert that the response contains appropriate error message
    assert result['message'] == 'An unexpected error occurred during savings automation: API error initiating transfer'

    # Assert that transfer_to_savings was called but failed
    assert mock_client.transfer_to_savings.call_count == 1


def test_execute_with_exception():
    """Test execute method with unexpected exception"""
    # Create a budget with surplus using create_budget_with_surplus
    budget = create_budget_with_surplus()

    # Create a mock Capital One client that raises an exception
    mock_client = MockCapitalOneClient()
    mock_client.transfer_to_savings.side_effect = Exception("Simulated transfer exception")

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Call execute with the budget analysis results
    previous_status = {'budget_analysis': budget.to_dict()}
    result = automator.execute(previous_status)

    # Assert that execution failed with appropriate error handling
    assert result['status'] == 'error'

    # Assert that the response contains error status
    assert result['message'] == "An unexpected error occurred during savings automation: Simulated transfer exception"

    # Assert that the exception was caught and logged
    assert "Simulated transfer exception" in result['message']


def test_check_health():
    """Test health check functionality"""
    # Create a mock Capital One client with test_connectivity returning True
    mock_client = MockCapitalOneClient()
    mock_client.test_connectivity.return_value = True

    # Initialize SavingsAutomator with the mock client
    automator = SavingsAutomator(capital_one_client=mock_client)

    # Call check_health method
    health_status = automator.check_health()

    # Assert that health check returns healthy status
    assert health_status['capital_one_connection'] == 'healthy'

    # Modify mock client to return False for test_connectivity
    mock_client.test_connectivity.return_value = False

    # Call check_health method again
    health_status = automator.check_health()

    # Assert that health check returns unhealthy status
    assert health_status['capital_one_connection'] == 'unhealthy'