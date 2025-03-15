"""
assertion_helpers.py - Utility module providing custom assertion functions for testing the Budget Management Application.

This module contains specialized assertions for financial data validation, API response
verification, model object comparison, and other test-specific validation needs to
improve test readability and error reporting.
"""

import pytest
import decimal
from decimal import Decimal
import datetime
import typing
from typing import List, Dict, Any, Optional, Union, Callable, TypeVar
import json
import re
import jsonschema

from .fixture_loader import load_fixture, load_expected_result_fixture
from ...backend.models.transaction import Transaction
from ...backend.models.budget import Budget
from ...backend.models.category import Category

# Default precision for decimal comparisons
DEFAULT_DECIMAL_PRECISION = Decimal('0.01')

# Default tolerance for datetime comparisons
DEFAULT_DATE_TOLERANCE = datetime.timedelta(seconds=1)

# API response schema definitions
API_SCHEMAS = {
    "capital_one": {},  # Will be populated with actual schemas
    "google_sheets": {},
    "gemini": {},
    "gmail": {}
}

# Error response patterns by API and error type
ERROR_RESPONSE_PATTERNS = {
    "capital_one": {
        "authentication": ["unauthorized", "invalid_token"],
        "rate_limit": ["rate limit", "too many requests"],
        "not_found": ["not found", "no record"]
    },
    "google_sheets": {
        "authentication": ["unauthorized", "invalid credentials"],
        "permission": ["permission denied", "insufficient permissions"],
        "not_found": ["not found", "no such sheet"]
    },
    "gemini": {
        "authentication": ["invalid api key", "unauthorized"],
        "rate_limit": ["quota exceeded", "rate limit"],
        "content_policy": ["content policy violation", "unsafe content"]
    },
    "gmail": {
        "authentication": ["unauthorized", "invalid credentials"],
        "permission": ["permission denied", "insufficient permissions"],
        "rate_limit": ["quota exceeded", "rate limit"]
    }
}


def assert_decimal_equal(actual: Decimal, expected: Decimal, precision: Optional[Decimal] = None, message: Optional[str] = None):
    """
    Assert that two decimal values are equal within a specified precision.
    
    Args:
        actual: Actual decimal value
        expected: Expected decimal value
        precision: Maximum allowed difference (default: DEFAULT_DECIMAL_PRECISION)
        message: Custom error message
        
    Raises:
        AssertionError: If the difference between actual and expected exceeds precision
    """
    if precision is None:
        precision = DEFAULT_DECIMAL_PRECISION
        
    # Calculate the absolute difference
    difference = abs(actual - expected)
    
    # Create error message if needed
    if message is None:
        message = f"Decimal values differ by {difference} which exceeds precision {precision}: {actual} != {expected}"
    
    # Assert the difference is within precision
    assert difference <= precision, message


def assert_datetime_equal(actual: datetime.datetime, expected: datetime.datetime, 
                          tolerance: Optional[datetime.timedelta] = None, message: Optional[str] = None):
    """
    Assert that two datetime values are equal within a specified tolerance.
    
    Args:
        actual: Actual datetime value
        expected: Expected datetime value
        tolerance: Maximum allowed difference (default: DEFAULT_DATE_TOLERANCE)
        message: Custom error message
        
    Raises:
        AssertionError: If the difference between actual and expected exceeds tolerance
    """
    if tolerance is None:
        tolerance = DEFAULT_DATE_TOLERANCE
        
    # Calculate the absolute difference
    difference = abs(actual - expected)
    
    # Create error message if needed
    if message is None:
        message = f"Datetime values differ by {difference} which exceeds tolerance {tolerance}: {actual} != {expected}"
    
    # Assert the difference is within tolerance
    assert difference <= tolerance, message


