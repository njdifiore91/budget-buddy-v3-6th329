"""
Provides test fixture data for budget categories used in unit and integration tests for the Budget Management Application. This module creates Category objects with predefined data for consistent and reproducible testing of transaction categorization and budget analysis functionality.
"""

import os  # standard library
import json  # standard library
import decimal  # standard library
from decimal import Decimal  # standard library
from typing import List, Dict, Optional  # standard library

from ...models.category import Category, create_category, create_categories_from_sheet_data
from ...utils.formatters import format_category_for_sheets

# Define fixture directory and files
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'data')
CATEGORIES_FILE = os.path.join(FIXTURES_DIR, 'categories.json')


def load_category_data() -> List:
    """
    Loads raw category data from the JSON fixture file
    
    Returns:
        List of category dictionaries
    """
    try:
        with open(CATEGORIES_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # If file doesn't exist, return a default list of categories
        return [
            {"name": "Groceries", "weekly_amount": "100.00"},
            {"name": "Dining Out", "weekly_amount": "50.00"},
            {"name": "Transportation", "weekly_amount": "75.00"},
            {"name": "Entertainment", "weekly_amount": "30.00"},
            {"name": "Shopping", "weekly_amount": "40.00"}
        ]
    except json.JSONDecodeError:
        # If JSON is invalid, return default list
        return [
            {"name": "Groceries", "weekly_amount": "100.00"},
            {"name": "Dining Out", "weekly_amount": "50.00"},
            {"name": "Transportation", "weekly_amount": "75.00"}
        ]


def create_test_category(name: str, weekly_amount) -> Category:
    """
    Creates a single Category object with test data
    
    Args:
        name: The category name
        weekly_amount: The weekly budget amount (string, float, or Decimal)
        
    Returns:
        A Category object with the specified properties
    """
    # Convert weekly_amount to Decimal if it's not already
    if not isinstance(weekly_amount, Decimal):
        weekly_amount_decimal = Decimal(str(weekly_amount))
    else:
        weekly_amount_decimal = weekly_amount
    
    # Create category data dictionary
    category_data = {
        'name': name,
        'weekly_amount': weekly_amount_decimal
    }
    
    # Create and return Category object
    return create_category(category_data)


def create_test_categories() -> List[Category]:
    """
    Creates a list of Category objects from the fixture data
    
    Returns:
        List of Category objects
    """
    # Load category data from fixture
    categories_data = load_category_data()
    
    # Initialize empty list for categories
    categories = []
    
    # Create Category objects for each item in data
    for category_data in categories_data:
        name = category_data.get('name')
        weekly_amount = category_data.get('weekly_amount')
        
        # Create and append Category object
        categories.append(create_test_category(name, weekly_amount))
    
    return categories


def get_category_by_name(name: str, categories: Optional[List[Category]] = None) -> Optional[Category]:
    """
    Finds a category in the test data by its name
    
    Args:
        name: Name of the category to find
        categories: Optional list of categories to search in (uses SAMPLE_CATEGORIES if None)
        
    Returns:
        The matching Category object or None if not found
    """
    # Use sample categories if none provided
    if categories is None:
        categories = SAMPLE_CATEGORIES
    
    # Standardize the input name
    formatted_name = format_category_for_sheets(name)
    
    # Search for matching category
    for category in categories:
        if category.name == formatted_name:
            return category
    
    # Return None if no match found
    return None


def create_custom_categories(category_data: List[Dict]) -> List[Category]:
    """
    Creates a list of Category objects with custom data
    
    Args:
        category_data: List of dictionaries with category data
        
    Returns:
        List of custom Category objects
    """
    categories = []
    
    for data in category_data:
        name = data.get('name')
        weekly_amount = data.get('weekly_amount')
        
        categories.append(create_test_category(name, weekly_amount))
    
    return categories


def create_categories_with_surplus() -> List[Category]:
    """
    Creates categories with budget amounts that ensure a surplus
    
    Returns:
        List of Category objects with high budget amounts
    """
    # Get base categories
    categories = create_test_categories()
    
    # Increase budget amounts to ensure surplus
    for category in categories:
        # Multiply the original amount by 1.5 to ensure surplus
        category.weekly_amount = category.weekly_amount * Decimal('1.5')
    
    return categories


def create_categories_with_deficit() -> List[Category]:
    """
    Creates categories with budget amounts that ensure a deficit
    
    Returns:
        List of Category objects with low budget amounts
    """
    # Get base categories
    categories = create_test_categories()
    
    # Decrease budget amounts to ensure deficit
    for category in categories:
        # Multiply the original amount by 0.5 to ensure deficit
        category.weekly_amount = category.weekly_amount * Decimal('0.5')
    
    return categories


# Create sample categories for tests
SAMPLE_CATEGORIES = create_test_categories()