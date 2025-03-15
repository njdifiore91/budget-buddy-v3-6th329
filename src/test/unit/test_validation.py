"""
test_validation.py - Unit tests for validation utility functions

This module contains unit tests for the validation utility functions in the Budget Management Application.
These tests ensure that data integrity checks are functioning correctly across the application.
"""

import pytest
import datetime
from decimal import Decimal

from ...backend.utils.validation import (
    is_valid_transaction, validate_transactions,
    is_valid_category, validate_categorization_results, is_categorization_successful,
    is_valid_amount, parse_amount,
    is_valid_email, validate_email_list,
    is_valid_transfer_amount, validate_budget_data, validate_api_response,
    is_duplicate_transaction, filter_duplicates,
    validate_calculation_results
)
from ...backend.utils.error_handlers import ValidationError
from ..fixtures.transactions import create_test_transaction, VALID_TRANSACTIONS, INVALID_TRANSACTIONS
from ..fixtures.categories import create_test_category, create_test_categories, DEFAULT_CATEGORIES
from ..utils.assertion_helpers import assert_decimal_equal

# Test is_valid_transaction function
def test_is_valid_transaction_with_valid_data():
    """Test that is_valid_transaction returns True for valid transaction data"""
    # Create a valid transaction with all required fields
    transaction = {
        'location': 'Test Store',
        'amount': Decimal('25.50'),
        'timestamp': datetime.datetime.now()
    }
    
    # Call the validation function
    result = is_valid_transaction(transaction)
    
    # Assert the result is True
    assert result is True

def test_is_valid_transaction_with_missing_fields():
    """Test that is_valid_transaction returns False when required fields are missing"""
    # Test missing location
    transaction_no_location = {
        'amount': Decimal('25.50'),
        'timestamp': datetime.datetime.now()
    }
    assert is_valid_transaction(transaction_no_location) is False
    
    # Test missing amount
    transaction_no_amount = {
        'location': 'Test Store',
        'timestamp': datetime.datetime.now()
    }
    assert is_valid_transaction(transaction_no_amount) is False
    
    # Test missing timestamp
    transaction_no_timestamp = {
        'location': 'Test Store',
        'amount': Decimal('25.50')
    }
    assert is_valid_transaction(transaction_no_timestamp) is False

def test_is_valid_transaction_with_invalid_types():
    """Test that is_valid_transaction returns False when fields have invalid types"""
    # Test invalid location type
    transaction_invalid_location = {
        'location': 123,  # Location should be a string
        'amount': Decimal('25.50'),
        'timestamp': datetime.datetime.now()
    }
    assert is_valid_transaction(transaction_invalid_location) is False
    
    # Test invalid amount type
    transaction_invalid_amount = {
        'location': 'Test Store',
        'amount': 'not-a-number',  # Amount should be numeric
        'timestamp': datetime.datetime.now()
    }
    assert is_valid_transaction(transaction_invalid_amount) is False
    
    # Test invalid timestamp type
    transaction_invalid_timestamp = {
        'location': 'Test Store',
        'amount': Decimal('25.50'),
        'timestamp': 'not-a-date'  # Timestamp should be a datetime
    }
    assert is_valid_transaction(transaction_invalid_timestamp) is False

def test_is_valid_transaction_with_negative_amount():
    """Test that is_valid_transaction returns False when amount is negative"""
    transaction = {
        'location': 'Test Store',
        'amount': Decimal('-25.50'),  # Negative amount
        'timestamp': datetime.datetime.now()
    }
    assert is_valid_transaction(transaction) is False

# Test validate_transactions function
def test_validate_transactions_with_all_valid():
    """Test that validate_transactions returns all transactions when all are valid"""
    # Create a list of valid transactions
    valid_transactions = [
        {
            'location': 'Store 1',
            'amount': Decimal('25.50'),
            'timestamp': datetime.datetime.now()
        },
        {
            'location': 'Store 2',
            'amount': Decimal('10.00'),
            'timestamp': datetime.datetime.now()
        }
    ]
    
    # Call the validation function
    result = validate_transactions(valid_transactions)
    
    # Assert that all transactions are returned
    assert len(result) == len(valid_transactions)
    assert all(is_valid_transaction(tx) for tx in result)

