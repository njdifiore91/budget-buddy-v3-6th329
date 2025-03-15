"""
Unit tests for the Capital One API client.

Tests verify functionality for transaction retrieval, account information access,
fund transfers, error handling, retry mechanisms, and data transformation.
"""

import pytest
import datetime
import decimal
from decimal import Decimal
from unittest.mock import MagicMock, patch, Mock
import requests
from freezegun import freeze_time

from ../../api_clients.capital_one_client import (
    CapitalOneClient, 
    format_date_for_api,
    get_date_range,
    mask_account_id
)
from ../../utils.error_handlers import APIError, AuthenticationError
from ../../models.transaction import Transaction, create_transactions_from_capital_one
from ../../models.transfer import Transfer, create_transfer

from ../mocks.mock_capital_one_client import (
    MockAuthenticationService,
    create_mock_transaction_response,
    create_mock_account_response,
    create_mock_transfer_response
)
from ../fixtures.api_responses import (
    load_capital_one_transactions_response,
    load_capital_one_accounts_response,
    load_capital_one_transfer_response,
    load_capital_one_error_response,
    MockResponse,
    create_mock_api_response,
    create_mock_error_response
)


def test_format_date_for_api():
    """Test that format_date_for_api correctly formats dates for the Capital One API"""
    # Arrange
    test_date = datetime.datetime(2023, 7, 15)
    
    # Act
    result = format_date_for_api(test_date)
    
    # Assert
    assert result == "2023-07-15"


@freeze_time("2023-07-23")
def test_get_date_range():
    """Test that get_date_range returns the correct date range for the past week"""
    # Act
    start_date, end_date = get_date_range()
    
    # Assert
    assert start_date == "2023-07-16"  # 7 days before 2023-07-23
    assert end_date == "2023-07-23"


def test_mask_account_id():
    """Test that mask_account_id properly masks account IDs for secure logging"""
    # Arrange
    account_id = "1234567890123456"
    
    # Act
    masked_id = mask_account_id(account_id)
    
    # Assert
    assert masked_id == "XXXXXXXXXXXX3456"
    assert len(masked_id) == len(account_id)
    assert masked_id[-4:] == account_id[-4:]
    
    # Test with shorter ID
    short_id = "1234"
    assert mask_account_id(short_id) == short_id  # Too short to mask
    
    # Test with non-string
    assert mask_account_id(None) == "[INVALID_ACCOUNT_ID]"


def test_capital_one_client_init():
    """Test that CapitalOneClient initializes correctly with the proper attributes"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    
    # Act
    client = CapitalOneClient(mock_auth_service)
    
    # Assert
    assert client.auth_service == mock_auth_service
    assert client.base_url is not None
    assert client.auth_url is not None
    assert client.checking_account_id is not None
    assert client.savings_account_id is not None


def test_authenticate_success():
    """Test successful authentication with the Capital One API"""
    # Arrange
    mock_auth_service = MockAuthenticationService(auth_success=True)
    mock_auth_service.authenticate_capital_one = MagicMock(return_value={"access_token": "test-token"})
    client = CapitalOneClient(mock_auth_service)
    
    # Act
    result = client.authenticate()
    
    # Assert
    assert result is True
    mock_auth_service.authenticate_capital_one.assert_called_once()


def test_authenticate_failure():
    """Test authentication failure with the Capital One API"""
    # Arrange
    mock_auth_service = MockAuthenticationService(auth_success=False)
    mock_auth_service.authenticate_capital_one = MagicMock(side_effect=Exception("Auth failed"))
    client = CapitalOneClient(mock_auth_service)
    
    # Act
    result = client.authenticate()
    
    # Assert
    assert result is False
    mock_auth_service.authenticate_capital_one.assert_called_once()


def test_get_auth_headers():
    """Test that get_auth_headers returns the correct authentication headers"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    mock_auth_service.get_token = MagicMock(return_value="test-token")
    client = CapitalOneClient(mock_auth_service)
    
    # Act
    headers = client.get_auth_headers()
    
    # Assert
    assert headers == {
        'Authorization': 'Bearer test-token',
        'Content-Type': 'application/json'
    }
    mock_auth_service.get_token.assert_called_once_with('CAPITAL_ONE')


