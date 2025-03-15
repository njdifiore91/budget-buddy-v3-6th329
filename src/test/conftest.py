"""
conftest.py - Pytest configuration file for Budget Management Application testing

This module provides fixtures and configuration for the pytest environment, including
mocks for external APIs, test data, and utilities for setting up consistent test environments.
"""

import pytest
import os
import datetime
import decimal
from decimal import Decimal
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

# Import fixture utilities
from .utils.fixture_loader import load_fixture
from .utils.mock_factory import MockFactory

# Import mocks
from .mocks.capital_one_client import MockCapitalOneClient
from .mocks.google_sheets_client import MockGoogleSheetsClient
from .mocks.gemini_client import MockGeminiClient
from .mocks.gmail_client import MockGmailClient

# Import models for test data
from ..backend.models.transaction import Transaction
from ..backend.models.budget import Budget
from ..backend.models.category import Category

# Define test data directory
TEST_DATA_DIR = Path(__file__).parent / 'fixtures' / 'json'

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
        'weekly_spending_id': 'test-weekly-spending-id',
        'master_budget_id': 'test-master-budget-id'
    },
    'gemini': {
        'api_key': 'test-api-key',
        'authenticated': True
    },
    'gmail': {
        'auth_service': None,
        'sender_email': 'njdifiore@gmail.com',
        'user_id': 'me'
    }
}