def test_validate_transactions_with_some_invalid():
    """Test that validate_transactions filters out invalid transactions"""
    # Create a list with both valid and invalid transactions
    mixed_transactions = [
        {
            'location': 'Store 1',
            'amount': Decimal('25.50'),
            'timestamp': datetime.datetime.now()
        },
        {
            'location': 'Store 2',
            'amount': Decimal('-10.00'),  # Invalid: negative amount
            'timestamp': datetime.datetime.now()
        },
        {
            'location': 'Store 3',
            'amount': Decimal('15.75'),
            'timestamp': datetime.datetime.now()
        }
    ]
    
    # Call the validation function
    result = validate_transactions(mixed_transactions)
    
    # Assert that only valid transactions are returned
    assert len(result) == 2  # Only 2 out of 3 are valid
    assert all(is_valid_transaction(tx) for tx in result)
    # Check that Store 2 with negative amount is filtered out
    assert not any(tx['location'] == 'Store 2' for tx in result)

def test_validate_transactions_raises_on_invalid():
    """Test that validate_transactions raises ValidationError when raise_on_invalid is True"""
    # Create a list with both valid and invalid transactions
    mixed_transactions = [
        {
            'location': 'Store 1',
            'amount': Decimal('25.50'),
            'timestamp': datetime.datetime.now()
        },
        {
            'location': 'Store 2',
            'amount': Decimal('-10.00'),  # Invalid: negative amount
            'timestamp': datetime.datetime.now()
        }
    ]
    
    # Assert that ValidationError is raised
    with pytest.raises(ValidationError):
        validate_transactions(mixed_transactions, raise_on_invalid=True)

# Test category validation functions
def test_is_valid_category_with_valid_data():
    """Test that is_valid_category returns True for valid category and valid_categories list"""
    # Define a list of valid categories
    valid_categories = ['Groceries', 'Dining Out', 'Entertainment', 'Shopping']
    
    # Test with a valid category
    assert is_valid_category('Groceries', valid_categories) is True

def test_is_valid_category_with_invalid_data():
    """Test that is_valid_category returns False for invalid category or invalid valid_categories"""
    # Define a list of valid categories
    valid_categories = ['Groceries', 'Dining Out', 'Entertainment', 'Shopping']
    
    # Test with an invalid category (not in the list)
    assert is_valid_category('Unknown Category', valid_categories) is False
    
    # Test with an empty category
    assert is_valid_category('', valid_categories) is False
    
    # Test with a non-string category
    assert is_valid_category(123, valid_categories) is False
    
    # Test with invalid valid_categories parameter
    assert is_valid_category('Groceries', 'not-a-list') is False
    assert is_valid_category('Groceries', None) is False

# Test AI categorization validation functions
def test_validate_categorization_results_with_valid_data():
    """Test that validate_categorization_results returns valid categorization results"""
    # Define valid categorization results
    categorization_results = {
        'Walmart': 'Groceries',
        'Amazon': 'Shopping',
        'AMC Theaters': 'Entertainment',
        'Olive Garden': 'Dining Out'
    }
    
    # Define valid categories
    valid_categories = ['Groceries', 'Dining Out', 'Entertainment', 'Shopping']
    
    # Define transaction locations
    transaction_locations = ['Walmart', 'Amazon', 'AMC Theaters', 'Olive Garden']
    
    # Call the validation function
    result = validate_categorization_results(categorization_results, valid_categories, transaction_locations)
    
    # Assert the results match the input
    assert result == categorization_results

