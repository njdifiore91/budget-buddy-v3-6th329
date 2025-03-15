"""
budget.py - Defines the Budget model class and related utility functions for budget analysis in the Budget Management Application.

This model encapsulates budget data, provides methods for comparing actual spending to budgeted amounts, 
calculating variances, and determining savings transfer amounts.
"""

import decimal  # standard library
from decimal import Decimal  # standard library
import logging  # standard library
from typing import List, Dict, Optional  # standard library

from .category import Category
from ..utils.validation import is_valid_amount, parse_amount, validate_calculation_results, is_valid_transfer_amount
from ..utils.formatters import format_currency, format_percentage
from ..config.settings import APP_SETTINGS
from ..utils.error_handlers import ValidationError

# Set up logger
logger = logging.getLogger(__name__)


class Budget:
    """Represents a budget with categories, actual spending, and analysis results"""
    
    def __init__(self, categories: List[Category], actual_spending: Dict[str, Decimal]):
        """
        Initialize a new Budget instance
        
        Args:
            categories: List of Category objects
            actual_spending: Dictionary mapping category names to actual spending amounts
        """
        self.categories = categories
        self.actual_spending = actual_spending
        self.category_variances = {}
        self.total_budget = Decimal(0)
        self.total_spent = Decimal(0)
        self.total_variance = Decimal(0)
        self.is_analyzed = False
        
        logger.debug(f"Created budget with {len(categories)} categories and {len(actual_spending)} spending entries")
    
    def __str__(self):
        """String representation of the Budget"""
        if self.is_analyzed:
            return (f"Budget: {format_currency(self.total_budget)}, "
                   f"Spent: {format_currency(self.total_spent)}, "
                   f"Variance: {format_currency(self.total_variance)}")
        else:
            return f"Budget: (not analyzed) with {len(self.categories)} categories"
    
    def __repr__(self):
        """Official string representation of the Budget"""
        return f'Budget(categories={self.categories}, actual_spending={self.actual_spending})'
    
    def analyze(self):
        """
        Analyze budget vs. actual spending and calculate variances
        
        Returns:
            Dict[str, object]: Analysis results
        """
        # Calculate total budget by summing category weekly amounts
        self.total_budget = sum(category.weekly_amount for category in self.categories)
        
        # Calculate total spent by summing actual spending
        self.total_spent = sum(self.actual_spending.values())
        
        # Calculate variances by category
        self.category_variances = calculate_category_variances(self.categories, self.actual_spending)
        
        # Calculate total variance
        self.total_variance = self.total_budget - self.total_spent
        
        # Validate calculations
        validate_calculation_results(
            self.actual_spending,
            self.category_variances,
            self.total_budget,
            self.total_spent,
            self.total_variance
        )
        
        # Mark as analyzed
        self.is_analyzed = True
        
        logger.info(f"Budget analysis completed. Total variance: {format_currency(self.total_variance)}")
        
        # Return analysis results
        return {
            'total_budget': self.total_budget,
            'total_spent': self.total_spent,
            'total_variance': self.total_variance,
            'category_variances': self.category_variances,
            'is_surplus': self.total_variance > 0
        }
    
    def get_transfer_amount(self):
        """
        Calculate amount to transfer to savings based on budget surplus
        
        Returns:
            decimal.Decimal: Amount to transfer (0 if no surplus)
        """
        # Ensure budget is analyzed
        if not self.is_analyzed:
            self.analyze()
        
        # Calculate transfer amount
        transfer_amount = calculate_transfer_amount(self.total_variance)
        
        logger.info(f"Calculated transfer amount: {format_currency(transfer_amount)}")
        
        return transfer_amount
    
    def to_dict(self):
        """
        Convert Budget to dictionary representation
        
        Returns:
            dict: Dictionary with budget data
        """
        # Ensure budget is analyzed
        if not self.is_analyzed:
            self.analyze()
        
        # Create dictionary of category details
        category_analysis = {}
        for category in self.categories:
            category_name = category.name
            budget_amount = category.weekly_amount
            actual_amount = self.actual_spending.get(category_name, Decimal('0'))
            variance_amount = self.category_variances.get(category_name, Decimal('0'))
            
            # Calculate variance percentage
            if budget_amount > 0:
                variance_percentage = (variance_amount / budget_amount) * 100
            else:
                variance_percentage = Decimal('0')
            
            category_analysis[category_name] = {
                'budget_amount': budget_amount,
                'actual_amount': actual_amount,
                'variance_amount': variance_amount,
                'variance_percentage': variance_percentage,
                'is_over_budget': variance_amount < 0
            }
        
        # Construct complete dictionary
        return {
            'total_budget': self.total_budget,
            'total_spent': self.total_spent,
            'total_variance': self.total_variance,
            'is_surplus': self.total_variance > 0,
            'category_analysis': category_analysis,
            'formatted_total_budget': format_currency(self.total_budget),
            'formatted_total_spent': format_currency(self.total_spent),
            'formatted_total_variance': format_currency(self.total_variance)
        }


