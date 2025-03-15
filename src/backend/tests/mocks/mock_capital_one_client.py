"""
Mock implementation of the Capital One API client for testing purposes.

This module provides a mock version of the Capital One API client that simulates
API responses without making actual network calls, allowing for consistent and
controlled testing of transaction retrieval, account access, and fund transfer
operations.
"""

import datetime  # standard library
import decimal  # standard library
from decimal import Decimal  # standard library
import uuid  # standard library
from typing import List, Dict, Optional, Union  # standard library

from ...api_clients.capital_one_client import (
    CapitalOneClient, 
    format_date_for_api, 
    get_date_range
)
from ...models.transaction import create_transactions_from_capital_one
from ...models.transfer import create_transfer, create_transfer_from_capital_one_response
from ..fixtures.transactions import load_transaction_data

# Default values for testing
DEFAULT_CHECKING_ACCOUNT_ID = 'checking-12345'
DEFAULT_SAVINGS_ACCOUNT_ID = 'savings-67890'
DEFAULT_CHECKING_BALANCE = Decimal('1000.00')
DEFAULT_SAVINGS_BALANCE = Decimal('5000.00')
MOCK_AUTH_TOKEN = 'mock-capital-one-token'


def generate_transaction_id():
    """
    Generates a unique transaction ID for mock transactions
    
    Returns:
        Unique transaction ID string
    """
    return str(uuid.uuid4())


def generate_transfer_id():
    """
    Generates a unique transfer ID for mock transfers
    
    Returns:
        Unique transfer ID string
    """
    return str(uuid.uuid4())


def create_mock_transaction_response(transactions):
    """
    Creates a mock API response for transaction retrieval
    
    Args:
        transactions: List of transactions to include in response
        
    Returns:
        Mock API response with transactions
    """
    response = {'transactions': []}
    
    for transaction in transactions:
        # Format transaction for API response format
        tx_dict = {}
        tx_dict['location'] = transaction.get('location', '')
        tx_dict['amount'] = f"{Decimal(str(transaction.get('amount', 0))):.2f}"
        tx_dict['timestamp'] = transaction.get('timestamp', datetime.datetime.now().isoformat())
        
        # Add transaction_id if not present
        if 'transaction_id' not in transaction:
            tx_dict['transaction_id'] = generate_transaction_id()
        else:
            tx_dict['transaction_id'] = transaction['transaction_id']
            
        if 'description' in transaction:
            tx_dict['description'] = transaction['description']
            
        response['transactions'].append(tx_dict)
    
    return response


def create_mock_account_response(account_id, balance):
    """
    Creates a mock API response for account details
    
    Args:
        account_id: Account ID to use in the response
        balance: Balance amount for the account
        
    Returns:
        Mock API response with account details
    """
    account_type = 'checking' if 'check' in account_id.lower() else 'savings'
    
    return {
        'accountId': account_id,
        'accountType': account_type,
        'balance': f"{Decimal(str(balance)):.2f}",
        'status': 'active'
    }


def create_mock_transfer_response(amount, source_account_id, destination_account_id, 
                                 transfer_id, status='pending'):
    """
    Creates a mock API response for transfer initiation
    
    Args:
        amount: Transfer amount
        source_account_id: Source account ID
        destination_account_id: Destination account ID
        transfer_id: Unique transfer ID
        status: Transfer status (default: 'pending')
        
    Returns:
        Mock API response with transfer details
    """
    return {
        'transferId': transfer_id,
        'amount': f"{Decimal(str(amount)):.2f}",
        'sourceAccountId': source_account_id,
        'destinationAccountId': destination_account_id,
        'status': status,
        'timestamp': datetime.datetime.now().isoformat()
    }


class MockAuthenticationService:
    """Mock authentication service for testing"""
    
    def __init__(self, auth_success=True):
        """
        Initialize the mock authentication service
        
        Args:
            auth_success: Whether authentication should succeed
        """
        self.auth_success = auth_success
        self.token = MOCK_AUTH_TOKEN
    
    def authenticate_capital_one(self):
        """
        Mock authentication with Capital One API
        
        Returns:
            Mock authentication response
        
        Raises:
            AuthenticationError: If auth_success is False
        """
        if self.auth_success:
            return {'access_token': self.token, 'expires_in': 3600}
        else:
            raise Exception("Authentication failed")
    
    def get_token(self, service_name):
        """
        Get mock authentication token
        
        Args:
            service_name: Name of the service
            
        Returns:
            Mock authentication token
        """
        if service_name == 'capital_one' and self.auth_success:
            return self.token
        return None
    
    def refresh_token(self, service_name):
        """
        Mock token refresh
        
        Args:
            service_name: Name of the service
            
        Returns:
            Success status of refresh
        """
        return self.auth_success


