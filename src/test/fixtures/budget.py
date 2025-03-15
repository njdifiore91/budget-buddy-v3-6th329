"""
budget.py - Provides test fixture data for budget objects to be used in unit and integration tests for the Budget Management Application.

This module contains predefined budget objects, factory functions, and utilities to generate test budget data with various properties for testing budget analysis, variance calculation, and savings transfer functionality.
"""

import json  # standard library
from decimal import Decimal  # standard library
import copy  # standard library
from typing import List, Dict, Optional, Union  # standard library

from ...backend.models.budget import Budget, create_budget, create_budget_from_sheet_data
from ..utils.fixture_loader import load_fixture
from .categories import create_test_categories, create_categories_with_amounts
from .transactions import create_transactions_with_amounts

# Load fixtures from JSON files
MASTER_BUDGET = load_fixture('json/budget/master_budget.json')
WEEKLY_SPENDING = load_fixture('json/budget/weekly_spending.json')
EXPECTED_BUDGET_ANALYSIS = load_fixture('json/expected/budget_analysis.json')

# Default budget amount
DEFAULT_TOTAL_BUDGET = Decimal('580.00')

def create_test_budget(categories: Optional[List] = None, actual_spending: Optional[Dict[str, Decimal]] = None) -> Budget:
    """
    Creates a Budget object with specified or default categories and actual spending
    
    Args:
        categories: List of Category objects
        actual_spending: Dictionary mapping category names to actual spending amounts
        
    Returns:
        A Budget object with the specified properties
    """
    # Set default values for any parameters not provided
    if categories is None:
        categories = create_test_categories()
    
    if actual_spending is None:
        actual_spending = {}
    
    # Create and return a Budget object
    return Budget(categories=categories, actual_spending=actual_spending)

def create_budget_with_variance(total_variance: Decimal) -> Budget:
    """
    Creates a Budget object with a specific total variance (surplus or deficit)
    
    Args:
        total_variance: The desired budget variance amount
        
    Returns:
        A Budget object with the specified variance
    """
    # Create categories with a known total budget amount
    categories = create_test_categories()
    total_budget = sum(category.weekly_amount for category in categories)
    
    # Calculate the required actual spending to achieve the specified variance
    total_spending = total_budget - total_variance
    
    # Create transactions with appropriate amounts to match the required spending
    actual_spending = {}
    if total_spending <= 0:
        # If total_spending is negative or zero, put all in the first category
        actual_spending[categories[0].name] = total_spending
    else:
        # Distribute spending proportionally
        remaining_spending = total_spending
        for i, category in enumerate(categories):
            if i == len(categories) - 1:
                # Assign remaining amount to last category to ensure total matches exactly
                actual_spending[category.name] = remaining_spending
            else:
                # Calculate proportional amount for this category
                ratio = category.weekly_amount / total_budget
                amount = (total_spending * ratio).quantize(Decimal('0.01'))
                actual_spending[category.name] = amount
                remaining_spending -= amount
    
    # Create a Budget object with these categories and actual spending
    return Budget(categories=categories, actual_spending=actual_spending)

def create_analyzed_budget(categories: Optional[List] = None, actual_spending: Optional[Dict[str, Decimal]] = None) -> Budget:
    """
    Creates a Budget object and runs the analyze method on it
    
    Args:
        categories: List of Category objects
        actual_spending: Dictionary mapping category names to actual spending amounts
        
    Returns:
        An analyzed Budget object
    """
    # Create a Budget object using create_test_budget
    budget = create_test_budget(categories, actual_spending)
    
    # Call the analyze method on the Budget object
    budget.analyze()
    
    # Return the analyzed Budget object
    return budget

def create_budget_from_fixtures() -> Budget:
    """
    Creates a Budget object from the master budget and weekly spending fixtures
    
    Returns:
        A Budget object created from fixture data
    """
    import decimal
    from ...backend.models.category import Category
    
    # Load the master budget categories from fixture
    categories = []
    if isinstance(MASTER_BUDGET, list):
        for item in MASTER_BUDGET:
            if isinstance(item, list) and len(item) >= 2:
                category_name = str(item[0])
                try:
                    weekly_amount = Decimal(str(item[1]))
                    categories.append(Category(name=category_name, weekly_amount=weekly_amount))
                except (ValueError, decimal.InvalidOperation):
                    continue  # Skip invalid amount
    elif isinstance(MASTER_BUDGET, dict):
        for category_name, data in MASTER_BUDGET.items():
            if isinstance(data, dict) and 'weekly_amount' in data:
                try:
                    weekly_amount = Decimal(str(data['weekly_amount']))
                    categories.append(Category(name=category_name, weekly_amount=weekly_amount))
                except (ValueError, decimal.InvalidOperation):
                    continue  # Skip invalid amount
    
    # Load the weekly spending transactions from fixture
    actual_spending = {}
    if isinstance(WEEKLY_SPENDING, list):
        for item in WEEKLY_SPENDING:
            if isinstance(item, list) and len(item) >= 4:
                try:
                    amount = Decimal(str(item[1]))
                    category = str(item[3]) if item[3] else None
                    
                    if category:
                        if category in actual_spending:
                            actual_spending[category] += amount
                        else:
                            actual_spending[category] = amount
                except (ValueError, decimal.InvalidOperation):
                    continue  # Skip invalid amount
    elif isinstance(WEEKLY_SPENDING, dict):
        for category, amount in WEEKLY_SPENDING.items():
            try:
                actual_spending[category] = Decimal(str(amount))
            except (ValueError, decimal.InvalidOperation):
                continue  # Skip invalid amount
    
    # Create and return a Budget object with these categories and actual spending
    return Budget(categories=categories, actual_spending=actual_spending)

