"""
test_helpers.py - Utility module providing helper functions for testing the Budget Management Application.

Contains functions for test setup, teardown, environment configuration, test data generation, 
and common testing operations to simplify test implementation and improve test maintainability.
"""

import os
import datetime
import decimal
from decimal import Decimal
import pytest
from typing import List, Dict, Any, Optional, Union, Callable, TypeVar
import contextlib
import tempfile

# Internal imports
from .fixture_loader import load_fixture
from .mock_factory import MockFactory
from ...backend.models.transaction import Transaction
from ...backend.models.budget import Budget
from ...backend.models.category import Category

# Set up test data directory
TEST_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fixtures', 'json')

# Default precision for decimal comparisons
DEFAULT_DECIMAL_PRECISION = Decimal('0.01')

# Default test configuration
DEFAULT_TEST_CONFIG = {
    'capital_one': {
        'client_id': 'test-client-id',
        'client_secret': 'test-client-secret',
        'checking_account_id': 'test-checking-account',
        'savings_account_id': 'test-savings-account'
    },
    'google_sheets': {
        'credentials_file': 'test-credentials.json',
        'master_budget_sheet_id': 'test-master-budget-id',
        'weekly_spending_sheet_id': 'test-weekly-spending-id'
    },
    'gemini': {
        'api_key': 'test-api-key',
        'model_name': 'test-model'
    },
    'gmail': {
        'credentials_file': 'test-credentials.json',
        'sender_email': 'test@example.com',
        'recipient_emails': ['recipient@example.com']
    }
}

def load_test_fixture(fixture_path: str) -> Dict[str, Any] or List[Dict[str, Any]]:
    """
    Load a test fixture file from the test data directory
    
    Args:
        fixture_path: Relative path to the fixture file
        
    Returns:
        Parsed data from the fixture file
    """
    return load_fixture(fixture_path)

def create_test_transaction(
    location: Optional[str] = None,
    amount: Optional[Decimal] = None,
    timestamp: Optional[datetime.datetime] = None,
    category: Optional[str] = None,
    transaction_id: Optional[str] = None
) -> Transaction:
    """
    Create a test Transaction object with specified or default values
    
    Args:
        location: Transaction location
        amount: Transaction amount
        timestamp: Transaction timestamp
        category: Transaction category
        transaction_id: Transaction ID
        
    Returns:
        A Transaction object with the specified values
    """
    # Set default values if not provided
    if location is None:
        location = "Test Location"
    
    if amount is None:
        amount = Decimal("10.00")
    
    if timestamp is None:
        timestamp = datetime.datetime.now()
    
    # Create and return transaction
    return Transaction(
        location=location,
        amount=amount,
        timestamp=timestamp,
        category=category,
        transaction_id=transaction_id
    )

def create_test_transactions(
    count: int,
    transaction_data: Optional[List[Dict[str, Any]]] = None
) -> List[Transaction]:
    """
    Create a list of test Transaction objects
    
    Args:
        count: Number of transactions to create
        transaction_data: Optional list of dictionaries with transaction data
        
    Returns:
        List of Transaction objects
    """
    transactions = []
    
    if transaction_data:
        # Create transactions from provided data
        for i, data in enumerate(transaction_data):
            if i >= count:
                break
                
            # Extract data with defaults
            location = data.get("location", f"Test Location {i}")
            amount = Decimal(str(data.get("amount", 10.00)))
            timestamp = data.get("timestamp", datetime.datetime.now())
            category = data.get("category")
            transaction_id = data.get("transaction_id", f"tx_{i}")
            
            # Create transaction and add to list
            transaction = create_test_transaction(
                location=location, 
                amount=amount,
                timestamp=timestamp,
                category=category,
                transaction_id=transaction_id
            )
            transactions.append(transaction)
    else:
        # Create transactions with generated data
        for i in range(count):
            transaction = create_test_transaction(
                location=f"Test Location {i}", 
                amount=Decimal(f"{10 + i}.00"),
                timestamp=datetime.datetime.now() - datetime.timedelta(days=i % 7),
                category=f"Category {i % 5}",
                transaction_id=f"tx_{i}"
            )
            transactions.append(transaction)
    
    return transactions