def assert_transaction_equal(actual: Transaction, expected: Transaction, 
                           check_category: Optional[bool] = True, 
                           amount_precision: Optional[Decimal] = None,
                           time_tolerance: Optional[datetime.timedelta] = None):
    """
    Assert that two Transaction objects are equal in their essential attributes.
    
    Args:
        actual: Actual Transaction object
        expected: Expected Transaction object
        check_category: Whether to check category equality
        amount_precision: Precision for amount comparison
        time_tolerance: Tolerance for timestamp comparison
        
    Raises:
        AssertionError: If transactions are not equal within specified parameters
    """
    # Compare location
    assert actual.location == expected.location, f"Transaction locations differ: {actual.location} != {expected.location}"
    
    # Compare amount with precision
    assert_decimal_equal(
        actual.amount, 
        expected.amount, 
        precision=amount_precision,
        message=f"Transaction amounts differ for {actual.location}: {actual.amount} != {expected.amount}"
    )
    
    # Compare timestamp with tolerance
    assert_datetime_equal(
        actual.timestamp,
        expected.timestamp,
        tolerance=time_tolerance,
        message=f"Transaction timestamps differ for {actual.location}: {actual.timestamp} != {expected.timestamp}"
    )
    
    # Compare category if requested
    if check_category:
        assert actual.category == expected.category, \
            f"Transaction categories differ for {actual.location}: {actual.category} != {expected.category}"


def assert_transactions_equal(actual: List[Transaction], expected: List[Transaction],
                            check_order: Optional[bool] = False,
                            check_category: Optional[bool] = True,
                            amount_precision: Optional[Decimal] = None,
                            time_tolerance: Optional[datetime.timedelta] = None):
    """
    Assert that two lists of Transaction objects are equal.
    
    Args:
        actual: List of actual Transaction objects
        expected: List of expected Transaction objects
        check_order: Whether to check transactions in order (False to ignore order)
        check_category: Whether to check transaction categories
        amount_precision: Precision for amount comparison
        time_tolerance: Tolerance for timestamp comparison
        
    Raises:
        AssertionError: If transaction lists are not equal within specified parameters
    """
    # Check lists have same length
    assert len(actual) == len(expected), \
        f"Transaction lists have different lengths: {len(actual)} != {len(expected)}"
    
    if check_order:
        # Compare transactions in order
        for i, (a_tx, e_tx) in enumerate(zip(actual, expected)):
            try:
                assert_transaction_equal(
                    a_tx, e_tx, 
                    check_category=check_category,
                    amount_precision=amount_precision,
                    time_tolerance=time_tolerance
                )
            except AssertionError as e:
                raise AssertionError(f"Transactions at index {i} differ: {str(e)}")
    else:
        # Sort transactions by location and timestamp for comparison
        sorted_actual = sorted(actual, key=lambda tx: (tx.location, tx.timestamp))
        sorted_expected = sorted(expected, key=lambda tx: (tx.location, tx.timestamp))
        
        # Compare sorted transactions
        for i, (a_tx, e_tx) in enumerate(zip(sorted_actual, sorted_expected)):
            try:
                assert_transaction_equal(
                    a_tx, e_tx, 
                    check_category=check_category,
                    amount_precision=amount_precision,
                    time_tolerance=time_tolerance
                )
            except AssertionError as e:
                raise AssertionError(f"Transactions at sorted index {i} differ: {str(e)}")


def assert_budget_equal(actual: Budget, expected: Budget, amount_precision: Optional[Decimal] = None):
    """
    Assert that two Budget objects are equal in their essential attributes.
    
    Args:
        actual: Actual Budget object
        expected: Expected Budget object
        amount_precision: Precision for amount comparisons
        
    Raises:
        AssertionError: If budgets are not equal within specified parameters
    """
    # Ensure both budgets are analyzed
    if not actual.is_analyzed:
        actual.analyze()
    if not expected.is_analyzed:
        expected.analyze()
    
    # Compare total budget
    assert_decimal_equal(
        actual.total_budget,
        expected.total_budget,
        precision=amount_precision,
        message=f"Budget total_budget differs: {actual.total_budget} != {expected.total_budget}"
    )
    
    # Compare total spent
    assert_decimal_equal(
        actual.total_spent,
        expected.total_spent,
        precision=amount_precision,
        message=f"Budget total_spent differs: {actual.total_spent} != {expected.total_spent}"
    )
    
    # Compare total variance
    assert_decimal_equal(
        actual.total_variance,
        expected.total_variance,
        precision=amount_precision,
        message=f"Budget total_variance differs: {actual.total_variance} != {expected.total_variance}"
    )
    
    # Compare categories
    assert_categories_equal(
        actual.categories,
        expected.categories,
        amount_precision=amount_precision
    )
    
    # Compare category variances
    # First check we have the same keys
    assert set(actual.category_variances.keys()) == set(expected.category_variances.keys()), \
        f"Budget category_variances have different keys: {actual.category_variances.keys()} != {expected.category_variances.keys()}"
    
    # Then check each variance
    for category, actual_variance in actual.category_variances.items():
        expected_variance = expected.category_variances[category]
        assert_decimal_equal(
            actual_variance,
            expected_variance,
            precision=amount_precision,
            message=f"Budget variance for {category} differs: {actual_variance} != {expected_variance}"
        )


