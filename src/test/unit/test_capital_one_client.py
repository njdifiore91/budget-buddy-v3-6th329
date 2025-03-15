import pytest
from unittest.mock import MagicMock, patch
import requests
from requests.exceptions import RequestException
from datetime import datetime, timedelta
from decimal import Decimal

from ...backend.api_clients.capital_one_client import (
    CapitalOneClient, format_date_for_api, get_date_range
)
from ...backend.services.authentication_service import AuthenticationService
from ...backend.utils.error_handlers import APIError
from ...backend.models.transaction import Transaction
from ...backend.models.transfer import Transfer
from ..utils.fixture_loader import load_fixture

class TestCapitalOneClient:
    def setup_method(self, method):
        """Set up test fixtures and mocks"""
        # Mock authentication service
        self.auth_service = MagicMock(spec=AuthenticationService)
        self.auth_service.authenticate_capital_one.return_value = True
        self.auth_service.get_token.return_value = "test_token"
        
        # Load test fixtures
        self.transactions_fixture = load_fixture("transactions/valid_transactions")
        self.accounts_fixture = load_fixture("api_responses/capital_one/accounts")
        self.transfers_fixture = load_fixture("api_responses/capital_one/transfers")
        
        # Initialize client with mock auth service
        self.client = CapitalOneClient(self.auth_service)
    
    def test_authenticate_success(self):
        """Test successful authentication with Capital One API"""
        result = self.client.authenticate()
        assert result is True
        self.auth_service.authenticate_capital_one.assert_called_once()
    
    def test_authenticate_failure(self):
        """Test authentication failure with Capital One API"""
        self.auth_service.authenticate_capital_one.return_value = False
        result = self.client.authenticate()
        assert result is False
        self.auth_service.authenticate_capital_one.assert_called_once()
    
    def test_get_auth_headers(self):
        """Test getting authentication headers for API requests"""
        headers = self.client.get_auth_headers()
        assert headers['Authorization'] == 'Bearer test_token'
        assert headers['Content-Type'] == 'application/json'
        self.auth_service.get_token.assert_called_with('CAPITAL_ONE')
    
    def test_refresh_auth_token_success(self):
        """Test successful token refresh"""
        self.auth_service.refresh_token.return_value = True
        result = self.client.refresh_auth_token()
        assert result is True
        self.auth_service.refresh_token.assert_called_with('CAPITAL_ONE')
    
    def test_refresh_auth_token_failure(self):
        """Test token refresh failure"""
        self.auth_service.refresh_token.return_value = False
        result = self.client.refresh_auth_token()
        assert result is False
        self.auth_service.refresh_token.assert_called_with('CAPITAL_ONE')
    
    def test_get_transactions_success(self):
        """Test successful transaction retrieval"""
        # Mock requests.get to return successful response
        mock_response = MagicMock()
        mock_response.json.return_value = self.transactions_fixture
        
        with patch('requests.get', return_value=mock_response):
            start_date, end_date = "2023-07-01", "2023-07-07"
            response = self.client.get_transactions(start_date, end_date)
        
        assert response == self.transactions_fixture
        requests.get.assert_called_once()
        args, kwargs = requests.get.call_args
        assert kwargs['params']['startDate'] == start_date
        assert kwargs['params']['endDate'] == end_date
    
    def test_get_transactions_with_default_dates(self):
        """Test transaction retrieval with default date range"""
        # Mock requests.get to return successful response
        mock_response = MagicMock()
        mock_response.json.return_value = self.transactions_fixture
        
        # Mock get_date_range to return specific dates
        mock_dates = ("2023-07-01", "2023-07-07")
        
        with patch('...backend.api_clients.capital_one_client.get_date_range', return_value=mock_dates):
            with patch('requests.get', return_value=mock_response):
                response = self.client.get_transactions()
        
        assert response == self.transactions_fixture
        requests.get.assert_called_once()
        args, kwargs = requests.get.call_args
        assert kwargs['params']['startDate'] == mock_dates[0]
        assert kwargs['params']['endDate'] == mock_dates[1]
    
    def test_get_transactions_api_error(self):
        """Test handling of API errors during transaction retrieval"""
        # Mock requests.get to raise an API error
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("API Error")
        mock_response.status_code = 400
        
        with patch('requests.get', return_value=mock_response):
            start_date, end_date = "2023-07-01", "2023-07-07"
            response = self.client.get_transactions(start_date, end_date)
        
        assert response['status'] == 'error'
        assert 'API Error' in response['error_message']
    
    def test_get_transactions_request_exception(self):
        """Test handling of request exceptions during transaction retrieval"""
        # Mock requests.get to raise a request exception
        with patch('requests.get', side_effect=RequestException("Connection Error")):
            start_date, end_date = "2023-07-01", "2023-07-07"
            response = self.client.get_transactions(start_date, end_date)
        
        assert response['status'] == 'error'
        assert 'Connection Error' in response['error_message']
    
    def test_get_account_details_success(self):
        """Test successful account details retrieval"""
        # Mock requests.get to return successful response
        mock_response = MagicMock()
        mock_response.json.return_value = self.accounts_fixture[0]  # First account in fixture
        
        with patch('requests.get', return_value=mock_response):
            account_id = "account123"
            response = self.client.get_account_details(account_id)
        
        assert response == self.accounts_fixture[0]
        requests.get.assert_called_once()
        args, kwargs = requests.get.call_args
        assert f"/accounts/{account_id}" in args[0]
    
    def test_get_checking_account_details(self):
        """Test retrieval of checking account details"""
        # Mock get_account_details to return checking account data
        with patch.object(self.client, 'get_account_details', return_value=self.accounts_fixture[0]):
            response = self.client.get_checking_account_details()
        
        assert response == self.accounts_fixture[0]
        self.client.get_account_details.assert_called_with(self.client.checking_account_id)
    
    def test_get_savings_account_details(self):
        """Test retrieval of savings account details"""
        # Mock get_account_details to return savings account data
        with patch.object(self.client, 'get_account_details', return_value=self.accounts_fixture[1]):
            response = self.client.get_savings_account_details()
        
        assert response == self.accounts_fixture[1]
        self.client.get_account_details.assert_called_with(self.client.savings_account_id)
    
    def test_initiate_transfer_success(self):
        """Test successful fund transfer initiation"""
        # Mock requests.post to return successful response
        mock_response = MagicMock()
        mock_response.json.return_value = self.transfers_fixture[0]  # First transfer in fixture
        
        with patch('requests.post', return_value=mock_response):
            with patch('...backend.api_clients.capital_one_client.create_transfer_from_capital_one_response', 
                      return_value=MagicMock(to_dict=lambda: {'amount': '$100.00'})):
                amount = Decimal("100.00")
                source_id = "source123"
                dest_id = "dest456"
                response = self.client.initiate_transfer(amount, source_id, dest_id)
        
        assert response['amount'] == '$100.00'
        requests.post.assert_called_once()
        args, kwargs = requests.post.call_args
        assert '/transfers' in args[0]
        assert kwargs['json']['sourceAccountId'] == source_id
        assert kwargs['json']['destinationAccountId'] == dest_id
        assert kwargs['json']['amount'] == '100.00'
    
    def test_transfer_to_savings(self):
        """Test transfer from checking to savings account"""
        # Mock initiate_transfer to return transfer data
        expected_result = {'amount': '$100.00', 'status': 'pending'}
        with patch.object(self.client, 'initiate_transfer', return_value=expected_result):
            amount = Decimal("100.00")
            response = self.client.transfer_to_savings(amount)
        
        assert response == expected_result
        self.client.initiate_transfer.assert_called_with(
            amount=amount,
            source_account_id=self.client.checking_account_id,
            destination_account_id=self.client.savings_account_id
        )
    
    def test_get_transfer_status_success(self):
        """Test successful retrieval of transfer status"""
        # Mock requests.get to return successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {'status': 'completed', 'transferId': 'transfer123'}
        
        with patch('requests.get', return_value=mock_response):
            transfer_id = "transfer123"
            response = self.client.get_transfer_status(transfer_id)
        
        assert response['status'] == 'completed'
        requests.get.assert_called_once()
        args, kwargs = requests.get.call_args
        assert f"/transfers/{transfer_id}" in args[0]
    
    def test_verify_transfer_completion_success(self):
        """Test verification of completed transfer"""
        # Mock get_transfer_status to return completed status
        with patch.object(self.client, 'get_transfer_status', return_value={'status': 'completed'}):
            transfer_id = "transfer123"
            result = self.client.verify_transfer_completion(transfer_id)
        
        assert result is True
        self.client.get_transfer_status.assert_called_with(transfer_id)
    
    def test_verify_transfer_completion_pending(self):
        """Test verification of pending transfer"""
        # Mock get_transfer_status to return pending status
        with patch.object(self.client, 'get_transfer_status', return_value={'status': 'pending'}):
            transfer_id = "transfer123"
            result = self.client.verify_transfer_completion(transfer_id)
        
        assert result is False
        self.client.get_transfer_status.assert_called_with(transfer_id)
    
    def test_get_weekly_transactions_success(self):
        """Test retrieval of weekly transactions"""
        # Mock get_date_range to return specific dates
        mock_dates = ("2023-07-01", "2023-07-07")
        
        # Mock get_transactions to return transaction data
        transaction_data = {'transactions': [
            {'merchant': {'name': 'Store A'}, 'amount': '10.00', 'transactionDate': '2023-07-01T12:00:00Z'},
            {'merchant': {'name': 'Store B'}, 'amount': '20.00', 'transactionDate': '2023-07-02T12:00:00Z'}
        ]}
        
        with patch('...backend.api_clients.capital_one_client.get_date_range', return_value=mock_dates):
            with patch.object(self.client, 'get_transactions', return_value=transaction_data):
                # Mock the create_transactions_from_capital_one function
                mock_transactions = [
                    Transaction(location='Store A', amount=Decimal('10.00'), timestamp=datetime.now()),
                    Transaction(location='Store B', amount=Decimal('20.00'), timestamp=datetime.now())
                ]
                with patch('...backend.api_clients.capital_one_client.create_transactions_from_capital_one', 
                          return_value=mock_transactions):
                    result = self.client.get_weekly_transactions()
        
        assert len(result) == 2
        assert result[0].location == 'Store A'
        assert result[1].location == 'Store B'
        
        self.client.get_transactions.assert_called_with(mock_dates[0], mock_dates[1])
    
    def test_get_weekly_transactions_error(self):
        """Test handling of errors during weekly transaction retrieval"""
        # Mock get_date_range to return specific dates
        mock_dates = ("2023-07-01", "2023-07-07")
        
        # Mock get_transactions to return error
        error_response = {'status': 'error', 'error_message': 'API Error'}
        
        with patch('...backend.api_clients.capital_one_client.get_date_range', return_value=mock_dates):
            with patch.object(self.client, 'get_transactions', return_value=error_response):
                result = self.client.get_weekly_transactions()
        
        assert result == []
        
        self.client.get_transactions.assert_called_with(mock_dates[0], mock_dates[1])
    
    def test_test_connectivity_success(self):
        """Test successful connectivity test"""
        # Mock authenticate to return True
        with patch.object(self.client, 'authenticate', return_value=True):
            # Mock get_checking_account_details to return account data
            with patch.object(self.client, 'get_checking_account_details', return_value={'accountId': 'account123'}):
                result = self.client.test_connectivity()
        
        assert result is True
        self.client.authenticate.assert_called_once()
        self.client.get_checking_account_details.assert_called_once()
    
    def test_test_connectivity_auth_failure(self):
        """Test connectivity test with authentication failure"""
        # Mock authenticate to return False
        with patch.object(self.client, 'authenticate', return_value=False):
            result = self.client.test_connectivity()
        
        assert result is False
        self.client.authenticate.assert_called_once()
        # Should not call get_checking_account_details if authentication fails
        assert not self.client.get_checking_account_details.called
    
    def test_retry_with_backoff(self):
        """Test retry mechanism for API calls"""
        # Mock requests.get to fail once, then succeed
        mock_response_success = MagicMock()
        mock_response_success.json.return_value = self.transactions_fixture
        
        # Create a side_effect that raises an exception on first call, then returns success
        side_effect = [RequestException("Temporary failure"), mock_response_success]
        
        with patch('requests.get', side_effect=side_effect):
            start_date, end_date = "2023-07-01", "2023-07-07"
            response = self.client.get_transactions(start_date, end_date)
        
        assert response == self.transactions_fixture
        assert requests.get.call_count == 2
    
    def test_format_date_for_api(self):
        """Test date formatting for API requests"""
        test_date = datetime(2023, 7, 15)
        result = format_date_for_api(test_date)
        assert result == "2023-07-15"
    
    def test_get_date_range(self):
        """Test date range calculation for weekly transactions"""
        # Call the function to get the date range
        start_date, end_date = get_date_range()
        
        # Verify basic properties of the results
        assert isinstance(start_date, str)
        assert isinstance(end_date, str)
        
        # Parse the dates to check the difference
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        # The difference should be 7 days
        delta = end - start
        assert delta.days == 7
        
        # The end date should be close to today
        today = datetime.now().date()
        end_date_obj = end.date()
        assert abs((today - end_date_obj).days) <= 1  # Allow for day boundary