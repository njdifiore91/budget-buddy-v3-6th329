import os  # Operating system interfaces
import uuid  # Generate unique IDs
import datetime  # Date and time handling
import decimal  # Decimal arithmetic
from decimal import Decimal  # Decimal class
import typing  # Type hints
from typing import Dict, List, Any, Optional  # Type annotations
import contextlib  # Context manager utilities
import pytest  # Testing framework

# Internal imports
from ...backend.main import run_budget_management_process  # Main function
from ..mocks.capital_one_client import MockCapitalOneClient  # Mock Capital One client
from ..mocks.google_sheets_client import MockGoogleSheetsClient  # Mock Google Sheets client
from ..mocks.gemini_client import MockGeminiClient  # Mock Gemini AI client
from ..mocks.gmail_client import MockGmailClient  # Mock Gmail API client
from ..utils.fixture_loader import load_fixture  # Load test fixtures
from ..utils.test_helpers import setup_test_environment, teardown_test_environment, with_test_environment  # Test helpers
from ..utils.mock_factory import MockFactory  # Factory for creating mock objects
from ..utils.assertion_helpers import assert_budget_variance_correct, assert_transfer_amount_valid, assert_email_content_valid, assert_categorization_correct  # Assertion helpers
from ...backend.components.transaction_retriever import TransactionRetriever  # Transaction Retriever component
from ...backend.components.transaction_categorizer import TransactionCategorizer  # Transaction Categorizer component
from ...backend.components.budget_analyzer import BudgetAnalyzer  # Budget Analyzer component
from ...backend.components.insight_generator import InsightGenerator  # Insight Generator component
from ...backend.components.report_distributor import ReportDistributor  # Report Distributor component
from ...backend.components.savings_automator import SavingsAutomator  # Savings Automator component

