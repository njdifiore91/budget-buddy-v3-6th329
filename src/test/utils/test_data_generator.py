"""
Utility module for generating realistic test data for the Budget Management Application.
Provides functions and classes to create test transactions, categories, budgets, and API responses
with configurable properties for various test scenarios.
"""

import os
import json
import random
import datetime
from datetime import timedelta
import decimal
from decimal import Decimal
import logging
from typing import List, Dict, Any, Optional, Union, Callable, TypeVar

from faker import Faker

from .fixture_loader import (
    load_fixture, save_fixture,
    TRANSACTION_FIXTURE_DIR, BUDGET_FIXTURE_DIR, API_RESPONSE_FIXTURE_DIR
)
from ...backend.models.transaction import Transaction, create_transaction
from ...backend.models.category import Category, create_category
from ...backend.models.budget import Budget
from .mock_factory import MockFactory

# Set up logger
logger = logging.getLogger(__name__)

# Initialize faker for generating realistic data
faker = Faker()

# Default values
DEFAULT_TRANSACTION_COUNT = 10
DEFAULT_CATEGORY_COUNT = 5
DEFAULT_CATEGORIES = [
    "Groceries", "Dining", "Entertainment", "Transportation", "Utilities", 
    "Shopping", "Healthcare", "Personal Care", "Home", "Miscellaneous"
]
DEFAULT_MERCHANTS = [
    "Walmart", "Target", "Amazon", "Kroger", "Starbucks", "McDonald's", 
    "Uber", "Netflix", "CVS Pharmacy", "Home Depot"
]


def generate_random_transaction(location=None, amount=None, timestamp=None, category=None, transaction_id=None):
    """
    Generate a random transaction with realistic data
    
    Args:
        location (Optional[str]): Optional predefined location
        amount (Optional[Decimal]): Optional predefined amount
        timestamp (Optional[datetime.datetime]): Optional predefined timestamp
        category (Optional[str]): Optional predefined category
        transaction_id (Optional[str]): Optional predefined transaction ID
        
    Returns:
        Dict[str, Any]: Dictionary with random transaction data
    """
    # Generate random location if not provided
    if location is None:
        location = random.choice(DEFAULT_MERCHANTS)
    
    # Generate random amount if not provided (between $1 and $200)
    if amount is None:
        amount = Decimal(str(round(random.uniform(1.0, 200.0), 2)))
    
    # Generate random timestamp within the past week if not provided
    if timestamp is None:
        days_ago = random.randint(0, 6)
        timestamp = datetime.datetime.now() - datetime.timedelta(days=days_ago)
    
    # Generate random category if not provided
    if category is None:
        category = random.choice(DEFAULT_CATEGORIES)
    
    # Generate random transaction ID if not provided
    if transaction_id is None:
        transaction_id = f"tr_{faker.uuid4()}"
    
    # Return transaction dictionary
    return {
        'location': location,
        'amount': amount,
        'timestamp': timestamp,
        'category': category,
        'transaction_id': transaction_id
    }


def generate_random_category(name=None, weekly_amount=None):
    """
    Generate a random budget category with realistic data
    
    Args:
        name (Optional[str]): Optional predefined category name
        weekly_amount (Optional[Decimal]): Optional predefined weekly budget amount
        
    Returns:
        Dict[str, Any]: Dictionary with random category data
    """
    # Generate random name if not provided
    if name is None:
        name = random.choice(DEFAULT_CATEGORIES)
    
    # Generate random weekly amount if not provided (between $50 and $500)
    if weekly_amount is None:
        weekly_amount = Decimal(str(round(random.uniform(50.0, 500.0), 2)))
    
    # Return category dictionary
    return {
        'name': name,
        'weekly_amount': weekly_amount
    }


def generate_transaction_batch(count=DEFAULT_TRANSACTION_COUNT, params=None):
    """
    Generate a batch of random transactions
    
    Args:
        count (int): Number of transactions to generate
        params (Optional[Dict[str, Any]]): Optional dictionary of parameters to customize generation
        
    Returns:
        List[Dict[str, Any]]: List of transaction dictionaries
    """
    transactions = []
    
    # Extract parameters from params dictionary or use defaults
    location_list = params.get('locations', DEFAULT_MERCHANTS) if params else DEFAULT_MERCHANTS
    category_list = params.get('categories', DEFAULT_CATEGORIES) if params else DEFAULT_CATEGORIES
    min_amount = params.get('min_amount', 1.0) if params else 1.0
    max_amount = params.get('max_amount', 200.0) if params else 200.0
    days_ago = params.get('days_ago', 7) if params else 7
    
    # Generate transactions
    for _ in range(count):
        # Generate random values within constraints
        location = random.choice(location_list)
        amount = Decimal(str(round(random.uniform(min_amount, max_amount), 2)))
        days_offset = random.randint(0, days_ago - 1)
        timestamp = datetime.datetime.now() - datetime.timedelta(days=days_offset)
        category = random.choice(category_list) if random.random() > 0.2 else None  # 20% chance of no category
        
        # Create transaction with these values
        transaction = generate_random_transaction(
            location=location,
            amount=amount,
            timestamp=timestamp,
            category=category
        )
        
        transactions.append(transaction)
    
    return transactions


