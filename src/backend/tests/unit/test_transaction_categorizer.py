import pytest
from unittest.mock import MagicMock, patch

from ...components.transaction_categorizer import TransactionCategorizer
from ..mocks.mock_gemini_client import MockGeminiClient, create_mock_completion_response, MockAuthenticationService
from ..mocks.mock_google_sheets_client import MockGoogleSheetsClient
from ..fixtures.transactions import create_test_transactions, create_uncategorized_transactions
from ..fixtures.categories import create_test_categories
from ...models.category import get_category_names
from ...models.transaction import get_transaction_locations
from ...utils.error_handlers import APIError, ValidationError


def test_transaction_categorizer_init():
    """Test that TransactionCategorizer initializes correctly with default and custom dependencies"""
    # Create mock dependencies
    gemini_client = MockGeminiClient()
    sheets_client = MockGoogleSheetsClient()
    auth_service = MockAuthenticationService()
    custom_threshold = 0.75
    
    # Test with default dependencies (should create them internally)
    categorizer = TransactionCategorizer()
    assert categorizer.gemini_client is not None
    assert categorizer.sheets_client is not None
    assert categorizer.auth_service is not None
    assert categorizer.categorization_threshold == 0.95  # Default from app settings
    
    # Test with custom dependencies
    categorizer = TransactionCategorizer(
        gemini_client=gemini_client,
        sheets_client=sheets_client,
        auth_service=auth_service,
        categorization_threshold=custom_threshold
    )
    
    assert categorizer.gemini_client is gemini_client
    assert categorizer.sheets_client is sheets_client
    assert categorizer.auth_service is auth_service
    assert categorizer.categorization_threshold == custom_threshold


def test_authenticate_success():
    """Test successful authentication with both APIs"""
    # Create mock clients that will return success
    gemini_client = MockGeminiClient()
    sheets_client = MockGoogleSheetsClient()
    
    # Create spies on authenticate methods
    gemini_client.authenticate = MagicMock(return_value=True)
    sheets_client.authenticate = MagicMock(return_value=True)
    
    # Create categorizer with mock clients
    categorizer = TransactionCategorizer(
        gemini_client=gemini_client,
        sheets_client=sheets_client
    )
    
    # Test authentication
    result = categorizer.authenticate()
    assert result is True
    
    # Verify that authenticate was called on both clients
    gemini_client.authenticate.assert_called_once()
    sheets_client.authenticate.assert_called_once()


def test_authenticate_failure():
    """Test authentication failure with one or both APIs"""
    # Test with Gemini failure
    gemini_client = MockGeminiClient()
    sheets_client = MockGoogleSheetsClient()
    
    gemini_client.authenticate = MagicMock(return_value=False)
    sheets_client.authenticate = MagicMock(return_value=True)
    
    categorizer = TransactionCategorizer(
        gemini_client=gemini_client,
        sheets_client=sheets_client
    )
    
    result = categorizer.authenticate()
    assert result is False
    
    # Test with Sheets failure
    gemini_client = MockGeminiClient()
    sheets_client = MockGoogleSheetsClient()
    
    gemini_client.authenticate = MagicMock(return_value=True)
    sheets_client.authenticate = MagicMock(return_value=False)
    
    categorizer = TransactionCategorizer(
        gemini_client=gemini_client,
        sheets_client=sheets_client
    )
    
    result = categorizer.authenticate()
    assert result is False
    
    # Test with both failures
    gemini_client = MockGeminiClient()
    sheets_client = MockGoogleSheetsClient()
    
    gemini_client.authenticate = MagicMock(return_value=False)
    sheets_client.authenticate = MagicMock(return_value=False)
    
    categorizer = TransactionCategorizer(
        gemini_client=gemini_client,
        sheets_client=sheets_client
    )
    
    result = categorizer.authenticate()
    assert result is False


