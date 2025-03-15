"""
categories.py - Provides test fixture data for budget categories to be used in unit and integration tests for the Budget Management Application.

This module contains predefined category objects, factory functions, and utilities to generate test category data for testing transaction categorization, budget analysis, and other category-related functionality.
"""

import json  # standard library
from decimal import Decimal  # standard library
import random  # standard library
from typing import List, Dict, Optional, Union  # standard library

from ...backend.models.category import Category, create_category, create_categories_from_sheet_data, get_category_names
from ..utils.fixture_loader import load_fixture

# Load master budget categories from fixture file
MASTER_BUDGET_CATEGORIES = load_fixture('json/budget/master_budget.json')

# Empty categories list for edge case testing
EMPTY_BUDGET_CATEGORIES = []

# Default set of categories for testing
DEFAULT_CATEGORIES = [
    {'spending_category': 'Groceries', 'weekly_amount': '150.00'},
    {'spending_category': 'Dining Out', 'weekly_amount': '75.00'},
    {'spending_category': 'Gas & Fuel', 'weekly_amount': '50.00'},
    {'spending_category': 'Entertainment', 'weekly_amount': '40.00'},
    {'spending_category': 'Shopping', 'weekly_amount': '100.00'}
]


def create_test_category(name: Optional[str] = None, weekly_amount: Optional[Union[Decimal, str, float]] = None) -> Category:
    """
    Creates a Category object with specified or default name and weekly amount.
    
    Args:
        name: Category name, defaults to 'Test Category' if None
        weekly_amount: Weekly budget amount, defaults to Decimal('50.00') if None
        
    Returns:
        A Category object with the specified properties
    """
    # Set default values if not provided
    if name is None:
        name = 'Test Category'
    
    if weekly_amount is None:
        weekly_amount = Decimal('50.00')
    elif not isinstance(weekly_amount, Decimal):
        weekly_amount = Decimal(str(weekly_amount))
        
    # Create and return a Category object
    return Category(name=name, weekly_amount=weekly_amount)


def create_test_categories(count: Optional[int] = None, category_data: Optional[List[Dict]] = None) -> List[Category]:
    """
    Creates a list of Category objects with default or specified properties.
    
    Args:
        count: Number of categories to create, defaults to 5 if None
        category_data: List of category dictionaries, defaults to DEFAULT_CATEGORIES if None
        
    Returns:
        A list of Category objects
    """
    # Set default values if not provided
    if count is None:
        count = 5
        
    if category_data is None:
        category_data = DEFAULT_CATEGORIES
    
    categories = []
    
    # If category_data is provided, use it to create categories
    if category_data:
        for data in category_data[:count]:  # Limit to count
            if isinstance(data, dict):
                # Convert spending_category key to name for create_category
                if 'spending_category' in data and 'name' not in data:
                    data = data.copy()  # Create a copy to avoid modifying the original
                    data['name'] = data['spending_category']
                
                try:
                    category = create_category(data)
                    categories.append(category)
                except ValueError:
                    # Skip invalid data
                    continue
    else:
        # Create count number of categories with default values
        for i in range(count):
            name = f"Test Category {i+1}"
            weekly_amount = Decimal('50.00')
            categories.append(Category(name=name, weekly_amount=weekly_amount))
    
    return categories


def create_categories_with_amounts(category_amounts: Dict[str, Union[Decimal, str, float]]) -> List[Category]:
    """
    Creates Category objects with specific names and weekly amounts.
    
    Args:
        category_amounts: Dictionary mapping category names to weekly amounts
        
    Returns:
        A list of Category objects with specified amounts
    """
    categories = []
    
    for name, amount in category_amounts.items():
        # Convert amount to Decimal if needed
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
            
        # Create Category and add to list
        category = Category(name=name, weekly_amount=amount)
        categories.append(category)
    
    return categories