def get_expected_budget_analysis() -> Dict:
    """
    Returns the expected budget analysis results from fixture
    
    Returns:
        Expected budget analysis results
    """
    return EXPECTED_BUDGET_ANALYSIS

def create_budget_with_specific_categories(category_amounts: Dict[str, Decimal]) -> Budget:
    """
    Creates a Budget object with specific category names and amounts
    
    Args:
        category_amounts: Dictionary mapping category names to budget amounts
        
    Returns:
        A Budget object with the specified categories
    """
    # Create Category objects using create_categories_with_amounts
    categories = create_categories_with_amounts(category_amounts)
    
    # Create an empty actual_spending dictionary
    actual_spending = {}
    
    # Create and return a Budget object with these categories and empty spending
    return Budget(categories=categories, actual_spending=actual_spending)

def create_budget_with_specific_spending(category_spending: Dict[str, Decimal]) -> Budget:
    """
    Creates a Budget object with specific actual spending by category
    
    Args:
        category_spending: Dictionary mapping category names to actual spending amounts
        
    Returns:
        A Budget object with the specified actual spending
    """
    # Create default categories using create_test_categories
    categories = create_test_categories()
    
    # Create actual_spending dictionary from category_spending parameter
    actual_spending = {}
    for category, amount in category_spending.items():
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        actual_spending[category] = amount
    
    # Create and return a Budget object with default categories and specified spending
    return Budget(categories=categories, actual_spending=actual_spending)

class BudgetFactory:
    """
    Factory class for creating test budget objects with various properties
    """
    
    def __init__(self):
        """Initialize the BudgetFactory"""
        # Initialize any required internal state
        pass
    
    def create_budget_with_surplus(self, surplus_amount: Decimal) -> Budget:
        """
        Creates a budget with a surplus (positive variance)
        
        Args:
            surplus_amount: The desired surplus amount
            
        Returns:
            A Budget object with the specified surplus
        """
        # Call create_budget_with_variance with a positive amount
        if not isinstance(surplus_amount, Decimal):
            surplus_amount = Decimal(str(surplus_amount))
        surplus_amount = abs(surplus_amount)  # Ensure it's positive
        return create_budget_with_variance(surplus_amount)
    
    def create_budget_with_deficit(self, deficit_amount: Decimal) -> Budget:
        """
        Creates a budget with a deficit (negative variance)
        
        Args:
            deficit_amount: The desired deficit amount
            
        Returns:
            A Budget object with the specified deficit
        """
        # Call create_budget_with_variance with a negative amount
        if not isinstance(deficit_amount, Decimal):
            deficit_amount = Decimal(str(deficit_amount))
        deficit_amount = -abs(deficit_amount)  # Ensure it's negative
        return create_budget_with_variance(deficit_amount)
    
    def create_budget_with_zero_variance(self) -> Budget:
        """
        Creates a budget with exactly balanced spending (zero variance)
        
        Args:
            
        Returns:
            A Budget object with zero variance
        """
        # Call create_budget_with_variance with zero
        return create_budget_with_variance(Decimal('0'))
    
    def create_budget_batch(self, count: int) -> List[Budget]:
        """
        Creates multiple Budget objects with different variances
        
        Args:
            count: Number of Budget objects to create
            
        Returns:
            A list of Budget objects
        """
        # Initialize an empty list for budgets
        budgets = []
        
        # Create 'count' number of Budget objects with varying variances
        for i in range(count):
            if i % 3 == 0:
                # Every third budget has a surplus
                budgets.append(self.create_budget_with_surplus(Decimal('50.00')))
            elif i % 3 == 1:
                # Every third + 1 budget has a deficit
                budgets.append(self.create_budget_with_deficit(Decimal('30.00')))
            else:
                # Every third + 2 budget has zero variance
                budgets.append(self.create_budget_with_zero_variance())
        
        return budgets
    
    def create_budget_with_category_variances(self, category_variances: Dict[str, Decimal]) -> Budget:
        """
        Creates a budget with specific variances for each category
        
        Args:
            category_variances: Dictionary mapping category names to desired variance amounts
            
        Returns:
            A Budget object with the specified category variances
        """
        # Create categories with specific budget amounts
        category_amounts = {}
        for category_name in category_variances.keys():
            category_amounts[category_name] = Decimal('100.00')
        
        categories = create_categories_with_amounts(category_amounts)
        
        # Calculate actual spending to achieve the specified variances
        actual_spending = {}
        for category in categories:
            # Variance = Budget - Actual, so Actual = Budget - Variance
            variance = category_variances.get(category.name, Decimal('0'))
            if not isinstance(variance, Decimal):
                variance = Decimal(str(variance))
            actual_spending[category.name] = category.weekly_amount - variance
        
        # Create a Budget object with these categories and actual spending
        return Budget(categories=categories, actual_spending=actual_spending)