def test_get_transactions_and_categories_success():
    """Test successful retrieval of transactions and categories"""
    # Create test data
    test_transactions = create_test_transactions()
    test_categories = create_test_categories()
    
    # Configure mock sheets client to return test data
    sheets_client = MockGoogleSheetsClient()
    sheets_client.set_sheet_data("Weekly Spending", [t.to_sheets_format() for t in test_transactions])
    sheets_client.set_sheet_data("Master Budget", [[c.name, str(c.weekly_amount)] for c in test_categories])
    
    # Create categorizer with mock client
    categorizer = TransactionCategorizer(sheets_client=sheets_client)
    
    # Call method
    transactions, categories = categorizer.get_transactions_and_categories()
    
    # Verify result
    assert len(transactions) == len(test_transactions)
    assert len(categories) == len(test_categories)
    
    # Verify that client methods were called
    assert len(sheets_client.get_sheet_data("Weekly Spending")) > 0
    assert len(sheets_client.get_sheet_data("Master Budget")) > 0


def test_get_transactions_and_categories_api_error():
    """Test error handling when API fails during data retrieval"""
    # Configure mock sheets client to raise API error
    sheets_client = MockGoogleSheetsClient(api_error=True)
    
    # Create categorizer with mock client
    categorizer = TransactionCategorizer(sheets_client=sheets_client)
    
    # Test that APIError is raised
    with pytest.raises(APIError):
        categorizer.get_transactions_and_categories()
    
    # Test retry behavior
    with patch('src.backend.components.transaction_categorizer.retry_with_backoff', return_value=lambda *args, **kwargs: ([], [])):
        # This is a placeholder to show we would test retry behavior
        # In a real test, we would need to properly patch the decorator
        pass


def test_categorize_transactions_success():
    """Test successful categorization of transactions"""
    # Create test data
    test_transactions = create_uncategorized_transactions()
    test_categories = create_test_categories()
    
    # Get transaction locations and category names
    transaction_locations = get_transaction_locations(test_transactions)
    category_names = get_category_names(test_categories)
    
    # Create mock categorization mapping
    mock_mapping = {
        loc: category_names[i % len(category_names)] 
        for i, loc in enumerate(transaction_locations)
    }
    
    # Configure mock gemini client
    gemini_client = MockGeminiClient()
    gemini_client.categorize_transactions = MagicMock(return_value=mock_mapping)
    
    # Create categorizer with mock client
    categorizer = TransactionCategorizer(gemini_client=gemini_client)
    
    # Call method
    location_to_category_map = categorizer.categorize_transactions(test_transactions, test_categories)
    
    # Verify result
    assert len(location_to_category_map) == len(transaction_locations)
    for location in transaction_locations:
        assert location in location_to_category_map
        assert location_to_category_map[location] in category_names
    
    # Verify that gemini_client.categorize_transactions was called with correct parameters
    gemini_client.categorize_transactions.assert_called_once_with(
        transaction_locations=transaction_locations,
        budget_categories=category_names
    )


def test_categorize_transactions_api_error():
    """Test error handling when AI API fails during categorization"""
    # Create test data
    test_transactions = create_uncategorized_transactions()
    test_categories = create_test_categories()
    
    # Configure mock gemini client to raise API error
    gemini_client = MockGeminiClient(api_error=True)
    
    # Create categorizer with mock client
    categorizer = TransactionCategorizer(gemini_client=gemini_client)
    
    # Test that APIError is raised
    with pytest.raises(APIError):
        categorizer.categorize_transactions(test_transactions, test_categories)


def test_categorize_transactions_validation_error():
    """Test error handling when AI response fails validation"""
    # Create test data
    test_transactions = create_uncategorized_transactions()
    test_categories = create_test_categories()
    
    # Configure mock gemini client to return empty mapping (will fail validation)
    gemini_client = MockGeminiClient()
    gemini_client.categorize_transactions = MagicMock(return_value={})
    
    # Mock validation function to raise error
    with patch('src.backend.components.transaction_categorizer.validate_categorization_results') as mock_validate:
        mock_validate.side_effect = ValidationError("Validation error", "categorization")
        
        # Create categorizer with mock client
        categorizer = TransactionCategorizer(gemini_client=gemini_client)
        
        # Test that ValidationError is raised
        with pytest.raises(ValidationError):
            categorizer.categorize_transactions(test_transactions, test_categories)


