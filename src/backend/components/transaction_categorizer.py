"""
transaction_categorizer.py - Component responsible for categorizing transactions using Gemini AI

This component is the second step in the budget management workflow, following transaction retrieval
and preceding budget analysis. It uses Gemini AI to categorize transactions by matching their locations
to budget categories, then updates Google Sheets with the assigned categories.
"""

from typing import List, Dict, Optional, Tuple
import time

# Internal imports
from ..models.transaction import Transaction, get_transaction_locations
from ..models.category import Category, get_category_names, create_categories_from_sheet_data
from ..api_clients.gemini_client import GeminiClient
from ..api_clients.google_sheets_client import GoogleSheetsClient
from ..utils.validation import is_valid_category, validate_categorization_results, is_categorization_successful
from ..config.settings import APP_SETTINGS
from ..utils.error_handlers import retry_with_backoff, handle_api_error, APIError, ValidationError
from ..config.logging_config import get_logger
from ..services.authentication_service import AuthenticationService

# Set up logger
logger = get_logger('transaction_categorizer')

class TransactionCategorizer:
    """
    Component responsible for categorizing transactions using Gemini AI and 
    updating Google Sheets with the assigned categories
    """
    
    def __init__(self, 
                 gemini_client: Optional[GeminiClient] = None,
                 sheets_client: Optional[GoogleSheetsClient] = None,
                 auth_service: Optional[AuthenticationService] = None,
                 categorization_threshold: Optional[float] = None):
        """
        Initialize the Transaction Categorizer component
        
        Args:
            gemini_client: Optional GeminiClient instance
            sheets_client: Optional GoogleSheetsClient instance
            auth_service: Optional AuthenticationService instance
            categorization_threshold: Required threshold for categorization success
        """
        # Initialize auth service
        self.auth_service = auth_service or AuthenticationService()
        
        # Initialize API clients
        self.gemini_client = gemini_client or GeminiClient(self.auth_service)
        self.sheets_client = sheets_client or GoogleSheetsClient(self.auth_service)
        
        # Set categorization threshold
        self.categorization_threshold = categorization_threshold or APP_SETTINGS.get('CATEGORIZATION_THRESHOLD', 0.95)
        
        # Initialize correlation ID for request tracing
        self.correlation_id = None
        
        logger.info("Transaction Categorizer component initialized")
    
    def authenticate(self) -> bool:
        """
        Authenticate with both Gemini AI and Google Sheets APIs
        
        Returns:
            True if authentication successful for both APIs, False otherwise
        """
        logger.info("Starting authentication process for Transaction Categorizer")
        
        # Authenticate with Gemini AI
        gemini_auth_success = self.gemini_client.authenticate()
        
        # Authenticate with Google Sheets
        sheets_auth_success = self.sheets_client.authenticate()
        
        # Both authentications must be successful
        success = gemini_auth_success and sheets_auth_success
        
        if success:
            logger.info("Successfully authenticated with both Gemini AI and Google Sheets APIs")
        else:
            logger.error(f"Authentication failed. Gemini: {gemini_auth_success}, Sheets: {sheets_auth_success}")
        
        return success
    
    @retry_with_backoff(exceptions=(APIError,), max_retries=3)
    def get_transactions_and_categories(self) -> Tuple[List[Transaction], List[Category]]:
        """
        Retrieve transactions and budget categories from Google Sheets
        
        Returns:
            Tuple containing lists of transactions and categories
        """
        try:
            logger.info("Retrieving transactions and categories from Google Sheets")
            
            # Get transactions from Weekly Spending sheet
            transactions = self.sheets_client.get_transactions()
            
            # Get budget data from Master Budget sheet
            budget_data = self.sheets_client.get_master_budget_data()
            
            # Create Category objects from budget data
            categories = create_categories_from_sheet_data(budget_data)
            
            logger.info(f"Retrieved {len(transactions)} transactions and {len(categories)} categories")
            
            return transactions, categories
            
        except APIError as e:
            logger.error(f"Error retrieving data from Google Sheets: {str(e)}")
            raise
    
    @retry_with_backoff(exceptions=(APIError,), max_retries=3)
    def categorize_transactions(self, transactions: List[Transaction], categories: List[Category]) -> Dict[str, str]:
        """
        Categorize transactions using Gemini AI
        
        Args:
            transactions: List of transactions to categorize
            categories: List of valid budget categories
            
        Returns:
            Mapping of transaction locations to categories
        """
        try:
            logger.info("Starting transaction categorization with Gemini AI")
            
            # Get transaction locations
            transaction_locations = get_transaction_locations(transactions)
            
            # Get category names
            category_names = get_category_names(categories)
            
            # No transactions or categories to process
            if not transaction_locations or not category_names:
                logger.warning(f"Missing data for categorization. Transactions: {len(transaction_locations)}, Categories: {len(category_names)}")
                return {}
            
            # Call Gemini AI to categorize transactions
            location_to_category_map = self.gemini_client.categorize_transactions(
                transaction_locations=transaction_locations,
                budget_categories=category_names
            )
            
            # Validate categorization results
            validated_map = validate_categorization_results(
                location_to_category_map, 
                category_names,
                transaction_locations
            )
            
            # Check if categorization successful (meets threshold)
            success = is_categorization_successful(
                validated_map, 
                transaction_locations, 
                self.categorization_threshold
            )
            
            # Calculate success rate for logging
            success_rate = len(validated_map) / len(transaction_locations) if transaction_locations else 0
            
            if success:
                logger.info(f"Categorization successful with {success_rate:.1%} coverage ({len(validated_map)}/{len(transaction_locations)})")
            else:
                logger.warning(f"Categorization below threshold with {success_rate:.1%} coverage ({len(validated_map)}/{len(transaction_locations)})")
            
            return validated_map
            
        except APIError as e:
            logger.error(f"Error categorizing transactions with Gemini AI: {str(e)}")
            raise
    
    def apply_categories(self, transactions: List[Transaction], location_to_category_map: Dict[str, str]) -> List[Transaction]:
        """
        Apply categorization results to transactions
        
        Args:
            transactions: List of transactions to update
            location_to_category_map: Mapping of transaction locations to categories
            
        Returns:
            Updated list of transactions with categories applied
        """
        logger.info("Applying categories to transactions")
        
        categorized_count = 0
        
        # Apply categories to transactions
        for transaction in transactions:
            location = transaction.location
            
            if location in location_to_category_map:
                category = location_to_category_map[location]
                transaction.set_category(category)
                categorized_count += 1
        
        logger.info(f"Applied categories to {categorized_count} transactions")
        
        return transactions
    
    @retry_with_backoff(exceptions=(APIError,), max_retries=3)
    def update_sheet_categories(self, transactions: List[Transaction], location_to_category_map: Dict[str, str]) -> int:
        """
        Update transaction categories in Google Sheets
        
        Args:
            transactions: List of transactions with assigned categories
            location_to_category_map: Mapping of transaction locations to categories
            
        Returns:
            Number of transactions updated in sheet
        """
        try:
            logger.info("Updating transaction categories in Google Sheets")
            
            # Update categories in Weekly Spending sheet
            updated_count = self.sheets_client.update_transaction_categories(
                transactions=transactions,
                location_to_category_map=location_to_category_map
            )
            
            logger.info(f"Updated {updated_count} transaction categories in Google Sheets")
            
            return updated_count
            
        except APIError as e:
            logger.error(f"Error updating transaction categories in Google Sheets: {str(e)}")
            raise
    
    def execute(self, previous_status: Dict) -> Dict:
        """
        Execute the complete transaction categorization process
        
        Args:
            previous_status: Status information from the Transaction Retriever
            
        Returns:
            Execution status and metadata
        """
        start_time = time.time()
        
        try:
            logger.info("Executing transaction categorization process")
            
            # Extract correlation ID from previous status if available
            self.correlation_id = previous_status.get('correlation_id')
            
            # Authenticate with APIs
            if not self.authenticate():
                logger.error("Authentication failed, cannot proceed with categorization")
                return {
                    'status': 'error',
                    'error': 'Authentication failed',
                    'component': 'transaction_categorizer',
                    'correlation_id': self.correlation_id
                }
            
            # Get transactions and categories
            transactions, categories = self.get_transactions_and_categories()
            
            # Check if we have data to process
            if not transactions:
                logger.warning("No transactions to categorize")
                return {
                    'status': 'warning',
                    'message': 'No transactions to categorize',
                    'component': 'transaction_categorizer',
                    'correlation_id': self.correlation_id,
                    'transactions': []
                }
            
            if not categories:
                logger.error("No budget categories available for categorization")
                return {
                    'status': 'error',
                    'error': 'No budget categories available',
                    'component': 'transaction_categorizer',
                    'correlation_id': self.correlation_id
                }
            
            # Categorize transactions
            location_to_category_map = self.categorize_transactions(transactions, categories)
            
            if not location_to_category_map:
                logger.error("Failed to categorize transactions")
                return {
                    'status': 'error',
                    'error': 'Failed to categorize transactions',
                    'component': 'transaction_categorizer',
                    'correlation_id': self.correlation_id
                }
            
            # Apply categories to transactions
            categorized_transactions = self.apply_categories(transactions, location_to_category_map)
            
            # Update Google Sheets with categories
            updated_count = self.update_sheet_categories(categorized_transactions, location_to_category_map)
            
            if updated_count == 0:
                logger.warning("No transaction categories were updated in Google Sheets")
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Prepare serializable transaction data for handoff to next component
            serialized_transactions = [t.to_dict() for t in categorized_transactions]
            
            # Prepare success response
            return {
                'status': 'success',
                'message': 'Transaction categorization completed successfully',
                'component': 'transaction_categorizer',
                'correlation_id': self.correlation_id,
                'metrics': {
                    'transactions_processed': len(transactions),
                    'categories_available': len(categories),
                    'transactions_categorized': len(location_to_category_map),
                    'categories_updated': updated_count,
                    'categorization_rate': len(location_to_category_map) / len(transactions) if transactions else 0,
                    'execution_time': execution_time
                },
                'transactions': serialized_transactions
            }
            
        except Exception as e:
            logger.error(f"Error during transaction categorization: {str(e)}")
            
            # Return error status
            return {
                'status': 'error',
                'error': str(e),
                'component': 'transaction_categorizer',
                'correlation_id': self.correlation_id,
                'execution_time': time.time() - start_time
            }
    
    def check_health(self) -> Dict:
        """
        Check health of API connections
        
        Returns:
            Health status of each integration
        """
        health_status = {}
        
        # Check Gemini AI connection
        try:
            gemini_auth = self.gemini_client.authenticate()
            health_status['gemini'] = 'healthy' if gemini_auth else 'unhealthy'
        except Exception as e:
            logger.error(f"Gemini health check failed: {str(e)}")
            health_status['gemini'] = f'unhealthy: {str(e)}'
        
        # Check Google Sheets connection
        try:
            sheets_auth = self.sheets_client.authenticate()
            health_status['google_sheets'] = 'healthy' if sheets_auth else 'unhealthy'
        except Exception as e:
            logger.error(f"Google Sheets health check failed: {str(e)}")
            health_status['google_sheets'] = f'unhealthy: {str(e)}'
        
        logger.info(f"Health check results: {health_status}")
        
        return health_status