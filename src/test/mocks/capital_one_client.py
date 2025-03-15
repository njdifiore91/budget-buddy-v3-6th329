"""
Mock implementation of the Capital One API client for testing purposes.
This class simulates the behavior of the real CapitalOneClient without making actual API calls,
providing predefined responses from test fixtures for transactions, account details, and fund transfers.
"""

import datetime
import decimal
from decimal import Decimal
import copy
from typing import List, Dict, Optional, Any

from ..utils.fixture_loader import load_fixture
from ...backend.models.transaction import create_transactions_from_capital_one
from ...backend.models.transfer import create_transfer_from_capital_one_response

# Default account IDs for testing
DEFAULT_CHECKING_ACCOUNT_ID = "acct_checking123"
DEFAULT_SAVINGS_ACCOUNT_ID = "acct_savings456"
DEFAULT_TRANSFER_ID = "tr_12345abcdef"

# Fixture paths
TRANSACTION_FIXTURE_PATH = "json/api_responses/capital_one/transactions.json"
ACCOUNT_FIXTURE_PATH = "json/api_responses/capital_one/accounts.json"
TRANSFER_FIXTURE_PATH = "json/api_responses/capital_one/transfer.json"
ERROR_RESPONSES_FIXTURE_PATH = "json/api_responses/capital_one/error_responses.json"


def format_date_for_api(date):
    """
    Formats a datetime object to the format expected by Capital One API (matches real implementation)
    
    Args:
        date: datetime object to format
        
    Returns:
        Formatted date string in ISO format (YYYY-MM-DD)
    """
    return date.strftime('%Y-%m-%d')


def get_date_range():
    """
    Calculates the date range for transaction retrieval (past 7 days) (matches real implementation)
    
    Returns:
        (start_date, end_date) as formatted strings
    """
    end_date = datetime.datetime.now().date()
    start_date = end_date - datetime.timedelta(days=7)
    return (format_date_for_api(start_date), format_date_for_api(end_date))


