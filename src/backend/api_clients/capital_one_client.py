"""
capital_one_client.py - Client for interacting with the Capital One API

This module provides a client for retrieving transaction data and performing
fund transfers through the Capital One API with comprehensive error handling,
retry mechanisms, and secure financial data processing.
"""

import requests  # requests 2.31.0+
import datetime  # standard library
import decimal  # standard library
from decimal import Decimal  # standard library
from typing import List, Dict, Optional, Union  # standard library

from ..config.settings import API_SETTINGS, RETRY_SETTINGS
from ..config.logging_config import get_logger
from ..services.authentication_service import AuthenticationService
from ..utils.error_handlers import retry_with_backoff, handle_api_error, APIError
from ..models.transaction import create_transactions_from_capital_one
from ..models.transfer import create_transfer, create_transfer_from_capital_one_response

# Set up logger
logger = get_logger('capital_one_client')


def format_date_for_api(date):
    """
    Formats a datetime object to the format expected by Capital One API
    
    Args:
        date: Date to format
        
    Returns:
        Formatted date string in ISO format (YYYY-MM-DD)
    """
    return date.strftime("%Y-%m-%d")


def get_date_range():
    """
    Calculates the date range for transaction retrieval (past 7 days)
    
    Returns:
        Tuple of (start_date, end_date) as formatted strings
    """
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=7)
    
    return (
        format_date_for_api(start_date),
        format_date_for_api(end_date)
    )


def mask_account_id(account_id):
    """
    Masks an account ID for secure logging
    
    Args:
        account_id: Account ID to mask
        
    Returns:
        Masked account ID with only last 4 digits visible
    """
    if isinstance(account_id, str) and len(account_id) > 4:
        masked = 'X' * (len(account_id) - 4) + account_id[-4:]
        return masked
    elif isinstance(account_id, str):
        return account_id  # If it's too short, just return it
    else:
        return '[INVALID_ACCOUNT_ID]'


