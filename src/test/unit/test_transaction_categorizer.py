"""
test_transaction_categorizer.py - Unit tests for the TransactionCategorizer component

Tests the functionality of the TransactionCategorizer component, which is responsible for
categorizing transactions using Gemini AI by matching transaction locations to budget categories.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from typing import List, Dict, Any

# Import the component to test
from ...backend.components.transaction_categorizer import TransactionCategorizer

# Import utilities needed for testing
from ..fixtures.transactions import create_test_transactions
from ..fixtures.categories import create_test_categories
from ..utils.fixture_loader import load_fixture
from ..utils.assertion_helpers import assert_transactions_equal, assert_categorization_correct
from ...backend.utils.error_handlers import APIError, ValidationError

@pytest.fixture
def setup_mocks():
    """Set up mock objects for testing the TransactionCategorizer"""
    # Create mock GeminiClient
    mock_gemini_client = MagicMock()
    mock_gemini_client.authenticate.return_value = True
    mock_gemini_client.categorize_transactions.return_value = {
        "Grocery Store": "Groceries",
        "Gas Station": "Gas & Fuel",
        "Restaurant": "Dining Out"
    }
    
    # Create mock GoogleSheetsClient
    mock_sheets_client = MagicMock()
    mock_sheets_client.authenticate.return_value = True
    mock_sheets_client.get_transactions.return_value = create_test_transactions()
    mock_sheets_client.get_master_budget_data.return_value = create_test_categories()
    mock_sheets_client.update_transaction_categories.return_value = 3
    
    # Create mock AuthenticationService
    mock_auth_service = MagicMock()
    
    return {
        "gemini_client": mock_gemini_client,
        "sheets_client": mock_sheets_client,
        "auth_service": mock_auth_service
    }

def test_transaction_categorizer_init(setup_mocks):
    """Test initialization of TransactionCategorizer"""
    mocks = setup_mocks
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"],
        categorization_threshold=0.95
    )
    
    # Assert that the categorizer has the expected properties
    assert categorizer.gemini_client == mocks["gemini_client"]
    assert categorizer.sheets_client == mocks["sheets_client"]
    assert categorizer.auth_service == mocks["auth_service"]
    assert categorizer.categorization_threshold == 0.95

def test_authenticate_success(setup_mocks):
    """Test successful authentication with both APIs"""
    mocks = setup_mocks
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"]
    )
    
    # Call authenticate method
    result = categorizer.authenticate()
    
    # Assert that both authenticate methods were called and result is True
    assert result is True
    mocks["gemini_client"].authenticate.assert_called_once()
    mocks["sheets_client"].authenticate.assert_called_once()

def test_authenticate_gemini_failure(setup_mocks):
    """Test authentication failure with Gemini API"""
    mocks = setup_mocks
    
    # Configure Gemini to fail authentication
    mocks["gemini_client"].authenticate.return_value = False
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"]
    )
    
    # Call authenticate method
    result = categorizer.authenticate()
    
    # Assert that result is False and only Gemini authenticate was called
    assert result is False
    mocks["gemini_client"].authenticate.assert_called_once()
    mocks["sheets_client"].authenticate.assert_not_called()

def test_authenticate_sheets_failure(setup_mocks):
    """Test authentication failure with Google Sheets API"""
    mocks = setup_mocks
    
    # Configure Sheets to fail authentication
    mocks["sheets_client"].authenticate.return_value = False
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"]
    )
    
    # Call authenticate method
    result = categorizer.authenticate()
    
    # Assert that result is False and both authenticate methods were called
    assert result is False
    mocks["gemini_client"].authenticate.assert_called_once()
    mocks["sheets_client"].authenticate.assert_called_once()

def test_get_transactions_and_categories_success(setup_mocks):
    """Test successful retrieval of transactions and categories"""
    mocks = setup_mocks
    
    # Create test transactions and categories
    test_transactions = create_test_transactions()
    test_categories = create_test_categories()
    
    # Configure mocks to return test data
    mocks["sheets_client"].get_transactions.return_value = test_transactions
    mocks["sheets_client"].get_master_budget_data.return_value = test_categories
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"]
    )
    
    # Call get_transactions_and_categories method
    transactions, categories = categorizer.get_transactions_and_categories()
    
    # Assert methods were called and data is returned correctly
    mocks["sheets_client"].get_transactions.assert_called_once()
    mocks["sheets_client"].get_master_budget_data.assert_called_once()
    assert transactions == test_transactions
    assert categories == test_categories

def test_get_transactions_and_categories_api_error(setup_mocks):
    """Test handling of API error during transaction and category retrieval"""
    mocks = setup_mocks
    
    # Configure get_transactions to raise APIError
    mocks["sheets_client"].get_transactions.side_effect = APIError(
        "API Error", "Google Sheets", "get_transactions"
    )
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"]
    )
    
    # Call get_transactions_and_categories method with pytest.raises
    with pytest.raises(APIError):
        categorizer.get_transactions_and_categories()
    
    # Assert get_transactions was called but get_master_budget_data was not
    mocks["sheets_client"].get_transactions.assert_called_once()
    mocks["sheets_client"].get_master_budget_data.assert_not_called()

def test_categorize_transactions_success(setup_mocks):
    """Test successful categorization of transactions"""
    mocks = setup_mocks
    
    # Create test data
    test_transactions = create_test_transactions()
    test_categories = create_test_categories()
    
    # Expected category mapping
    expected_mapping = {
        "Grocery Store": "Groceries",
        "Gas Station": "Gas & Fuel",
        "Restaurant": "Dining Out"
    }
    
    # Configure mock to return expected mapping
    mocks["gemini_client"].categorize_transactions.return_value = expected_mapping
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"]
    )
    
    # Call categorize_transactions method
    result = categorizer.categorize_transactions(test_transactions, test_categories)
    
    # Assert that the method returns the expected mapping
    assert result == expected_mapping
    
    # Assert that the gemini_client.categorize_transactions method was called with correct parameters
    category_names = [category.name for category in test_categories]
    transaction_locations = [tx.location for tx in test_transactions]
    mocks["gemini_client"].categorize_transactions.assert_called_with(
        transaction_locations=transaction_locations,
        budget_categories=category_names
    )

def test_categorize_transactions_api_error(setup_mocks):
    """Test handling of API error during transaction categorization"""
    mocks = setup_mocks
    
    # Create test data
    test_transactions = create_test_transactions()
    test_categories = create_test_categories()
    
    # Configure categorize_transactions to raise APIError
    mocks["gemini_client"].categorize_transactions.side_effect = APIError(
        "API Error", "Gemini", "categorize_transactions"
    )
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"]
    )
    
    # Call categorize_transactions method with pytest.raises
    with pytest.raises(APIError):
        categorizer.categorize_transactions(test_transactions, test_categories)
    
    # Assert that the gemini_client.categorize_transactions method was called with correct parameters
    category_names = [category.name for category in test_categories]
    transaction_locations = [tx.location for tx in test_transactions]
    mocks["gemini_client"].categorize_transactions.assert_called_with(
        transaction_locations=transaction_locations,
        budget_categories=category_names
    )

def test_apply_categories(setup_mocks):
    """Test applying categories to transactions"""
    mocks = setup_mocks
    
    # Create test transactions without categories
    test_transactions = create_test_transactions()
    for tx in test_transactions:
        tx.category = None
    
    # Create location to category mapping
    location_to_category_map = {
        "Grocery Store": "Groceries",
        "Gas Station": "Gas & Fuel",
        "Restaurant": "Dining Out"
    }
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"]
    )
    
    # Call apply_categories method
    result = categorizer.apply_categories(test_transactions, location_to_category_map)
    
    # Assert that the transactions have been updated with categories
    for tx in result:
        if tx.location in location_to_category_map:
            assert tx.category == location_to_category_map[tx.location]

def test_update_sheet_categories_success(setup_mocks):
    """Test successful update of transaction categories in Google Sheets"""
    mocks = setup_mocks
    
    # Create test transactions with categories
    test_transactions = create_test_transactions()
    # Set categories
    for tx in test_transactions:
        tx.category = "Test Category"
    
    # Create location to category mapping
    location_to_category_map = {
        "Grocery Store": "Groceries",
        "Gas Station": "Gas & Fuel",
        "Restaurant": "Dining Out"
    }
    
    # Configure update_transaction_categories to return 3 (number of updated records)
    mocks["sheets_client"].update_transaction_categories.return_value = 3
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"]
    )
    
    # Call update_sheet_categories method
    result = categorizer.update_sheet_categories(test_transactions, location_to_category_map)
    
    # Assert that the method returns the expected number of updated transactions
    assert result == 3
    
    # Assert that sheets_client.update_transaction_categories was called with correct parameters
    mocks["sheets_client"].update_transaction_categories.assert_called_with(
        transactions=test_transactions,
        location_to_category_map=location_to_category_map
    )

def test_update_sheet_categories_api_error(setup_mocks):
    """Test handling of API error during sheet update"""
    mocks = setup_mocks
    
    # Create test transactions with categories
    test_transactions = create_test_transactions()
    # Create location to category mapping
    location_to_category_map = {
        "Grocery Store": "Groceries",
        "Gas Station": "Gas & Fuel",
        "Restaurant": "Dining Out"
    }
    
    # Configure update_transaction_categories to raise APIError
    mocks["sheets_client"].update_transaction_categories.side_effect = APIError(
        "API Error", "Google Sheets", "update_transaction_categories"
    )
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"]
    )
    
    # Call update_sheet_categories method with pytest.raises
    with pytest.raises(APIError):
        categorizer.update_sheet_categories(test_transactions, location_to_category_map)
    
    # Assert that sheets_client.update_transaction_categories was called with correct parameters
    mocks["sheets_client"].update_transaction_categories.assert_called_with(
        transactions=test_transactions,
        location_to_category_map=location_to_category_map
    )

def test_execute_success(setup_mocks):
    """Test successful execution of the complete categorization process"""
    mocks = setup_mocks
    
    # Create test data
    test_transactions = create_test_transactions()
    test_categories = create_test_categories()
    
    # Create location to category mapping
    location_to_category_map = {
        "Grocery Store": "Groceries",
        "Gas Station": "Gas & Fuel",
        "Restaurant": "Dining Out"
    }
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"]
    )
    
    # Mock the component methods to track calls
    categorizer.authenticate = MagicMock(return_value=True)
    categorizer.get_transactions_and_categories = MagicMock(return_value=(test_transactions, test_categories))
    categorizer.categorize_transactions = MagicMock(return_value=location_to_category_map)
    categorizer.apply_categories = MagicMock(return_value=test_transactions)
    categorizer.update_sheet_categories = MagicMock(return_value=3)
    
    # Call execute method with empty previous_status
    result = categorizer.execute({})
    
    # Assert that the method returns success status
    assert result["status"] == "success"
    
    # Assert that all methods were called in the correct order
    categorizer.authenticate.assert_called_once()
    categorizer.get_transactions_and_categories.assert_called_once()
    categorizer.categorize_transactions.assert_called_once()
    categorizer.apply_categories.assert_called_once()
    categorizer.update_sheet_categories.assert_called_once()

def test_execute_authentication_failure(setup_mocks):
    """Test execution with authentication failure"""
    mocks = setup_mocks
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"]
    )
    
    # Mock the authenticate method to return False
    categorizer.authenticate = MagicMock(return_value=False)
    
    # Mock other methods to track calls
    categorizer.get_transactions_and_categories = MagicMock()
    categorizer.categorize_transactions = MagicMock()
    categorizer.apply_categories = MagicMock()
    categorizer.update_sheet_categories = MagicMock()
    
    # Call execute method
    result = categorizer.execute({})
    
    # Assert that the method returns error status with authentication_error
    assert result["status"] == "error"
    assert "Authentication failed" in result["error"]
    
    # Assert that only authenticate was called
    categorizer.authenticate.assert_called_once()
    categorizer.get_transactions_and_categories.assert_not_called()
    categorizer.categorize_transactions.assert_not_called()
    categorizer.apply_categories.assert_not_called()
    categorizer.update_sheet_categories.assert_not_called()

def test_execute_no_transactions(setup_mocks):
    """Test execution with no transactions found"""
    mocks = setup_mocks
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"]
    )
    
    # Mock the component methods
    categorizer.authenticate = MagicMock(return_value=True)
    categorizer.get_transactions_and_categories = MagicMock(return_value=([], []))
    categorizer.categorize_transactions = MagicMock()
    categorizer.apply_categories = MagicMock()
    categorizer.update_sheet_categories = MagicMock()
    
    # Call execute method
    result = categorizer.execute({})
    
    # Assert that the method returns success status with no_transactions flag
    assert result["status"] == "warning"
    assert "No transactions to categorize" in result["message"]
    
    # Assert that only authenticate and get_transactions_and_categories were called
    categorizer.authenticate.assert_called_once()
    categorizer.get_transactions_and_categories.assert_called_once()
    categorizer.categorize_transactions.assert_not_called()
    categorizer.apply_categories.assert_not_called()
    categorizer.update_sheet_categories.assert_not_called()

def test_execute_categorization_failure(setup_mocks):
    """Test execution with categorization failure"""
    mocks = setup_mocks
    
    # Create test data
    test_transactions = create_test_transactions()
    test_categories = create_test_categories()
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"]
    )
    
    # Mock the component methods
    categorizer.authenticate = MagicMock(return_value=True)
    categorizer.get_transactions_and_categories = MagicMock(return_value=(test_transactions, test_categories))
    categorizer.categorize_transactions = MagicMock(side_effect=ValidationError("Categorization failed", "transactions"))
    categorizer.apply_categories = MagicMock()
    categorizer.update_sheet_categories = MagicMock()
    
    # Call execute method
    result = categorizer.execute({})
    
    # Assert that the method returns failure status with categorization_error
    assert result["status"] == "error"
    assert "Categorization failed" in result["error"]
    
    # Assert that only authenticate, get_transactions_and_categories, and categorize_transactions were called
    categorizer.authenticate.assert_called_once()
    categorizer.get_transactions_and_categories.assert_called_once()
    categorizer.categorize_transactions.assert_called_once()
    categorizer.apply_categories.assert_not_called()
    categorizer.update_sheet_categories.assert_not_called()

def test_execute_update_failure(setup_mocks):
    """Test execution with sheet update failure"""
    mocks = setup_mocks
    
    # Create test data
    test_transactions = create_test_transactions()
    test_categories = create_test_categories()
    
    # Create location to category mapping
    location_to_category_map = {
        "Grocery Store": "Groceries",
        "Gas Station": "Gas & Fuel",
        "Restaurant": "Dining Out"
    }
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"]
    )
    
    # Mock the component methods
    categorizer.authenticate = MagicMock(return_value=True)
    categorizer.get_transactions_and_categories = MagicMock(return_value=(test_transactions, test_categories))
    categorizer.categorize_transactions = MagicMock(return_value=location_to_category_map)
    categorizer.apply_categories = MagicMock(return_value=test_transactions)
    categorizer.update_sheet_categories = MagicMock(side_effect=APIError("Update failed", "Google Sheets", "update_transaction_categories"))
    
    # Call execute method
    result = categorizer.execute({})
    
    # Assert that the method returns failure status with update_error
    assert result["status"] == "error"
    assert "Update failed" in result["error"]
    
    # Assert that all methods were called
    categorizer.authenticate.assert_called_once()
    categorizer.get_transactions_and_categories.assert_called_once()
    categorizer.categorize_transactions.assert_called_once()
    categorizer.apply_categories.assert_called_once()
    categorizer.update_sheet_categories.assert_called_once()

def test_execute_with_correlation_id(setup_mocks):
    """Test execution with correlation ID passed from previous status"""
    mocks = setup_mocks
    
    # Create test data
    test_transactions = create_test_transactions()
    test_categories = create_test_categories()
    
    # Create location to category mapping
    location_to_category_map = {
        "Grocery Store": "Groceries",
        "Gas Station": "Gas & Fuel",
        "Restaurant": "Dining Out"
    }
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"]
    )
    
    # Mock the component methods
    categorizer.authenticate = MagicMock(return_value=True)
    categorizer.get_transactions_and_categories = MagicMock(return_value=(test_transactions, test_categories))
    categorizer.categorize_transactions = MagicMock(return_value=location_to_category_map)
    categorizer.apply_categories = MagicMock(return_value=test_transactions)
    categorizer.update_sheet_categories = MagicMock(return_value=3)
    
    # Call execute method with correlation_id in previous_status
    correlation_id = "test-correlation-id"
    result = categorizer.execute({"correlation_id": correlation_id})
    
    # Assert that the method returns success status with the same correlation_id
    assert result["status"] == "success"
    assert result["correlation_id"] == correlation_id

@pytest.mark.parametrize('accuracy', [0.95, 0.98, 1.0])
def test_categorization_accuracy(setup_mocks, accuracy):
    """Test that categorization meets the required accuracy threshold"""
    mocks = setup_mocks
    
    # Create test transactions without categories
    test_transactions = create_test_transactions()
    for tx in test_transactions:
        tx.category = None
    
    # Create expected categories mapping with specified accuracy
    expected_categories = {}
    for i, tx in enumerate(test_transactions):
        if i < int(len(test_transactions) * accuracy):
            expected_categories[tx.location] = f"Category {i}"
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"]
    )
    
    # Mock the component methods
    categorizer.authenticate = MagicMock(return_value=True)
    categorizer.get_transactions_and_categories = MagicMock(return_value=(test_transactions, []))
    categorizer.categorize_transactions = MagicMock(return_value=expected_categories)
    
    # Use the actual apply_categories implementation
    original_apply_categories = categorizer.apply_categories
    categorizer.apply_categories = lambda txs, mapping: original_apply_categories(txs, mapping)
    
    categorizer.update_sheet_categories = MagicMock(return_value=len(expected_categories))
    
    # Call execute method
    result = categorizer.execute({})
    
    # Assert that the method returns success status
    assert result["status"] == "success"
    
    # Use assert_categorization_correct to verify accuracy meets threshold
    assert_categorization_correct([tx for tx in test_transactions if tx.category], 
                                 expected_categories, 
                                 min_accuracy=0.95)

@pytest.mark.parametrize('accuracy', [0.80, 0.85, 0.90])
def test_categorization_below_threshold(setup_mocks, accuracy):
    """Test that categorization below threshold is handled correctly"""
    mocks = setup_mocks
    
    # Create test transactions without categories
    test_transactions = create_test_transactions()
    for tx in test_transactions:
        tx.category = None
    
    # Create expected categories mapping with accuracy below threshold
    expected_categories = {}
    for i, tx in enumerate(test_transactions):
        if i < int(len(test_transactions) * accuracy):
            expected_categories[tx.location] = f"Category {i}"
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"],
        categorization_threshold=0.95
    )
    
    # Mock the component methods
    categorizer.authenticate = MagicMock(return_value=True)
    categorizer.get_transactions_and_categories = MagicMock(return_value=(test_transactions, []))
    categorizer.categorize_transactions = MagicMock(return_value=expected_categories)
    categorizer.apply_categories = MagicMock()
    categorizer.update_sheet_categories = MagicMock()
    
    # Call execute method
    result = categorizer.execute({})
    
    # Assert that the method returns failure status with accuracy_below_threshold
    assert result["status"] == "error"
    assert "accuracy_below_threshold" in result["error"].lower()
    
    # Assert that update_sheet_categories was not called
    categorizer.update_sheet_categories.assert_not_called()

def test_integration_with_real_fixtures(setup_mocks):
    """Test categorization using real fixture data"""
    mocks = setup_mocks
    
    # Load real transaction data from fixtures
    transactions_data = load_fixture("transactions/weekly_transactions")
    categories_data = load_fixture("budget/master_budget")
    expected_categorizations = load_fixture("expected/categorized_transactions")
    
    # Convert to model objects
    from ...backend.models.transaction import create_transaction
    from ...backend.models.category import create_category
    
    transactions = [create_transaction(tx) for tx in transactions_data]
    categories = [create_category(cat) for cat in categories_data]
    
    # Create location to category mapping from expected categorizations
    expected_mapping = {tx["location"]: tx["category"] for tx in expected_categorizations if "category" in tx}
    
    # Create TransactionCategorizer with mock objects
    categorizer = TransactionCategorizer(
        gemini_client=mocks["gemini_client"],
        sheets_client=mocks["sheets_client"],
        auth_service=mocks["auth_service"]
    )
    
    # Mock the component methods
    categorizer.authenticate = MagicMock(return_value=True)
    categorizer.get_transactions_and_categories = MagicMock(return_value=(transactions, categories))
    categorizer.categorize_transactions = MagicMock(return_value=expected_mapping)
    
    # Keep original apply_categories functionality
    original_apply_categories = categorizer.apply_categories
    categorizer.apply_categories = lambda txs, mapping: original_apply_categories(txs, mapping)
    
    categorizer.update_sheet_categories = MagicMock(return_value=len(expected_mapping))
    
    # Call execute method
    result = categorizer.execute({})
    
    # Assert that the method returns success status
    assert result["status"] == "success"
    
    # Assert that transactions were categorized according to expected results
    for i, tx_dict in enumerate(result["transactions"]):
        location = tx_dict["location"]
        if location in expected_mapping:
            assert tx_dict["category"] == expected_mapping[location], f"Transaction {i} has incorrect category"
    
    # Assert that categorization accuracy meets threshold
    categorized_count = sum(1 for tx in result["transactions"] if "category" in tx and tx["category"])
    total_count = len(result["transactions"])
    accuracy = categorized_count / total_count if total_count > 0 else 0
    assert accuracy >= 0.95, f"Categorization accuracy {accuracy} is below threshold"