def test_apply_categories():
    """Test applying category mapping to transactions"""
    # Create test transactions without categories
    transactions = create_uncategorized_transactions()
    
    # Create category mapping
    location_to_category_map = {
        t.location: f"Category {i}" for i, t in enumerate(transactions)
    }
    
    # Create categorizer
    categorizer = TransactionCategorizer()
    
    # Call method
    updated_transactions = categorizer.apply_categories(transactions, location_to_category_map)
    
    # Verify that categories were applied correctly
    categorized_count = 0
    for transaction in updated_transactions:
        if transaction.location in location_to_category_map:
            assert transaction.category == location_to_category_map[transaction.location]
            categorized_count += 1
    
    assert categorized_count > 0
    
    # Test with transactions that have no matching category
    transactions = create_uncategorized_transactions()
    location_to_category_map = {}  # Empty mapping
    
    updated_transactions = categorizer.apply_categories(transactions, location_to_category_map)
    
    # Verify that no categories were applied
    for transaction in updated_transactions:
        assert transaction.category is None


def test_update_sheet_categories_success():
    """Test successful update of transaction categories in Google Sheets"""
    # Create test data
    test_transactions = create_uncategorized_transactions()
    location_to_category_map = {
        t.location: f"Category {i}" for i, t in enumerate(test_transactions)
    }
    
    # Apply categories to transactions
    for transaction in test_transactions:
        if transaction.location in location_to_category_map:
            transaction.set_category(location_to_category_map[transaction.location])
    
    # Configure mock sheets client
    sheets_client = MockGoogleSheetsClient()
    sheets_client.update_transaction_categories = MagicMock(return_value=len(test_transactions))
    
    # Create categorizer with mock client
    categorizer = TransactionCategorizer(sheets_client=sheets_client)
    
    # Call method
    updated_count = categorizer.update_sheet_categories(test_transactions, location_to_category_map)
    
    # Verify result
    assert updated_count == len(test_transactions)
    
    # Verify that client method was called with correct parameters
    sheets_client.update_transaction_categories.assert_called_once_with(
        transactions=test_transactions,
        location_to_category_map=location_to_category_map
    )


def test_update_sheet_categories_api_error():
    """Test error handling when API fails during sheet update"""
    # Create test data
    test_transactions = create_uncategorized_transactions()
    location_to_category_map = {
        t.location: f"Category {i}" for i, t in enumerate(test_transactions)
    }
    
    # Configure mock sheets client to raise API error
    sheets_client = MockGoogleSheetsClient()
    sheets_client.update_transaction_categories = MagicMock(
        side_effect=APIError("API error", "Google Sheets", "update_transaction_categories")
    )
    
    # Create categorizer with mock client
    categorizer = TransactionCategorizer(sheets_client=sheets_client)
    
    # Test that APIError is raised
    with pytest.raises(APIError):
        categorizer.update_sheet_categories(test_transactions, location_to_category_map)


