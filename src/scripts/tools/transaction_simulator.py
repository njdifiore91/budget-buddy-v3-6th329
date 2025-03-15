"""
transaction_simulator.py - A utility tool for simulating financial transactions for the Budget Management Application.

This module generates realistic transaction data that mimics Capital One API responses, allowing for testing, 
development, and demonstration of the application without requiring actual banking API access.
"""

import os
import json
import random
import datetime
from datetime import timedelta
import uuid
import decimal
from decimal import Decimal
import argparse
from typing import List, Dict, Optional, Union, Any

from ...scripts.config.script_settings import DEVELOPMENT_SETTINGS
from ...scripts.config.path_constants import ROOT_DIR, DATA_DIR, ensure_dir_exists
from ...scripts.config.logging_setup import get_logger
from ...backend.models.transaction import Transaction
from ...backend.api_clients.capital_one_client import format_date_for_api

# Set up logger
logger = get_logger('transaction_simulator')

# Default settings
DEFAULT_TRANSACTION_COUNT = DEVELOPMENT_SETTINGS.get('GENERATE_TEST_DATA_COUNT', 50)
DEFAULT_OUTPUT_DIR = os.path.join(DATA_DIR, 'simulated_transactions')

# Merchant categories and their typical merchants
MERCHANT_CATEGORIES = {
    "Grocery": ["Grocery Store", "Supermarket", "Whole Foods", "Trader Joe's", "Safeway", "Kroger", "Publix"],
    "Dining": ["Restaurant", "Cafe", "Coffee Shop", "Fast Food", "Diner", "Pizzeria", "Food Delivery"],
    "Transportation": ["Gas Station", "Uber", "Lyft", "Public Transit", "Parking", "Toll", "Auto Repair"],
    "Shopping": ["Online Retailer", "Department Store", "Clothing Store", "Electronics Store", "Bookstore", "Hardware Store"],
    "Utilities": ["Electric Company", "Water Service", "Gas Company", "Internet Provider", "Phone Company", "Streaming Service"],
    "Entertainment": ["Movie Theater", "Concert Venue", "Sports Event", "Subscription Service", "Gaming"],
    "Health": ["Pharmacy", "Doctor's Office", "Hospital", "Gym", "Fitness Center", "Health Insurance"],
    "Home": ["Rent Payment", "Mortgage Payment", "Home Improvement", "Furniture Store", "Home Goods", "Cleaning Service"]
}

# Amount ranges for each category (min, max) in USD
AMOUNT_RANGES = {
    "Grocery": (15.00, 200.00),
    "Dining": (8.00, 100.00),
    "Transportation": (20.00, 80.00),
    "Shopping": (10.00, 300.00),
    "Utilities": (30.00, 200.00),
    "Entertainment": (10.00, 150.00),
    "Health": (5.00, 200.00),
    "Home": (50.00, 2000.00)
}


def load_sample_transactions(fixture_path: str) -> List[Dict[str, Any]]:
    """
    Loads sample transactions from a fixture file

    Args:
        fixture_path: Path to the sample transaction fixture file

    Returns:
        List of transaction dictionaries
    """
    try:
        # Construct the absolute path if a relative path is given
        if not os.path.isabs(fixture_path):
            fixture_path = os.path.join(ROOT_DIR, fixture_path)

        # Check if file exists
        if not os.path.exists(fixture_path):
            logger.warning(f"Fixture file not found: {fixture_path}")
            return []

        # Load JSON data from file
        with open(fixture_path, 'r') as f:
            transactions = json.load(f)

        logger.info(f"Loaded {len(transactions)} transactions from {fixture_path}")
        return transactions

    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading sample transactions: {str(e)}")
        return []