def assert_category_equal(actual: Category, expected: Category, amount_precision: Optional[Decimal] = None):
    """
    Assert that two Category objects are equal in their essential attributes.
    
    Args:
        actual: Actual Category object
        expected: Expected Category object
        amount_precision: Precision for amount comparison
        
    Raises:
        AssertionError: If categories are not equal within specified parameters
    """
    # Compare name
    assert actual.name == expected.name, f"Category names differ: {actual.name} != {expected.name}"
    
    # Compare weekly amount
    assert_decimal_equal(
        actual.weekly_amount,
        expected.weekly_amount,
        precision=amount_precision,
        message=f"Category weekly_amount differs for {actual.name}: {actual.weekly_amount} != {expected.weekly_amount}"
    )


def assert_categories_equal(actual: List[Category], expected: List[Category],
                          check_order: Optional[bool] = False,
                          amount_precision: Optional[Decimal] = None):
    """
    Assert that two lists of Category objects are equal.
    
    Args:
        actual: List of actual Category objects
        expected: List of expected Category objects
        check_order: Whether to check categories in order (False to ignore order)
        amount_precision: Precision for amount comparison
        
    Raises:
        AssertionError: If category lists are not equal within specified parameters
    """
    # Check lists have same length
    assert len(actual) == len(expected), \
        f"Category lists have different lengths: {len(actual)} != {len(expected)}"
    
    if check_order:
        # Compare categories in order
        for i, (a_cat, e_cat) in enumerate(zip(actual, expected)):
            try:
                assert_category_equal(a_cat, e_cat, amount_precision=amount_precision)
            except AssertionError as e:
                raise AssertionError(f"Categories at index {i} differ: {str(e)}")
    else:
        # Sort categories by name for comparison
        sorted_actual = sorted(actual, key=lambda cat: cat.name)
        sorted_expected = sorted(expected, key=lambda cat: cat.name)
        
        # Compare sorted categories
        for i, (a_cat, e_cat) in enumerate(zip(sorted_actual, sorted_expected)):
            try:
                assert_category_equal(a_cat, e_cat, amount_precision=amount_precision)
            except AssertionError as e:
                raise AssertionError(f"Categories at sorted index {i} differ: {str(e)}")


def assert_dict_subset(actual: Dict[Any, Any], expected_subset: Dict[Any, Any], message: Optional[str] = None):
    """
    Assert that a dictionary contains all key-value pairs from another dictionary.
    
    Args:
        actual: The actual dictionary to check
        expected_subset: Dictionary containing key-value pairs that should be in actual
        message: Custom error message
        
    Raises:
        AssertionError: If actual doesn't contain all expected key-value pairs
    """
    missing_keys = []
    mismatched_values = []
    
    for key, expected_value in expected_subset.items():
        if key not in actual:
            missing_keys.append(key)
            continue
            
        actual_value = actual[key]
        
        # Handle nested dictionaries recursively
        if isinstance(expected_value, dict) and isinstance(actual_value, dict):
            try:
                assert_dict_subset(actual_value, expected_value)
            except AssertionError as e:
                mismatched_values.append(f"{key}: {str(e)}")
        elif actual_value != expected_value:
            mismatched_values.append(f"{key}: Expected {expected_value}, got {actual_value}")
    
    # Build error message
    errors = []
    if missing_keys:
        errors.append(f"Missing keys: {missing_keys}")
    if mismatched_values:
        errors.append(f"Mismatched values: {mismatched_values}")
    
    if errors:
        if message:
            errors.insert(0, message)
        raise AssertionError("\n".join(errors))


def validate_response_schema(response: Dict[str, Any], api_name: str, response_type: str) -> bool:
    """
    Validate an API response against its JSON schema.
    
    Args:
        response: API response to validate
        api_name: Name of the API (e.g., 'capital_one', 'gemini')
        response_type: Type of response (e.g., 'transactions', 'categorization')
        
    Returns:
        True if validation passes, False otherwise
    """
    # Get schema for this API and response type
    schema_key = f"{api_name}_{response_type}"
    schema = API_SCHEMAS.get(api_name, {}).get(response_type)
    
    if not schema:
        # Log warning but don't fail if schema not found
        import logging
        logging.warning(f"No schema found for {schema_key}")
        return True
    
    try:
        # Validate response against schema
        jsonschema.validate(response, schema)
        return True
    except jsonschema.ValidationError as e:
        # Log validation error
        import logging
        logging.error(f"Schema validation failed for {schema_key}: {e}")
        return False


