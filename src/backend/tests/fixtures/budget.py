"""
Provides test fixture data for budget objects used in unit and integration tests for the Budget Management Application. This module creates Budget objects with predefined data for consistent and reproducible testing of budget analysis, variance calculation, and savings transfer functionality.
"""

import os  # standard library
import json  # standard library
import decimal  # standard library
from decimal import Decimal  # standard library
from typing import List, Dict, Optional, Union  # standard library

from ...models.budget import Budget, create_budget, create_budget_from_sheet_data, calculate_category_variances, calculate_transfer_amount
from .categories import create_test_categories, create_categories_with_surplus, create_categories_with_deficit, SAMPLE_CATEGORIES
from .transactions import create_categorized_transactions, CATEGORIZED_TRANSACTIONS

# Define fixture directory and file paths
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'data')
BUDGET_FILE = os.path.join(FIXTURES_DIR, 'budget.json')


def load_budget_data() -> Dict:
    """
    Loads raw budget data from the JSON fixture file
    
    Returns:
        Dictionary containing budget data including categories, actual_spending, and expected_analysis
    """
    try:
        with open(BUDGET_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If file doesn't exist or is invalid, return a default budget data structure
        return {
            "actual_spending": {
                "Groceries": "75.32",
                "Dining Out": "45.67",
                "Transportation": "30.00",
                "Entertainment": "20.00",
                "Shopping": "50.00"
            },
            "expected_analysis": {
                "total_budget": "295.00",
                "total_spent": "220.99",
                "total_variance": "74.01",
                "is_surplus": True
            },
            "test_scenarios": {
                "surplus": {
                    "total_budget": "295.00",
                    "total_spent": "220.99",
                    "total_variance": "74.01",
                    "is_surplus": True
                },
                "deficit": {
                    "total_budget": "190.00",
                    "total_spent": "220.99",
                    "total_variance": "-30.99",
                    "is_surplus": False
                },
                "zero": {
                    "total_budget": "220.99",
                    "total_spent": "220.99",
                    "total_variance": "0.00",
                    "is_surplus": False
                }
            },
            "sheet_data": [
                ["Groceries", "100.00"],
                ["Dining Out", "50.00"],
                ["Transportation", "75.00"],
                ["Entertainment", "30.00"],
                ["Shopping", "40.00"]
            ]
        }


def create_test_budget(categories: Optional[List] = None, actual_spending: Optional[Dict[str, Decimal]] = None) -> Budget:
    """
    Creates a Budget object with test data
    
    Args:
        categories: Optional list of Category objects (defaults to SAMPLE_CATEGORIES)
        actual_spending: Optional dictionary mapping category names to actual spending amounts
        
    Returns:
        A Budget object with the specified properties
    """
    # If categories parameter is None, use SAMPLE_CATEGORIES
    if categories is None:
        categories = SAMPLE_CATEGORIES
    
    # If actual_spending parameter is None, load from budget data
    if actual_spending is None:
        budget_data = load_budget_data()
        actual_spending = budget_data.get('actual_spending', {})
    
    # Convert string amounts in actual_spending to Decimal objects
    decimal_spending = {}
    for category, amount in actual_spending.items():
        if not isinstance(amount, Decimal):
            decimal_spending[category] = Decimal(str(amount))
        else:
            decimal_spending[category] = amount
    
    # Create a Budget object
    return create_budget({'categories': categories, 'actual_spending': decimal_spending})


def create_analyzed_budget(categories: Optional[List] = None, actual_spending: Optional[Dict[str, Decimal]] = None) -> Budget:
    """
    Creates a Budget object and runs the analyze method on it
    
    Args:
        categories: Optional list of Category objects
        actual_spending: Optional dictionary mapping category names to actual spending amounts
        
    Returns:
        An analyzed Budget object with variance calculations
    """
    # Create a Budget object
    budget = create_test_budget(categories, actual_spending)
    
    # Run the analyze method
    budget.analyze()
    
    return budget


def create_budget_with_surplus() -> Budget:
    """
    Creates a Budget object that will have a surplus when analyzed
    
    Returns:
        A Budget object that will show a surplus
    """
    # Create categories with surplus
    categories = create_categories_with_surplus()
    
    # Get actual spending from budget data
    budget_data = load_budget_data()
    actual_spending = budget_data.get('actual_spending', {})
    
    # Create a Budget object with these parameters
    budget = create_test_budget(categories, actual_spending)
    
    # Call analyze on the Budget object
    budget.analyze()
    
    return budget


def create_budget_with_deficit() -> Budget:
    """
    Creates a Budget object that will have a deficit when analyzed
    
    Returns:
        A Budget object that will show a deficit
    """
    # Create categories with deficit
    categories = create_categories_with_deficit()
    
    # Get actual spending from budget data
    budget_data = load_budget_data()
    actual_spending = budget_data.get('actual_spending', {})
    
    # Create a Budget object with these parameters
    budget = create_test_budget(categories, actual_spending)
    
    # Call analyze on the Budget object
    budget.analyze()
    
    return budget


def create_budget_with_zero_balance() -> Budget:
    """
    Creates a Budget object that will have a zero balance when analyzed
    
    Returns:
        A Budget object that will show a zero balance
    """
    # Create test categories
    categories = create_test_categories()
    
    # Create actual_spending dictionary with amounts matching budget exactly
    actual_spending = {}
    for category in categories:
        actual_spending[category.name] = category.weekly_amount
    
    # Create a Budget object with these parameters
    budget = create_test_budget(categories, actual_spending)
    
    # Call analyze on the Budget object
    budget.analyze()
    
    return budget


def create_budget_from_test_sheet_data() -> Budget:
    """
    Creates a Budget object from test sheet data format
    
    Returns:
        A Budget object created from sheet data
    """
    # Load sheet_data from budget data
    budget_data = load_budget_data()
    sheet_data = budget_data.get('sheet_data', [])
    
    # Load actual_spending from budget data
    actual_spending = budget_data.get('actual_spending', {})
    
    # Create a Budget object using create_budget_from_sheet_data function
    return create_budget_from_sheet_data(sheet_data, actual_spending)


def get_expected_analysis_results(scenario: Optional[str] = None) -> Dict:
    """
    Returns the expected analysis results for test validation
    
    Args:
        scenario: Optional scenario name ('surplus', 'deficit', 'zero')
        
    Returns:
        Dictionary with expected analysis results
    """
    # If scenario is None, use 'surplus' as default
    if scenario is None:
        scenario = 'surplus'
    
    # Load budget data and extract test_scenarios
    budget_data = load_budget_data()
    test_scenarios = budget_data.get('test_scenarios', {})
    
    # Return the expected results for the specified scenario
    if scenario in test_scenarios:
        results = test_scenarios[scenario]
    else:
        results = budget_data.get('expected_analysis', {})
    
    # Convert string amounts to Decimal objects
    for key in ['total_budget', 'total_spent', 'total_variance']:
        if key in results and not isinstance(results[key], Decimal):
            results[key] = Decimal(str(results[key]))
    
    return results


def create_budget_with_transactions(transactions: Optional[List] = None) -> Budget:
    """
    Creates a Budget object from categorized transactions
    
    Args:
        transactions: Optional list of Transaction objects
        
    Returns:
        A Budget object created from transaction data
    """
    # If transactions parameter is None, use CATEGORIZED_TRANSACTIONS
    if transactions is None:
        transactions = CATEGORIZED_TRANSACTIONS
    
    # Create categories using create_test_categories
    categories = create_test_categories()
    
    # Build actual_spending dictionary by aggregating transactions by category
    actual_spending = {}
    for transaction in transactions:
        if transaction.category:
            category = transaction.category
            if category not in actual_spending:
                actual_spending[category] = Decimal('0')
            actual_spending[category] += transaction.amount
    
    # Create a Budget object with categories and actual_spending
    budget = create_test_budget(categories, actual_spending)
    
    return budget


# Create predefined Budget objects for tests
SAMPLE_BUDGET = create_test_budget()
ANALYZED_BUDGET = create_analyzed_budget()