def test_validate_categorization_results_with_invalid_data():
    """Test that validate_categorization_results handles invalid categorization results"""
    # Define categorization results with invalid categories
    categorization_results = {
        'Walmart': 'Groceries',
        'Amazon': 'Shopping',
        'AMC Theaters': 'Movies',  # Invalid category
        'Olive Garden': 'Food'  # Invalid category
    }
    
    # Define valid categories
    valid_categories = ['Groceries', 'Dining Out', 'Entertainment', 'Shopping']
    
    # Define transaction locations
    transaction_locations = ['Walmart', 'Amazon', 'AMC Theaters', 'Olive Garden']
    
    # Call the validation function
    result = validate_categorization_results(categorization_results, valid_categories, transaction_locations)
    
    # Assert invalid categories are removed
    assert 'Walmart' in result
    assert 'Amazon' in result
    assert 'AMC Theaters' not in result
    assert 'Olive Garden' not in result
    assert len(result) == 2

def test_is_categorization_successful_above_threshold():
    """Test that is_categorization_successful returns True when success rate is above threshold"""
    # Define categorization results with high success rate
    categorization_results = {
        'Walmart': 'Groceries',
        'Amazon': 'Shopping',
        'AMC Theaters': 'Entertainment',
        'Olive Garden': 'Dining Out'
    }
    
    # Define transaction locations (all categorized)
    transaction_locations = ['Walmart', 'Amazon', 'AMC Theaters', 'Olive Garden']
    
    # Call the function with 75% threshold
    result = is_categorization_successful(categorization_results, transaction_locations, threshold=0.75)
    
    # Assert the result is True
    assert result is True

def test_is_categorization_successful_below_threshold():
    """Test that is_categorization_successful returns False when success rate is below threshold"""
    # Define categorization results with low success rate
    categorization_results = {
        'Walmart': 'Groceries',
        'Amazon': 'Shopping'
    }
    
    # Define transaction locations (only 2 out of 4 categorized)
    transaction_locations = ['Walmart', 'Amazon', 'AMC Theaters', 'Olive Garden']
    
    # Call the function with 75% threshold
    result = is_categorization_successful(categorization_results, transaction_locations, threshold=0.75)
    
    # Assert the result is False
    assert result is False

# Test amount validation functions
def test_is_valid_amount_with_valid_data():
    """Test that is_valid_amount returns True for valid amount values"""
    # Test with Decimal
    assert is_valid_amount(Decimal('25.50')) is True
    
    # Test with integer
    assert is_valid_amount(100) is True
    
    # Test with float
    assert is_valid_amount(25.50) is True
    
    # Test with string
    assert is_valid_amount('25.50') is True
    
    # Test with string with dollar sign
    assert is_valid_amount('$25.50') is True

def test_is_valid_amount_with_invalid_data():
    """Test that is_valid_amount returns False for invalid amount values"""
    # Test with negative amount
    assert is_valid_amount(Decimal('-25.50')) is False
    
    # Test with non-numeric string
    assert is_valid_amount('not-a-number') is False
    
    # Test with None
    assert is_valid_amount(None) is False
    
    # Test with complex object
    assert is_valid_amount({'amount': 25.50}) is False

def test_parse_amount_with_valid_data():
    """Test that parse_amount correctly converts various formats to Decimal"""
    # Test with Decimal
    decimal_amount = Decimal('25.50')
    assert parse_amount(decimal_amount) == decimal_amount
    
    # Test with integer
    assert parse_amount(100) == Decimal('100')
    
    # Test with float
    assert parse_amount(25.50) == Decimal('25.50')
    
    # Test with string
    assert parse_amount('25.50') == Decimal('25.50')
    
    # Test with string with dollar sign
    assert parse_amount('$25.50') == Decimal('25.50')
    
    # Test with string with commas
    assert parse_amount('1,234.56') == Decimal('1234.56')

def test_parse_amount_with_invalid_data():
    """Test that parse_amount raises ValueError for invalid amount formats"""
    # Test with non-numeric string
    with pytest.raises(ValueError):
        parse_amount('not-a-number')
    
    # Test with None
    with pytest.raises(ValueError):
        parse_amount(None)
    
    # Test with complex object
    with pytest.raises(ValueError):
        parse_amount({'amount': 25.50})