def create_test_category(
    name: Optional[str] = None,
    weekly_amount: Optional[Decimal] = None
) -> Category:
    """
    Create a test Category object with specified or default values
    
    Args:
        name: Category name
        weekly_amount: Weekly budget amount
        
    Returns:
        A Category object with the specified values
    """
    # Set default values if not provided
    if name is None:
        name = "Test Category"
    
    if weekly_amount is None:
        weekly_amount = Decimal("100.00")
    
    # Create and return category
    return Category(name=name, weekly_amount=weekly_amount)

def create_test_categories(
    count: int,
    category_data: Optional[List[Dict[str, Any]]] = None
) -> List[Category]:
    """
    Create a list of test Category objects
    
    Args:
        count: Number of categories to create
        category_data: Optional list of dictionaries with category data
        
    Returns:
        List of Category objects
    """
    categories = []
    
    if category_data:
        # Create categories from provided data
        for i, data in enumerate(category_data):
            if i >= count:
                break
                
            # Extract data with defaults
            name = data.get("name", f"Category {i}")
            weekly_amount = Decimal(str(data.get("weekly_amount", 100.00)))
            
            # Create category and add to list
            category = create_test_category(name=name, weekly_amount=weekly_amount)
            categories.append(category)
    else:
        # Create categories with generated data
        for i in range(count):
            category = create_test_category(
                name=f"Category {i}", 
                weekly_amount=Decimal(f"{100 + i * 25}.00")
            )
            categories.append(category)
    
    return categories

def create_test_budget(
    categories: Optional[List[Category]] = None,
    transactions: Optional[List[Transaction]] = None
) -> Budget:
    """
    Create a test Budget object with specified or default values
    
    Args:
        categories: List of Category objects
        transactions: List of Transaction objects
        
    Returns:
        A Budget object with the specified values
    """
    # Create default categories if not provided
    if categories is None:
        categories = create_test_categories(5)
    
    # Create default transactions if not provided
    if transactions is None:
        transactions = create_test_transactions(10)
    
    # Calculate actual spending from transactions
    actual_spending = {}
    for transaction in transactions:
        category = transaction.category
        if category:
            if category in actual_spending:
                actual_spending[category] += transaction.amount
            else:
                actual_spending[category] = transaction.amount
    
    # Create and return budget
    return Budget(categories=categories, actual_spending=actual_spending)