def generate_category_batch(count=DEFAULT_CATEGORY_COUNT, params=None):
    """
    Generate a batch of random categories
    
    Args:
        count (int): Number of categories to generate
        params (Optional[Dict[str, Any]]): Optional dictionary of parameters to customize generation
        
    Returns:
        List[Dict[str, Any]]: List of category dictionaries
    """
    categories = []
    
    # Extract parameters from params dictionary or use defaults
    category_names = list(params.get('category_names', DEFAULT_CATEGORIES)) if params else list(DEFAULT_CATEGORIES)
    min_amount = params.get('min_amount', 50.0) if params else 50.0
    max_amount = params.get('max_amount', 500.0) if params else 500.0
    
    # Ensure we don't try to generate more categories than we have names
    count = min(count, len(category_names))
    
    # Randomly select 'count' categories from the list
    selected_categories = random.sample(category_names, count)
    
    # Generate categories
    for name in selected_categories:
        # Generate random weekly amount within constraints
        weekly_amount = Decimal(str(round(random.uniform(min_amount, max_amount), 2)))
        
        # Create category with these values
        category = generate_random_category(
            name=name,
            weekly_amount=weekly_amount
        )
        
        categories.append(category)
    
    return categories


def generate_budget_data(category_count=None, transaction_count=None, params=None):
    """
    Generate a complete budget dataset with categories and transactions
    
    Args:
        category_count (Optional[int]): Number of categories to generate
        transaction_count (Optional[int]): Number of transactions to generate
        params (Optional[Dict[str, Any]]): Optional dictionary of parameters to customize generation
        
    Returns:
        Dict[str, Any]: Dictionary with budget data including categories and transactions
    """
    # Set defaults if not provided
    if category_count is None:
        category_count = DEFAULT_CATEGORY_COUNT
    
    if transaction_count is None:
        transaction_count = DEFAULT_TRANSACTION_COUNT
    
    # Generate categories
    categories = generate_category_batch(category_count, params)
    
    # Extract just the category names
    category_names = [category['name'] for category in categories]
    
    # Prepare parameters for transaction generation with these categories
    transaction_params = params.copy() if params else {}
    transaction_params['categories'] = category_names
    
    # Generate transactions
    transactions = generate_transaction_batch(transaction_count, transaction_params)
    
    # Calculate spending by category
    category_spending = {}
    for transaction in transactions:
        category = transaction.get('category')
        if category:
            if category not in category_spending:
                category_spending[category] = Decimal('0')
            category_spending[category] += transaction['amount']
    
    # Create budget data dictionary
    budget_data = {
        'categories': categories,
        'transactions': transactions,
        'actual_spending': category_spending,
        'total_budget': sum(category['weekly_amount'] for category in categories),
        'total_spent': sum(category_spending.values())
    }
    
    return budget_data