# Test email validation functions
def test_is_valid_email_with_valid_data():
    """Test that is_valid_email returns True for valid email addresses"""
    # Test with simple email
    assert is_valid_email('user@example.com') is True
    
    # Test with email containing dots
    assert is_valid_email('first.last@example.com') is True
    
    # Test with email containing plus
    assert is_valid_email('user+tag@example.com') is True
    
    # Test with subdomain
    assert is_valid_email('user@subdomain.example.com') is True

def test_is_valid_email_with_invalid_data():
    """Test that is_valid_email returns False for invalid email addresses"""
    # Test with no @ symbol
    assert is_valid_email('userexample.com') is False
    
    # Test with no domain
    assert is_valid_email('user@') is False
    
    # Test with no username
    assert is_valid_email('@example.com') is False
    
    # Test with non-string
    assert is_valid_email(123) is False
    
    # Test with None
    assert is_valid_email(None) is False

def test_validate_email_list_with_all_valid():
    """Test that validate_email_list returns all emails when all are valid"""
    # Define a list of valid emails
    valid_emails = ['user1@example.com', 'user2@example.com', 'user3@example.com']
    
    # Call the validation function
    result = validate_email_list(valid_emails)
    
    # Assert that all emails are returned
    assert len(result) == len(valid_emails)
    assert all(is_valid_email(email) for email in result)

def test_validate_email_list_with_some_invalid():
    """Test that validate_email_list filters out invalid email addresses"""
    # Create a list with both valid and invalid emails
    mixed_emails = ['user1@example.com', 'invalid-email', 'user2@example.com']
    
    # Call the validation function
    result = validate_email_list(mixed_emails)
    
    # Assert that only valid emails are returned
    assert len(result) == 2  # Only 2 out of 3 are valid
    assert all(is_valid_email(email) for email in result)
    # Check that the invalid email is filtered out
    assert 'invalid-email' not in result

def test_validate_email_list_raises_on_invalid():
    """Test that validate_email_list raises ValidationError when raise_on_invalid is True"""
    # Create a list with both valid and invalid emails
    mixed_emails = ['user1@example.com', 'invalid-email', 'user2@example.com']
    
    # Assert that ValidationError is raised
    with pytest.raises(ValidationError):
        validate_email_list(mixed_emails, raise_on_invalid=True)

# Test transfer amount validation functions
def test_is_valid_transfer_amount_with_valid_data():
    """Test that is_valid_transfer_amount returns True for valid transfer amounts"""
    # Test with amount above minimum
    assert is_valid_transfer_amount(Decimal('10.00'), Decimal('1.00')) is True
    
    # Test with amount equal to minimum
    assert is_valid_transfer_amount(Decimal('1.00'), Decimal('1.00')) is True

def test_is_valid_transfer_amount_with_invalid_data():
    """Test that is_valid_transfer_amount returns False for invalid transfer amounts"""
    # Test with amount below minimum
    assert is_valid_transfer_amount(Decimal('0.50'), Decimal('1.00')) is False
    
    # Test with negative amount
    assert is_valid_transfer_amount(Decimal('-5.00'), Decimal('1.00')) is False
    
    # Test with non-numeric value
    assert is_valid_transfer_amount('not-a-number', Decimal('1.00')) is False

# Test budget data validation functions
def test_validate_budget_data_with_valid_data():
    """Test that validate_budget_data returns True for valid budget data"""
    # Create valid budget data
    budget_data = {
        'categories': ['Groceries', 'Dining Out', 'Entertainment'],
        'amounts': {
            'Groceries': Decimal('150.00'),
            'Dining Out': Decimal('75.00'),
            'Entertainment': Decimal('50.00')
        }
    }
    
    # Call the validation function
    result = validate_budget_data(budget_data)
    
    # Assert the result is True
    assert result is True