def validate_response_content(response: Dict[str, Any], expected_content: Dict[str, Any]) -> bool:
    """
    Validate that an API response contains expected content.
    
    Args:
        response: API response to validate
        expected_content: Expected content to be found in response
        
    Returns:
        True if validation passes, False otherwise
    """
    for key, expected_value in expected_content.items():
        # Check if key exists in response
        if key not in response:
            import logging
            logging.error(f"Expected key '{key}' not found in response")
            return False
            
        actual_value = response[key]
        
        # Handle nested dictionaries
        if isinstance(expected_value, dict) and isinstance(actual_value, dict):
            if not validate_response_content(actual_value, expected_value):
                return False
        
        # Handle lists
        elif isinstance(expected_value, list) and isinstance(actual_value, list):
            # Check each item in the list
            for i, item in enumerate(expected_value):
                if i >= len(actual_value):
                    import logging
                    logging.error(f"Response list '{key}' has fewer items than expected")
                    return False
                
                if isinstance(item, dict):
                    if not validate_response_content(actual_value[i], item):
                        return False
                elif actual_value[i] != item:
                    import logging
                    logging.error(f"List item mismatch for '{key}' at index {i}")
                    return False
        
        # Direct comparison for other types
        elif actual_value != expected_value:
            import logging
            logging.error(f"Value mismatch for '{key}': expected {expected_value}, got {actual_value}")
            return False
    
    return True


def validate_error_response(response: Dict[str, Any], api_name: str, expected_error_type: str) -> bool:
    """
    Validate that an error response contains expected error information.
    
    Args:
        response: API error response to validate
        api_name: Name of the API (e.g., 'capital_one', 'gemini')
        expected_error_type: Type of error expected (e.g., 'authentication', 'rate_limit')
        
    Returns:
        True if validation passes, False otherwise
    """
    # Get error patterns for this API and error type
    error_patterns = ERROR_RESPONSE_PATTERNS.get(api_name, {}).get(expected_error_type, [])
    
    if not error_patterns:
        import logging
        logging.warning(f"No error patterns defined for {api_name}/{expected_error_type}")
        return False
    
    # Extract error message from response (format varies by API)
    error_message = ""
    
    if api_name == "capital_one":
        error_message = response.get("error", {}).get("message", "")
    elif api_name == "google_sheets":
        error_message = response.get("error", {}).get("message", "")
    elif api_name == "gemini":
        error_message = response.get("error", {}).get("message", "")
    elif api_name == "gmail":
        error_message = response.get("error", {}).get("message", "")
    else:
        # Generic fallback
        error_message = str(response.get("error", response.get("message", "")))
    
    # Convert error message to lowercase for case-insensitive matching
    error_message = error_message.lower()
    
    # Check if any error pattern appears in the error message
    for pattern in error_patterns:
        if pattern.lower() in error_message:
            return True
    
    import logging
    logging.error(f"Error response does not match expected type {expected_error_type}")
    return False


def assert_api_response_valid(response: Dict[str, Any], api_name: str, response_type: str, 
                             expected_content: Optional[Dict[str, Any]] = None):
    """
    Assert that an API response is valid according to schema and expected content.
    
    Args:
        response: API response to validate
        api_name: Name of the API (e.g., 'capital_one', 'gemini')
        response_type: Type of response (e.g., 'transactions', 'categorization')
        expected_content: Optional expected content to validate
        
    Raises:
        AssertionError: If response is not valid
    """
    # Validate against schema
    schema_valid = validate_response_schema(response, api_name, response_type)
    assert schema_valid, f"API response failed schema validation for {api_name}/{response_type}"
    
    # Validate content if provided
    if expected_content:
        content_valid = validate_response_content(response, expected_content)
        assert content_valid, f"API response failed content validation for {api_name}/{response_type}"


def assert_api_error_response(response: Dict[str, Any], api_name: str, expected_error_type: str):
    """
    Assert that an API error response contains the expected error type.
    
    Args:
        response: API error response to validate
        api_name: Name of the API (e.g., 'capital_one', 'gemini')
        expected_error_type: Type of error expected (e.g., 'authentication', 'rate_limit')
        
    Raises:
        AssertionError: If error response is not valid
    """
    is_valid = validate_error_response(response, api_name, expected_error_type)
    assert is_valid, f"API error response does not contain expected error type {expected_error_type}"