def test_refresh_auth_token_success():
    """Test successful token refresh"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    mock_auth_service.refresh_token = MagicMock(return_value=True)
    client = CapitalOneClient(mock_auth_service)
    
    # Act
    result = client.refresh_auth_token()
    
    # Assert
    assert result is True
    mock_auth_service.refresh_token.assert_called_once_with('CAPITAL_ONE')


def test_refresh_auth_token_failure():
    """Test token refresh failure"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    mock_auth_service.refresh_token = MagicMock(return_value=False)
    client = CapitalOneClient(mock_auth_service)
    
    # Act
    result = client.refresh_auth_token()
    
    # Assert
    assert result is False
    mock_auth_service.refresh_token.assert_called_once_with('CAPITAL_ONE')


def test_get_transactions_success():
    """Test successful transaction retrieval"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    
    # Mock the requests.get method
    mock_response = create_mock_api_response(load_capital_one_transactions_response())
    
    with patch('requests.get', return_value=mock_response) as mock_get:
        # Act
        start_date = "2023-07-16"
        end_date = "2023-07-23"
        result = client.get_transactions(start_date, end_date)
        
        # Assert
        assert result == load_capital_one_transactions_response()
        mock_get.assert_called_once()
        # Verify the URL and params
        args, kwargs = mock_get.call_args
        assert client.base_url in args[0]
        assert kwargs['params'] == {
            'startDate': start_date,
            'endDate': end_date
        }


@freeze_time("2023-07-23")
def test_get_transactions_with_default_dates():
    """Test transaction retrieval with default date range"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    
    # Mock the requests.get method
    mock_response = create_mock_api_response(load_capital_one_transactions_response())
    
    with patch('requests.get', return_value=mock_response) as mock_get:
        # Act
        result = client.get_transactions()  # No dates provided
        
        # Assert
        assert result == load_capital_one_transactions_response()
        mock_get.assert_called_once()
        # Verify the params use the default date range
        args, kwargs = mock_get.call_args
        assert kwargs['params'] == {
            'startDate': "2023-07-16",  # 7 days before 2023-07-23
            'endDate': "2023-07-23"
        }


def test_get_transactions_error():
    """Test error handling during transaction retrieval"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    
    # Mock requests.get to raise an exception
    with patch('requests.get', side_effect=requests.RequestException("API error")) as mock_get:
        # Act
        result = client.get_transactions("2023-07-16", "2023-07-23")
        
        # Assert
        assert result['status'] == 'error'
        assert 'error_message' in result
        assert result['operation'] == 'get_transactions'
        mock_get.assert_called_once()


def test_get_transactions_retry():
    """Test retry mechanism for transaction retrieval"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    
    # Create a side effect that fails on first call then succeeds
    mock_response = create_mock_api_response(load_capital_one_transactions_response())
    side_effects = [
        requests.RequestException("API error"),
        mock_response
    ]
    
    with patch('requests.get', side_effect=side_effects) as mock_get:
        # Act
        result = client.get_transactions("2023-07-16", "2023-07-23")
        
        # Assert
        assert result == load_capital_one_transactions_response()  # Should succeed on retry
        assert mock_get.call_count == 2  # Should be called twice (initial + retry)


def test_get_account_details_success():
    """Test successful account details retrieval"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    account_id = "account-123"
    
    # Mock the requests.get method
    mock_response = create_mock_api_response(load_capital_one_accounts_response())
    
    with patch('requests.get', return_value=mock_response) as mock_get:
        # Act
        result = client.get_account_details(account_id)
        
        # Assert
        assert result == load_capital_one_accounts_response()
        mock_get.assert_called_once()
        # Verify the URL
        args, kwargs = mock_get.call_args
        assert client.base_url in args[0]
        assert account_id in args[0]


def test_get_account_details_error():
    """Test error handling during account details retrieval"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    account_id = "account-123"
    
    # Mock requests.get to raise an exception
    with patch('requests.get', side_effect=requests.RequestException("API error")) as mock_get:
        # Act
        result = client.get_account_details(account_id)
        
        # Assert
        assert result['status'] == 'error'
        assert 'error_message' in result
        assert result['operation'] == 'get_account_details'
        mock_get.assert_called_once()


