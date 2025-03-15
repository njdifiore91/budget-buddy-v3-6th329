"""
transaction.py - Defines the Transaction model class and related utility functions for representing financial transactions in the Budget Management Application.

This model encapsulates transaction data from Capital One API and Google Sheets, providing methods for categorization, formatting, and aggregation.
"""

import decimal  # standard library
from decimal import Decimal  # standard library
import datetime  # standard library
import logging  # standard library
from typing import List, Dict, Optional, Union  # standard library

from ..utils.validation import is_valid_transaction, parse_amount, filter_duplicates
from ..utils.formatters import format_transaction_for_sheets, format_category_for_sheets
from ..utils.date_utils import parse_capital_one_date, parse_sheets_date, convert_to_est
from ..utils.error_handlers import ValidationError
from .category import Category

# Set up logger
logger = logging.getLogger(__name__)

# Constants
REQUIRED_TRANSACTION_FIELDS = ['location', 'amount', 'timestamp']


class Transaction:
    """Represents a financial transaction with location, amount, timestamp, and optional category"""
    
    def __init__(self, location: str, amount: decimal.Decimal, timestamp: datetime, 
                 category: Optional[str] = None, transaction_id: Optional[str] = None, 
                 description: Optional[str] = None):
        """
        Initialize a new Transaction instance
        
        Args:
            location: Merchant name or transaction location
            amount: Transaction amount in USD
            timestamp: Transaction date and time
            category: Budget category (optional)
            transaction_id: Unique identifier from Capital One (optional)
            description: Additional transaction details (optional)
        """
        self.location = location
        self.amount = amount
        self.timestamp = convert_to_est(timestamp)
        self.category = category
        self.transaction_id = transaction_id
        self.description = description
        logger.debug(f"Created transaction: {self.location} for {self.amount:.2f} at {self.timestamp}")
    
    def __str__(self) -> str:
        """String representation of the Transaction"""
        category_str = f", category: {self.category}" if self.category else ""
        return f"{self.location}: ${self.amount:.2f} on {self.timestamp.strftime('%Y-%m-%d')}{category_str}"
    
    def __repr__(self) -> str:
        """Official string representation of the Transaction"""
        return f'Transaction(location="{self.location}", amount={self.amount}, timestamp={self.timestamp}, category="{self.category}")'
    
    def __eq__(self, other: object) -> bool:
        """Equality comparison between Transaction objects"""
        if not isinstance(other, Transaction):
            return False
        return (self.location == other.location and
                self.amount == other.amount and
                self.timestamp == other.timestamp)
    
    def set_category(self, category: Union[str, Category]) -> None:
        """
        Set or update the category for this transaction
        
        Args:
            category: Category name or Category object
        """
        if isinstance(category, Category):
            category = category.name
        
        if isinstance(category, str):
            category = format_category_for_sheets(category)
            
        self.category = category
        logger.debug(f"Set category '{category}' for transaction: {self.location}")
    
    def to_dict(self) -> Dict:
        """
        Convert Transaction to dictionary representation
        
        Returns:
            Dictionary with transaction data
        """
        transaction_dict = {
            'location': self.location,
            'amount': self.amount,
            'timestamp': self.timestamp,
            'category': self.category
        }
        
        if self.transaction_id:
            transaction_dict['transaction_id'] = self.transaction_id
            
        if self.description:
            transaction_dict['description'] = self.description
            
        return transaction_dict
    
    def to_sheets_format(self) -> List:
        """
        Convert Transaction to format suitable for Google Sheets
        
        Returns:
            List of values formatted for Google Sheets
        """
        return format_transaction_for_sheets(self.to_dict())


def create_transaction(transaction_data: Dict) -> Transaction:
    """
    Factory function to create a Transaction object from raw data
    
    Args:
        transaction_data: Dictionary containing transaction data
        
    Returns:
        A new Transaction instance
        
    Raises:
        ValidationError: If transaction_data is invalid
    """
    try:
        # Validate transaction data
        if not is_valid_transaction(transaction_data):
            logger.error(f"Invalid transaction data: {transaction_data}")
            raise ValidationError(f"Invalid transaction data", "transaction")
        
        # Extract required fields
        location = transaction_data['location']
        amount = parse_amount(transaction_data['amount'])
        
        # Parse timestamp based on its type
        timestamp = transaction_data['timestamp']
        if isinstance(timestamp, str):
            try:
                # Try parsing as Capital One format first
                timestamp = parse_capital_one_date(timestamp)
            except ValueError:
                try:
                    # Then try Google Sheets format
                    timestamp = parse_sheets_date(timestamp)
                except ValueError:
                    # If both fail, use datetime's parsing as a fallback
                    timestamp = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Extract optional fields
        category = transaction_data.get('category')
        transaction_id = transaction_data.get('transaction_id')
        description = transaction_data.get('description')
        
        # Create and return Transaction instance
        return Transaction(
            location=location,
            amount=amount,
            timestamp=timestamp,
            category=category,
            transaction_id=transaction_id,
            description=description
        )
        
    except (ValueError, KeyError, decimal.InvalidOperation) as e:
        logger.error(f"Error creating transaction: {str(e)}")
        raise ValidationError(f"Error creating transaction: {str(e)}", "transaction")