def assert_matches_fixture(actual: Any, fixture_path: str, comparison_func: Optional[Callable[[Any, Any], bool]] = None):
    """
    Assert that an object matches the expected data from a fixture file.
    
    Args:
        actual: Actual object to compare
        fixture_path: Path to the fixture file with expected data
        comparison_func: Optional custom comparison function
        
    Raises:
        AssertionError: If object doesn't match fixture data
    """
    # Load expected data from fixture
    expected = load_fixture(fixture_path)
    
    # If custom comparison function is provided, use it
    if comparison_func:
        is_match = comparison_func(actual, expected)
        assert is_match, f"Object does not match fixture data using custom comparison"
        return
    
    # Otherwise use appropriate assertion based on data type
    if isinstance(actual, dict) and isinstance(expected, dict):
        assert_dict_subset(actual, expected)
    elif isinstance(actual, list) and isinstance(expected, list):
        assert len(actual) == len(expected), \
            f"Lists have different lengths: {len(actual)} != {len(expected)}"
        
        for i, (actual_item, expected_item) in enumerate(zip(actual, expected)):
            try:
                assert_matches_fixture(actual_item, expected_item)
            except AssertionError as e:
                raise AssertionError(f"Items at index {i} differ: {str(e)}")
    elif isinstance(actual, Transaction) and isinstance(expected, dict):
        # Compare Transaction to dictionary
        for key, value in expected.items():
            if hasattr(actual, key):
                assert getattr(actual, key) == value, \
                    f"Transaction.{key} differs: {getattr(actual, key)} != {value}"
    elif isinstance(actual, Budget) and isinstance(expected, dict):
        # Compare Budget to dictionary
        for key, value in expected.items():
            if hasattr(actual, key):
                assert getattr(actual, key) == value, \
                    f"Budget.{key} differs: {getattr(actual, key)} != {value}"
    elif isinstance(actual, Category) and isinstance(expected, dict):
        # Compare Category to dictionary
        for key, value in expected.items():
            if hasattr(actual, key):
                assert getattr(actual, key) == value, \
                    f"Category.{key} differs: {getattr(actual, key)} != {value}"
    else:
        # Default equality comparison
        assert actual == expected, f"Objects differ: {actual} != {expected}"


def assert_contains_transaction(transactions: List[Transaction], location: Optional[str] = None,
                              amount: Optional[Decimal] = None, category: Optional[str] = None,
                              amount_precision: Optional[Decimal] = None):
    """
    Assert that a list of transactions contains a transaction matching the specified criteria.
    
    Args:
        transactions: List of transactions to search
        location: Optional location to match
        amount: Optional amount to match
        category: Optional category to match
        amount_precision: Precision for amount comparison
        
    Raises:
        AssertionError: If no matching transaction is found
    """
    if amount_precision is None:
        amount_precision = DEFAULT_DECIMAL_PRECISION
        
    found = False
    for transaction in transactions:
        matches = True
        
        # Check location if specified
        if location is not None and transaction.location != location:
            matches = False
            continue
            
        # Check amount if specified
        if amount is not None:
            if abs(transaction.amount - amount) > amount_precision:
                matches = False
                continue
                
        # Check category if specified
        if category is not None and transaction.category != category:
            matches = False
            continue
            
        if matches:
            found = True
            break
    
    # Build error message if not found
    if not found:
        criteria = []
        if location is not None:
            criteria.append(f"location='{location}'")
        if amount is not None:
            criteria.append(f"amount={amount}")
        if category is not None:
            criteria.append(f"category='{category}'")
            
        available = "\n".join([str(tx) for tx in transactions])
        assert False, f"No transaction found matching criteria: {', '.join(criteria)}\nAvailable transactions:\n{available}"