class MockCapitalOneClient:
    """
    Mock implementation of the Capital One API client for testing.
    Implements the same interface as the real CapitalOneClient without making actual API calls.
    """
    
    def __init__(self, client_id=None, client_secret=None, checking_account_id=None, 
                 savings_account_id=None, base_url=None, auth_url=None):
        """
        Initialize the mock Capital One API client
        
        Args:
            client_id: Optional client ID for authentication
            client_secret: Optional client secret for authentication
            checking_account_id: ID of the checking account to use
            savings_account_id: ID of the savings account to use
            base_url: Base URL for API requests
            auth_url: URL for authentication requests
        """
        self.base_url = base_url or "https://mock-capital-one-api.example.com"
        self.auth_url = auth_url or "https://mock-capital-one-api.example.com/oauth2/token"
        self.checking_account_id = checking_account_id or DEFAULT_CHECKING_ACCOUNT_ID
        self.savings_account_id = savings_account_id or DEFAULT_SAVINGS_ACCOUNT_ID
        
        # Authentication state
        self.authenticated = False
        
        # Load fixtures
        self.transaction_fixtures = load_fixture(TRANSACTION_FIXTURE_PATH)
        self.account_fixtures = load_fixture(ACCOUNT_FIXTURE_PATH)
        self.transfer_fixtures = load_fixture(TRANSFER_FIXTURE_PATH)
        self.error_fixtures = load_fixture(ERROR_RESPONSES_FIXTURE_PATH)
        
        # For tracking initiated transfers
        self.initiated_transfers = []
        
        # For simulating errors
        self.should_fail_authentication = False
        self.should_fail_transactions = False
        self.should_fail_accounts = False
        self.should_fail_transfers = False
    
    def authenticate(self):
        """
        Mock authentication with the Capital One API
        
        Returns:
            True if authentication successful, False otherwise
        """
        if self.should_fail_authentication:
            return False
            
        self.authenticated = True
        return True
    
    def get_transactions(self, account_id, start_date=None, end_date=None):
        """
        Mock retrieval of transactions from the specified account
        
        Args:
            account_id: ID of the account to get transactions from
            start_date: Optional start date for filtering transactions
            end_date: Optional end date for filtering transactions
            
        Returns:
            Mock API response with transactions
        """
        if not self.authenticated:
            return self.error_fixtures.get("authentication_error")
            
        if self.should_fail_transactions:
            return self.error_fixtures.get("transaction_error")
            
        # Use default date range if not provided
        if not start_date or not end_date:
            start_date, end_date = get_date_range()
            
        # Return a copy of the transactions fixture to prevent modification
        return copy.deepcopy(self.transaction_fixtures)
    
    def get_account_details(self, account_id):
        """
        Mock retrieval of account details
        
        Args:
            account_id: ID of the account to get details for
            
        Returns:
            Mock API response with account details
        """
        if not self.authenticated:
            return self.error_fixtures.get("authentication_error")
            
        if self.should_fail_accounts:
            return self.error_fixtures.get("account_error")
            
        # If account ID exists in account fixtures, return its details
        account = next((acc for acc in self.account_fixtures.get("accounts", []) 
                       if acc.get("accountId") == account_id), None)
                       
        if account:
            return {"account": copy.deepcopy(account)}
        else:
            return self.error_fixtures.get("unknown_account_error")
    
    def get_checking_account_details(self):
        """
        Mock retrieval of checking account details
        
        Returns:
            Mock API response with checking account details
        """
        return self.get_account_details(self.checking_account_id)
    
    def get_savings_account_details(self):
        """
        Mock retrieval of savings account details
        
        Returns:
            Mock API response with savings account details
        """
        return self.get_account_details(self.savings_account_id)
    
    def initiate_transfer(self, amount, source_account_id, destination_account_id):
        """
        Mock initiation of a transfer between accounts
        
        Args:
            amount: Amount to transfer
            source_account_id: ID of the source account
            destination_account_id: ID of the destination account
            
        Returns:
            Mock API response with transfer details
        """
        if not self.authenticated:
            return self.error_fixtures.get("authentication_error")
            
        if self.should_fail_transfers:
            return self.error_fixtures.get("transfer_error")
            
        # Create a copy of the transfer fixture
        transfer_response = copy.deepcopy(self.transfer_fixtures)
        
        # Update with provided details
        transfer_response["amount"] = str(amount)
        transfer_response["sourceAccountId"] = source_account_id
        transfer_response["destinationAccountId"] = destination_account_id
        transfer_response["transferId"] = DEFAULT_TRANSFER_ID
        transfer_response["status"] = "completed"
        
        # Add to initiated transfers for test assertions
        self.initiated_transfers.append(copy.deepcopy(transfer_response))
        
        return transfer_response
    
    def transfer_to_savings(self, amount):
        """
        Mock transfer from checking to savings account
        
        Args:
            amount: Amount to transfer
            
        Returns:
            Mock API response with transfer details
        """
        return self.initiate_transfer(
            amount, 
            self.checking_account_id, 
            self.savings_account_id
        )
    
    def get_transfer_status(self, transfer_id):
        """
        Mock checking of transfer status
        
        Args:
            transfer_id: ID of the transfer to check
            
        Returns:
            Mock API response with transfer status
        """
        if not self.authenticated:
            return self.error_fixtures.get("authentication_error")
            
        if self.should_fail_transfers:
            return self.error_fixtures.get("transfer_status_error")
            
        # Return a status object for the transfer
        transfer_status = copy.deepcopy(self.transfer_fixtures)
        transfer_status["transferId"] = transfer_id
        transfer_status["status"] = "completed"
        
        return transfer_status
    
    def verify_transfer_completion(self, transfer_id):
        """
        Mock verification of transfer completion
        
        Args:
            transfer_id: ID of the transfer to verify
            
        Returns:
            True if transfer completed successfully, False otherwise
        """
        response = self.get_transfer_status(transfer_id)
        
        if "status" in response:
            return response["status"] == "completed"
            
        return False
    
    def get_weekly_transactions(self):
        """
        Mock retrieval of transactions from the past week
        
        Returns:
            List of Transaction objects
        """
        start_date, end_date = get_date_range()
        response = self.get_transactions(self.checking_account_id, start_date, end_date)
        
        if response and "transactions" in response:
            transactions = response.get("transactions", [])
            return create_transactions_from_capital_one(transactions)
        
        return []
    
    def test_connectivity(self):
        """
        Mock testing of connectivity to the Capital One API
        
        Returns:
            True if connection successful, False otherwise
        """
        return self.authenticated and not self.should_fail_transactions and not self.should_fail_accounts
    
    def set_should_fail_authentication(self, should_fail):
        """
        Set whether authentication should fail (for testing error scenarios)
        
        Args:
            should_fail: Whether authentication should fail
        """
        self.should_fail_authentication = should_fail
    
    def set_should_fail_transactions(self, should_fail):
        """
        Set whether transaction retrieval should fail (for testing error scenarios)
        
        Args:
            should_fail: Whether transaction retrieval should fail
        """
        self.should_fail_transactions = should_fail
    
    def set_should_fail_accounts(self, should_fail):
        """
        Set whether account retrieval should fail (for testing error scenarios)
        
        Args:
            should_fail: Whether account retrieval should fail
        """
        self.should_fail_accounts = should_fail
    
    def set_should_fail_transfers(self, should_fail):
        """
        Set whether transfer operations should fail (for testing error scenarios)
        
        Args:
            should_fail: Whether transfer operations should fail
        """
        self.should_fail_transfers = should_fail
    
    def get_initiated_transfers(self):
        """
        Get list of transfers that have been initiated (for test assertions)
        
        Returns:
            List of initiated transfers
        """
        return copy.deepcopy(self.initiated_transfers)
    
    def reset(self):
        """
        Reset the mock client to its initial state
        """
        self.authenticated = False
        self.initiated_transfers = []
        self.should_fail_authentication = False
        self.should_fail_transactions = False
        self.should_fail_accounts = False
        self.should_fail_transfers = False
    
    def set_transactions(self, transactions):
        """
        Set custom transactions fixture for testing
        
        Args:
            transactions: Custom transactions data
        """
        self.transaction_fixtures = transactions
    
    def set_accounts(self, accounts):
        """
        Set custom accounts fixture for testing
        
        Args:
            accounts: Custom accounts data
        """
        self.account_fixtures = accounts
    
    def set_transfers(self, transfers):
        """
        Set custom transfers fixture for testing
        
        Args:
            transfers: Custom transfers data
        """
        self.transfer_fixtures = transfers