def create_transactions_from_capital_one(api_transactions: List) -> List[Transaction]:
    """
    Creates a list of Transaction objects from Capital One API response
    
    Args:
        api_transactions: List of transaction dictionaries from Capital One API
        
    Returns:
        List of Transaction objects
    """
    if not isinstance(api_transactions, list):
        logger.warning("Invalid API transactions: not a list")
        return []
    
    transactions = []
    
    for transaction_data in api_transactions:
        try:
            # Extract required fields from Capital One format
            transaction_dict = {
                'location': transaction_data.get('merchant', {}).get('name', transaction_data.get('description', 'Unknown')),
                'amount': transaction_data.get('amount'),
                'timestamp': transaction_data.get('transactionDate'),
                'transaction_id': transaction_data.get('id'),
                'description': transaction_data.get('description')
            }
            
            # Create Transaction object
            transaction = create_transaction(transaction_dict)
            transactions.append(transaction)
            
        except Exception as e:
            logger.warning(f"Error processing transaction from Capital One: {str(e)}")
            continue
    
    # Filter out any duplicate transactions
    unique_transactions = filter_duplicates([t.to_dict() for t in transactions])
    filtered_transactions = [create_transaction(t) for t in unique_transactions]
    
    logger.info(f"Created {len(filtered_transactions)} unique transactions from Capital One data")
    return filtered_transactions


def create_transactions_from_sheet_data(sheet_data: List) -> List[Transaction]:
    """
    Creates a list of Transaction objects from Google Sheets data
    
    Args:
        sheet_data: Rows of transaction data from Google Sheets
        
    Returns:
        List of Transaction objects
    """
    if not isinstance(sheet_data, list):
        logger.warning("Invalid sheet data: not a list")
        return []
    
    transactions = []
    invalid_rows = 0
    
    for i, row in enumerate(sheet_data):
        try:
            # Skip rows that don't have enough data
            if not isinstance(row, list) or len(row) < 3:
                logger.warning(f"Skipping row {i}: insufficient data")
                invalid_rows += 1
                continue
            
            # Extract data from sheet row format [Location, Amount, Timestamp, Category]
            location = str(row[0]) if row[0] is not None else ""
            amount = row[1]
            timestamp = row[2]
            category = row[3] if len(row) > 3 and row[3] else None
            
            # Create transaction dictionary
            transaction_dict = {
                'location': location,
                'amount': amount,
                'timestamp': timestamp
            }
            
            if category:
                transaction_dict['category'] = category
            
            # Create Transaction object
            transaction = create_transaction(transaction_dict)
            transactions.append(transaction)
            
        except Exception as e:
            # Log invalid rows that are skipped
            logger.warning(f"Error processing row {i}: {str(e)}")
            invalid_rows += 1
            continue
    
    if invalid_rows:
        logger.info(f"Skipped {invalid_rows} invalid rows when creating transactions")
    
    logger.info(f"Created {len(transactions)} transactions from sheet data")
    return transactions


def get_transaction_locations(transactions: List[Transaction]) -> List[str]:
    """
    Extracts just the locations from a list of Transaction objects
    
    Args:
        transactions: List of Transaction objects
        
    Returns:
        List of transaction locations as strings
    """
    if not isinstance(transactions, list):
        logger.warning("Invalid transactions input: not a list")
        return []
    
    # Use list comprehension to extract location attribute from each Transaction object
    return [transaction.location for transaction in transactions if isinstance(transaction, Transaction)]


def group_transactions_by_category(transactions: List[Transaction]) -> Dict[str, List[Transaction]]:
    """
    Groups transactions by their assigned category
    
    Args:
        transactions: List of Transaction objects
        
    Returns:
        Dictionary mapping category names to lists of transactions
    """
    if not isinstance(transactions, list):
        logger.warning("Invalid transactions input: not a list")
        return {}
    
    grouped_transactions = {}
    
    for transaction in transactions:
        if not isinstance(transaction, Transaction):
            continue
            
        # Get category, defaulting to "Uncategorized" if None
        category = transaction.category or "Uncategorized"
        
        # Add transaction to appropriate category list
        if category not in grouped_transactions:
            grouped_transactions[category] = []
            
        grouped_transactions[category].append(transaction)
    
    return grouped_transactions


def calculate_category_totals(transactions: List[Transaction]) -> Dict[str, Decimal]:
    """
    Calculates the total amount spent in each category
    
    Args:
        transactions: List of Transaction objects
        
    Returns:
        Dictionary mapping category names to total amounts
    """
    # Group transactions by category
    grouped_transactions = group_transactions_by_category(transactions)
    
    # Calculate totals for each category
    category_totals = {}
    for category, category_transactions in grouped_transactions.items():
        # Sum transaction amounts in this category
        total = sum(transaction.amount for transaction in category_transactions)
        category_totals[category] = total
    
    return category_totals