def get_category_fixture_by_name(fixture_name: str) -> list:
    """
    Retrieves a specific category fixture by name.
    
    Args:
        fixture_name: Name of the fixture ('master_budget', 'empty', or 'default')
        
    Returns:
        Category fixture data
        
    Raises:
        ValueError: If fixture_name is not recognized
    """
    if fixture_name == 'master_budget':
        return MASTER_BUDGET_CATEGORIES
    elif fixture_name == 'empty':
        return EMPTY_BUDGET_CATEGORIES
    elif fixture_name == 'default':
        return DEFAULT_CATEGORIES
    else:
        raise ValueError(f"Unknown fixture name: {fixture_name}")


def get_category_mapping(categories: List[Category]) -> Dict[str, Category]:
    """
    Creates a mapping of category names to their objects.
    
    Args:
        categories: List of Category objects
        
    Returns:
        Dictionary mapping category names to Category objects
    """
    mapping = {}
    
    for category in categories:
        if isinstance(category, Category):
            mapping[category.name] = category
    
    return mapping


class CategoryFactory:
    """
    Factory class for creating test category objects with various properties.
    """
    
    def __init__(self):
        """Initialize the CategoryFactory"""
        # No initialization needed for now
        pass
    
    def create_random_category(self) -> Category:
        """
        Creates a category with random name and amount.
        
        Returns:
            A Category object with random properties
        """
        # Generate a random category name
        suffixes = ["Expenses", "Bills", "Spending", "Costs", "Purchases"]
        prefixes = ["Home", "Food", "Travel", "Entertainment", "Clothing", "Personal", "Health", "Auto", "Tech"]
        
        name = f"{random.choice(prefixes)} {random.choice(suffixes)}"
        
        # Generate a random weekly amount between 10.00 and 200.00
        amount_value = random.uniform(10.0, 200.0)
        # Round to 2 decimal places
        amount = Decimal(str(round(amount_value, 2)))
        
        # Create and return a Category with these random values
        return Category(name=name, weekly_amount=amount)
    
    def create_category_batch(self, count: int) -> List[Category]:
        """
        Creates multiple Category objects with different properties.
        
        Args:
            count: Number of categories to create
            
        Returns:
            A list of Category objects
        """
        categories = []
        
        # Create categories with varying properties
        for i in range(count):
            if i % 3 == 0:
                # Every third category is random
                categories.append(self.create_random_category())
            else:
                # Others use deterministic names with varying amounts
                name = f"Category Type {i}"
                amount = Decimal(str(25.0 + (i * 10.0)))
                categories.append(Category(name=name, weekly_amount=amount))
        
        return categories
    
    def create_categories_with_total_budget(self, count: int, total_budget: Union[Decimal, str, float]) -> List[Category]:
        """
        Creates categories that sum to a specific total budget.
        
        Args:
            count: Number of categories to create
            total_budget: Total budget amount to distribute
            
        Returns:
            A list of Category objects with amounts summing to total_budget
        """
        categories = []
        
        # Ensure total_budget is a Decimal
        if not isinstance(total_budget, Decimal):
            total_budget = Decimal(str(total_budget))
        
        # Distribute budget across categories randomly but ensuring they sum to total_budget
        if count <= 0:
            return []
            
        # Create random weights for distribution
        weights = [random.uniform(0.5, 1.5) for _ in range(count)]
        weight_sum = sum(weights)
        
        # Normalize weights to sum to 1
        normalized_weights = [w/weight_sum for w in weights]
        
        # Distribute budget according to weights
        remaining_budget = total_budget
        for i in range(count):
            # For the last category, use whatever budget remains
            if i == count - 1:
                amount = remaining_budget
            else:
                # Calculate this category's share of the budget
                amount = (total_budget * normalized_weights[i]).quantize(Decimal('.01'))
                remaining_budget -= amount
            
            # Create category with this amount
            name = f"Budget Category {i+1}"
            categories.append(Category(name=name, weekly_amount=amount))
        
        return categories