def test_get_checking_account_details():
    """Test checking account details retrieval"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    
    # Mock the get_account_details method
    client.get_account_details = MagicMock(return_value=load_capital_one_accounts_response())
    
    # Act
    result = client.get_checking_account_details()
    
    # Assert
    assert result == load_capital_one_accounts_response()
    client.get_account_details.assert_called_once_with(client.checking_account_id)


def test_get_savings_account_details():
    """Test savings account details retrieval"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    
    # Mock the get_account_details method
    client.get_account_details = MagicMock(return_value=load_capital_one_accounts_response())
    
    # Act
    result = client.get_savings_account_details()
    
    # Assert
    assert result == load_capital_one_accounts_response()
    client.get_account_details.assert_called_once_with(client.savings_account_id)


def test_initiate_transfer_success():
    """Test successful fund transfer initiation"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    amount = Decimal('100.00')
    source_id = "account-123"
    dest_id = "account-456"
    
    # Mock the requests.post method
    mock_response = create_mock_api_response(load_capital_one_transfer_response())
    
    with patch('requests.post', return_value=mock_response) as mock_post, \
         patch('src.backend.models.transfer.create_transfer_from_capital_one_response') as mock_create_transfer:
        
        # Mock the create_transfer_from_capital_one_response function
        mock_transfer = MagicMock()
        mock_transfer.to_dict.return_value = {'amount': '$100.00', 'source_account_id': source_id}
        mock_create_transfer.return_value = mock_transfer
        
        # Act
        result = client.initiate_transfer(amount, source_id, dest_id)
        
        # Assert
        mock_post.assert_called_once()
        # Verify the URL and data
        args, kwargs = mock_post.call_args
        assert client.base_url in args[0]
        assert 'transfers' in args[0]
        # Verify the request data contains the correct fields
        assert 'json' in kwargs
        json_data = kwargs['json']
        assert 'sourceAccountId' in json_data
        assert 'destinationAccountId' in json_data
        assert 'amount' in json_data


def test_initiate_transfer_error():
    """Test error handling during transfer initiation"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    amount = Decimal('100.00')
    source_id = "account-123"
    dest_id = "account-456"
    
    # Mock requests.post to raise an exception
    with patch('requests.post', side_effect=requests.RequestException("API error")) as mock_post:
        # Act
        result = client.initiate_transfer(amount, source_id, dest_id)
        
        # Assert
        assert result['status'] == 'error'
        assert 'error_message' in result
        assert result['operation'] == 'initiate_transfer'
        mock_post.assert_called_once()


def test_transfer_to_savings():
    """Test transfer from checking to savings account"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    amount = Decimal('100.00')
    
    # Mock the initiate_transfer method
    expected_result = {'transfer_id': 'test-transfer', 'amount': '$100.00'}
    client.initiate_transfer = MagicMock(return_value=expected_result)
    
    # Act
    result = client.transfer_to_savings(amount)
    
    # Assert
    assert result == expected_result
    client.initiate_transfer.assert_called_once_with(
        amount=amount,
        source_account_id=client.checking_account_id,
        destination_account_id=client.savings_account_id
    )


def test_get_transfer_status_success():
    """Test successful transfer status retrieval"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    transfer_id = "transfer-123"
    
    # Mock the requests.get method
    mock_response = create_mock_api_response(load_capital_one_transfer_response())
    
    with patch('requests.get', return_value=mock_response) as mock_get:
        # Act
        result = client.get_transfer_status(transfer_id)
        
        # Assert
        assert result == load_capital_one_transfer_response()
        mock_get.assert_called_once()
        # Verify the URL
        args, kwargs = mock_get.call_args
        assert client.base_url in args[0]
        assert 'transfers' in args[0]
        assert transfer_id in args[0]


def test_get_transfer_status_error():
    """Test error handling during transfer status retrieval"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    transfer_id = "transfer-123"
    
    # Mock requests.get to raise an exception
    with patch('requests.get', side_effect=requests.RequestException("API error")) as mock_get:
        # Act
        result = client.get_transfer_status(transfer_id)
        
        # Assert
        assert result['status'] == 'error'
        assert 'error_message' in result
        assert result['operation'] == 'get_transfer_status'
        mock_get.assert_called_once()


def test_verify_transfer_completion_success():
    """Test successful transfer completion verification"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    transfer_id = "transfer-123"
    
    # Mock the get_transfer_status method
    client.get_transfer_status = MagicMock(return_value={'status': 'completed'})
    
    # Act
    result = client.verify_transfer_completion(transfer_id)
    
    # Assert
    assert result is True
    client.get_transfer_status.assert_called_once_with(transfer_id)


