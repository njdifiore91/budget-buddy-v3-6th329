"""
category.py - Defines the Category model class and related utility functions for representing budget categories in the Budget Management Application.

This model encapsulates the properties of spending categories from the Master Budget sheet 
and provides functionality for category creation and manipulation.
"""

import decimal  # standard library
from decimal import Decimal  # standard library
import logging  # standard library

from ..utils.validation import is_valid_amount, parse_amount
from ..utils.formatters import format_category_for_sheets

# Set up logger
logger = logging.getLogger(__name__)


class Category:
    """Represents a budget category with name and weekly budget amount"""
    
    def __init__(self, name, weekly_amount):
        """
        Initialize a new Category instance
        
        Args:
            name (str): The category name
            weekly_amount (decimal.Decimal): The weekly budget amount
        """
        self.name = format_category_for_sheets(name)
        self.weekly_amount = weekly_amount
        logger.debug(f"Created category: {self.name} with weekly amount: {self.weekly_amount}")
    
    def __str__(self):
        """String representation of the Category"""
        return f"{self.name}: ${self.weekly_amount:.2f}/week"
    
    def __repr__(self):
        """Official string representation of the Category"""
        return f'Category(name="{self.name}", weekly_amount={self.weekly_amount})'
    
    def __eq__(self, other):
        """Equality comparison between Category objects"""
        if not isinstance(other, Category):
            return False
        return self.name == other.name and self.weekly_amount == other.weekly_amount
    
    def to_dict(self):
        """
        Convert Category to dictionary representation
        
        Returns:
            dict: Dictionary with category data
        """
        return {
            'name': self.name,
            'weekly_amount': self.weekly_amount
        }


def create_category(category_data):
    """
    Factory function to create a Category object from raw data
    
    Args:
        category_data (dict): Dictionary containing category data
        
    Returns:
        Category: A new Category instance
        
    Raises:
        ValueError: If category_data is not a dictionary or contains invalid data
    """
    if not isinstance(category_data, dict):
        logger.error("Invalid category data: not a dictionary")
        raise ValueError("Category data must be a dictionary")
    
    # Extract name and weekly_amount
    name = category_data.get('name')
    weekly_amount = category_data.get('weekly_amount')
    
    # Validate name is a non-empty string
    if not name or not isinstance(name, str) or not name.strip():
        logger.error(f"Invalid category name: {name}")
        raise ValueError(f"Invalid category name: {name}")
    
    # Parse weekly_amount to Decimal using parse_amount
    try:
        weekly_amount = parse_amount(weekly_amount)
        
        # Validate amount is valid
        if not is_valid_amount(weekly_amount):
            logger.error(f"Invalid weekly amount: {weekly_amount}")
            raise ValueError(f"Invalid weekly amount: {weekly_amount}")
    except (ValueError, decimal.InvalidOperation) as e:
        logger.error(f"Error parsing weekly amount: {e}")
        raise ValueError(f"Invalid weekly amount: {weekly_amount}")
    
    # Create and return a new Category instance
    return Category(name, weekly_amount)


def create_categories_from_sheet_data(sheet_data):
    """
    Creates a list of Category objects from Google Sheets data
    
    Args:
        sheet_data (list): Rows of category data from Google Sheets
        
    Returns:
        list: List of Category objects
    """
    if not isinstance(sheet_data, list):
        logger.error("Invalid sheet data: not a list")
        return []
    
    categories = []
    invalid_rows = 0
    
    for i, row in enumerate(sheet_data):
        # Initialize empty list for categories
        if not isinstance(row, list) or len(row) < 2:
            logger.warning(f"Skipping row {i}: insufficient data")
            invalid_rows += 1
            continue
        
        try:
            # Extract category name and weekly amount from each row
            category_name = str(row[0]) if row[0] is not None else ""
            weekly_amount = row[1]
            
            # Skip empty category names
            if not category_name.strip():
                logger.warning(f"Skipping row {i} with empty category name")
                invalid_rows += 1
                continue
            
            # Create Category object for each valid row using create_category
            category_data = {
                'name': category_name,
                'weekly_amount': weekly_amount
            }
            
            category = create_category(category_data)
            categories.append(category)
                
        except Exception as e:
            # Log invalid categories that are skipped
            logger.warning(f"Error processing row {i}: {e}")
            invalid_rows += 1
            continue
    
    if invalid_rows:
        logger.info(f"Skipped {invalid_rows} invalid rows when creating categories")
    
    logger.info(f"Created {len(categories)} categories from sheet data")
    
    # Return list of Category objects
    return categories


def get_category_names(categories):
    """
    Extracts just the names from a list of Category objects
    
    Args:
        categories (list): List of Category objects
        
    Returns:
        list: List of category names as strings
    """
    if not isinstance(categories, list):
        logger.warning("Invalid categories input: not a list")
        return []
    
    # Use list comprehension to extract name attribute from each Category object
    return [category.name for category in categories if isinstance(category, Category)]