def assert_budget_variance_correct(budget: Budget, precision: Optional[Decimal] = None):
    """
    Assert that budget variance calculations are mathematically correct.
    
    Args:
        budget: Budget object to validate
        precision: Precision for decimal comparisons
        
    Raises:
        AssertionError: If calculations are incorrect
    """
    if not budget.is_analyzed:
        budget.analyze()
        
    if precision is None:
        precision = DEFAULT_DECIMAL_PRECISION
    
    # Calculate expected total budget
    expected_total_budget = sum(category.weekly_amount for category in budget.categories)
    
    # Calculate expected total spent
    expected_total_spent = sum(budget.actual_spending.values())
    
    # Calculate expected total variance
    expected_total_variance = expected_total_budget - expected_total_spent
    
    # Verify total budget
    assert_decimal_equal(
        budget.total_budget,
        expected_total_budget,
        precision=precision,
        message=f"Budget total_budget incorrect: {budget.total_budget} != {expected_total_budget}"
    )
    
    # Verify total spent
    assert_decimal_equal(
        budget.total_spent,
        expected_total_spent,
        precision=precision,
        message=f"Budget total_spent incorrect: {budget.total_spent} != {expected_total_spent}"
    )
    
    # Verify total variance
    assert_decimal_equal(
        budget.total_variance,
        expected_total_variance,
        precision=precision,
        message=f"Budget total_variance incorrect: {budget.total_variance} != {expected_total_variance}"
    )
    
    # Verify category variances
    for category in budget.categories:
        category_name = category.name
        budget_amount = category.weekly_amount
        actual_amount = budget.actual_spending.get(category_name, Decimal('0'))
        expected_variance = budget_amount - actual_amount
        
        if category_name in budget.category_variances:
            assert_decimal_equal(
                budget.category_variances[category_name],
                expected_variance,
                precision=precision,
                message=f"Budget variance for {category_name} incorrect: {budget.category_variances[category_name]} != {expected_variance}"
            )
        else:
            assert False, f"Missing variance calculation for category {category_name}"


def assert_transfer_amount_valid(transfer_amount: Decimal, total_variance: Decimal,
                               min_transfer_amount: Optional[Decimal] = None,
                               precision: Optional[Decimal] = None):
    """
    Assert that a calculated transfer amount is valid based on budget surplus.
    
    Args:
        transfer_amount: Calculated transfer amount
        total_variance: Total budget variance
        min_transfer_amount: Minimum allowed transfer amount
        precision: Precision for decimal comparisons
        
    Raises:
        AssertionError: If transfer amount is invalid
    """
    if precision is None:
        precision = DEFAULT_DECIMAL_PRECISION
        
    # If no surplus, transfer amount should be 0
    if total_variance <= 0:
        assert transfer_amount == 0, \
            f"Transfer amount should be 0 for negative variance (deficit), got {transfer_amount}"
        return
        
    # If surplus is below minimum transfer amount, transfer amount should be 0
    if min_transfer_amount is not None and total_variance < min_transfer_amount:
        assert transfer_amount == 0, \
            f"Transfer amount should be 0 for variance below minimum ({total_variance} < {min_transfer_amount}), got {transfer_amount}"
        return
        
    # Otherwise, transfer amount should equal the variance
    assert_decimal_equal(
        transfer_amount,
        total_variance,
        precision=precision,
        message=f"Transfer amount incorrect: {transfer_amount} != {total_variance}"
    )


def assert_email_content_valid(email_content: str, budget_data: Dict[str, Any],
                             required_sections: Optional[List[str]] = None):
    """
    Assert that email content contains expected information.
    
    Args:
        email_content: HTML email content to validate
        budget_data: Budget data that should be reflected in the email
        required_sections: Optional list of required sections
        
    Raises:
        AssertionError: If email content is invalid
    """
    if required_sections is None:
        required_sections = ['header', 'budget status', 'categories']
    
    # Check for required sections
    missing_sections = []
    for section in required_sections:
        if section.lower() not in email_content.lower():
            missing_sections.append(section)
    
    assert not missing_sections, f"Email content missing required sections: {missing_sections}"
    
    # Check that budget values are included
    total_budget = str(budget_data.get('total_budget', '') or budget_data.get('formatted_total_budget', ''))
    assert total_budget in email_content, f"Email missing total budget: {total_budget}"
    
    total_spent = str(budget_data.get('total_spent', '') or budget_data.get('formatted_total_spent', ''))
    assert total_spent in email_content, f"Email missing total spent: {total_spent}"
    
    total_variance = str(budget_data.get('total_variance', '') or budget_data.get('formatted_total_variance', ''))
    assert total_variance in email_content, f"Email missing total variance: {total_variance}"
    
    # Check that categories are included
    for category in budget_data.get('categories', []):
        if isinstance(category, dict):
            category_name = category.get('name', '')
        elif isinstance(category, Category):
            category_name = category.name
        else:
            category_name = str(category)
            
        assert category_name in email_content, f"Email missing category: {category_name}"


