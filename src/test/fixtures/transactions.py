"""
transactions.py - Provides test fixture data for financial transactions to be used 
in unit and integration tests for the Budget Management Application.

This module contains predefined transaction objects and factory functions to 
generate test transaction data with various properties for testing transaction 
retrieval, categorization, and budget analysis components.
"""

import json
import datetime
from decimal import Decimal
import random
import copy
from typing import List, Dict, Optional, Union

from ...backend.models.transaction import Transaction, create_transaction
from ...backend.models.category import Category
from ..utils.fixture_loader import load_fixture

# Global constants
VALID_TRANSACTIONS = load_fixture('json/transactions/valid_transactions.json')
INVALID_TRANSACTIONS = load_fixture('json/transactions/invalid_transactions.json')
LARGE_VOLUME_TRANSACTIONS = load_fixture('json/transactions/large_volume_transactions.json')
COMMON_MERCHANTS = ["Grocery Store", "Gas Station", "Coffee Shop", "Restaurant", "Online Retailer", 
                    "Pharmacy", "Movie Theater", "Public Transit", "Gym", "Hardware Store"]
DEFAULT_TRANSACTION_AMOUNT = Decimal('25.00')

def create_test_transaction(
    location: str = "Test Merchant",
    amount: Decimal = DEFAULT_TRANSACTION_AMOUNT,
    timestamp: datetime = None,
    category: Optional[str] = None,
    transaction_id: Optional[str] = None,
    description: Optional[str] = None
) -> Transaction:
    """
    Creates a single Transaction object with specified or default values
    
    Args:
        location: Merchant name or transaction location
        amount: Transaction amount in USD
        timestamp: Transaction date and time
        category: Budget category (optional)
        transaction_id: Unique identifier (optional)
        description: Additional transaction details (optional)
        
    Returns:
        A Transaction object with the specified properties
    """
    # Set default timestamp if none provided
    if timestamp is None:
        timestamp = datetime.datetime.now()
        
    # Create transaction object
    transaction = Transaction(
        location=location,
        amount=amount,
        timestamp=timestamp,
        transaction_id=transaction_id,
        description=description
    )
    
    # Set category if provided
    if category:
        transaction.set_category(category)
        
    return transaction

def create_test_transactions() -> List[Transaction]:
    """
    Creates a list of Transaction objects from the valid transactions fixture
    
    Returns:
        A list of Transaction objects
    """
    transactions = []
    for tx_data in VALID_TRANSACTIONS:
        transaction = create_transaction(tx_data)
        transactions.append(transaction)
    return transactions

def create_categorized_transactions(
    transactions_data: List[Dict],
    category_mapping: Dict[str, str]
) -> List[Transaction]:
    """
    Creates a list of Transaction objects with assigned categories
    
    Args:
        transactions_data: List of transaction dictionaries
        category_mapping: Dictionary mapping location patterns to categories
        
    Returns:
        A list of Transaction objects with categories assigned
    """
    categorized_transactions = []
    
    for tx_data in transactions_data:
        # Create transaction
        transaction = create_transaction(tx_data)
        
        # Assign category based on location
        location = transaction.location
        for pattern, category in category_mapping.items():
            if pattern.lower() in location.lower():
                transaction.set_category(category)
                break
        
        categorized_transactions.append(transaction)
    
    return categorized_transactions

def create_transactions_with_amounts(
    location_amount_mapping: Dict[str, Decimal]
) -> List[Transaction]:
    """
    Creates transactions with specific amounts for budget testing
    
    Args:
        location_amount_mapping: Dictionary mapping locations to amounts
        
    Returns:
        A list of Transaction objects with specified amounts
    """
    transactions = []
    
    for location, amount in location_amount_mapping.items():
        transaction = create_test_transaction(
            location=location,
            amount=amount
        )
        transactions.append(transaction)
    
    return transactions

def get_transaction_fixture_by_name(fixture_name: str) -> List[Dict]:
    """
    Retrieves a specific transaction fixture by name
    
    Args:
        fixture_name: Name of the fixture ('valid', 'invalid', or 'large_volume')
        
    Returns:
        The requested transaction fixture data
    """
    if fixture_name == 'valid':
        return VALID_TRANSACTIONS
    elif fixture_name == 'invalid':
        return INVALID_TRANSACTIONS
    elif fixture_name == 'large_volume':
        return LARGE_VOLUME_TRANSACTIONS
    else:
        raise ValueError(f"Unknown fixture name: {fixture_name}")

class TransactionFactory:
    """
    Factory class for creating test transaction objects with various properties
    """
    
    def __init__(self):
        """Initialize the TransactionFactory"""
        pass
        
    def create_random_transaction(self) -> Transaction:
        """
        Creates a transaction with random but valid values
        
        Returns:
            A Transaction object with random values
        """
        # Generate random location
        location = random.choice(COMMON_MERCHANTS)
        
        # Generate random amount between $1.00 and $100.00
        amount = Decimal(str(round(random.uniform(1.00, 100.00), 2)))
        
        # Generate random timestamp within the past week
        days_ago = random.randint(0, 7)
        hours_ago = random.randint(0, 23)
        timestamp = datetime.datetime.now() - datetime.timedelta(days=days_ago, hours=hours_ago)
        
        # Generate random transaction ID
        transaction_id = f"t-{random.randint(10000, 99999)}"
        
        # Create and return transaction
        return create_test_transaction(
            location=location,
            amount=amount,
            timestamp=timestamp,
            transaction_id=transaction_id
        )
    
    def create_transaction_batch(self, count: int) -> List[Transaction]:
        """
        Creates a batch of transactions
        
        Args:
            count: Number of transactions to create
            
        Returns:
            A list of Transaction objects
        """
        return [self.create_random_transaction() for _ in range(count)]
    
    def create_transactions_for_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        count: int
    ) -> List[Transaction]:
        """
        Creates transactions spread across a date range
        
        Args:
            start_date: Start date for transactions
            end_date: End date for transactions
            count: Number of transactions to create
            
        Returns:
            A list of Transaction objects within the date range
        """
        # Calculate time delta between dates
        delta = end_date - start_date
        delta_seconds = delta.total_seconds()
        
        transactions = []
        for i in range(count):
            # Distribute timestamps evenly across the range
            offset_seconds = (delta_seconds / count) * i
            timestamp = start_date + datetime.timedelta(seconds=offset_seconds)
            
            # Create transaction with the calculated timestamp
            transaction = self.create_random_transaction()
            transaction.timestamp = timestamp
            transactions.append(transaction)
        
        # Sort transactions by timestamp
        transactions.sort(key=lambda t: t.timestamp)
        
        return transactions