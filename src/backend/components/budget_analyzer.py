"""
budget_analyzer.py - Component responsible for comparing actual spending to budgeted amounts, calculating variances, and determining the overall budget status.

This component retrieves transaction and budget data from Google Sheets, calculates category totals, 
compares them to budgeted amounts, and determines the overall budget status. It's the third step 
in the budget management workflow, determining if there's a budget surplus for savings transfer.
"""

import decimal  # standard library
from decimal import Decimal  # standard library
import time  # standard library
from typing import List, Dict, Optional  # standard library

from ..models.transaction import Transaction, calculate_category_totals
from ..models.budget import Budget
from ..api_clients.google_sheets_client import GoogleSheetsClient
from ..utils.validation import validate_calculation_results
from ..utils.error_handlers import retry_with_backoff, APIError, ValidationError
from ..services.logging_service import get_component_logger
from ..services.error_handling_service import ErrorHandlingContext
from ..services.authentication_service import AuthenticationService

# Set up logger
logger = get_component_logger('budget_analyzer')


class BudgetAnalyzer:
    """Component responsible for analyzing budget performance by comparing actual spending to budgeted amounts"""
    
    def __init__(self, sheets_client: Optional[GoogleSheetsClient] = None, 
                 auth_service: Optional[AuthenticationService] = None):
        """
        Initialize the Budget Analyzer component
        
        Args:
            sheets_client: Optional Google Sheets client instance
            auth_service: Optional Authentication Service instance
        """
        # Initialize auth_service with provided service or create new instance
        self.auth_service = auth_service or AuthenticationService()
        
        # Initialize sheets_client with provided client or create new instance with auth_service
        self.sheets_client = sheets_client or GoogleSheetsClient(self.auth_service)
        
        # Initialize state variables
        self.correlation_id = None
        self.budget = None
        self.category_totals = {}
        self.transfer_amount = Decimal('0')
        
        logger.info("Budget Analyzer component initialized")
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Sheets API
        
        Returns:
            True if authentication successful, False otherwise
        """
        logger.info("Starting authentication with Google Sheets API")
        result = self.sheets_client.authenticate()
        logger.info(f"Authentication {'successful' if result else 'failed'}")
        return result
    
    @retry_with_backoff(exceptions=(APIError,), max_retries=3)
    def get_transactions_and_budget(self) -> tuple:
        """
        Retrieve transactions and budget data from Google Sheets
        
        Returns:
            tuple: (List[Transaction], Budget)
            
        Raises:
            APIError: If there's an error retrieving data from Google Sheets
        """
        try:
            logger.info("Retrieving transactions and budget data from Google Sheets")
            
            # Get transactions from Weekly Spending sheet
            transactions = self.sheets_client.get_transactions()
            
            # Calculate category totals from transactions
            self.category_totals = calculate_category_totals(transactions)
            
            # Get budget data with category totals for analysis
            self.budget = self.sheets_client.get_budget(self.category_totals)
            
            logger.info(f"Retrieved {len(transactions)} transactions and budget data with {len(self.category_totals)} categories")
            return transactions, self.budget
            
        except APIError as e:
            logger.error(f"Error retrieving data from Google Sheets: {str(e)}")
            raise
    
    def analyze_budget(self, budget: Budget) -> Dict:
        """
        Analyze budget performance by comparing actual spending to budget
        
        Args:
            budget: Budget object with categories and actual spending
            
        Returns:
            Dict: Budget analysis results
        """
        logger.info("Starting budget analysis")
        
        # Perform budget analysis to calculate variances
        analysis_results = budget.analyze()
        
        # Validate calculation results for mathematical accuracy
        if not validate_calculation_results(
            self.category_totals,
            analysis_results['category_variances'],
            analysis_results['total_budget'],
            analysis_results['total_spent'],
            analysis_results['total_variance']
        ):
            logger.warning("Budget calculation validation failed - check for mathematical errors")
        
        # Calculate transfer amount based on budget surplus
        self.transfer_amount = budget.get_transfer_amount()
        
        logger.info(f"Analysis complete. Total variance: {analysis_results['total_variance']}, " +
                    f"Transfer amount: {self.transfer_amount}")
        
        return analysis_results
    
    def format_analysis_results(self, analysis_results: Dict) -> Dict:
        """
        Format budget analysis results for reporting
        
        Args:
            analysis_results: Analysis results from budget.analyze()
            
        Returns:
            Dict: Formatted analysis results
        """
        # Create formatted results with key metrics
        formatted_results = {
            'total_budget': analysis_results['total_budget'],
            'total_spent': analysis_results['total_spent'],
            'total_variance': analysis_results['total_variance'],
            'category_variances': analysis_results['category_variances'],
            'transfer_amount': self.transfer_amount,
            'budget_status': 'surplus' if analysis_results['total_variance'] > 0 else 'deficit'
        }
        
        return formatted_results
    
    def execute(self, previous_status: Dict) -> Dict:
        """
        Execute the complete budget analysis process
        
        Args:
            previous_status: Status information from the Transaction Categorizer
            
        Returns:
            Dict: Execution status and analysis results
        """
        logger.info("Starting Budget Analyzer execution")
        start_time = time.time()
        
        # Extract correlation_id from previous_status if available
        self.correlation_id = previous_status.get('correlation_id')
        
        try:
            # Authenticate with Google Sheets API
            if not self.authenticate():
                return {
                    'status': 'error',
                    'message': 'Failed to authenticate with Google Sheets API',
                    'correlation_id': self.correlation_id
                }
            
            # Retrieve transactions and budget
            try:
                transactions, budget = self.get_transactions_and_budget()
                
                # Validate data was retrieved successfully
                if not transactions:
                    logger.warning("No transactions found for analysis")
                    return {
                        'status': 'warning',
                        'message': 'No transactions found for analysis',
                        'correlation_id': self.correlation_id
                    }
                
                if not budget:
                    logger.error("Failed to retrieve budget data")
                    return {
                        'status': 'error',
                        'message': 'Failed to retrieve budget data',
                        'correlation_id': self.correlation_id
                    }
            except APIError as e:
                logger.error(f"Failed to retrieve data: {str(e)}")
                return {
                    'status': 'error',
                    'message': f'Failed to retrieve transaction or budget data: {str(e)}',
                    'correlation_id': self.correlation_id
                }
            
            # Analyze budget
            analysis_results = self.analyze_budget(budget)
            
            # Format results for reporting
            formatted_results = self.format_analysis_results(analysis_results)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Return success status with analysis results
            result = {
                'status': 'success',
                'message': 'Budget analysis completed successfully',
                'analysis_results': formatted_results,
                'transfer_amount': self.transfer_amount,
                'correlation_id': self.correlation_id,
                'execution_time': execution_time
            }
            
            logger.info(f"Budget Analyzer execution completed in {execution_time:.2f} seconds")
            return result
            
        except Exception as e:
            # Handle any unexpected exceptions
            execution_time = time.time() - start_time
            logger.error(f"Budget Analyzer execution failed: {str(e)}")
            return {
                'status': 'error',
                'message': f'An unexpected error occurred during budget analysis: {str(e)}',
                'correlation_id': self.correlation_id,
                'execution_time': execution_time
            }
    
    def check_health(self) -> Dict:
        """
        Check health of API connections
        
        Returns:
            Dict: Health status of each integration
        """
        health_status = {}
        
        # Check Google Sheets API
        try:
            if self.authenticate():
                health_status['google_sheets'] = 'healthy'
            else:
                health_status['google_sheets'] = 'unhealthy'
        except Exception as e:
            health_status['google_sheets'] = f'unhealthy: {str(e)}'
        
        logger.info(f"Health check results: {health_status}")
        return health_status