def generate_api_response(api_name, response_type, custom_data=None):
    """
    Generate a mock API response for testing
    
    Args:
        api_name (str): Name of the API (e.g., 'capital_one', 'gemini')
        response_type (str): Type of response (e.g., 'transactions', 'categorization')
        custom_data (Optional[Dict[str, Any]]): Optional custom data to include in the response
        
    Returns:
        Dict[str, Any]: Mock API response data
    """
    # Try to load an existing response fixture to use as a template
    fixture_path = os.path.join(API_RESPONSE_FIXTURE_DIR, api_name, f"{response_type}.json")
    
    try:
        # Load the fixture as a template
        response_template = load_fixture(fixture_path)
        
        # Create a copy to modify
        response = json.loads(json.dumps(response_template))
    except (FileNotFoundError, json.JSONDecodeError):
        # If fixture doesn't exist or can't be loaded, create a basic structure
        if api_name == "capital_one":
            if response_type == "transactions":
                response = {"transactions": []}
            elif response_type == "accounts":
                response = {"accounts": []}
            elif response_type == "transfer":
                response = {"transferId": f"tr_{faker.uuid4()}", "status": "completed"}
            else:
                response = {}
        
        elif api_name == "google_sheets":
            if response_type in ["master_budget", "weekly_spending"]:
                response = {"values": []}
            else:
                response = {}
        
        elif api_name == "gemini":
            if response_type == "categorization":
                response = {
                    "candidates": [{
                        "content": {
                            "parts": [{"text": ""}],
                            "role": "model"
                        },
                        "finishReason": "STOP",
                        "index": 0,
                        "safetyRatings": []
                    }],
                    "promptFeedback": {}
                }
            elif response_type == "insights":
                response = {
                    "candidates": [{
                        "content": {
                            "parts": [{"text": "Weekly Budget Update"}],
                            "role": "model"
                        },
                        "finishReason": "STOP",
                        "index": 0,
                        "safetyRatings": []
                    }],
                    "promptFeedback": {}
                }
            else:
                response = {}
        
        elif api_name == "gmail":
            if response_type == "send":
                response = {"id": f"msg_{faker.uuid4()}", "threadId": f"thread_{faker.uuid4()}"}
            else:
                response = {}
        
        else:
            # Default empty response for unknown API
            response = {}
    
    # Merge with custom data if provided
    if custom_data:
        # If response is a dictionary, we can update it
        if isinstance(response, dict) and isinstance(custom_data, dict):
            # Deep merge function would be better but this is simpler for now
            response.update(custom_data)
        elif isinstance(response, list) and isinstance(custom_data, list):
            # Append lists
            response.extend(custom_data)
    
    return response


def create_transaction_fixture(fixture_name, count=None, params=None):
    """
    Create a transaction fixture file with generated data
    
    Args:
        fixture_name (str): Name to give the fixture file
        count (Optional[int]): Number of transactions to generate
        params (Optional[Dict[str, Any]]): Optional parameters for customizing generation
        
    Returns:
        str: Path to the created fixture file
    """
    if count is None:
        count = DEFAULT_TRANSACTION_COUNT
    
    # Generate transaction data
    transactions = generate_transaction_batch(count, params)
    
    # Save to fixture file
    fixture_path = os.path.join(TRANSACTION_FIXTURE_DIR, fixture_name)
    return save_fixture(transactions, fixture_path)


def create_category_fixture(fixture_name, count=None, params=None):
    """
    Create a category fixture file with generated data
    
    Args:
        fixture_name (str): Name to give the fixture file
        count (Optional[int]): Number of categories to generate
        params (Optional[Dict[str, Any]]): Optional parameters for customizing generation
        
    Returns:
        str: Path to the created fixture file
    """
    if count is None:
        count = DEFAULT_CATEGORY_COUNT
    
    # Generate category data
    categories = generate_category_batch(count, params)
    
    # Save to fixture file
    fixture_path = os.path.join(BUDGET_FIXTURE_DIR, fixture_name)
    return save_fixture(categories, fixture_path)


def create_budget_fixture(fixture_name, category_count=None, transaction_count=None, params=None):
    """
    Create a budget fixture file with generated data
    
    Args:
        fixture_name (str): Name to give the fixture file
        category_count (Optional[int]): Number of categories to generate
        transaction_count (Optional[int]): Number of transactions to generate
        params (Optional[Dict[str, Any]]): Optional parameters for customizing generation
        
    Returns:
        str: Path to the created fixture file
    """
    # Set defaults if not provided
    if category_count is None:
        category_count = DEFAULT_CATEGORY_COUNT
    
    if transaction_count is None:
        transaction_count = DEFAULT_TRANSACTION_COUNT
    
    # Generate budget data
    budget_data = generate_budget_data(category_count, transaction_count, params)
    
    # Save to fixture file
    fixture_path = os.path.join(BUDGET_FIXTURE_DIR, fixture_name)
    return save_fixture(budget_data, fixture_path)


def create_api_response_fixture(api_name, response_type, fixture_name, custom_data=None):
    """
    Create an API response fixture file with generated data
    
    Args:
        api_name (str): Name of the API (e.g., 'capital_one', 'gemini')
        response_type (str): Type of response (e.g., 'transactions', 'categorization')
        fixture_name (str): Name to give the fixture file
        custom_data (Optional[Dict[str, Any]]): Optional custom data to include in the response
        
    Returns:
        str: Path to the created fixture file
    """
    # Generate API response data
    response_data = generate_api_response(api_name, response_type, custom_data)
    
    # Construct path
    fixture_path = os.path.join(API_RESPONSE_FIXTURE_DIR, api_name, fixture_name)
    
    # Save to fixture file
    return save_fixture(response_data, fixture_path)