def setup_test_environment(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Set up a test environment with mock objects and test data
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Dictionary containing mock objects and test data
    """
    # Use provided config or default
    if config is None:
        config = DEFAULT_TEST_CONFIG.copy()
    else:
        # Merge with default config
        merged_config = DEFAULT_TEST_CONFIG.copy()
        for key, value in config.items():
            if isinstance(value, dict) and key in merged_config and isinstance(merged_config[key], dict):
                merged_config[key].update(value)
            else:
                merged_config[key] = value
        config = merged_config
    
    # Create mock factory and mocks
    mock_factory = MockFactory(config)
    mocks = mock_factory.create_all_mocks()
    
    # Create test data
    transactions = create_test_transactions(10)
    categories = create_test_categories(5)
    budget = create_test_budget(categories, transactions)
    
    # Return test environment
    return {
        "config": config,
        "mocks": mocks,
        "test_data": {
            "transactions": transactions,
            "categories": categories,
            "budget": budget
        }
    }

def teardown_test_environment(test_env: Dict[str, Any]) -> None:
    """
    Clean up resources created during test environment setup
    
    Args:
        test_env: Test environment dictionary from setup_test_environment
    """
    # Reset all mocks
    if "mocks" in test_env:
        for mock_name, mock in test_env["mocks"].items():
            if hasattr(mock, "reset"):
                mock.reset()

@contextlib.contextmanager
def with_test_environment(config: Optional[Dict[str, Any]] = None):
    """
    Context manager for setting up and tearing down a test environment
    
    Args:
        config: Optional configuration dictionary
        
    Yields:
        Test environment dictionary
    """
    # Set up test environment
    test_env = setup_test_environment(config)
    
    try:
        # Yield the environment to the caller
        yield test_env
    finally:
        # Clean up the environment
        teardown_test_environment(test_env)

def create_temp_file(content: Optional[str] = None, suffix: Optional[str] = None) -> str:
    """
    Create a temporary file with optional content
    
    Args:
        content: Optional content to write to the file
        suffix: Optional file suffix
        
    Returns:
        Path to the created temporary file
    """
    # Create a temporary file
    fd, path = tempfile.mkstemp(suffix=suffix)
    
    try:
        # Write content if provided
        if content:
            with os.fdopen(fd, 'w') as f:
                f.write(content)
        else:
            os.close(fd)
    except:
        # Close file descriptor on error
        os.close(fd)
        raise
    
    return path

@contextlib.contextmanager
def set_environment_variables(env_vars: Dict[str, str]):
    """
    Set environment variables for testing and restore original values after test
    
    Args:
        env_vars: Dictionary of environment variables to set
        
    Yields:
        None
    """
    # Save original environment variables
    original_env = {}
    for key in env_vars:
        if key in os.environ:
            original_env[key] = os.environ[key]
        else:
            original_env[key] = None
    
    try:
        # Set environment variables
        for key, value in env_vars.items():
            os.environ[key] = value
        
        # Yield control to the caller
        yield
    finally:
        # Restore original environment variables
        for key, value in original_env.items():
            if value is None:
                if key in os.environ:
                    del os.environ[key]
            else:
                os.environ[key] = value

def mock_api_response(
    api_name: str,
    response_type: str,
    custom_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a mock API response for testing
    
    Args:
        api_name: Name of the API ('capital_one', 'google_sheets', 'gemini', 'gmail')
        response_type: Type of response
        custom_data: Optional custom data to include in the response
        
    Returns:
        Mock API response data
    """
    # Load default response based on api_name and response_type
    fixture_path = f"api_responses/{api_name}/{response_type}"
    response = load_test_fixture(fixture_path)
    
    # Merge with custom data if provided
    if custom_data:
        if isinstance(response, dict) and isinstance(custom_data, dict):
            # Deep merge for dictionaries
            def deep_merge(source, destination):
                for key, value in source.items():
                    if key in destination and isinstance(value, dict) and isinstance(destination[key], dict):
                        deep_merge(value, destination[key])
                    else:
                        destination[key] = value
                return destination
            
            response = deep_merge(custom_data, response.copy())
        elif isinstance(response, list) and isinstance(custom_data, dict) and "replace" in custom_data:
            # Replace entire response if custom_data has "replace" key
            response = custom_data["replace"]
    
    return response

def compare_decimal_values(
    value1: Decimal,
    value2: Decimal,
    precision: Optional[Decimal] = None
) -> bool:
    """
    Compare two decimal values with a specified precision
    
    Args:
        value1: First value to compare
        value2: Second value to compare
        precision: Precision for comparison (default: DEFAULT_DECIMAL_PRECISION)
        
    Returns:
        True if values are equal within precision, False otherwise
    """
    # Use default precision if not specified
    if precision is None:
        precision = DEFAULT_DECIMAL_PRECISION
    
    # Calculate absolute difference
    diff = abs(value1 - value2)
    
    # Compare with precision
    return diff <= precision

def generate_test_data(
    data_type: str,
    params: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Generate test data for various test scenarios
    
    Args:
        data_type: Type of data to generate ('transactions', 'categories', 'budget', 'api_response')
        params: Optional parameters for data generation
        
    Returns:
        Generated test data
    """
    # Initialize params if not provided
    if params is None:
        params = {}
    
    # Generate data based on data_type
    if data_type == "transactions":
        count = params.get("count", 10)
        return create_test_transactions(count, params.get("transaction_data"))
    
    elif data_type == "categories":
        count = params.get("count", 5)
        return create_test_categories(count, params.get("category_data"))
    
    elif data_type == "budget":
        categories = params.get("categories")
        transactions = params.get("transactions")
        return create_test_budget(categories, transactions)
    
    elif data_type == "api_response":
        api_name = params.get("api_name", "capital_one")
        response_type = params.get("response_type", "transactions")
        custom_data = params.get("custom_data")
        return mock_api_response(api_name, response_type, custom_data)
    
    else:
        raise ValueError(f"Unknown data type: {data_type}")

class TestEnvironment:
    """Class for managing test environment setup and teardown"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the test environment with optional configuration
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or DEFAULT_TEST_CONFIG.copy()
        self.mocks = {}
        self.test_data = {}
        self.temp_files = []
    
    def setup(self):
        """
        Set up the test environment with mock objects and test data
        """
        # Create mock factory and mocks
        mock_factory = MockFactory(self.config)
        self.mocks = mock_factory.create_all_mocks()
        
        # Create test data
        self.test_data["transactions"] = create_test_transactions(10)
        self.test_data["categories"] = create_test_categories(5)
        self.test_data["budget"] = create_test_budget(
            self.test_data["categories"], 
            self.test_data["transactions"]
        )
    
    def teardown(self):
        """
        Clean up resources created during test environment setup
        """
        # Reset all mocks
        for mock_name, mock in self.mocks.items():
            if hasattr(mock, "reset"):
                mock.reset()
        
        # Clean up temp files
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Error cleaning up temp file {file_path}: {e}")
        
        # Clear data
        self.mocks = {}
        self.test_data = {}
        self.temp_files = []
    
    def get_mock(self, mock_type: str) -> Any:
        """
        Get a mock object of the specified type
        
        Args:
            mock_type: Type of mock to get
            
        Returns:
            Mock object
        """
        if mock_type not in self.mocks:
            raise KeyError(f"Mock of type '{mock_type}' not found")
        
        return self.mocks[mock_type]
    
    def get_test_data(self, data_type: str) -> Any:
        """
        Get test data of the specified type
        
        Args:
            data_type: Type of test data to get
            
        Returns:
            Test data
        """
        if data_type not in self.test_data:
            raise KeyError(f"Test data of type '{data_type}' not found")
        
        return self.test_data[data_type]
    
    def create_temp_file(self, content: Optional[str] = None, suffix: Optional[str] = None) -> str:
        """
        Create a temporary file for testing
        
        Args:
            content: Optional content to write to the file
            suffix: Optional file suffix
            
        Returns:
            Path to the created temporary file
        """
        path = create_temp_file(content, suffix)
        self.temp_files.append(path)
        return path
    
    @contextlib.contextmanager
    def set_environment_variables(self, env_vars: Dict[str, str]):
        """
        Set environment variables for testing
        
        Args:
            env_vars: Dictionary of environment variables to set
            
        Yields:
            None
        """
        with set_environment_variables(env_vars):
            yield

class TestDataGenerator:
    """Class for generating test data for various test scenarios"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the test data generator with optional configuration
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
    
    def generate_transactions(self, count: int, params: Optional[Dict[str, Any]] = None) -> List[Transaction]:
        """
        Generate test transaction data
        
        Args:
            count: Number of transactions to generate
            params: Optional parameters for transaction generation
            
        Returns:
            List of Transaction objects
        """
        return create_test_transactions(count, params and params.get("transaction_data"))
    
    def generate_categories(self, count: int, params: Optional[Dict[str, Any]] = None) -> List[Category]:
        """
        Generate test category data
        
        Args:
            count: Number of categories to generate
            params: Optional parameters for category generation
            
        Returns:
            List of Category objects
        """
        return create_test_categories(count, params and params.get("category_data"))
    
    def generate_budget(
        self,
        categories: Optional[List[Category]] = None,
        transactions: Optional[List[Transaction]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Budget:
        """
        Generate test budget data
        
        Args:
            categories: Optional list of categories
            transactions: Optional list of transactions
            params: Optional parameters for budget generation
            
        Returns:
            Budget object
        """
        return create_test_budget(categories, transactions)
    
    def generate_api_response(
        self,
        api_name: str,
        response_type: str,
        custom_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate mock API response data
        
        Args:
            api_name: Name of the API
            response_type: Type of response
            custom_data: Optional custom data to include
            
        Returns:
            Mock API response data
        """
        return mock_api_response(api_name, response_type, custom_data)
    
    def generate(self, data_type: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Generate test data of the specified type
        
        Args:
            data_type: Type of data to generate
            params: Optional parameters for data generation
            
        Returns:
            Generated test data
        """
        return generate_test_data(data_type, params)