def test_validate_budget_data_with_invalid_data():
    """Test that validate_budget_data returns False for invalid budget data"""
    # Test with missing required keys
    budget_data_missing_keys = {
        'categories': ['Groceries', 'Dining Out']
        # Missing 'amounts' key
    }
    assert validate_budget_data(budget_data_missing_keys) is False
    
    # Test with invalid categories (not a list)
    budget_data_invalid_categories = {
        'categories': 'not-a-list',
        'amounts': {
            'Groceries': Decimal('150.00')
        }
    }
    assert validate_budget_data(budget_data_invalid_categories) is False
    
    # Test with invalid amounts (not a dictionary)
    budget_data_invalid_amounts = {
        'categories': ['Groceries', 'Dining Out'],
        'amounts': 'not-a-dictionary'
    }
    assert validate_budget_data(budget_data_invalid_amounts) is False
    
    # Test with negative amount
    budget_data_negative_amount = {
        'categories': ['Groceries', 'Dining Out'],
        'amounts': {
            'Groceries': Decimal('150.00'),
            'Dining Out': Decimal('-75.00')  # Negative amount
        }
    }
    assert validate_budget_data(budget_data_negative_amount) is False
    
    # Test with non-numeric amount
    budget_data_non_numeric = {
        'categories': ['Groceries', 'Dining Out'],
        'amounts': {
            'Groceries': Decimal('150.00'),
            'Dining Out': 'not-a-number'
        }
    }
    assert validate_budget_data(budget_data_non_numeric) is False

# Test API response validation functions
def test_validate_api_response_with_valid_data():
    """Test that validate_api_response returns True for valid API responses"""
    # Create a valid API response
    api_response = {
        'status': 'success',
        'data': {
            'transactions': [
                {'id': '1', 'amount': '25.50', 'description': 'Test Transaction 1'},
                {'id': '2', 'amount': '15.75', 'description': 'Test Transaction 2'}
            ]
        },
        'count': 2
    }
    
    # Define required fields
    required_fields = ['status', 'data', 'count']
    
    # Call the validation function
    result = validate_api_response(api_response, required_fields, 'Capital One')
    
    # Assert the result is True
    assert result is True

def test_validate_api_response_with_missing_fields():
    """Test that validate_api_response returns False when required fields are missing"""
    # Create an API response with missing fields
    api_response_missing_field = {
        'status': 'success',
        'data': {
            'transactions': []
        }
        # Missing 'count' field
    }
    
    # Define required fields
    required_fields = ['status', 'data', 'count']
    
    # Call the validation function
    result = validate_api_response(api_response_missing_field, required_fields, 'Capital One')
    
    # Assert the result is False
    assert result is False
    
    # Test with non-dictionary response
    assert validate_api_response('not-a-dictionary', required_fields, 'Capital One') is False

# Test duplicate transaction functions
def test_is_duplicate_transaction_with_duplicate():
    """Test that is_duplicate_transaction returns True for duplicate transactions"""
    # Create a transaction
    transaction = {
        'location': 'Test Store',
        'amount': Decimal('25.50'),
        'timestamp': datetime.datetime(2023, 7, 15, 12, 0, 0)
    }
    
    # Create existing transactions list including the same transaction
    existing_transactions = [
        {
            'location': 'Another Store',
            'amount': Decimal('10.00'),
            'timestamp': datetime.datetime(2023, 7, 14, 12, 0, 0)
        },
        {
            'location': 'Test Store',  # Same location
            'amount': Decimal('25.50'),  # Same amount
            'timestamp': datetime.datetime(2023, 7, 15, 12, 0, 0)  # Same date
        }
    ]
    
    # Call the function
    result = is_duplicate_transaction(transaction, existing_transactions)
    
    # Assert the result is True
    assert result is True

def test_is_duplicate_transaction_with_unique():
    """Test that is_duplicate_transaction returns False for unique transactions"""
    # Create a transaction
    transaction = {
        'location': 'Test Store',
        'amount': Decimal('25.50'),
        'timestamp': datetime.datetime(2023, 7, 15, 12, 0, 0)
    }
    
    # Create existing transactions list with different transactions
    existing_transactions = [
        {
            'location': 'Another Store',
            'amount': Decimal('10.00'),
            'timestamp': datetime.datetime(2023, 7, 14, 12, 0, 0)
        },
        {
            'location': 'Test Store',
            'amount': Decimal('30.00'),  # Different amount
            'timestamp': datetime.datetime(2023, 7, 15, 12, 0, 0)
        }
    ]
    
    # Call the function
    result = is_duplicate_transaction(transaction, existing_transactions)
    
    # Assert the result is False
    assert result is False