def test_verify_transfer_completion_pending():
    """Test transfer completion verification with pending status"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    transfer_id = "transfer-123"
    
    # Mock the get_transfer_status method
    client.get_transfer_status = MagicMock(return_value={'status': 'pending'})
    
    # Act
    result = client.verify_transfer_completion(transfer_id)
    
    # Assert
    assert result is False
    client.get_transfer_status.assert_called_once_with(transfer_id)


def test_verify_transfer_completion_error():
    """Test error handling during transfer completion verification"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    transfer_id = "transfer-123"
    
    # Mock the get_transfer_status method to return an error
    client.get_transfer_status = MagicMock(return_value={'status': 'error'})
    
    # Act
    result = client.verify_transfer_completion(transfer_id)
    
    # Assert
    assert result is False
    client.get_transfer_status.assert_called_once_with(transfer_id)


@freeze_time("2023-07-23")
def test_get_weekly_transactions_success():
    """Test successful weekly transaction retrieval"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    
    # Mock the get_transactions method
    transactions_response = load_capital_one_transactions_response()
    client.get_transactions = MagicMock(return_value=transactions_response)
    
    # Mock create_transactions_from_capital_one
    expected_transactions = [MagicMock(spec=Transaction)]
    
    with patch('src.backend.api_clients.capital_one_client.create_transactions_from_capital_one', 
              return_value=expected_transactions) as mock_create:
        # Act
        result = client.get_weekly_transactions()
        
        # Assert
        assert result == expected_transactions
        # Verify get_transactions was called with the correct date range
        client.get_transactions.assert_called_once()
        args, kwargs = client.get_transactions.call_args
        assert args[0] == "2023-07-16"  # 7 days before 2023-07-23
        assert args[1] == "2023-07-23"
        # Verify create_transactions_from_capital_one was called
        mock_create.assert_called_once_with(transactions_response.get('transactions', []))


def test_get_weekly_transactions_error():
    """Test error handling during weekly transaction retrieval"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    
    # Mock the get_transactions method to return an error
    client.get_transactions = MagicMock(return_value={'status': 'error', 'error_message': 'API error'})
    
    # Act
    result = client.get_weekly_transactions()
    
    # Assert
    assert isinstance(result, list)
    assert len(result) == 0  # Should return empty list on error
    client.get_transactions.assert_called_once()


def test_test_connectivity_success():
    """Test successful connectivity test"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    
    # Mock the authenticate and get_checking_account_details methods
    client.authenticate = MagicMock(return_value=True)
    client.get_checking_account_details = MagicMock(return_value={'accountId': 'test-account'})
    
    # Act
    result = client.test_connectivity()
    
    # Assert
    assert result is True
    client.authenticate.assert_called_once()
    client.get_checking_account_details.assert_called_once()


def test_test_connectivity_auth_failure():
    """Test connectivity test with authentication failure"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    
    # Mock the authenticate method to fail
    client.authenticate = MagicMock(return_value=False)
    client.get_checking_account_details = MagicMock()  # Should not be called
    
    # Act
    result = client.test_connectivity()
    
    # Assert
    assert result is False
    client.authenticate.assert_called_once()
    client.get_checking_account_details.assert_not_called()


def test_test_connectivity_api_failure():
    """Test connectivity test with API failure"""
    # Arrange
    mock_auth_service = MockAuthenticationService()
    client = CapitalOneClient(mock_auth_service)
    
    # Mock the authenticate method to succeed but get_checking_account_details to fail
    client.authenticate = MagicMock(return_value=True)
    client.get_checking_account_details = MagicMock(return_value={'status': 'error'})
    
    # Act
    result = client.test_connectivity()
    
    # Assert
    assert result is False
    client.authenticate.assert_called_once()
    client.get_checking_account_details.assert_called_once()