def generate_test_data_set(scenario_name, params=None):
    """
    Generate a complete set of test data for a test scenario
    
    Args:
        scenario_name (str): Name of the test scenario
        params (Optional[Dict[str, Any]]): Optional parameters for customizing generation
        
    Returns:
        Dict[str, str]: Dictionary mapping data types to fixture paths
    """
    fixtures = {}
    
    # Create transaction fixture
    transactions_fixture = create_transaction_fixture(
        f"{scenario_name}_transactions",
        params.get('transaction_count', DEFAULT_TRANSACTION_COUNT) if params else DEFAULT_TRANSACTION_COUNT,
        params
    )
    fixtures['transactions'] = transactions_fixture
    
    # Create category fixture
    categories_fixture = create_category_fixture(
        f"{scenario_name}_categories",
        params.get('category_count', DEFAULT_CATEGORY_COUNT) if params else DEFAULT_CATEGORY_COUNT,
        params
    )
    fixtures['categories'] = categories_fixture
    
    # Create budget fixture
    budget_fixture = create_budget_fixture(
        f"{scenario_name}_budget",
        params.get('category_count', DEFAULT_CATEGORY_COUNT) if params else DEFAULT_CATEGORY_COUNT,
        params.get('transaction_count', DEFAULT_TRANSACTION_COUNT) if params else DEFAULT_TRANSACTION_COUNT,
        params
    )
    fixtures['budget'] = budget_fixture
    
    # Create API response fixtures
    api_fixtures = {}
    
    # Capital One API responses
    capital_one_transactions = create_api_response_fixture(
        'capital_one',
        'transactions',
        f"{scenario_name}_transactions",
        {'transactions': generate_transaction_batch(
            params.get('transaction_count', DEFAULT_TRANSACTION_COUNT) if params else DEFAULT_TRANSACTION_COUNT,
            params
        )}
    )
    api_fixtures['capital_one_transactions'] = capital_one_transactions
    
    # Gemini API responses
    gemini_categorization = create_api_response_fixture(
        'gemini',
        'categorization',
        f"{scenario_name}_categorization"
    )
    api_fixtures['gemini_categorization'] = gemini_categorization
    
    gemini_insights = create_api_response_fixture(
        'gemini',
        'insights',
        f"{scenario_name}_insights"
    )
    api_fixtures['gemini_insights'] = gemini_insights
    
    fixtures['api_responses'] = api_fixtures
    
    return fixtures