def pytest_configure(config):
    """
    Configure pytest environment before test execution.
    
    Args:
        config: Pytest configuration object
    """
    # Register custom markers
    config.addinivalue_line("markers", "unit: mark a test as a unit test")
    config.addinivalue_line("markers", "integration: mark a test as an integration test")
    config.addinivalue_line("markers", "api: mark a test as an API test")
    config.addinivalue_line("markers", "capital_one: mark a test as a Capital One API test")
    config.addinivalue_line("markers", "google_sheets: mark a test as a Google Sheets API test")
    config.addinivalue_line("markers", "gemini: mark a test as a Gemini AI test")
    config.addinivalue_line("markers", "gmail: mark a test as a Gmail API test")
    
    # Configure logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test items after collection to add markers based on path or name.
    
    Args:
        config: Pytest configuration object
        items: List of collected test items
    """
    for item in items:
        # Add unit/integration markers based on directory structure
        if "unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # Add API-specific markers based on test name
        if "capital_one" in item.nodeid:
            item.add_marker(pytest.mark.capital_one)
        elif "google_sheets" in item.nodeid:
            item.add_marker(pytest.mark.google_sheets)
        elif "gemini" in item.nodeid:
            item.add_marker(pytest.mark.gemini)
        elif "gmail" in item.nodeid:
            item.add_marker(pytest.mark.gmail)


@pytest.fixture
def mock_factory():
    """
    Provide a MockFactory instance for creating mock objects.
    
    Returns:
        MockFactory: Factory for creating mock API clients
    """
    factory = MockFactory(DEFAULT_TEST_CONFIG)
    yield factory
    # Reset all mocks after test completes
    factory.reset_all_mocks()


@pytest.fixture
def capital_one_client(mock_factory):
    """
    Provide a mock Capital One API client.
    
    Args:
        mock_factory: Factory for creating mocks
        
    Returns:
        MockCapitalOneClient: Configured mock Capital One client
    """
    client = mock_factory.create_capital_one_client()
    client.authenticate()
    return client


@pytest.fixture
def google_sheets_client(mock_factory):
    """
    Provide a mock Google Sheets API client.
    
    Args:
        mock_factory: Factory for creating mocks
        
    Returns:
        MockGoogleSheetsClient: Configured mock Google Sheets client
    """
    client = mock_factory.create_google_sheets_client()
    client.authenticate()
    return client


@pytest.fixture
def gemini_client(mock_factory):
    """
    Provide a mock Gemini AI client.
    
    Args:
        mock_factory: Factory for creating mocks
        
    Returns:
        MockGeminiClient: Configured mock Gemini client
    """
    client = mock_factory.create_gemini_client()
    client.authenticate()
    return client


@pytest.fixture
def gmail_client(mock_factory):
    """
    Provide a mock Gmail API client.
    
    Args:
        mock_factory: Factory for creating mocks
        
    Returns:
        MockGmailClient: Configured mock Gmail client
    """
    client = mock_factory.create_gmail_client()
    client.authenticate()
    return client


@pytest.fixture
def all_mocks(mock_factory):
    """
    Provide all mock clients in a dictionary.
    
    Args:
        mock_factory: Factory for creating mocks
        
    Returns:
        Dict: Dictionary containing all mock clients
    """
    return mock_factory.create_all_mocks()


@pytest.fixture
def test_transactions():
    """
    Provide test transaction data.
    
    Returns:
        List[Transaction]: List of test Transaction objects
    """
    # Load transaction test data from fixture
    transaction_data = load_fixture('transactions/test_transactions')
    
    # Convert to Transaction objects
    transactions = []
    for item in transaction_data:
        transactions.append(Transaction.from_dict(item))
    
    return transactions


@pytest.fixture
def test_categories():
    """
    Provide test category data.
    
    Returns:
        List[Category]: List of test Category objects
    """
    # Load category test data from fixture
    category_data = load_fixture('budget/test_categories')
    
    # Convert to Category objects
    categories = []
    for item in category_data:
        categories.append(Category.from_dict(item))
    
    return categories


@pytest.fixture
def test_budget(test_categories):
    """
    Provide test budget data.
    
    Args:
        test_categories: List of test categories
        
    Returns:
        Budget: Test Budget object
    """
    # Create spending data (actual spending for each category)
    actual_spending = {}
    for category in test_categories:
        # Set actual spending to 80% of budget for testing
        actual_spending[category.name] = category.weekly_amount * Decimal('0.8')
    
    # Create and return a Budget object
    return Budget(test_categories, actual_spending)


@pytest.fixture
def test_environment(all_mocks, test_transactions, test_categories, test_budget):
    """
    Set up a complete test environment with mocks and test data.
    
    Args:
        all_mocks: Dictionary of all mock clients
        test_transactions: List of test transactions
        test_categories: List of test categories
        test_budget: Test budget object
        
    Returns:
        Dict: Complete test environment with mocks and test data
    """
    # Initialize Google Sheets client with test data
    google_sheets_client = all_mocks['google_sheets']
    
    # Load transactions into Weekly Spending sheet
    google_sheets_client.set_sheet_data("Weekly Spending", [
        [transaction.location, str(transaction.amount), 
         transaction.timestamp.strftime("%Y-%m-%d %H:%M:%S"), 
         transaction.category if transaction.category else ""]
        for transaction in test_transactions
    ])
    
    # Load categories into Master Budget sheet
    google_sheets_client.set_sheet_data("Master Budget", [
        [category.name, str(category.weekly_amount)]
        for category in test_categories
    ])
    
    # Set up Capital One client with test transactions
    capital_one_client = all_mocks['capital_one']
    capital_one_transactions = {
        "transactions": [
            {
                "id": f"tx_{i}",
                "merchant": {"name": transaction.location},
                "amount": str(transaction.amount),
                "transactionDate": transaction.timestamp.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "description": f"Transaction {i}"
            }
            for i, transaction in enumerate(test_transactions)
        ]
    }
    capital_one_client.set_transactions(capital_one_transactions)
    
    # Create complete environment dictionary
    environment = {
        "mocks": all_mocks,
        "transactions": test_transactions,
        "categories": test_categories,
        "budget": test_budget
    }
    
    return environment


@pytest.fixture
def temp_file(tmp_path):
    """
    Create a temporary file for testing.
    
    Args:
        tmp_path: Pytest built-in fixture for temporary directory
        
    Returns:
        Path: Path to temporary file
    """
    # Create a temporary file
    temp_file = tmp_path / "test_file.txt"
    temp_file.write_text("Test content")
    
    return temp_file


@pytest.fixture
def test_config():
    """
    Provide test configuration.
    
    Returns:
        Dict: Test configuration dictionary
    """
    return DEFAULT_TEST_CONFIG.copy()