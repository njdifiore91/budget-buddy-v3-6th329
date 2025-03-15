"""
Provides test fixture data for financial transactions used in unit and integration tests for the Budget Management Application. This module creates Transaction objects with predefined data for consistent and reproducible testing of transaction retrieval, categorization, and budget analysis functionality.
"""

import os  # standard library
import json  # standard library
import decimal  # standard library
from decimal import Decimal  # standard library
import datetime  # standard library
from typing import List, Dict, Optional, Union  # standard library
import random  # standard library

from ...models.transaction import Transaction, create_transaction, create_transactions_from_capital_one
from ...models.category import Category
from .categories import get_category_by_name, SAMPLE_CATEGORIES
from ...utils.date_utils import parse_capital_one_date, convert_to_est

# Define fixture directory and files
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'data')
TRANSACTIONS_FILE = os.path.join(FIXTURES_DIR, 'transactions.json')


def load_transaction_data() -> List[Dict]:
    """
    Loads raw transaction data from the JSON fixture file
    
    Returns:
        List of transaction dictionaries
    """
    try:
        with open(TRANSACTIONS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # If file doesn't exist, return a default list of transactions
        return [
            {
                "location": "Whole Foods",
                "amount": "75.32",
                "timestamp": "2023-07-16T10:30:45.123Z",
                "transaction_id": "tx_123456",
                "description": "Grocery shopping"
            },
            {
                "location": "Starbucks",
                "amount": "5.45",
                "timestamp": "2023-07-15T08:15:22.456Z",
                "transaction_id": "tx_123457",
                "description": "Morning coffee"
            },
            {
                "location": "Amazon",
                "amount": "29.99",
                "timestamp": "2023-07-14T14:22:11.789Z",
                "transaction_id": "tx_123458",
                "description": "Online purchase"
            }
        ]
    except json.JSONDecodeError:
        # If JSON is invalid, return a simple list
        return [
            {
                "location": "Grocery Store",
                "amount": "50.00",
                "timestamp": "2023-07-16T12:00:00.000Z",
                "transaction_id": "tx_default",
                "description": "Default transaction"
            }
        ]


def create_test_transaction(location: str, amount: str, timestamp: str, 
                           transaction_id: Optional[str] = None, 
                           description: Optional[str] = None, 
                           category: Optional[Union[str, Category]] = None) -> Transaction:
    """
    Creates a single Transaction object with test data
    
    Args:
        location: Merchant name or transaction location
        amount: Transaction amount in USD
        timestamp: Transaction date and time
        transaction_id: Unique identifier (optional)
        description: Additional transaction details (optional)
        category: Budget category (string or Category object, optional)
        
    Returns:
        A Transaction object with the specified properties
    """
    # Convert amount to Decimal
    amount_decimal = Decimal(str(amount))
    
    # Parse timestamp string to datetime
    try:
        dt = parse_capital_one_date(timestamp)
    except ValueError:
        # Use current time if parsing fails
        dt = datetime.datetime.now()
    
    dt = convert_to_est(dt)
    
    # Create transaction data dictionary
    transaction_data = {
        'location': location,
        'amount': amount_decimal,
        'timestamp': dt
    }
    
    if transaction_id:
        transaction_data['transaction_id'] = transaction_id
    
    if description:
        transaction_data['description'] = description
    
    # Create transaction object
    transaction = create_transaction(transaction_data)
    
    # Set category if provided
    if category:
        transaction.set_category(category)
    
    return transaction


def create_test_transactions() -> List[Transaction]:
    """
    Creates a list of Transaction objects from the fixture data
    
    Returns:
        List of Transaction objects
    """
    # Load transaction data from fixture
    transactions_data = load_transaction_data()
    
    # Initialize empty list for transactions
    transactions = []
    
    # Create Transaction objects for each item in data
    for transaction_data in transactions_data:
        location = transaction_data.get('location')
        amount = transaction_data.get('amount')
        timestamp = transaction_data.get('timestamp')
        transaction_id = transaction_data.get('transaction_id')
        description = transaction_data.get('description')
        
        # Create and append Transaction object
        transactions.append(create_test_transaction(
            location, amount, timestamp, transaction_id, description
        ))
    
    return transactions


def create_categorized_transactions(categories: Optional[List[Category]] = None) -> List[Transaction]:
    """
    Creates a list of Transaction objects with categories assigned
    
    Args:
        categories: Optional list of Category objects to use for categorization
        
    Returns:
        List of categorized Transaction objects
    """
    # Use sample categories if none provided
    if categories is None:
        categories = SAMPLE_CATEGORIES
    
    # Create test transactions
    transactions = create_test_transactions()
    
    # Assign categories based on transaction location
    for i, transaction in enumerate(transactions):
        # Assign categories in a round-robin fashion
        category_index = i % len(categories)
        transaction.set_category(categories[category_index])
    
    return transactions


def create_uncategorized_transactions() -> List[Transaction]:
    """
    Creates a list of Transaction objects without categories
    
    Returns:
        List of uncategorized Transaction objects
    """
    # Just return basic test transactions without setting categories
    return create_test_transactions()


def get_transaction_by_location(location: str, transactions: List[Transaction]) -> Optional[Transaction]:
    """
    Finds a transaction in the test data by its location
    
    Args:
        location: Transaction location to search for
        transactions: List of transactions to search in
        
    Returns:
        The matching Transaction object or None if not found
    """
    for transaction in transactions:
        if transaction.location == location:
            return transaction
    
    return None


# Create sample transactions for tests
SAMPLE_TRANSACTIONS = create_test_transactions()
CATEGORIZED_TRANSACTIONS = create_categorized_transactions()