class TestDataGenerator:
    """
    Class for generating test data for the Budget Management Application
    """
    
    def __init__(self, config=None):
        """
        Initialize the test data generator with optional configuration
        
        Args:
            config (Optional[Dict[str, Any]]): Optional configuration dictionary
        """
        self.faker = Faker()
        self.config = config or {}
    
    def generate_transaction(self, params=None):
        """
        Generate a single transaction with optional parameters
        
        Args:
            params (Optional[Dict[str, Any]]): Optional dictionary of parameters
            
        Returns:
            Transaction: Generated Transaction object
        """
        # Extract parameters or use defaults
        location = params.get('location') if params else None
        amount = params.get('amount') if params else None
        timestamp = params.get('timestamp') if params else None
        category = params.get('category') if params else None
        transaction_id = params.get('transaction_id') if params else None
        
        # Generate random values for anything not provided
        if location is None:
            location = random.choice(self.config.get('merchants', DEFAULT_MERCHANTS))
        
        if amount is None:
            min_amount = self.config.get('min_transaction_amount', 1.0)
            max_amount = self.config.get('max_transaction_amount', 200.0)
            amount = Decimal(str(round(random.uniform(min_amount, max_amount), 2)))
        
        if timestamp is None:
            days_ago = self.config.get('transaction_days_ago', 7)
            days_offset = random.randint(0, days_ago - 1)
            timestamp = datetime.datetime.now() - datetime.timedelta(days=days_offset)
        
        if category is None and random.random() > 0.2:  # 80% chance of having a category
            category = random.choice(self.config.get('categories', DEFAULT_CATEGORIES))
        
        # Create a Transaction object
        transaction_data = {
            'location': location,
            'amount': amount,
            'timestamp': timestamp
        }
        
        if category:
            transaction_data['category'] = category
        
        if transaction_id:
            transaction_data['transaction_id'] = transaction_id
        
        return create_transaction(transaction_data)
    
    def generate_transactions(self, count, params=None):
        """
        Generate multiple transactions
        
        Args:
            count (int): Number of transactions to generate
            params (Optional[Dict[str, Any]]): Optional parameters for customization
            
        Returns:
            List[Transaction]: List of generated Transaction objects
        """
        transactions = []
        
        for _ in range(count):
            transaction = self.generate_transaction(params)
            transactions.append(transaction)
        
        return transactions
    
    def generate_category(self, params=None):
        """
        Generate a single category with optional parameters
        
        Args:
            params (Optional[Dict[str, Any]]): Optional dictionary of parameters
            
        Returns:
            Category: Generated Category object
        """
        # Extract parameters or use defaults
        name = params.get('name') if params else None
        weekly_amount = params.get('weekly_amount') if params else None
        
        # Generate random values for anything not provided
        if name is None:
            name = random.choice(self.config.get('categories', DEFAULT_CATEGORIES))
        
        if weekly_amount is None:
            min_amount = self.config.get('min_category_amount', 50.0)
            max_amount = self.config.get('max_category_amount', 500.0)
            weekly_amount = Decimal(str(round(random.uniform(min_amount, max_amount), 2)))
        
        # Create a Category object
        category_data = {
            'name': name,
            'weekly_amount': weekly_amount
        }
        
        return create_category(category_data)
    
    def generate_categories(self, count, params=None):
        """
        Generate multiple categories
        
        Args:
            count (int): Number of categories to generate
            params (Optional[Dict[str, Any]]): Optional parameters for customization
            
        Returns:
            List[Category]: List of generated Category objects
        """
        # Get available category names
        available_categories = list(self.config.get('categories', DEFAULT_CATEGORIES))
        
        # Ensure we don't try to generate more categories than we have names
        count = min(count, len(available_categories))
        
        # Randomly select 'count' categories from the list
        selected_categories = random.sample(available_categories, count)
        
        categories = []
        
        for name in selected_categories:
            category_params = params.copy() if params else {}
            category_params['name'] = name
            
            category = self.generate_category(category_params)
            categories.append(category)
        
        return categories
    
    def generate_budget(self, categories=None, transactions=None, params=None):
        """
        Generate a budget with categories and transactions
        
        Args:
            categories (Optional[List[Category]]): Optional list of Category objects
            transactions (Optional[List[Transaction]]): Optional list of Transaction objects
            params (Optional[Dict[str, Any]]): Optional parameters for customization
            
        Returns:
            Budget: Generated Budget object
        """
        # Generate categories if not provided
        if categories is None:
            category_count = params.get('category_count', DEFAULT_CATEGORY_COUNT) if params else DEFAULT_CATEGORY_COUNT
            categories = self.generate_categories(category_count, params)
        
        # Generate transactions if not provided
        if transactions is None:
            transaction_count = params.get('transaction_count', DEFAULT_TRANSACTION_COUNT) if params else DEFAULT_TRANSACTION_COUNT
            
            # Extract category names for transaction generation
            category_names = [category.name for category in categories]
            transaction_params = params.copy() if params else {}
            transaction_params['categories'] = category_names
            
            transactions = self.generate_transactions(transaction_count, transaction_params)
        
        # Calculate actual spending by category
        actual_spending = {}
        for transaction in transactions:
            category = transaction.category
            if category:
                if category not in actual_spending:
                    actual_spending[category] = Decimal('0')
                actual_spending[category] += transaction.amount
        
        # Create Budget object
        budget_data = {
            'categories': categories,
            'actual_spending': actual_spending
        }
        
        return Budget(categories, actual_spending)
    
    def generate_capital_one_transactions(self, count, params=None):
        """
        Generate transactions in Capital One API response format
        
        Args:
            count (int): Number of transactions to generate
            params (Optional[Dict[str, Any]]): Optional parameters for customization
            
        Returns:
            Dict[str, Any]: Capital One API response with transactions
        """
        # Generate Transaction objects
        transactions = self.generate_transactions(count, params)
        
        # Convert to Capital One API format
        api_transactions = []
        for transaction in transactions:
            api_transaction = {
                'id': transaction.transaction_id or f"tr_{self.faker.uuid4()}",
                'amount': str(transaction.amount),
                'merchant': {
                    'name': transaction.location,
                    'category': transaction.category or "Uncategorized"
                },
                'transactionDate': transaction.timestamp.isoformat(),
                'description': f"Transaction at {transaction.location}"
            }
            api_transactions.append(api_transaction)
        
        # Create Capital One API response
        response = {
            'transactions': api_transactions
        }
        
        return response
    
    def generate_sheets_data(self, sheet_type, params=None):
        """
        Generate data in Google Sheets format
        
        Args:
            sheet_type (str): Type of sheet ('master_budget' or 'weekly_spending')
            params (Optional[Dict[str, Any]]): Optional parameters for customization
            
        Returns:
            List[List[Any]]: Data formatted for Google Sheets
        """
        if sheet_type == 'master_budget':
            # Generate categories
            category_count = params.get('category_count', DEFAULT_CATEGORY_COUNT) if params else DEFAULT_CATEGORY_COUNT
            categories = self.generate_categories(category_count, params)
            
            # Format for Google Sheets
            sheet_data = [
                [category.name, str(category.weekly_amount)]
                for category in categories
            ]
            
            # Add header row
            sheet_data.insert(0, ["Spending Category", "Weekly Amount"])
            
            return sheet_data
        
        elif sheet_type == 'weekly_spending':
            # Generate transactions
            transaction_count = params.get('transaction_count', DEFAULT_TRANSACTION_COUNT) if params else DEFAULT_TRANSACTION_COUNT
            transactions = self.generate_transactions(transaction_count, params)
            
            # Format for Google Sheets
            sheet_data = [
                [
                    transaction.location,
                    str(transaction.amount),
                    transaction.timestamp.isoformat(),
                    transaction.category or ""
                ]
                for transaction in transactions
            ]
            
            # Add header row
            sheet_data.insert(0, ["Transaction Location", "Transaction Amount", "Transaction Time", "Corresponding Category"])
            
            return sheet_data
        
        else:
            logger.warning(f"Unknown sheet type: {sheet_type}")
            return []
    
    def generate_gemini_response(self, response_type, params=None):
        """
        Generate a Gemini AI response for testing
        
        Args:
            response_type (str): Type of response ('categorization' or 'insights')
            params (Optional[Dict[str, Any]]): Optional parameters for customization
            
        Returns:
            Dict[str, Any]: Gemini API response
        """
        if response_type == 'categorization':
            # Generate category assignments
            categories = params.get('categories', DEFAULT_CATEGORIES) if params else DEFAULT_CATEGORIES
            locations = params.get('locations', DEFAULT_MERCHANTS) if params else DEFAULT_MERCHANTS
            
            # Create categorization text
            categorization_text = ""
            for location in locations:
                category = random.choice(categories)
                categorization_text += f"Location: {location} -> Category: {category}\n"
            
            # Create Gemini API response
            response = {
                "candidates": [{
                    "content": {
                        "parts": [{"text": categorization_text}],
                        "role": "model"
                    },
                    "finishReason": "STOP",
                    "index": 0,
                    "safetyRatings": []
                }],
                "promptFeedback": {}
            }
            
            return response
        
        elif response_type == 'insights':
            # Generate budget insights
            total_budget = params.get('total_budget', Decimal('500.00')) if params else Decimal('500.00')
            total_spent = params.get('total_spent', Decimal('450.00')) if params else Decimal('450.00')
            total_variance = total_budget - total_spent
            
            # Create insights text
            insights_text = f"# Weekly Budget Update: ${total_variance} "
            if total_variance >= 0:
                insights_text += "Under Budget\n\n"
                insights_text += "Great job this week! You've managed to stay under budget.\n\n"
            else:
                insights_text += "Over Budget\n\n"
                insights_text += "You've exceeded your budget this week.\n\n"
            
            insights_text += "## Category Performance\n\n"
            
            # Add some fake category performances
            categories = params.get('categories', DEFAULT_CATEGORIES) if params else DEFAULT_CATEGORIES
            for category in random.sample(categories, min(3, len(categories))):
                variance = Decimal(str(round(random.uniform(-50.0, 50.0), 2)))
                percentage = round((variance / Decimal('100.00')) * 100, 2)
                
                if variance >= 0:
                    insights_text += f"- {category}: ${variance} under ({percentage}% saved)\n"
                else:
                    insights_text += f"- {category}: ${abs(variance)} over ({abs(percentage)}% exceeded)\n"
            
            insights_text += "\n## Recommendations\n\n"
            
            # Add some fake recommendations
            if total_variance > 0:
                insights_text += f"1. Consider transferring your surplus of ${total_variance} to savings\n"
            else:
                insights_text += "1. Consider reviewing your spending in over-budget categories\n"
            
            insights_text += "2. Watch your discretionary spending categories\n"
            insights_text += "3. Plan ahead for upcoming expenses\n"
            
            # Create Gemini API response
            response = {
                "candidates": [{
                    "content": {
                        "parts": [{"text": insights_text}],
                        "role": "model"
                    },
                    "finishReason": "STOP",
                    "index": 0,
                    "safetyRatings": []
                }],
                "promptFeedback": {}
            }
            
            return response
        
        else:
            logger.warning(f"Unknown Gemini response type: {response_type}")
            return {}
    
    def save_to_fixture(self, data, fixture_name, fixture_type=None):
        """
        Save generated data to a fixture file
        
        Args:
            data (Any): Data to save
            fixture_name (str): Name for the fixture file
            fixture_type (Optional[str]): Type of fixture ('transaction', 'category', 'budget', or 'api_response')
            
        Returns:
            str: Path to the saved fixture file
        """
        # Determine fixture directory based on type
        if fixture_type == 'transaction':
            fixture_dir = TRANSACTION_FIXTURE_DIR
        elif fixture_type in ['category', 'budget']:
            fixture_dir = BUDGET_FIXTURE_DIR
        elif fixture_type == 'api_response':
            fixture_dir = API_RESPONSE_FIXTURE_DIR
        else:
            # Default to API_RESPONSE_FIXTURE_DIR
            fixture_dir = API_RESPONSE_FIXTURE_DIR
        
        # Convert model objects to serializable dicts if needed
        serializable_data = data
        if hasattr(data, 'to_dict'):
            serializable_data = data.to_dict()
        elif isinstance(data, list) and all(hasattr(item, 'to_dict') for item in data):
            serializable_data = [item.to_dict() for item in data]
        
        # Save to fixture file
        fixture_path = os.path.join(fixture_dir, fixture_name)
        return save_fixture(serializable_data, fixture_path)
    
    def generate_test_scenario(self, scenario_name, params=None):
        """
        Generate a complete test scenario with all required data
        
        Args:
            scenario_name (str): Name of the test scenario
            params (Optional[Dict[str, Any]]): Optional parameters for customization
            
        Returns:
            Dict[str, Any]: Dictionary with all generated test data
        """
        result = {}
        
        # Generate categories
        category_count = params.get('category_count', DEFAULT_CATEGORY_COUNT) if params else DEFAULT_CATEGORY_COUNT
        categories = self.generate_categories(category_count, params)
        result['categories'] = categories
        
        # Generate transactions
        transaction_count = params.get('transaction_count', DEFAULT_TRANSACTION_COUNT) if params else DEFAULT_TRANSACTION_COUNT
        transactions = self.generate_transactions(transaction_count, params)
        result['transactions'] = transactions
        
        # Generate budget
        budget = self.generate_budget(categories, transactions, params)
        result['budget'] = budget
        
        # Generate API responses
        api_responses = {
            'capital_one': {
                'transactions': self.generate_capital_one_transactions(transaction_count, params)
            },
            'gemini': {
                'categorization': self.generate_gemini_response('categorization', params),
                'insights': self.generate_gemini_response('insights', params)
            }
        }
        result['api_responses'] = api_responses
        
        return result