def assert_categorization_correct(categorized_transactions: List[Transaction],
                                expected_categories: Dict[str, str],
                                min_accuracy: Optional[float] = None):
    """
    Assert that transactions are correctly categorized according to expected categories.
    
    Args:
        categorized_transactions: List of transactions with categories assigned
        expected_categories: Dictionary mapping transaction locations to expected categories
        min_accuracy: Minimum required categorization accuracy (default: 0.95)
        
    Raises:
        AssertionError: If categorization accuracy is below threshold
    """
    if min_accuracy is None:
        min_accuracy = 0.95  # Default to 95% accuracy requirement
        
    # Count correct categorizations
    correct_count = 0
    incorrect_categorizations = []
    
    for transaction in categorized_transactions:
        if transaction.location in expected_categories:
            expected_category = expected_categories[transaction.location]
            if transaction.category == expected_category:
                correct_count += 1
            else:
                incorrect_categorizations.append({
                    'location': transaction.location,
                    'expected': expected_category,
                    'actual': transaction.category
                })
    
    # Calculate accuracy
    total_count = len(categorized_transactions)
    if total_count == 0:
        assert False, "No transactions to categorize"
        
    accuracy = correct_count / total_count
    
    # Assert accuracy meets threshold
    assert accuracy >= min_accuracy, \
        f"Categorization accuracy {accuracy:.2%} below required threshold {min_accuracy:.2%}\n" \
        f"Incorrect categorizations: {incorrect_categorizations}"


class BudgetAssertions:
    """Class providing specialized assertions for budget-related testing"""
    
    @staticmethod
    def assert_variance_calculation(budget: Budget, precision: Optional[Decimal] = None):
        """
        Assert that budget variance calculations are mathematically correct.
        
        Args:
            budget: Budget object to validate
            precision: Precision for decimal comparisons
            
        Raises:
            AssertionError: If calculations are incorrect
        """
        assert_budget_variance_correct(budget, precision)
    
    @staticmethod
    def assert_transfer_calculation(budget: Budget, precision: Optional[Decimal] = None):
        """
        Assert that transfer amount calculation is correct based on budget surplus.
        
        Args:
            budget: Budget object to validate
            precision: Precision for decimal comparisons
            
        Raises:
            AssertionError: If calculation is incorrect
        """
        if not budget.is_analyzed:
            budget.analyze()
            
        transfer_amount = budget.get_transfer_amount()
        assert_transfer_amount_valid(transfer_amount, budget.total_variance, precision=precision)
    
    @staticmethod
    def assert_budget_matches_fixture(budget: Budget, fixture_name: str, precision: Optional[Decimal] = None):
        """
        Assert that a budget matches the expected data from a fixture file.
        
        Args:
            budget: Budget object to validate
            fixture_name: Name of the fixture file to load
            precision: Precision for decimal comparisons
            
        Raises:
            AssertionError: If budget doesn't match fixture
        """
        expected_data = load_expected_result_fixture(fixture_name)
        
        # Ensure budget is analyzed
        if not budget.is_analyzed:
            budget.analyze()
        
        # Convert budget to dictionary for comparison
        budget_dict = budget.to_dict()
        
        # Compare with expected data
        for key, expected_value in expected_data.items():
            if key not in budget_dict:
                assert False, f"Budget missing expected key: {key}"
                
            actual_value = budget_dict[key]
            
            # Special handling for decimal values
            if isinstance(expected_value, (int, float, str)) and isinstance(actual_value, Decimal):
                expected_decimal = Decimal(str(expected_value))
                assert_decimal_equal(actual_value, expected_decimal, precision=precision,
                                   message=f"Budget {key} differs: {actual_value} != {expected_value}")
            elif isinstance(expected_value, dict) and isinstance(actual_value, dict):
                assert_dict_subset(actual_value, expected_value)
            else:
                assert actual_value == expected_value, \
                    f"Budget {key} differs: {actual_value} != {expected_value}"