def create_budget(budget_data):
    """
    Factory function to create a Budget object from raw data
    
    Args:
        budget_data (dict): Dictionary containing budget data
        
    Returns:
        Budget: A new Budget instance
    """
    try:
        # Extract categories and actual_spending
        categories = budget_data.get('categories', [])
        actual_spending = budget_data.get('actual_spending', {})
        
        # Validate categories is a list of Category objects
        if not isinstance(categories, list):
            logger.error("Invalid categories data: not a list")
            raise ValidationError("Categories must be a list", "categories")
        
        # Validate actual_spending is a dictionary mapping category names to amounts
        if not isinstance(actual_spending, dict):
            logger.error("Invalid actual_spending data: not a dictionary")
            raise ValidationError("Actual spending must be a dictionary", "actual_spending")
        
        # Parse actual spending amounts to Decimal
        parsed_spending = {}
        for category, amount in actual_spending.items():
            try:
                parsed_spending[category] = parse_amount(amount)
            except ValueError as e:
                logger.warning(f"Invalid amount for category {category}: {e}")
                # Skip invalid amounts or use 0
                parsed_spending[category] = Decimal('0')
        
        # Create and return a new Budget instance
        return Budget(categories, parsed_spending)
    
    except Exception as e:
        logger.error(f"Error creating budget: {str(e)}")
        raise


def create_budget_from_sheet_data(budget_sheet_data, actual_spending):
    """
    Creates a Budget object from Google Sheets data
    
    Args:
        budget_sheet_data (list): Rows of budget data from Google Sheets
        actual_spending (dict): Dictionary mapping category names to actual spending amounts
        
    Returns:
        Budget: A Budget instance with data from sheets
    """
    try:
        # Import here to avoid circular imports
        from .category import create_categories_from_sheet_data
        
        # Create Category objects from budget_sheet_data
        categories = create_categories_from_sheet_data(budget_sheet_data)
        
        # Validate actual_spending is a dictionary
        if not isinstance(actual_spending, dict):
            logger.error("Invalid actual_spending data: not a dictionary")
            raise ValidationError("Actual spending must be a dictionary", "actual_spending")
        
        # Create and return Budget using create_budget
        return create_budget({'categories': categories, 'actual_spending': actual_spending})
    
    except Exception as e:
        logger.error(f"Error creating budget from sheet data: {str(e)}")
        raise


def calculate_category_variances(categories, actual_spending):
    """
    Calculates variances between budget and actual spending by category
    
    Args:
        categories (list): List of Category objects
        actual_spending (dict): Dictionary mapping category names to actual spending amounts
        
    Returns:
        dict: Dictionary mapping category names to variance amounts
    """
    variances = {}
    
    for category in categories:
        category_name = category.name
        budget_amount = category.weekly_amount
        
        # Get actual spending for this category (default to 0 if not found)
        actual_amount = actual_spending.get(category_name, Decimal('0'))
        
        # Calculate variance (budget - actual)
        # Positive variance means under budget, negative means over budget
        variance = budget_amount - actual_amount
        
        # Store in variances dictionary
        variances[category_name] = variance
    
    return variances


def calculate_transfer_amount(total_variance):
    """
    Calculates the amount to transfer to savings based on budget surplus
    
    Args:
        total_variance (decimal.Decimal): Total variance amount
        
    Returns:
        decimal.Decimal: Amount to transfer (0 if no surplus)
    """
    # If no surplus, return 0
    if total_variance <= 0:
        logger.info("No budget surplus available for transfer")
        return Decimal('0')
    
    # Get minimum transfer amount from settings
    min_transfer_amount = APP_SETTINGS.get('MIN_TRANSFER_AMOUNT', Decimal('1.00'))
    
    # Validate transfer amount meets minimum threshold
    if not is_valid_transfer_amount(total_variance, min_transfer_amount):
        logger.info(f"Surplus ({format_currency(total_variance)}) below minimum transfer amount ({format_currency(min_transfer_amount)})")
        return Decimal('0')
    
    # Round to two decimal places
    transfer_amount = total_variance.quantize(Decimal('0.01'))
    
    logger.info(f"Transfer amount calculated: {format_currency(transfer_amount)}")
    
    return transfer_amount