"""
Defines pytest fixtures for the Budget Management Application tests. This file provides reusable test fixtures including mock API clients, test data, and utility functions that can be shared across unit, integration, and end-to-end tests.
"""

import pytest  # pytest 7.4.0+
from typing import List, Dict, Optional, Any  # standard library
import os  # standard library
import tempfile  # standard library
from datetime import datetime  # standard library
from decimal import decimal  # standard library
from decimal import Decimal  # standard library

# Internal imports
from .mocks.mock_capital_one_client import MockCapitalOneClient  # src/backend/tests/mocks/mock_capital_one_client.py
from .mocks.mock_google_sheets_client import MockGoogleSheetsClient  # src/backend/tests/mocks/mock_google_sheets_client.py
from .mocks.mock_gemini_client import MockGeminiClient  # src/backend/tests/mocks/mock_gemini_client.py
from .mocks.mock_gmail_client import MockGmailClient  # src/backend/tests/mocks/mock_gmail_client.py
from .fixtures.transactions import create_test_transactions, create_categorized_transactions  # src/backend/tests/fixtures/transactions.py
from .fixtures.categories import create_test_categories  # src/backend/tests/fixtures/categories.py
from .fixtures.budget import create_test_budget, create_analyzed_budget, create_budget_with_surplus, create_budget_with_deficit  # src/backend/tests/fixtures/budget.py
from ..components.transaction_retriever import TransactionRetriever  # src/backend/components/transaction_retriever.py
from ..components.transaction_categorizer import TransactionCategorizer  # src/backend/components/transaction_categorizer.py
from ..components.budget_analyzer import BudgetAnalyzer  # src/backend/components/budget_analyzer.py
from ..components.insight_generator import InsightGenerator  # src/backend/components/insight_generator.py
from ..components.report_distributor import ReportDistributor  # src/backend/components/report_distributor.py
from ..components.savings_automator import SavingsAutomator  # src/backend/components/savings_automator.py


def pytest_configure(config):
    """Configure pytest for the test session"""
    # Set up any global pytest configuration
    # Register custom markers for test categorization
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test."
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test."
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test."
    )
    # Configure logging for tests
    # (You can add logging setup here if needed)


@pytest.fixture
def mock_capital_one_client():
    """Fixture providing a mock Capital One API client for testing"""
    return MockCapitalOneClient()


@pytest.fixture
def mock_google_sheets_client():
    """Fixture providing a mock Google Sheets API client for testing"""
    return MockGoogleSheetsClient()


@pytest.fixture
def mock_gemini_client():
    """Fixture providing a mock Gemini AI API client for testing"""
    return MockGeminiClient()


@pytest.fixture
def mock_gmail_client():
    """Fixture providing a mock Gmail API client for testing"""
    return MockGmailClient()


@pytest.fixture
def test_transactions():
    """Fixture providing test transaction data"""
    return create_test_transactions()


@pytest.fixture
def categorized_transactions():
    """Fixture providing categorized transaction data"""
    return create_categorized_transactions()


@pytest.fixture
def test_categories():
    """Fixture providing test budget categories"""
    return create_test_categories()


@pytest.fixture
def test_budget():
    """Fixture providing test budget data"""
    return create_test_budget()


@pytest.fixture
def analyzed_budget():
    """Fixture providing analyzed budget data"""
    return create_analyzed_budget()


@pytest.fixture
def budget_with_surplus():
    """Fixture providing budget data with a surplus"""
    return create_budget_with_surplus()


@pytest.fixture
def budget_with_deficit():
    """Fixture providing budget data with a deficit"""
    return create_budget_with_deficit()


@pytest.fixture
def transaction_retriever(mock_capital_one_client, mock_google_sheets_client):
    """Fixture providing a TransactionRetriever instance with mock clients"""
    return TransactionRetriever(
        capital_one_client=mock_capital_one_client,
        sheets_client=mock_google_sheets_client
    )


@pytest.fixture
def transaction_categorizer(mock_gemini_client, mock_google_sheets_client):
    """Fixture providing a TransactionCategorizer instance with mock clients"""
    return TransactionCategorizer(
        gemini_client=mock_gemini_client,
        sheets_client=mock_google_sheets_client
    )


@pytest.fixture
def budget_analyzer(mock_google_sheets_client):
    """Fixture providing a BudgetAnalyzer instance with mock clients"""
    return BudgetAnalyzer(sheets_client=mock_google_sheets_client)


@pytest.fixture
def insight_generator(mock_gemini_client):
    """Fixture providing an InsightGenerator instance with mock clients"""
    return InsightGenerator(gemini_client=mock_gemini_client)


@pytest.fixture
def report_distributor(mock_gmail_client):
    """Fixture providing a ReportDistributor instance with mock clients"""
    return ReportDistributor(gmail_client=mock_gmail_client)


@pytest.fixture
def savings_automator(mock_capital_one_client):
    """Fixture providing a SavingsAutomator instance with mock clients"""
    return SavingsAutomator(capital_one_client=mock_capital_one_client)


@pytest.fixture
def temp_dir():
    """Fixture providing a temporary directory for test file operations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def api_error_context():
    """Fixture providing a context manager for testing API error scenarios"""
    class APIErrorContext:
        def __init__(self, mock_client, method_name, error_state=True):
            self.mock_client = mock_client
            self.method_name = method_name
            self.error_state = error_state

        def __enter__(self):
            setattr(self.mock_client, 'api_error', self.error_state)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            setattr(self.mock_client, 'api_error', False)  # Reset to no error

    return APIErrorContext