def test_execute_success():
    """Test successful execution of the complete categorization process"""
    # Create test data
    test_transactions = create_uncategorized_transactions()
    test_categories = create_test_categories()
    
    # Create categorizer for testing
    categorizer = TransactionCategorizer()
    
    # Create mock methods for all the component methods
    categorizer.authenticate = MagicMock(return_value=True)
    categorizer.get_transactions_and_categories = MagicMock(return_value=(test_transactions, test_categories))
    
    location_to_category_map = {
        t.location: f"Category {i}" for i, t in enumerate(test_transactions)
    }
    categorizer.categorize_transactions = MagicMock(return_value=location_to_category_map)
    
    for transaction in test_transactions:
        if transaction.location in location_to_category_map:
            transaction.set_category(location_to_category_map[transaction.location])
    categorizer.apply_categories = MagicMock(return_value=test_transactions)
    
    categorizer.update_sheet_categories = MagicMock(return_value=len(test_transactions))
    
    # Call execute method
    previous_status = {'correlation_id': 'test-correlation-id'}
    result = categorizer.execute(previous_status)
    
    # Verify that component methods were called in order
    categorizer.authenticate.assert_called_once()
    categorizer.get_transactions_and_categories.assert_called_once()
    categorizer.categorize_transactions.assert_called_once()
    categorizer.apply_categories.assert_called_once()
    categorizer.update_sheet_categories.assert_called_once()
    
    # Verify result
    assert result['status'] == 'success'
    assert result['correlation_id'] == 'test-correlation-id'
    assert 'metrics' in result
    assert 'transactions' in result
    
    # Verify metrics
    metrics = result['metrics']
    assert metrics['transactions_processed'] == len(test_transactions)
    assert metrics['categories_available'] == len(test_categories)
    assert metrics['transactions_categorized'] > 0
    assert metrics['categories_updated'] == len(test_transactions)
    assert metrics['categorization_rate'] > 0
    assert metrics['execution_time'] >= 0


def test_execute_authentication_failure():
    """Test execute method handling of authentication failure"""
    # Create categorizer for testing
    categorizer = TransactionCategorizer()
    
    # Mock authenticate to return failure
    categorizer.authenticate = MagicMock(return_value=False)
    
    # Mock get_transactions_and_categories to verify it's not called
    categorizer.get_transactions_and_categories = MagicMock()
    
    # Call execute method
    result = categorizer.execute({})
    
    # Verify that error status is returned
    assert result['status'] == 'error'
    assert 'Authentication failed' in result['error']
    
    # Verify that get_transactions_and_categories was not called
    categorizer.get_transactions_and_categories.assert_not_called()


def test_execute_data_retrieval_failure():
    """Test execute method handling of data retrieval failure"""
    # Create categorizer for testing
    categorizer = TransactionCategorizer()
    
    # Mock authenticate to return success
    categorizer.authenticate = MagicMock(return_value=True)
    
    # Mock get_transactions_and_categories to raise APIError
    categorizer.get_transactions_and_categories = MagicMock(
        side_effect=APIError("API error", "Google Sheets", "get_transactions")
    )
    
    # Mock categorize_transactions to verify it's not called
    categorizer.categorize_transactions = MagicMock()
    
    # Call execute method
    result = categorizer.execute({})
    
    # Verify that error status is returned
    assert result['status'] == 'error'
    assert 'API error' in result['error']
    
    # Verify that categorize_transactions was not called
    categorizer.categorize_transactions.assert_not_called()


def test_execute_categorization_failure():
    """Test execute method handling of categorization failure"""
    # Create test data
    test_transactions = create_uncategorized_transactions()
    test_categories = create_test_categories()
    
    # Create categorizer for testing
    categorizer = TransactionCategorizer()
    
    # Mock authenticate to return success
    categorizer.authenticate = MagicMock(return_value=True)
    
    # Mock get_transactions_and_categories to return test data
    categorizer.get_transactions_and_categories = MagicMock(return_value=(test_transactions, test_categories))
    
    # Mock categorize_transactions to raise APIError
    categorizer.categorize_transactions = MagicMock(
        side_effect=APIError("API error", "Gemini", "categorize_transactions")
    )
    
    # Mock update_sheet_categories to verify it's not called
    categorizer.update_sheet_categories = MagicMock()
    
    # Call execute method
    result = categorizer.execute({})
    
    # Verify that error status is returned
    assert result['status'] == 'error'
    assert 'API error' in result['error']
    
    # Verify that update_sheet_categories was not called
    categorizer.update_sheet_categories.assert_not_called()