class MockCapitalOneClient:
    """Mock implementation of the Capital One API client for testing"""
    
    def __init__(self, auth_service=None, auth_success=True, api_error=False, 
                 mock_transactions=None, checking_account_id=None, 
                 savings_account_id=None, checking_balance=None,
                 savings_balance=None):
        """
        Initialize the mock Capital One client
        
        Args:
            auth_service: Optional authentication service mock
            auth_success: Whether authentication should succeed
            api_error: Whether to simulate API errors
            mock_transactions: Optional list of mock transactions
            checking_account_id: Custom checking account ID
            savings_account_id: Custom savings account ID
            checking_balance: Custom checking account balance
            savings_balance: Custom savings account balance
        """
        # Set base URLs for mock API
        self.base_url = 'https://api.mock.capitalone.com'
        self.auth_url = 'https://auth.mock.capitalone.com'
        
        # Set account IDs
        self.checking_account_id = checking_account_id or DEFAULT_CHECKING_ACCOUNT_ID
        self.savings_account_id = savings_account_id or DEFAULT_SAVINGS_ACCOUNT_ID
        
        # Set authentication behavior
        self.auth_success = auth_success
        self.api_error = api_error
        self.auth_service = auth_service or MockAuthenticationService(auth_success)
        
        # Initialize transaction storage
        self.transactions = {}
        
        # Initialize account storage with balances
        self.accounts = {
            self.checking_account_id: create_mock_account_response(
                self.checking_account_id, 
                checking_balance or DEFAULT_CHECKING_BALANCE
            ),
            self.savings_account_id: create_mock_account_response(
                self.savings_account_id, 
                savings_balance or DEFAULT_SAVINGS_BALANCE
            )
        }
        
        # Initialize transfer storage
        self.transfers = {}
        
        # Transfer tracking properties
        self.transfer_initiated = False
        self.transfer_amount = Decimal('0.00')
        
        # Load mock transactions if provided, otherwise load from fixtures
        if mock_transactions:
            self.set_transactions(mock_transactions)
        else:
            # Load from fixture data
            self.set_transactions(load_transaction_data())
    
    def authenticate(self):
        """
        Mock authentication with Capital One API
        
        Returns:
            True if authentication successful, False otherwise
        """
        return self.auth_success
    
    def get_auth_headers(self):
        """
        Get mock authentication headers
        
        Returns:
            Headers dictionary with mock authentication token
        """
        if self.auth_success:
            return {'Authorization': f'Bearer {MOCK_AUTH_TOKEN}'}
        return {}
    
    def refresh_auth_token(self):
        """
        Mock refresh of authentication token
        
        Returns:
            True if refresh successful, False otherwise
        """
        return self.auth_success
    
    def set_transactions(self, transactions):
        """
        Set mock transactions for testing
        
        Args:
            transactions: List of transaction dictionaries
        """
        self.transactions = {}
        for tx in transactions:
            tx_id = tx.get('transaction_id', generate_transaction_id())
            self.transactions[tx_id] = tx
    
    def set_account_balance(self, account_id, balance):
        """
        Set mock account balance for testing
        
        Args:
            account_id: Account ID to update
            balance: New balance amount
        """
        if account_id in self.accounts:
            self.accounts[account_id]['balance'] = f"{Decimal(str(balance)):.2f}"
    
    def set_api_error(self, error_state):
        """
        Set API error flag for testing error scenarios
        
        Args:
            error_state: True to simulate API errors, False otherwise
        """
        self.api_error = error_state
    
    def get_transactions(self, start_date=None, end_date=None):
        """
        Mock retrieval of transactions from Capital One API
        
        Args:
            start_date: Start date for transaction range
            end_date: End date for transaction range
            
        Returns:
            Mock API response with transactions
        """
        if self.api_error:
            return {
                'status': 'error',
                'error_message': 'API error retrieving transactions',
                'operation': 'get_transactions'
            }
        
        # Get default date range if not provided
        if not start_date or not end_date:
            start_date, end_date = get_date_range()
        
        # Filter transactions by date range
        filtered_transactions = []
        for tx_id, tx in self.transactions.items():
            # Include transaction if within date range
            # In a real implementation, we would parse dates and compare,
            # but for simplicity in the mock, we'll include all transactions
            filtered_transactions.append(tx)
        
        return create_mock_transaction_response(filtered_transactions)
    
    def get_account_details(self, account_id):
        """
        Mock retrieval of account details from Capital One API
        
        Args:
            account_id: Account ID to get details for
            
        Returns:
            Mock API response with account details
        """
        if self.api_error:
            return {
                'status': 'error',
                'error_message': 'API error retrieving account details',
                'operation': 'get_account_details'
            }
        
        if account_id in self.accounts:
            return self.accounts[account_id]
        
        return {
            'status': 'error',
            'error_message': f'Account not found: {account_id}',
            'operation': 'get_account_details'
        }
    
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
            source_account_id: Source account ID
            destination_account_id: Destination account ID
            
        Returns:
            Mock API response with transfer details
        """
        if self.api_error:
            return {
                'status': 'error',
                'error_message': 'API error initiating transfer',
                'operation': 'initiate_transfer'
            }
        
        # Validate accounts exist
        if source_account_id not in self.accounts:
            return {
                'status': 'error',
                'error_message': f'Source account not found: {source_account_id}',
                'operation': 'initiate_transfer'
            }
        
        if destination_account_id not in self.accounts:
            return {
                'status': 'error',
                'error_message': f'Destination account not found: {destination_account_id}',
                'operation': 'initiate_transfer'
            }
        
        # Validate sufficient funds
        source_balance = Decimal(self.accounts[source_account_id]['balance'])
        decimal_amount = Decimal(str(amount))
        
        if source_balance < decimal_amount:
            return {
                'status': 'error',
                'error_message': 'Insufficient funds for transfer',
                'operation': 'initiate_transfer'
            }
        
        # Generate transfer ID
        transfer_id = generate_transfer_id()
        
        # Create transfer
        transfer = create_transfer(
            amount=decimal_amount,
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            transfer_id=transfer_id,
            status='pending'
        )
        
        # Create mock response
        response = create_mock_transfer_response(
            amount=decimal_amount,
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            transfer_id=transfer_id
        )
        
        # Store transfer in mock state
        self.transfers[transfer_id] = response
        
        # Update account balances
        source_balance = Decimal(self.accounts[source_account_id]['balance'])
        dest_balance = Decimal(self.accounts[destination_account_id]['balance'])
        
        self.accounts[source_account_id]['balance'] = f"{(source_balance - decimal_amount):.2f}"
        self.accounts[destination_account_id]['balance'] = f"{(dest_balance + decimal_amount):.2f}"
        
        # Set transfer status
        self.transfer_initiated = True
        self.transfer_amount = decimal_amount
        
        return response
    
    def transfer_to_savings(self, amount):
        """
        Mock transfer from checking to savings account
        
        Args:
            amount: Amount to transfer
            
        Returns:
            Mock API response with transfer details
        """
        return self.initiate_transfer(
            amount=amount,
            source_account_id=self.checking_account_id,
            destination_account_id=self.savings_account_id
        )
    
    def get_transfer_status(self, transfer_id):
        """
        Mock retrieval of transfer status
        
        Args:
            transfer_id: ID of the transfer to check
            
        Returns:
            Mock API response with transfer status
        """
        if self.api_error:
            return {
                'status': 'error',
                'error_message': 'API error retrieving transfer status',
                'operation': 'get_transfer_status'
            }
        
        if transfer_id in self.transfers:
            return self.transfers[transfer_id]
        
        return {
            'status': 'error',
            'error_message': f'Transfer not found: {transfer_id}',
            'operation': 'get_transfer_status'
        }
    
    def verify_transfer_completion(self, transfer_id):
        """
        Mock verification of transfer completion
        
        Args:
            transfer_id: ID of the transfer to verify
            
        Returns:
            True if transfer completed successfully, False otherwise
        """
        if self.api_error:
            return False
        
        if transfer_id in self.transfers:
            return self.transfers[transfer_id]['status'] == 'completed'
        
        return False
    
    def complete_all_transfers(self):
        """
        Mark all pending transfers as completed for testing
        """
        for transfer_id, transfer in self.transfers.items():
            if transfer['status'] == 'pending':
                transfer['status'] = 'completed'
    
    def fail_all_transfers(self):
        """
        Mark all pending transfers as failed for testing
        """
        for transfer_id, transfer in self.transfers.items():
            if transfer['status'] == 'pending':
                transfer['status'] = 'failed'
    
    def get_weekly_transactions(self):
        """
        Mock retrieval of transactions from the past week
        
        Returns:
            List of Transaction objects
        """
        # Get date range for past week
        start_date, end_date = get_date_range()
        
        # Call get_transactions with date range
        response = self.get_transactions(start_date, end_date)
        
        # Return empty list on error
        if response.get('status') == 'error':
            return []
        
        # Extract transactions from response
        transactions = response.get('transactions', [])
        
        # Convert to Transaction objects
        return create_transactions_from_capital_one(transactions)
    
    def test_connectivity(self):
        """
        Mock test of connectivity to Capital One API
        
        Returns:
            True if connection successful, False otherwise
        """
        return not self.api_error