class TransactionGenerator:
    """
    Specialized generator for transaction test data
    """
    
    def __init__(self, merchants=None, categories=None):
        """
        Initialize the transaction generator
        
        Args:
            merchants (Optional[List[str]]): Optional list of merchant names
            categories (Optional[List[str]]): Optional list of category names
        """
        self.faker = Faker()
        self.merchants = merchants or DEFAULT_MERCHANTS
        self.categories = categories or DEFAULT_CATEGORIES
    
    def generate_transaction(self, params=None):
        """
        Generate a single transaction with realistic data
        
        Args:
            params (Optional[Dict[str, Any]]): Optional dictionary of parameters
            
        Returns:
            Dict[str, Any]: Transaction data dictionary
        """
        # Extract parameters or use defaults
        location = params.get('location') if params else None
        amount = params.get('amount') if params else None
        timestamp = params.get('timestamp') if params else None
        category = params.get('category') if params else None
        
        # Generate random values for anything not provided
        if location is None:
            location = random.choice(self.merchants)
        
        if amount is None:
            min_amount = params.get('min_amount', 1.0) if params else 1.0
            max_amount = params.get('max_amount', 200.0) if params else 200.0
            amount = Decimal(str(round(random.uniform(min_amount, max_amount), 2)))
        
        if timestamp is None:
            days_ago = params.get('days_ago', 7) if params else 7
            days_offset = random.randint(0, days_ago - 1)
            timestamp = datetime.datetime.now() - datetime.timedelta(days=days_offset)
        
        if category is None and random.random() > 0.2:  # 80% chance of having a category
            category = random.choice(self.categories)
        
        # Create transaction dictionary
        transaction = {
            'location': location,
            'amount': amount,
            'timestamp': timestamp
        }
        
        if category:
            transaction['category'] = category
        
        return transaction
    
    def generate_batch(self, count, params=None):
        """
        Generate a batch of transactions
        
        Args:
            count (int): Number of transactions to generate
            params (Optional[Dict[str, Any]]): Optional parameters for customization
            
        Returns:
            List[Dict[str, Any]]: List of transaction dictionaries
        """
        transactions = []
        
        for _ in range(count):
            transaction = self.generate_transaction(params)
            transactions.append(transaction)
        
        return transactions
    
    def to_capital_one_format(self, transactions):
        """
        Convert transactions to Capital One API format
        
        Args:
            transactions (List[Dict[str, Any]]): List of transaction dictionaries
            
        Returns:
            Dict[str, Any]: Capital One API response with transactions
        """
        api_transactions = []
        
        for transaction in transactions:
            api_transaction = {
                'id': transaction.get('transaction_id', f"tr_{self.faker.uuid4()}"),
                'amount': str(transaction['amount']),
                'merchant': {
                    'name': transaction['location'],
                    'category': transaction.get('category', "Uncategorized")
                },
                'transactionDate': transaction['timestamp'].isoformat(),
                'description': f"Transaction at {transaction['location']}"
            }
            api_transactions.append(api_transaction)
        
        # Create Capital One API response
        response = {
            'transactions': api_transactions
        }
        
        return response
    
    def to_sheets_format(self, transactions):
        """
        Convert transactions to Google Sheets format
        
        Args:
            transactions (List[Dict[str, Any]]): List of transaction dictionaries
            
        Returns:
            List[List[Any]]: Data formatted for Google Sheets
        """
        # Format for Google Sheets
        sheet_data = [
            [
                transaction['location'],
                str(transaction['amount']),
                transaction['timestamp'].isoformat(),
                transaction.get('category', "")
            ]
            for transaction in transactions
        ]
        
        # Add header row
        sheet_data.insert(0, ["Transaction Location", "Transaction Amount", "Transaction Time", "Corresponding Category"])
        
        return sheet_data