class CapitalOneClient:
    """Client for interacting with the Capital One API"""
    
    def __init__(self, auth_service):
        """
        Initialize the Capital One API client
        
        Args:
            auth_service: AuthenticationService instance for handling API authentication
        """
        self.auth_service = auth_service
        
        # Get settings from configuration
        capital_one_settings = API_SETTINGS['CAPITAL_ONE']
        self.base_url = capital_one_settings['BASE_URL']
        self.auth_url = capital_one_settings['AUTH_URL']
        self.checking_account_id = capital_one_settings['CHECKING_ACCOUNT_ID']
        self.savings_account_id = capital_one_settings['SAVINGS_ACCOUNT_ID']
        
        logger.info("Capital One API client initialized")
    
    def authenticate(self):
        """
        Authenticate with the Capital One API
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Use authentication service to authenticate with Capital One
            self.auth_service.authenticate_capital_one()
            logger.info("Successfully authenticated with Capital One API")
            return True
        except Exception as e:
            logger.error(f"Authentication with Capital One API failed: {str(e)}")
            return False
    
    def get_auth_headers(self):
        """
        Get authentication headers for API requests
        
        Returns:
            Headers dictionary with authentication token
        """
        try:
            # Get token from authentication service
            token = self.auth_service.get_token('CAPITAL_ONE')
            
            # Create headers with token
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            return headers
        except Exception as e:
            logger.error(f"Failed to get authentication headers: {str(e)}")
            raise
    
    def refresh_auth_token(self):
        """
        Refresh the authentication token if expired
        
        Returns:
            True if refresh successful, False otherwise
        """
        try:
            result = self.auth_service.refresh_token('CAPITAL_ONE')
            if result:
                logger.info("Successfully refreshed Capital One authentication token")
            else:
                logger.error("Failed to refresh Capital One authentication token")
            return result
        except Exception as e:
            logger.error(f"Error refreshing authentication token: {str(e)}")
            return False
    
    @retry_with_backoff(requests.RequestException, max_retries=RETRY_SETTINGS['DEFAULT_MAX_RETRIES'])
    def get_transactions(self, start_date=None, end_date=None):
        """
        Retrieve transactions from the checking account for a date range
        
        Args:
            start_date: Start date for transaction range (YYYY-MM-DD)
            end_date: End date for transaction range (YYYY-MM-DD)
            
        Returns:
            API response with transactions or error details
        """
        try:
            # If dates not provided, use default (past 7 days)
            if not start_date or not end_date:
                start_date, end_date = get_date_range()
            
            # Build URL for transactions endpoint
            endpoint = f"{self.base_url}/accounts/{self.checking_account_id}/transactions"
            
            # Get authentication headers
            headers = self.get_auth_headers()
            
            # Set up query parameters
            params = {
                'startDate': start_date,
                'endDate': end_date
            }
            
            # Make API request
            logger.info(f"Retrieving transactions from {start_date} to {end_date}")
            response = requests.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            
            # Parse response
            transactions_data = response.json()
            logger.info(f"Successfully retrieved {len(transactions_data.get('transactions', []))} transactions")
            
            return transactions_data
            
        except requests.RequestException as e:
            error_context = {
                'start_date': start_date,
                'end_date': end_date,
                'account_id': mask_account_id(self.checking_account_id)
            }
            return handle_api_error(e, 'Capital One', 'get_transactions', error_context)
    
    @retry_with_backoff(requests.RequestException, max_retries=RETRY_SETTINGS['DEFAULT_MAX_RETRIES'])
    def get_account_details(self, account_id):
        """
        Retrieve details for a specific account
        
        Args:
            account_id: Account ID to get details for
            
        Returns:
            API response with account details or error details
        """
        try:
            # Build URL for account endpoint
            endpoint = f"{self.base_url}/accounts/{account_id}"
            
            # Get authentication headers
            headers = self.get_auth_headers()
            
            # Make API request
            logger.info(f"Retrieving account details for {mask_account_id(account_id)}")
            response = requests.get(endpoint, headers=headers)
            response.raise_for_status()
            
            # Parse response
            account_data = response.json()
            logger.info(f"Successfully retrieved account details for {mask_account_id(account_id)}")
            
            return account_data
            
        except requests.RequestException as e:
            error_context = {
                'account_id': mask_account_id(account_id)
            }
            return handle_api_error(e, 'Capital One', 'get_account_details', error_context)
    
    def get_checking_account_details(self):
        """
        Retrieve details for the checking account
        
        Returns:
            API response with checking account details or error details
        """
        logger.info("Retrieving checking account details")
        return self.get_account_details(self.checking_account_id)
    
    def get_savings_account_details(self):
        """
        Retrieve details for the savings account
        
        Returns:
            API response with savings account details or error details
        """
        logger.info("Retrieving savings account details")
        return self.get_account_details(self.savings_account_id)
    
    @retry_with_backoff(requests.RequestException, max_retries=RETRY_SETTINGS['DEFAULT_MAX_RETRIES'])
    def initiate_transfer(self, amount, source_account_id, destination_account_id):
        """
        Initiate a transfer between accounts
        
        Args:
            amount: Amount to transfer
            source_account_id: Source account ID
            destination_account_id: Destination account ID
            
        Returns:
            API response with transfer details or error details
        """
        try:
            # Create transfer object
            transfer = create_transfer(
                amount=amount,
                source_account_id=source_account_id,
                destination_account_id=destination_account_id
            )
            
            if not transfer:
                raise ValueError(f"Failed to create valid transfer with amount {amount}")
            
            # Convert transfer to API format
            transfer_data = transfer.to_api_format()
            
            # Build URL for transfers endpoint
            endpoint = f"{self.base_url}/transfers"
            
            # Get authentication headers
            headers = self.get_auth_headers()
            
            # Make API request
            logger.info(
                f"Initiating transfer of {amount} from {mask_account_id(source_account_id)} "
                f"to {mask_account_id(destination_account_id)}"
            )
            response = requests.post(endpoint, headers=headers, json=transfer_data)
            response.raise_for_status()
            
            # Parse response
            transfer_response = response.json()
            
            # Create Transfer object from response
            result_transfer = create_transfer_from_capital_one_response(transfer_response)
            if not result_transfer:
                logger.warning("Failed to parse transfer response, returning raw response")
                return transfer_response
            
            logger.info(f"Successfully initiated transfer with ID: {result_transfer.transfer_id}")
            
            return result_transfer.to_dict()
            
        except requests.RequestException as e:
            error_context = {
                'amount': str(amount),
                'source_account_id': mask_account_id(source_account_id),
                'destination_account_id': mask_account_id(destination_account_id)
            }
            return handle_api_error(e, 'Capital One', 'initiate_transfer', error_context)
        except Exception as e:
            logger.error(f"Error initiating transfer: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'operation': 'initiate_transfer'
            }
    
    def transfer_to_savings(self, amount):
        """
        Transfer funds from checking to savings account
        
        Args:
            amount: Amount to transfer
            
        Returns:
            API response with transfer details or error details
        """
        logger.info(f"Initiating transfer of {amount} from checking to savings")
        return self.initiate_transfer(
            amount=amount,
            source_account_id=self.checking_account_id,
            destination_account_id=self.savings_account_id
        )
    
    @retry_with_backoff(requests.RequestException, max_retries=RETRY_SETTINGS['DEFAULT_MAX_RETRIES'])
    def get_transfer_status(self, transfer_id):
        """
        Check the status of a transfer
        
        Args:
            transfer_id: ID of the transfer to check
            
        Returns:
            API response with transfer status or error details
        """
        try:
            # Build URL for transfer status endpoint
            endpoint = f"{self.base_url}/transfers/{transfer_id}"
            
            # Get authentication headers
            headers = self.get_auth_headers()
            
            # Make API request
            logger.info(f"Checking status of transfer {transfer_id}")
            response = requests.get(endpoint, headers=headers)
            response.raise_for_status()
            
            # Parse response
            transfer_status = response.json()
            logger.info(f"Transfer {transfer_id} status: {transfer_status.get('status', 'unknown')}")
            
            return transfer_status
            
        except requests.RequestException as e:
            error_context = {
                'transfer_id': transfer_id
            }
            return handle_api_error(e, 'Capital One', 'get_transfer_status', error_context)
    
    def verify_transfer_completion(self, transfer_id):
        """
        Verify that a transfer has completed successfully
        
        Args:
            transfer_id: ID of the transfer to verify
            
        Returns:
            True if transfer completed successfully, False otherwise
        """
        try:
            # Get transfer status
            transfer_status = self.get_transfer_status(transfer_id)
            
            # Check if status field exists
            if 'status' not in transfer_status:
                logger.warning(f"Transfer status response missing 'status' field: {transfer_status}")
                return False
            
            # Check if status is completed
            is_completed = transfer_status['status'] == 'completed'
            
            if is_completed:
                logger.info(f"Transfer {transfer_id} completed successfully")
            else:
                logger.warning(f"Transfer {transfer_id} not completed: {transfer_status['status']}")
            
            return is_completed
            
        except Exception as e:
            logger.error(f"Error verifying transfer completion: {str(e)}")
            return False
    
    def get_weekly_transactions(self):
        """
        Get transactions from the past week
        
        Returns:
            List of Transaction objects or empty list on error
        """
        try:
            # Get date range for past week
            start_date, end_date = get_date_range()
            
            # Retrieve transactions from API
            response = self.get_transactions(start_date, end_date)
            
            # Check if response was successful
            if response.get('status') == 'error':
                logger.error(f"Error retrieving weekly transactions: {response.get('error_message')}")
                return []
            
            # Extract transactions from response
            transactions = response.get('transactions', [])
            
            # Convert to Transaction objects
            transaction_objects = create_transactions_from_capital_one(transactions)
            
            logger.info(f"Processed {len(transaction_objects)} weekly transactions")
            return transaction_objects
            
        except Exception as e:
            logger.error(f"Error retrieving weekly transactions: {str(e)}")
            return []
    
    def test_connectivity(self):
        """
        Test connectivity to the Capital One API
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to authenticate
            if not self.authenticate():
                logger.error("Connectivity test failed: Authentication failed")
                return False
            
            # Try a simple API call
            account_details = self.get_checking_account_details()
            
            # Check if response contains expected data
            if account_details.get('status') == 'error' or 'accountId' not in account_details:
                logger.error(f"Connectivity test failed: Could not retrieve account details")
                return False
            
            logger.info("Connectivity test successful")
            return True
            
        except Exception as e:
            logger.error(f"Connectivity test failed: {str(e)}")
            return False