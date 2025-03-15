"""
savings_automator.py - Component for automating the transfer of budget surplus to savings

This component is responsible for the final step in the budget management workflow, 
calculating and executing the transfer of unspent budget funds to a savings account
based on the budget analysis results.
"""

import decimal  # standard library
from decimal import Decimal  # standard library
import time  # standard library
from typing import Dict, Optional  # standard library

from ..api_clients.capital_one_client import CapitalOneClient
from ..models.transfer import Transfer, create_transfer_from_capital_one_response
from ..utils.validation import is_valid_transfer_amount
from ..config.settings import APP_SETTINGS
from ..services.logging_service import get_component_logger, LoggingContext
from ..services.error_handling_service import (
    with_error_handling,
    graceful_degradation,
    with_circuit_breaker
)
from ..services.authentication_service import AuthenticationService

# Set up logger for this component
logger = get_component_logger('savings_automator')

class SavingsAutomator:
    """Component responsible for automating the transfer of budget surplus to a savings account"""
    
    def __init__(self, capital_one_client: Optional[CapitalOneClient] = None, 
                 auth_service: Optional[AuthenticationService] = None):
        """
        Initialize the Savings Automator component
        
        Args:
            capital_one_client: Optional pre-configured Capital One client
            auth_service: Optional pre-configured authentication service
        """
        # Initialize authentication service
        self.auth_service = auth_service or AuthenticationService()
        
        # Initialize Capital One client
        self.capital_one_client = capital_one_client or CapitalOneClient(self.auth_service)
        
        # Initialize tracking variables
        self.correlation_id = None
        self.transfer_amount = Decimal('0')
        self.transfer = None
        self.transfer_successful = False
        
        logger.info("Savings Automator component initialized")
    
    def authenticate(self) -> bool:
        """
        Authenticate with Capital One API
        
        Returns:
            True if authentication successful, False otherwise
        """
        logger.info("Starting authentication with Capital One API")
        
        # Authenticate with Capital One API
        auth_success = self.capital_one_client.authenticate()
        
        if auth_success:
            logger.info("Successfully authenticated with Capital One API")
        else:
            logger.error("Failed to authenticate with Capital One API")
        
        return auth_success
    
    def validate_transfer_amount(self, amount: Decimal) -> bool:
        """
        Validate that the transfer amount meets requirements
        
        Args:
            amount: Amount to validate for transfer
            
        Returns:
            True if amount is valid for transfer, False otherwise
        """
        # Check if amount is positive
        if amount <= 0:
            logger.info(f"Transfer amount {amount} is not positive, no transfer needed")
            return False
        
        # Validate amount meets minimum transfer threshold
        min_transfer_amount = APP_SETTINGS["MIN_TRANSFER_AMOUNT"]
        if not is_valid_transfer_amount(amount, min_transfer_amount):
            logger.warning(
                f"Transfer amount {amount} does not meet minimum threshold of {min_transfer_amount}"
            )
            return False
        
        logger.info(f"Transfer amount {amount} is valid for processing")
        return True
    
    @with_circuit_breaker('capital_one', failure_threshold=3, recovery_timeout=300)
    def verify_account_status(self) -> bool:
        """
        Verify that both checking and savings accounts are active
        
        Returns:
            True if both accounts are active, False otherwise
        """
        logger.info("Verifying account status for checking and savings accounts")
        
        # Get checking account details
        checking_account = self.capital_one_client.get_checking_account_details()
        
        # Verify checking account is active
        if checking_account.get('status') != 'active':
            logger.error(f"Checking account is not active: {checking_account.get('status')}")
            return False
        
        # Get savings account details
        savings_account = self.capital_one_client.get_savings_account_details()
        
        # Verify savings account is active
        if savings_account.get('status') != 'active':
            logger.error(f"Savings account is not active: {savings_account.get('status')}")
            return False
        
        logger.info("Both checking and savings accounts are active")
        return True
    
    @with_circuit_breaker('capital_one', failure_threshold=3, recovery_timeout=300)
    def verify_sufficient_funds(self, amount: Decimal) -> bool:
        """
        Verify that checking account has sufficient funds for transfer
        
        Args:
            amount: Amount to transfer
            
        Returns:
            True if sufficient funds available, False otherwise
        """
        logger.info(f"Verifying sufficient funds for transfer of {amount}")
        
        # Get checking account details
        checking_account = self.capital_one_client.get_checking_account_details()
        
        # Extract available balance
        available_balance = Decimal(str(checking_account.get('availableBalance', '0')))
        
        # Verify sufficient funds
        if available_balance < amount:
            logger.error(
                f"Insufficient funds for transfer: available balance {available_balance}, "
                f"transfer amount {amount}"
            )
            return False
        
        logger.info(
            f"Sufficient funds available for transfer: available balance {available_balance}, "
            f"transfer amount {amount}"
        )
        return True
    
    @with_circuit_breaker('capital_one', failure_threshold=3, recovery_timeout=300)
    def initiate_transfer(self, amount: Decimal) -> Dict:
        """
        Initiate transfer from checking to savings account
        
        Args:
            amount: Amount to transfer
            
        Returns:
            Transfer result with status and details
        """
        logger.info(f"Initiating transfer of {amount} to savings account")
        
        # Call Capital One API to transfer funds
        transfer_response = self.capital_one_client.transfer_to_savings(amount)
        
        # Create Transfer object from response
        self.transfer = create_transfer_from_capital_one_response(transfer_response)
        
        if self.transfer:
            logger.info(
                f"Transfer initiated successfully with ID: {self.transfer.transfer_id}"
            )
            return {
                'status': 'success',
                'transfer_id': self.transfer.transfer_id,
                'amount': str(amount),
                'timestamp': self.transfer.timestamp.isoformat()
            }
        else:
            logger.error("Failed to create transfer from API response")
            return {
                'status': 'error',
                'error_message': 'Failed to process transfer response',
                'original_response': transfer_response
            }
    
    @with_circuit_breaker('capital_one', failure_threshold=3, recovery_timeout=300)
    def verify_transfer(self, transfer_id: str) -> bool:
        """
        Verify that the transfer completed successfully
        
        Args:
            transfer_id: ID of the transfer to verify
            
        Returns:
            True if transfer completed successfully, False otherwise
        """
        logger.info(f"Verifying completion of transfer {transfer_id}")
        
        # Call Capital One API to check transfer status
        verification_result = self.capital_one_client.verify_transfer_completion(transfer_id)
        
        # Update transfer status based on verification
        if self.transfer:
            transfer_status = 'completed' if verification_result else 'failed'
            self.transfer.update_status(transfer_status)
        
        if verification_result:
            logger.info(f"Transfer {transfer_id} verified as completed")
            self.transfer_successful = True
        else:
            logger.warning(f"Transfer {transfer_id} could not be verified as completed")
        
        return verification_result
    
    @with_error_handling('savings_automator', 'transfer_surplus', {})
    def transfer_surplus(self, amount: Decimal) -> Dict:
        """
        Transfer budget surplus to savings account
        
        Args:
            amount: Amount to transfer
            
        Returns:
            Transfer result with status and details
        """
        logger.info(f"Processing surplus transfer of {amount}")
        
        # Validate transfer amount
        if not self.validate_transfer_amount(amount):
            logger.info("No valid transfer amount, skipping transfer")
            return {
                'status': 'no_transfer',
                'reason': 'Invalid transfer amount',
                'amount': str(amount)
            }
        
        # Verify account status
        if not self.verify_account_status():
            logger.error("Account status verification failed, cannot proceed with transfer")
            return {
                'status': 'error',
                'error_message': 'Account status verification failed',
                'amount': str(amount)
            }
        
        # Verify sufficient funds
        if not self.verify_sufficient_funds(amount):
            logger.error("Insufficient funds verification failed, cannot proceed with transfer")
            return {
                'status': 'error',
                'error_message': 'Insufficient funds for transfer',
                'amount': str(amount)
            }
        
        # Initiate transfer
        transfer_result = self.initiate_transfer(amount)
        
        # If transfer was initiated successfully, verify completion
        if transfer_result.get('status') == 'success' and 'transfer_id' in transfer_result:
            transfer_id = transfer_result['transfer_id']
            verification_result = self.verify_transfer(transfer_id)
            
            transfer_result['verified'] = verification_result
            transfer_result['transfer_successful'] = self.transfer_successful
        
        return transfer_result
    
    def execute(self, previous_status: Dict) -> Dict:
        """
        Execute the savings automation process
        
        Args:
            previous_status: Status information from previous components
            
        Returns:
            Execution status and transfer results
        """
        logger.info("Starting savings automation execution")
        
        # Record start time for performance measurement
        start_time = time.time()
        
        try:
            # Extract correlation_id from previous_status if available
            self.correlation_id = previous_status.get('correlation_id')
            
            # Extract transfer amount from budget analysis results
            budget_analysis = previous_status.get('budget_analysis', {})
            self.transfer_amount = Decimal(str(budget_analysis.get('total_variance', '0')))
            
            # Use logging context for consistent logging
            with LoggingContext(logger, "savings_automation", {
                'correlation_id': self.correlation_id,
                'transfer_amount': str(self.transfer_amount)
            }):
                # Authenticate with Capital One API
                if not self.authenticate():
                    return {
                        'status': 'error',
                        'component': 'savings_automator',
                        'error_message': 'Authentication failed',
                        'correlation_id': self.correlation_id,
                        'execution_time': time.time() - start_time
                    }
                
                # If no surplus or negative (deficit), log and return success with no transfer
                if self.transfer_amount <= 0:
                    logger.info(f"No budget surplus to transfer (amount: {self.transfer_amount})")
                    return {
                        'status': 'success',
                        'component': 'savings_automator',
                        'message': 'No budget surplus to transfer',
                        'transfer_amount': str(self.transfer_amount),
                        'transfer_executed': False,
                        'correlation_id': self.correlation_id,
                        'execution_time': time.time() - start_time
                    }
                
                # Transfer surplus
                transfer_result = self.transfer_surplus(self.transfer_amount)
                
                # Calculate execution time
                execution_time = time.time() - start_time
                
                # Return result with execution metadata
                result = {
                    'status': 'success',
                    'component': 'savings_automator',
                    'transfer_result': transfer_result,
                    'transfer_amount': str(self.transfer_amount),
                    'transfer_executed': True,
                    'transfer_successful': self.transfer_successful,
                    'correlation_id': self.correlation_id,
                    'execution_time': execution_time
                }
                
                logger.info(
                    f"Savings automation completed in {execution_time:.2f}s with status: "
                    f"{transfer_result.get('status')}"
                )
                
                return result
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error during savings automation: {str(e)}")
            
            return {
                'status': 'error',
                'component': 'savings_automator',
                'error_message': str(e),
                'correlation_id': self.correlation_id,
                'execution_time': execution_time
            }
    
    def check_health(self) -> Dict:
        """
        Check health of Capital One API connection
        
        Returns:
            Health status of Capital One integration
        """
        health_status = {
            'component': 'savings_automator',
            'capital_one_connection': 'unknown'
        }
        
        try:
            # Test Capital One API connectivity
            connectivity = self.capital_one_client.test_connectivity()
            health_status['capital_one_connection'] = 'healthy' if connectivity else 'unhealthy'
            
            logger.info(f"Health check completed: Capital One connection is {health_status['capital_one_connection']}")
            
        except Exception as e:
            health_status['capital_one_connection'] = 'unhealthy'
            health_status['error'] = str(e)
            logger.error(f"Health check error: {str(e)}")
        
        return health_status