TEST_CONFIG = {
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

@pytest.fixture
def setup_mocks() -> Dict[str, Any]:
    """Set up mock objects for testing"""
    mock_factory = MockFactory(TEST_CONFIG)  # Create a MockFactory instance with TEST_CONFIG
    mocks = mock_factory.create_all_mocks()  # Call create_all_mocks to create all mock objects
    yield mocks  # Yield the mocks to the test function
    mock_factory.reset_all_mocks()  # After test completes, reset all mocks

@pytest.fixture
def setup_test_data() -> Dict[str, Any]:
    """Set up test data for end-to-end testing"""
    transactions = load_fixture("transactions/valid_transactions.json")  # Load transaction fixture data from 'transactions/valid_transactions.json'
    budget = load_fixture("budget/master_budget.json")  # Load budget fixture data from 'budget/master_budget.json'
    categorization_response = load_fixture("api_responses/gemini/categorization.json")  # Load categorization response fixture from 'api_responses/gemini/categorization.json'
    insight_response = load_fixture("api_responses/gemini/insights.json")  # Load insight response fixture from 'api_responses/gemini/insights.json'
    return {  # Return dictionary with all test data
        "transactions": transactions,
        "budget": budget,
        "categorization_response": categorization_response,
        "insight_response": insight_response
    }

def configure_mocks_with_test_data(mocks: Dict[str, Any], test_data: Dict[str, Any]) -> None:
    """Configure mock objects with test data"""
    capital_one_client = mocks['capital_one']  # Get capital_one_client from mocks
    capital_one_client.set_transactions(test_data['transactions'])  # Set transactions on capital_one_client using test_data['transactions']
    google_sheets_client = mocks['google_sheets']  # Get google_sheets_client from mocks
    google_sheets_client.set_sheet_data('Master Budget', test_data['budget'])  # Set 'Master Budget' sheet data on google_sheets_client using test_data['budget']
    gemini_client = mocks['gemini']  # Get gemini_client from mocks
    gemini_client.set_categorization_response(test_data['categorization_response'])  # Set categorization response on gemini_client using test_data['categorization_response']
    gemini_client.set_insight_response(test_data['insight_response'])  # Set insight response on gemini_client using test_data['insight_response']

def create_components_with_mocks(mocks: Dict[str, Any]) -> Dict[str, Any]:
    """Create application components with mock dependencies"""
    capital_one_client = mocks['capital_one']  # Get all required mock clients from mocks dictionary
    google_sheets_client = mocks['google_sheets']
    gemini_client = mocks['gemini']
    gmail_client = mocks['gmail']
    transaction_retriever = TransactionRetriever(capital_one_client=capital_one_client, sheets_client=google_sheets_client)  # Create TransactionRetriever with capital_one_client and google_sheets_client
    transaction_categorizer = TransactionCategorizer(gemini_client=gemini_client, sheets_client=google_sheets_client)  # Create TransactionCategorizer with google_sheets_client and gemini_client
    budget_analyzer = BudgetAnalyzer(sheets_client=google_sheets_client)  # Create BudgetAnalyzer with google_sheets_client
    insight_generator = InsightGenerator(gemini_client=gemini_client)  # Create InsightGenerator with gemini_client
    report_distributor = ReportDistributor(gmail_client=gmail_client)  # Create ReportDistributor with gmail_client
    savings_automator = SavingsAutomator(capital_one_client=capital_one_client)  # Create SavingsAutomator with capital_one_client
    return {  # Return dictionary with all component instances
        "transaction_retriever": transaction_retriever,
        "transaction_categorizer": transaction_categorizer,
        "budget_analyzer": budget_analyzer,
        "insight_generator": insight_generator,
        "report_distributor": report_distributor,
        "savings_automator": savings_automator
    }

@contextlib.contextmanager
def patch_components(components: Dict[str, Any]):
    """Patch application components to use mock dependencies"""
    from unittest.mock import patch  # Import necessary patching utilities
    patches = []
    for component_name, component in components.items():  # Create patches for each component class to return the mock instances
        patch_target = f"backend.main.{component.__class__.__name__}"
        patches.append(patch(patch_target, return_value=component))
    
    try:
        for p in patches:  # Start all patches
            p.start()
        yield  # Yield control to the test function
    finally:
        for p in patches:  # Stop all patches after test completes
            p.stop()

@pytest.mark.integration
def test_end_to_end_happy_path(setup_mocks: Dict[str, Any], setup_test_data: Dict[str, Any]):
    """Test the complete budget management workflow with successful execution of all components"""
    configure_mocks_with_test_data(setup_mocks, setup_test_data)  # Configure mocks with test data using configure_mocks_with_test_data
    correlation_id = str(uuid.uuid4())  # Create a unique correlation_id using uuid.uuid4()
    status = run_budget_management_process(correlation_id=correlation_id)  # Execute run_budget_management_process with correlation_id
    assert status['status'] == 'success'  # Verify that the process completed successfully (status['success'] is True)
    assert status['retriever']['status'] == 'success'  # Verify that all components executed successfully
    assert status['categorizer']['status'] == 'success'
    assert status['analyzer']['status'] == 'success'
    assert status['insight']['status'] == 'success'
    assert setup_mocks['capital_one'].get_weekly_transactions() is not None  # Verify that transactions were retrieved correctly
    assert setup_mocks['google_sheets'].get_sheet_data('Weekly Spending') is not None  # Verify that transactions were categorized correctly
    assert 'total_variance' in status['analyzer']['analysis_results']  # Verify that budget analysis was performed correctly
    assert 'insights' in status['insight']  # Verify that insights were generated correctly
    assert setup_mocks['gmail'].get_sent_email_count() == 1  # Verify that email was sent correctly
    if status['analyzer']['analysis_results']['total_variance'] > 0:  # Verify that savings transfer was initiated correctly if there was a budget surplus
        assert setup_mocks['capital_one'].get_initiated_transfers() is not None

@pytest.mark.integration
def test_end_to_end_with_component_mocking(setup_mocks: Dict[str, Any], setup_test_data: Dict[str, Any]):
    """Test the complete budget management workflow with mocked components"""
    configure_mocks_with_test_data(setup_mocks, setup_test_data)  # Configure mocks with test data using configure_mocks_with_test_data
    components = create_components_with_mocks(setup_mocks)  # Create component instances with mocks using create_components_with_mocks
    with patch_components(components):  # Use patch_components context manager to patch application components
        correlation_id = str(uuid.uuid4())  # Create a unique correlation_id using uuid.uuid4()
        status = run_budget_management_process(correlation_id=correlation_id)  # Execute run_budget_management_process with correlation_id
        assert status['status'] == 'success'  # Verify that the process completed successfully (status['success'] is True)
        assert status['retriever']['status'] == 'success'  # Verify that all components executed successfully
        assert status['categorizer']['status'] == 'success'
        assert status['analyzer']['status'] == 'success'
        assert status['insight']['status'] == 'success'
        assert components['transaction_retriever'].capital_one_client.get_weekly_transactions.called  # Verify that the correct mock methods were called in the expected sequence
        assert components['transaction_categorizer'].gemini_client.categorize_transactions.called
        assert components['budget_analyzer'].sheets_client.get_budget.called
        assert components['insight_generator'].gemini_client.generate_spending_insights.called
        assert components['report_distributor'].gmail_client.get_sent_email_count() == 1

@pytest.mark.integration
def test_end_to_end_transaction_retrieval_failure(setup_mocks: Dict[str, Any], setup_test_data: Dict[str, Any]):
    """Test error handling when transaction retrieval fails"""
    configure_mocks_with_test_data(setup_mocks, setup_test_data)  # Configure mocks with test data using configure_mocks_with_test_data
    capital_one_client = setup_mocks['capital_one']  # Get capital_one_client from setup_mocks
    capital_one_client.set_should_fail_transactions(True)  # Configure capital_one_client to fail transaction retrieval
    correlation_id = str(uuid.uuid4())  # Create a unique correlation_id using uuid.uuid4()
    status = run_budget_management_process(correlation_id=correlation_id)  # Execute run_budget_management_process with correlation_id
    assert status['status'] == 'error'  # Verify that the process failed (status['success'] is False)
    assert status['retriever']['status'] == 'error'  # Verify that the failure occurred in the transaction retrieval step
    assert 'categorizer' not in status  # Verify that subsequent components were not executed

@pytest.mark.integration
def test_end_to_end_categorization_failure(setup_mocks: Dict[str, Any], setup_test_data: Dict[str, Any]):
    """Test error handling when transaction categorization fails"""
    configure_mocks_with_test_data(setup_mocks, setup_test_data)  # Configure mocks with test data using configure_mocks_with_test_data
    gemini_client = setup_mocks['gemini']  # Get gemini_client from setup_mocks
    gemini_client.set_failure_mode(True, 'categorization')  # Configure gemini_client to fail categorization
    correlation_id = str(uuid.uuid4())  # Create a unique correlation_id using uuid.uuid4()
    status = run_budget_management_process(correlation_id=correlation_id)  # Execute run_budget_management_process with correlation_id
    assert status['status'] == 'error'  # Verify that the process failed (status['success'] is False)
    assert status['categorizer']['status'] == 'error'  # Verify that the failure occurred in the categorization step
    assert status['retriever']['status'] == 'success'  # Verify that transaction retrieval completed successfully
    assert 'analyzer' not in status  # Verify that subsequent components were not executed

@pytest.mark.integration
def test_end_to_end_email_failure_continues(setup_mocks: Dict[str, Any], setup_test_data: Dict[str, Any]):
    """Test that process continues when email delivery fails (non-critical)"""
    configure_mocks_with_test_data(setup_mocks, setup_test_data)  # Configure mocks with test data using configure_mocks_with_test_data
    gmail_client = setup_mocks['gmail']  # Get gmail_client from setup_mocks
    gmail_client.set_should_fail_sending(True)  # Configure gmail_client to fail email sending
    correlation_id = str(uuid.uuid4())  # Create a unique correlation_id using uuid.uuid4()
    status = run_budget_management_process(correlation_id=correlation_id)  # Execute run_budget_management_process with correlation_id
    assert status['status'] == 'success'  # Verify that the process completed successfully (status['success'] is True)
    assert status['retriever']['status'] == 'success'  # Verify that transaction retrieval, categorization, and budget analysis completed successfully
    assert status['categorizer']['status'] == 'success'
    assert status['analyzer']['status'] == 'success'
    assert status['report']['status'] == 'error'  # Verify that email delivery failed but process continued
    assert status['savings']['status'] == 'success'  # Verify that savings transfer was still attempted

@pytest.mark.integration
def test_end_to_end_savings_failure_continues(setup_mocks: Dict[str, Any], setup_test_data: Dict[str, Any]):
    """Test that process completes when savings transfer fails (non-critical)"""
    configure_mocks_with_test_data(setup_mocks, setup_test_data)  # Configure mocks with test data using configure_mocks_with_test_data
    capital_one_client = setup_mocks['capital_one']  # Get capital_one_client from setup_mocks
    capital_one_client.set_should_fail_transfers(True)  # Configure capital_one_client to fail transfers
    correlation_id = str(uuid.uuid4())  # Create a unique correlation_id using uuid.uuid4()
    status = run_budget_management_process(correlation_id=correlation_id)  # Execute run_budget_management_process with correlation_id
    assert status['status'] == 'success'  # Verify that the process completed successfully (status['success'] is True)
    assert status['retriever']['status'] == 'success'  # Verify that transaction retrieval, categorization, budget analysis, and email delivery completed successfully
    assert status['categorizer']['status'] == 'success'
    assert status['analyzer']['status'] == 'success'
    assert status['report']['status'] == 'success'
    assert status['savings']['status'] == 'success'  # Verify that savings transfer failed but process still completed successfully

@pytest.mark.integration
def test_end_to_end_with_budget_deficit(setup_mocks: Dict[str, Any], setup_test_data: Dict[str, Any]):
    """Test that no savings transfer occurs when there is a budget deficit"""
    test_data = setup_test_data.copy()  # Modify test_data to create a budget deficit scenario
    test_data['budget']['categories'][0]['weekly_amount'] = 50  # Set a low budget for the first category
    configure_mocks_with_test_data(setup_mocks, test_data)  # Configure mocks with modified test data
    correlation_id = str(uuid.uuid4())  # Create a unique correlation_id using uuid.uuid4()
    status = run_budget_management_process(correlation_id=correlation_id)  # Execute run_budget_management_process with correlation_id
    assert status['status'] == 'success'  # Verify that the process completed successfully (status['success'] is True)
    assert status['analyzer']['analysis_results']['total_variance'] < 0  # Verify that budget analysis correctly identified a deficit
    assert not setup_mocks['capital_one'].get_initiated_transfers()  # Verify that no savings transfer was initiated

@pytest.mark.integration
@pytest.mark.performance
def test_end_to_end_with_large_transaction_volume(setup_mocks: Dict[str, Any]):
    """Test performance with a large volume of transactions"""
    large_transactions = load_fixture("transactions/large_volume_transactions.json")  # Load large transaction dataset from 'transactions/large_volume_transactions.json'
    setup_mocks['capital_one'].set_transactions(large_transactions)  # Configure mocks with large transaction dataset
    correlation_id = str(uuid.uuid4())  # Create a unique correlation_id using uuid.uuid4()
    status = run_budget_management_process(correlation_id=correlation_id)  # Execute run_budget_management_process with correlation_id
    assert status['status'] == 'success'  # Verify that the process completed successfully (status['success'] is True)
    assert len(setup_mocks['google_sheets'].get_sheet_data('Weekly Spending')) == len(large_transactions)  # Verify that all transactions were processed correctly
    assert status['retriever']['execution_time'] < 60  # Verify that performance metrics are within acceptable limits
    assert status['categorizer']['execution_time'] < 120

@pytest.mark.integration
def test_end_to_end_retry_mechanism(setup_mocks: Dict[str, Any], setup_test_data: Dict[str, Any]):
    """Test that retry mechanism works for transient failures"""
    configure_mocks_with_test_data(setup_mocks, setup_test_data)  # Configure mocks with test data
    capital_one_client = setup_mocks['capital_one']
    capital_one_client.set_should_fail_transactions(True)  # Configure mocks to fail initially but succeed on retry
    correlation_id = str(uuid.uuid4())  # Create a unique correlation_id using uuid.uuid4()
    status = run_budget_management_process(correlation_id=correlation_id)  # Execute run_budget_management_process with correlation_id
    assert status['status'] == 'success'  # Verify that the process completed successfully (status['success'] is True)
    assert capital_one_client.retry_count > 0  # Verify that retry attempts were made
    assert status['retriever']['status'] == 'success'  # Verify that all components eventually executed successfully