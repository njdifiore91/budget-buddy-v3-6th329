"""
transaction_retriever.py - Component for retrieving transaction data from Capital One API and storing it in Google Sheets

This component serves as the initial data acquisition module in the Budget Management Application workflow,
handling authentication, transaction retrieval, error handling, and data storage for financial transactions.
"""

from typing import List, Dict, Optional  # standard library

from ..api_clients.capital_one_client import CapitalOneClient
from ..api_clients.google_sheets_client import GoogleSheetsClient
from ..models.transaction import Transaction
from ..services.authentication_service import AuthenticationService
from ..utils.error_handlers import retry_with_backoff, handle_api_error, APIError
from ..config.logging_config import get_logger

# Set up logger
logger = get_logger('transaction_retriever')

class TransactionRetriever:
    """Component responsible for retrieving transactions from Capital One and storing them in Google Sheets"""
    
    def __init__(self, capital_one_client: Optional[CapitalOneClient] = None, 
                 sheets_client: Optional[GoogleSheetsClient] = None,
                 auth_service: Optional[AuthenticationService] = None):
        """
        Initialize the Transaction Retriever component
        
        Args:
            capital_one_client: Optional custom Capital One client
            sheets_client: Optional custom Google Sheets client
            auth_service: Optional custom authentication service
        """
        # Initialize auth_service with provided service or create new instance
        self.auth_service = auth_service or AuthenticationService()
        
        # Initialize capital_one_client with provided client or create new instance
        self.capital_one_client = capital_one_client or CapitalOneClient(self.auth_service)
        
        # Initialize sheets_client with provided client or create new instance
        self.sheets_client = sheets_client or GoogleSheetsClient(self.auth_service)
        
        logger.info("Transaction Retriever component initialized")
    
    def authenticate(self) -> bool:
        """
        Authenticate with both Capital One and Google Sheets APIs
        
        Returns:
            bool: True if authentication successful for both APIs, False otherwise
        """
        logger.info("Starting authentication process for APIs")
        
        # Authenticate with Capital One API
        capital_one_auth = self.capital_one_client.authenticate()
        if not capital_one_auth:
            logger.error("Failed to authenticate with Capital One API")
            return False
        
        # Authenticate with Google Sheets API
        sheets_auth = self.sheets_client.authenticate()
        if not sheets_auth:
            logger.error("Failed to authenticate with Google Sheets API")
            return False
        
        logger.info("Successfully authenticated with both APIs")
        return True
    
    @retry_with_backoff(exceptions=(APIError,), max_retries=3)
    def retrieve_transactions(self) -> List[Transaction]:
        """
        Retrieve transactions from Capital One API
        
        Returns:
            List[Transaction]: List of Transaction objects
        """
        logger.info("Starting transaction retrieval from Capital One")
        
        try:
            # Get transactions from past week
            transactions = self.capital_one_client.get_weekly_transactions()
            
            logger.info(f"Retrieved {len(transactions)} transactions from Capital One")
            return transactions
            
        except APIError as e:
            logger.error(f"Error retrieving transactions: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during transaction retrieval: {str(e)}")
            raise APIError(
                f"Transaction retrieval failed: {str(e)}",
                "Capital One",
                "retrieve_transactions"
            )
    
    @retry_with_backoff(exceptions=(APIError,), max_retries=3)
    def store_transactions(self, transactions: List[Transaction]) -> int:
        """
        Store transactions in Google Sheets
        
        Args:
            transactions: List of Transaction objects to store
            
        Returns:
            int: Number of transactions stored
        """
        logger.info(f"Starting storage of {len(transactions)} transactions in Google Sheets")
        
        try:
            # Store transactions in Weekly Spending sheet
            stored_count = self.sheets_client.append_transactions(transactions)
            
            logger.info(f"Successfully stored {stored_count} transactions in Google Sheets")
            return stored_count
            
        except APIError as e:
            logger.error(f"Error storing transactions: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during transaction storage: {str(e)}")
            raise APIError(
                f"Transaction storage failed: {str(e)}",
                "Google Sheets",
                "store_transactions"
            )
    
    def execute(self) -> Dict:
        """
        Execute the complete transaction retrieval and storage process
        
        Returns:
            Dict: Execution status and metadata
        """
        logger.info("Starting transaction retrieval and storage process")
        
        try:
            # Step 1: Authenticate with APIs
            if not self.authenticate():
                logger.error("Authentication failed, cannot proceed with transaction processing")
                return {
                    "status": "error",
                    "error": "Authentication failed with one or more APIs",
                    "transaction_count": 0
                }
            
            # Step 2: Retrieve transactions
            transactions = self.retrieve_transactions()
            
            if not transactions:
                logger.warning("No transactions retrieved from Capital One")
                return {
                    "status": "success",
                    "message": "No transactions retrieved for the past week",
                    "transaction_count": 0
                }
            
            # Step 3: Store transactions
            stored_count = self.store_transactions(transactions)
            
            if stored_count == 0:
                logger.warning("No transactions were stored in Google Sheets")
                return {
                    "status": "warning",
                    "message": "Retrieved transactions but none were stored",
                    "transaction_count": 0,
                    "retrieved_count": len(transactions)
                }
            
            # Return success status
            logger.info(f"Transaction process completed successfully: {stored_count} transactions processed")
            return {
                "status": "success",
                "message": "Transactions successfully retrieved and stored",
                "transaction_count": stored_count,
                "retrieved_count": len(transactions)
            }
            
        except Exception as e:
            logger.error(f"Transaction process failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def check_health(self) -> Dict:
        """
        Check health of API connections
        
        Returns:
            Dict: Health status of each integration
        """
        logger.info("Performing API health check")
        health_status = {}
        
        # Check Capital One API connectivity
        try:
            capital_one_status = self.capital_one_client.test_connectivity()
            health_status['capital_one'] = 'healthy' if capital_one_status else 'unhealthy'
        except Exception as e:
            logger.error(f"Capital One API health check failed: {str(e)}")
            health_status['capital_one'] = f'unhealthy: {str(e)}'
        
        # Check Google Sheets API connectivity
        try:
            # Authenticate to test connectivity
            sheets_status = self.sheets_client.authenticate()
            health_status['google_sheets'] = 'healthy' if sheets_status else 'unhealthy'
        except Exception as e:
            logger.error(f"Google Sheets API health check failed: {str(e)}")
            health_status['google_sheets'] = f'unhealthy: {str(e)}'
        
        logger.info(f"Health check results: {health_status}")
        return health_status