def test_execute_sheet_update_failure():
    """Test execute method handling of sheet update failure"""
    # Create test data
    test_transactions = create_uncategorized_transactions()
    test_categories = create_test_categories()
    
    # Create categorizer for testing
    categorizer = TransactionCategorizer()
    
    # Mock authenticate to return success
    categorizer.authenticate = MagicMock(return_value=True)
    
    # Mock get_transactions_and_categories to return test data
    categorizer.get_transactions_and_categories = MagicMock(return_value=(test_transactions, test_categories))
    
    # Create location_to_category_map
    location_to_category_map = {
        t.location: f"Category {i}" for i, t in enumerate(test_transactions)
    }
    
    # Mock categorize_transactions to return mapping
    categorizer.categorize_transactions = MagicMock(return_value=location_to_category_map)
    
    # Mock apply_categories to return transactions with categories
    for transaction in test_transactions:
        if transaction.location in location_to_category_map:
            transaction.set_category(location_to_category_map[transaction.location])
    categorizer.apply_categories = MagicMock(return_value=test_transactions)
    
    # Mock update_sheet_categories to raise APIError
    categorizer.update_sheet_categories = MagicMock(
        side_effect=APIError("API error", "Google Sheets", "update_sheet_categories")
    )
    
    # Call execute method
    result = categorizer.execute({})
    
    # Verify that error status is returned
    assert result['status'] == 'error'
    assert 'API error' in result['error']


def test_execute_empty_data():
    """Test execute method handling of empty transaction or category data"""
    # Create categorizer for testing
    categorizer = TransactionCategorizer()
    
    # Mock authenticate to return success
    categorizer.authenticate = MagicMock(return_value=True)
    
    # Mock get_transactions_and_categories to return empty transactions
    categorizer.get_transactions_and_categories = MagicMock(
        return_value=([], create_test_categories())
    )
    
    # Call execute method
    result = categorizer.execute({})
    
    # Verify that warning status is returned
    assert result['status'] == 'warning'
    assert 'No transactions to categorize' in result['message']
    
    # Test with empty categories
    categorizer.get_transactions_and_categories = MagicMock(
        return_value=(create_uncategorized_transactions(), [])
    )
    
    # Call execute method
    result = categorizer.execute({})
    
    # Verify that error status is returned
    assert result['status'] == 'error'
    assert 'No budget categories available' in result['error']


def test_check_health():
    """Test health check functionality"""
    # Create mock clients with different health statuses
    gemini_client = MockGeminiClient()
    gemini_client.authenticate = MagicMock(return_value=True)
    
    sheets_client = MockGoogleSheetsClient()
    sheets_client.authenticate = MagicMock(return_value=True)
    
    # Create categorizer with mock clients
    categorizer = TransactionCategorizer(
        gemini_client=gemini_client,
        sheets_client=sheets_client
    )
    
    # Check health - both healthy
    health_status = categorizer.check_health()
    assert health_status['gemini'] == 'healthy'
    assert health_status['google_sheets'] == 'healthy'
    
    # Test with gemini client unhealthy
    gemini_client.authenticate = MagicMock(return_value=False)
    
    health_status = categorizer.check_health()
    assert health_status['gemini'] == 'unhealthy'
    assert health_status['google_sheets'] == 'healthy'
    
    # Test with sheets client unhealthy
    gemini_client.authenticate = MagicMock(return_value=True)
    sheets_client.authenticate = MagicMock(return_value=False)
    
    health_status = categorizer.check_health()
    assert health_status['gemini'] == 'healthy'
    assert health_status['google_sheets'] == 'unhealthy'
    
    # Test with both unhealthy
    gemini_client.authenticate = MagicMock(return_value=False)
    sheets_client.authenticate = MagicMock(return_value=False)
    
    health_status = categorizer.check_health()
    assert health_status['gemini'] == 'unhealthy'
    assert health_status['google_sheets'] == 'unhealthy'
    
    # Test with exception in authentication
    gemini_client.authenticate = MagicMock(side_effect=Exception("Test exception"))
    sheets_client.authenticate = MagicMock(return_value=True)
    
    health_status = categorizer.check_health()
    assert 'unhealthy' in health_status['gemini']
    assert 'Test exception' in health_status['gemini']
    assert health_status['google_sheets'] == 'healthy'