def generate_random_transaction(timestamp: Optional[datetime.datetime] = None,
                               category: Optional[str] = None) -> Dict[str, Any]:
    """
    Generates a single random transaction

    Args:
        timestamp: Optional timestamp for the transaction
        category: Optional category for the transaction

    Returns:
        Dictionary with transaction data
    """
    # Generate random timestamp within the last week if not provided
    if timestamp is None:
        now = datetime.datetime.now()
        days_ago = random.randint(0, 6)  # 0-6 days ago
        hours_ago = random.randint(0, 23)  # 0-23 hours ago
        minutes_ago = random.randint(0, 59)  # 0-59 minutes ago
        timestamp = now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)

    # Select random category if not provided
    if category is None:
        category = random.choice(list(MERCHANT_CATEGORIES.keys()))

    # Select random merchant for the category
    merchant = random.choice(MERCHANT_CATEGORIES[category])

    # Generate random amount for the category
    min_amount, max_amount = AMOUNT_RANGES[category]
    amount = round(random.uniform(min_amount, max_amount), 2)

    # Generate unique transaction ID
    transaction_id = str(uuid.uuid4())

    # Create transaction dictionary
    transaction = {
        'id': transaction_id,
        'merchant': {
            'name': merchant,
            'category': category
        },
        'amount': str(amount),
        'transactionDate': timestamp.isoformat() + 'Z',
        'description': f"Purchase at {merchant}"
    }

    return transaction


def generate_transactions(count: int,
                         start_date: Optional[datetime.datetime] = None,
                         end_date: Optional[datetime.datetime] = None) -> List[Dict[str, Any]]:
    """
    Generates a list of random transactions

    Args:
        count: Number of transactions to generate
        start_date: Optional start date for transactions
        end_date: Optional end date for transactions

    Returns:
        List of transaction dictionaries
    """
    # Set default date range if not provided
    if start_date is None:
        start_date = datetime.datetime.now() - timedelta(days=7)
    if end_date is None:
        end_date = datetime.datetime.now()

    transactions = []
    for _ in range(count):
        # Generate random timestamp within date range
        time_range = (end_date - start_date).total_seconds()
        random_seconds = random.randint(0, int(time_range))
        timestamp = start_date + timedelta(seconds=random_seconds)

        # Generate random transaction
        transaction = generate_random_transaction(timestamp)
        transactions.append(transaction)

    # Sort transactions by date (newest first)
    transactions.sort(key=lambda x: x['transactionDate'], reverse=True)

    logger.info(f"Generated {len(transactions)} random transactions")
    return transactions


def generate_realistic_transactions(count: int,
                                  start_date: Optional[datetime.datetime] = None,
                                  end_date: Optional[datetime.datetime] = None) -> List[Dict[str, Any]]:
    """
    Generates a realistic set of transactions with appropriate distribution

    Args:
        count: Number of transactions to generate
        start_date: Optional start date for transactions
        end_date: Optional end date for transactions

    Returns:
        List of transaction dictionaries
    """
    # Set default date range if not provided
    if start_date is None:
        start_date = datetime.datetime.now() - timedelta(days=7)
    if end_date is None:
        end_date = datetime.datetime.now()

    # Define realistic distribution of transactions by category
    category_distribution = {
        "Grocery": 0.20,  # 20% of transactions
        "Dining": 0.25,   # 25% of transactions
        "Transportation": 0.15,
        "Shopping": 0.10,
        "Utilities": 0.05,
        "Entertainment": 0.10,
        "Health": 0.05,
        "Home": 0.10
    }

    transactions = []
    
    # Calculate number of transactions per category
    for category, percentage in category_distribution.items():
        category_count = int(count * percentage)
        
        # Ensure at least one transaction per category
        if category_count == 0 and percentage > 0:
            category_count = 1
            
        # Generate transactions for this category
        for _ in range(category_count):
            # Generate realistic timestamp
            # More frequent categories have more recent timestamps
            recency_factor = category_distribution[category]
            max_days_ago = 7 * (1 - recency_factor)  # Higher percentage = more recent
            days_ago = random.uniform(0, max_days_ago)
            
            timestamp = end_date - timedelta(days=days_ago)
            
            # Ensure timestamp is after start date
            if timestamp < start_date:
                timestamp = start_date + timedelta(seconds=random.randint(0, int((end_date - start_date).total_seconds())))
            
            # Generate transaction for this category
            transaction = generate_random_transaction(timestamp, category)
            transactions.append(transaction)

    # Generate any remaining transactions needed to reach the requested count
    remaining = count - len(transactions)
    if remaining > 0:
        for _ in range(remaining):
            timestamp = start_date + timedelta(seconds=random.randint(0, int((end_date - start_date).total_seconds())))
            transaction = generate_random_transaction(timestamp)
            transactions.append(transaction)

    # Sort transactions by date (newest first)
    transactions.sort(key=lambda x: x['transactionDate'], reverse=True)

    logger.info(f"Generated {len(transactions)} realistic transactions")
    return transactions