class TransactionAssertions:
    """Class providing specialized assertions for transaction-related testing"""
    
    @staticmethod
    def assert_transaction_matches(transaction: Transaction, location: Optional[str] = None,
                               amount: Optional[Decimal] = None, category: Optional[str] = None,
                               amount_precision: Optional[Decimal] = None):
        """
        Assert that a transaction matches specified criteria.
        
        Args:
            transaction: Transaction object to validate
            location: Expected location
            amount: Expected amount
            category: Expected category
            amount_precision: Precision for amount comparison
            
        Raises:
            AssertionError: If transaction doesn't match criteria
        """
        if location is not None:
            assert transaction.location == location, \
                f"Transaction location differs: {transaction.location} != {location}"
        
        if amount is not None:
            assert_decimal_equal(
                transaction.amount,
                amount,
                precision=amount_precision,
                message=f"Transaction amount differs: {transaction.amount} != {amount}"
            )
            
        if category is not None:
            assert transaction.category == category, \
                f"Transaction category differs: {transaction.category} != {category}"
    
    @staticmethod
    def assert_transactions_match_fixture(transactions: List[Transaction], fixture_name: str,
                                      check_order: Optional[bool] = False,
                                      check_category: Optional[bool] = True,
                                      amount_precision: Optional[Decimal] = None):
        """
        Assert that a list of transactions matches the expected data from a fixture file.
        
        Args:
            transactions: List of Transaction objects to validate
            fixture_name: Name of the fixture file to load
            check_order: Whether to check transactions in order
            check_category: Whether to check transaction categories
            amount_precision: Precision for amount comparison
            
        Raises:
            AssertionError: If transactions don't match fixture
        """
        expected_data = load_expected_result_fixture(fixture_name)
        
        # Handle case where expected data is not a list
        if not isinstance(expected_data, list):
            assert False, f"Expected fixture data to be a list, got {type(expected_data)}"
        
        # Convert expected data to Transaction objects if needed
        from ...backend.models.transaction import create_transaction
        expected_transactions = []
        for tx_data in expected_data:
            if isinstance(tx_data, dict):
                expected_transactions.append(create_transaction(tx_data))
            elif isinstance(tx_data, Transaction):
                expected_transactions.append(tx_data)
            else:
                assert False, f"Unexpected transaction data type in fixture: {type(tx_data)}"
        
        # Compare transactions
        assert_transactions_equal(
            transactions,
            expected_transactions,
            check_order=check_order,
            check_category=check_category,
            amount_precision=amount_precision
        )
    
    @staticmethod
    def assert_categorization_accuracy(categorized_transactions: List[Transaction],
                                   expected_categories: Dict[str, str],
                                   min_accuracy: Optional[float] = None):
        """
        Assert that transactions are correctly categorized with a minimum accuracy.
        
        Args:
            categorized_transactions: List of transactions with categories assigned
            expected_categories: Dictionary mapping transaction locations to expected categories
            min_accuracy: Minimum required categorization accuracy
            
        Raises:
            AssertionError: If accuracy is below threshold
        """
        assert_categorization_correct(categorized_transactions, expected_categories, min_accuracy)


class APIAssertions:
    """Class providing specialized assertions for API-related testing"""
    
    @staticmethod
    def assert_response_valid(response: Dict[str, Any], api_name: str, response_type: str,
                         expected_content: Optional[Dict[str, Any]] = None):
        """
        Assert that an API response is valid according to schema and expected content.
        
        Args:
            response: API response to validate
            api_name: Name of the API (e.g., 'capital_one', 'gemini')
            response_type: Type of response (e.g., 'transactions', 'categorization')
            expected_content: Optional expected content to validate
            
        Raises:
            AssertionError: If response is not valid
        """
        assert_api_response_valid(response, api_name, response_type, expected_content)
    
    @staticmethod
    def assert_error_response(response: Dict[str, Any], api_name: str, expected_error_type: str):
        """
        Assert that an API error response contains the expected error type.
        
        Args:
            response: API error response to validate
            api_name: Name of the API (e.g., 'capital_one', 'gemini')
            expected_error_type: Type of error expected (e.g., 'authentication', 'rate_limit')
            
        Raises:
            AssertionError: If error response is not valid
        """
        assert_api_error_response(response, api_name, expected_error_type)
    
    @staticmethod
    def assert_response_matches_fixture(response: Dict[str, Any], api_name: str, fixture_name: str):
        """
        Assert that an API response matches the expected data from a fixture file.
        
        Args:
            response: API response to validate
            api_name: Name of the API (for logging context)
            fixture_name: Name of the fixture file to load
            
        Raises:
            AssertionError: If response doesn't match fixture
        """
        expected_data = load_expected_result_fixture(fixture_name)
        assert_dict_subset(
            response, 
            expected_data,
            message=f"API response for {api_name} doesn't match expected fixture"
        )