def test_filter_duplicates_with_duplicates():
    """Test that filter_duplicates removes duplicate transactions"""
    # Create a list of transactions with duplicates
    transactions_with_duplicates = [
        {
            'location': 'Store 1',
            'amount': Decimal('25.50'),
            'timestamp': datetime.datetime(2023, 7, 15, 12, 0, 0)
        },
        {
            'location': 'Store 2',
            'amount': Decimal('10.00'),
            'timestamp': datetime.datetime(2023, 7, 14, 12, 0, 0)
        },
        {
            'location': 'Store 1',  # Duplicate location
            'amount': Decimal('25.50'),  # Duplicate amount
            'timestamp': datetime.datetime(2023, 7, 15, 12, 0, 0)  # Duplicate date
        }
    ]
    
    # Call the function
    result = filter_duplicates(transactions_with_duplicates)
    
    # Assert that duplicates are removed
    assert len(result) == 2
    # Check that only one 'Store 1' transaction remains
    assert len([tx for tx in result if tx['location'] == 'Store 1']) == 1

def test_filter_duplicates_with_no_duplicates():
    """Test that filter_duplicates returns the same list when there are no duplicates"""
    # Create a list of transactions without duplicates
    unique_transactions = [
        {
            'location': 'Store 1',
            'amount': Decimal('25.50'),
            'timestamp': datetime.datetime(2023, 7, 15, 12, 0, 0)
        },
        {
            'location': 'Store 2',
            'amount': Decimal('10.00'),
            'timestamp': datetime.datetime(2023, 7, 14, 12, 0, 0)
        },
        {
            'location': 'Store 3',
            'amount': Decimal('15.75'),
            'timestamp': datetime.datetime(2023, 7, 13, 12, 0, 0)
        }
    ]
    
    # Call the function
    result = filter_duplicates(unique_transactions)
    
    # Assert that the result has the same length as the input
    assert len(result) == len(unique_transactions)
    # Check that all original transactions are in the result
    for tx in unique_transactions:
        assert any(r['location'] == tx['location'] and r['amount'] == tx['amount'] for r in result)

# Test calculation validation functions
def test_validate_calculation_results_with_valid_data():
    """Test that validate_calculation_results returns True for accurate calculations"""
    # Create test data
    category_totals = {
        'Groceries': Decimal('120.50'),
        'Dining Out': Decimal('65.75'),
        'Entertainment': Decimal('0.00')
    }
    category_variances = {
        'Groceries': Decimal('29.50'),  # 150 - 120.50
        'Dining Out': Decimal('9.25'),  # 75 - 65.75
        'Entertainment': Decimal('50.00')  # 50 - 0
    }
    total_budget = Decimal('275.00')  # 150 + 75 + 50
    total_spent = Decimal('186.25')  # 120.50 + 65.75 + 0
    total_variance = Decimal('88.75')  # 275 - 186.25
    
    # Call the validation function
    result = validate_calculation_results(
        category_totals,
        category_variances,
        total_budget,
        total_spent,
        total_variance
    )
    
    # Assert the result is True
    assert result is True

def test_validate_calculation_results_with_invalid_data():
    """Test that validate_calculation_results returns False for inaccurate calculations"""
    # Create test data with invalid calculations
    category_totals = {
        'Groceries': Decimal('120.50'),
        'Dining Out': Decimal('65.75'),
        'Entertainment': Decimal('0.00')
    }
    category_variances = {
        'Groceries': Decimal('29.50'),
        'Dining Out': Decimal('9.25'),
        'Entertainment': Decimal('50.00')
    }
    total_budget = Decimal('275.00')
    total_spent = Decimal('186.25')
    total_variance = Decimal('100.00')  # Incorrect, should be 88.75
    
    # Call the validation function
    result = validate_calculation_results(
        category_totals,
        category_variances,
        total_budget,
        total_spent,
        total_variance
    )
    
    # Assert the result is False
    assert result is False