def save_transactions(transactions: List[Dict[str, Any]], output_path: str) -> bool:
    """
    Saves generated transactions to a JSON file

    Args:
        transactions: List of transaction dictionaries
        output_path: Path to save the transactions

    Returns:
        True if save was successful, False otherwise
    """
    try:
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        ensure_dir_exists(output_dir)

        # Write transactions to file
        with open(output_path, 'w') as f:
            json.dump(transactions, f, indent=2)

        logger.info(f"Saved {len(transactions)} transactions to {output_path}")
        return True

    except Exception as e:
        logger.error(f"Error saving transactions: {str(e)}")
        return False


def create_capital_one_response(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Creates a simulated Capital One API response containing transactions

    Args:
        transactions: List of transaction dictionaries

    Returns:
        Simulated API response
    """
    response = {
        "transactions": transactions,
        "pagination": {
            "totalPages": 1,
            "limit": len(transactions),
            "offset": 0,
            "totalResults": len(transactions)
        },
        "status": "success"
    }

    return response


def simulate_weekly_transactions(count: int, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Simulates a week's worth of transactions for testing

    Args:
        count: Number of transactions to generate
        output_path: Optional path to save the transactions

    Returns:
        Simulated Capital One API response
    """
    # Calculate date range for the past week
    end_date = datetime.datetime.now()
    start_date = end_date - timedelta(days=7)

    # Generate realistic transactions
    transactions = generate_realistic_transactions(count, start_date, end_date)

    # Create Capital One API response format
    api_response = create_capital_one_response(transactions)

    # Save to file if output path is provided
    if output_path:
        # Ensure the directory exists
        output_dir = os.path.dirname(output_path)
        ensure_dir_exists(output_dir)

        with open(output_path, 'w') as f:
            json.dump(api_response, f, indent=2)
        
        logger.info(f"Saved simulated API response to {output_path}")

    return api_response


class TransactionSimulator:
    """
    Class for simulating financial transactions with various parameters
    """
    
    def __init__(self, 
                 merchant_categories: Optional[Dict[str, List[str]]] = None,
                 amount_ranges: Optional[Dict[str, tuple]] = None,
                 output_dir: Optional[str] = None):
        """
        Initialize the transaction simulator with configuration

        Args:
            merchant_categories: Dictionary mapping categories to merchant lists
            amount_ranges: Dictionary mapping categories to (min, max) amount ranges
            output_dir: Directory for saving generated transactions
        """
        # Use provided values or defaults
        self.merchant_categories = merchant_categories or MERCHANT_CATEGORIES
        self.amount_ranges = amount_ranges or AMOUNT_RANGES
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        
        # Ensure output directory exists
        ensure_dir_exists(self.output_dir)
        
        logger.info("Initialized TransactionSimulator")
    
    def generate_transaction(self, 
                            category: Optional[str] = None,
                            merchant: Optional[str] = None,
                            amount: Optional[Decimal] = None,
                            timestamp: Optional[datetime.datetime] = None) -> Dict[str, Any]:
        """
        Generate a single transaction with specified or random parameters

        Args:
            category: Optional category for the transaction
            merchant: Optional merchant name
            amount: Optional transaction amount
            timestamp: Optional transaction timestamp

        Returns:
            Transaction dictionary
        """
        # Select random category if not provided
        if category is None:
            category = random.choice(list(self.merchant_categories.keys()))
        elif category not in self.merchant_categories:
            logger.warning(f"Unknown category: {category}. Using random category instead.")
            category = random.choice(list(self.merchant_categories.keys()))
        
        # Select random merchant from category if not provided
        if merchant is None:
            merchant = random.choice(self.merchant_categories[category])
        
        # Generate random amount for category if not provided
        if amount is None:
            min_amount, max_amount = self.amount_ranges[category]
            amount = Decimal(str(round(random.uniform(min_amount, max_amount), 2)))
        
        # Generate random timestamp if not provided
        if timestamp is None:
            now = datetime.datetime.now()
            days_ago = random.randint(0, 6)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            timestamp = now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
        
        # Generate unique transaction ID
        transaction_id = str(uuid.uuid4())
        
        # Create transaction dictionary
        transaction = {
            'id': transaction_id,
            'merchant': {
                'name': merchant,
                'category': category
            },
            'amount': str(amount),
            'transactionDate': timestamp.isoformat() + 'Z',
            'description': f"Purchase at {merchant}"
        }
        
        return transaction
    
    def generate_batch(self, 
                      count: int,
                      start_date: Optional[datetime.datetime] = None,
                      end_date: Optional[datetime.datetime] = None,
                      realistic: bool = True) -> List[Dict[str, Any]]:
        """
        Generate a batch of transactions

        Args:
            count: Number of transactions to generate
            start_date: Optional start date for transactions
            end_date: Optional end date for transactions
            realistic: Whether to use realistic distribution

        Returns:
            List of transaction dictionaries
        """
        if realistic:
            return generate_realistic_transactions(count, start_date, end_date)
        else:
            return generate_transactions(count, start_date, end_date)
    
    def save_to_file(self, 
                    transactions: List[Dict[str, Any]],
                    filename: Optional[str] = None,
                    format: str = 'raw') -> str:
        """
        Save generated transactions to a file

        Args:
            transactions: List of transaction dictionaries
            filename: Optional filename (default: auto-generated with timestamp)
            format: Output format ('raw' or 'capital_one')

        Returns:
            Path to saved file
        """
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"transactions_{timestamp}.json"
        
        # Construct full output path
        output_path = os.path.join(self.output_dir, filename)
        
        # Format data according to specified format
        if format.lower() == 'capital_one':
            data = create_capital_one_response(transactions)
        else:
            data = transactions
        
        # Save to file
        success = save_transactions(data, output_path)
        
        if success:
            return output_path
        else:
            logger.error(f"Failed to save transactions to {output_path}")
            return ""
    
    def simulate_week(self, 
                     count: int,
                     output_file: Optional[str] = None,
                     format: str = 'capital_one') -> Dict[str, Any]:
        """
        Simulate a full week of transactions

        Args:
            count: Number of transactions to simulate
            output_file: Optional filename to save results
            format: Output format ('raw' or 'capital_one')

        Returns:
            Simulation results with transactions and metadata
        """
        # Calculate date range for the past week
        end_date = datetime.datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # Generate transactions
        transactions = self.generate_batch(count, start_date, end_date, realistic=True)
        
        # Format response
        if format.lower() == 'capital_one':
            result = create_capital_one_response(transactions)
        else:
            result = {
                'transactions': transactions,
                'metadata': {
                    'count': len(transactions),
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                }
            }
        
        # Save to file if output_file provided
        if output_file:
            self.save_to_file(transactions, output_file, format)
        
        return result
    
    def load_from_fixture(self, fixture_path: str) -> List[Dict[str, Any]]:
        """
        Load transactions from a fixture file

        Args:
            fixture_path: Path to the fixture file

        Returns:
            List of transaction dictionaries
        """
        return load_sample_transactions(fixture_path)


def main() -> int:
    """
    Main function for command-line execution

    Returns:
        Exit code (0 for success)
    """
    parser = argparse.ArgumentParser(description='Generate simulated financial transactions for testing')
    parser.add_argument('-c', '--count', type=int, default=DEFAULT_TRANSACTION_COUNT,
                        help=f'Number of transactions to generate (default: {DEFAULT_TRANSACTION_COUNT})')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Output file path (default: auto-generated in data/simulated_transactions/)')
    parser.add_argument('-f', '--format', type=str, choices=['raw', 'capital_one'], default='capital_one',
                        help='Output format (default: capital_one)')
    parser.add_argument('-r', '--realistic', action='store_true',
                        help='Generate realistic transaction distribution')
    parser.add_argument('-d', '--days', type=int, default=7,
                        help='Number of days to generate transactions for (default: 7)')
    
    args = parser.parse_args()
    
    # Create simulator
    simulator = TransactionSimulator()
    
    # Calculate date range
    end_date = datetime.datetime.now()
    start_date = end_date - timedelta(days=args.days)
    
    # Generate transactions
    if args.realistic:
        transactions = simulator.generate_batch(args.count, start_date, end_date, realistic=True)
    else:
        transactions = simulator.generate_batch(args.count, start_date, end_date, realistic=False)
    
    # Save to file
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(DEFAULT_OUTPUT_DIR, f"transactions_{timestamp}.json")
    
    simulator.save_to_file(transactions, output_path, args.format)
    
    logger.info(f"Successfully generated {len(transactions)} transactions and saved to {output_path}")
    return 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)