class CategoryGenerator:
    """
    Specialized generator for category test data
    """
    
    def __init__(self, category_names=None):
        """
        Initialize the category generator
        
        Args:
            category_names (Optional[List[str]]): Optional list of category names
        """
        self.faker = Faker()
        self.category_names = category_names or DEFAULT_CATEGORIES
    
    def generate_category(self, params=None):
        """
        Generate a single category with realistic data
        
        Args:
            params (Optional[Dict[str, Any]]): Optional dictionary of parameters
            
        Returns:
            Dict[str, Any]: Category data dictionary
        """
        # Extract parameters or use defaults
        name = params.get('name') if params else None
        weekly_amount = params.get('weekly_amount') if params else None
        
        # Generate random values for anything not provided
        if name is None:
            name = random.choice(self.category_names)
        
        if weekly_amount is None:
            min_amount = params.get('min_amount', 50.0) if params else 50.0
            max_amount = params.get('max_amount', 500.0) if params else 500.0
            weekly_amount = Decimal(str(round(random.uniform(min_amount, max_amount), 2)))
        
        # Create category dictionary
        category = {
            'name': name,
            'weekly_amount': weekly_amount
        }
        
        return category
    
    def generate_batch(self, count, params=None):
        """
        Generate a batch of categories
        
        Args:
            count (int): Number of categories to generate
            params (Optional[Dict[str, Any]]): Optional parameters for customization
            
        Returns:
            List[Dict[str, Any]]: List of category dictionaries
        """
        # Ensure we don't try to generate more categories than we have names
        count = min(count, len(self.category_names))
        
        # Randomly select 'count' categories from the list
        selected_categories = random.sample(self.category_names, count)
        
        categories = []
        
        for name in selected_categories:
            category_params = params.copy() if params else {}
            category_params['name'] = name
            
            category = self.generate_category(category_params)
            categories.append(category)
        
        return categories
    
    def to_sheets_format(self, categories):
        """
        Convert categories to Google Sheets format
        
        Args:
            categories (List[Dict[str, Any]]): List of category dictionaries
            
        Returns:
            List[List[Any]]: Data formatted for Google Sheets
        """
        # Format for Google Sheets
        sheet_data = [
            [
                category['name'],
                str(category['weekly_amount'])
            ]
            for category in categories
        ]
        
        # Add header row
        sheet_data.insert(0, ["Spending Category", "Weekly Amount"])
        
        return sheet_data