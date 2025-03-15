"""
Unit tests for the formatters utility module in the Budget Management Application.

These tests validate the correct functioning of various formatting functions used for currency, 
percentages, variances, email content, and other data transformations throughout the application.
"""

import pytest
import decimal
from decimal import Decimal
import datetime
import re

from ...backend.utils.formatters import (
    format_currency,
    format_percentage,
    format_variance,
    format_budget_status,
    format_email_subject,
    format_category_for_sheets,
    format_transaction_for_sheets,
    format_transactions_for_sheets,
    format_budget_analysis_for_ai,
    truncate_text,
    clean_html,
    format_list_for_html,
    format_dict_for_sheets
)
from ...backend.utils.error_handlers import ValidationError
from ...backend.utils.validation import parse_amount
from ..utils.assertion_helpers import assert_decimal_equal
from ..fixtures.transactions import create_test_transaction


def test_format_currency_with_decimal():
    """Test that format_currency correctly formats Decimal values as currency strings"""
    # Test cases
    test_cases = [
        (Decimal('0'), '$0.00'),
        (Decimal('1'), '$1.00'),
        (Decimal('10.5'), '$10.50'),
        (Decimal('100.25'), '$100.25'),
        (Decimal('1000.99'), '$1000.99'),
        (Decimal('-10.5'), '($10.50)'),  # Negative amounts in parentheses
        (Decimal('0.01'), '$0.01'),
        (Decimal('123456.78'), '$123456.78')
    ]
    
    # Test each case
    for amount, expected in test_cases:
        result = format_currency(amount)
        assert result == expected, f"Expected {expected} but got {result} for amount {amount}"


def test_format_currency_with_string():
    """Test that format_currency correctly formats string values as currency strings"""
    # Test cases
    test_cases = [
        ('0', '$0.00'),
        ('1', '$1.00'),
        ('10.5', '$10.50'),
        ('100.25', '$100.25'),
        ('$100.25', '$100.25'),  # Already has dollar sign
        ('-10.5', '($10.50)'),  # Negative amounts in parentheses
        ('1,000.99', '$1000.99')  # With comma
    ]
    
    # Test each case
    for amount, expected in test_cases:
        result = format_currency(amount)
        assert result == expected, f"Expected {expected} but got {result} for amount {amount}"


def test_format_currency_with_numeric():
    """Test that format_currency correctly formats numeric values (int, float) as currency strings"""
    # Test cases
    test_cases = [
        (0, '$0.00'),
        (1, '$1.00'),
        (10.5, '$10.50'),
        (100.25, '$100.25'),
        (-10.5, '($10.50)'),  # Negative amounts in parentheses
    ]
    
    # Test each case
    for amount, expected in test_cases:
        result = format_currency(amount)
        assert result == expected, f"Expected {expected} but got {result} for amount {amount}"


def test_format_currency_with_invalid_input():
    """Test that format_currency handles invalid inputs gracefully"""
    # None should raise ValidationError
    with pytest.raises(ValueError):
        format_currency(None)
    
    # Non-numeric string should raise ValidationError
    with pytest.raises(ValueError):
        format_currency("not a number")
    
    # Complex types should raise ValidationError
    with pytest.raises(ValueError):
        format_currency(complex(1, 2))


def test_format_percentage_with_valid_input():
    """Test that format_percentage correctly formats numeric values as percentage strings"""
    # Test cases with default decimal places (2)
    test_cases = [
        (0, '0.00%'),
        (1, '100.00%'),
        (0.5, '50.00%'),
        (0.25, '25.00%'),
        (0.125, '12.50%'),
        (0.01, '1.00%'),
        (1.5, '150.00%')
    ]
    
    # Test each case
    for value, expected in test_cases:
        result = format_percentage(value)
        assert result == expected, f"Expected {expected} but got {result} for value {value}"
    
    # Test with different decimal places
    assert format_percentage(0.5, 0) == '50%'
    assert format_percentage(0.125, 1) == '12.5%'
    assert format_percentage(0.33333, 3) == '33.333%'


def test_format_percentage_with_invalid_input():
    """Test that format_percentage handles invalid inputs gracefully"""
    # None should raise TypeError
    with pytest.raises(TypeError):
        format_percentage(None)
    
    # Non-numeric string should raise ValueError
    with pytest.raises(ValueError):
        format_percentage("not a number")


def test_format_variance_positive():
    """Test that format_variance correctly formats positive variances (under budget)"""
    # Test cases without color
    test_cases = [
        (Decimal('0'), '$0.00'),
        (Decimal('1'), '+$1.00'),
        (Decimal('10.5'), '+$10.50'),
        (Decimal('100.25'), '+$100.25'),
    ]
    
    # Test each case without color
    for variance, expected in test_cases:
        result = format_variance(variance, include_color=False)
        assert result == expected, f"Expected {expected} but got {result} for variance {variance}"
    
    # Test with color should include span tags with green color
    result = format_variance(Decimal('10.5'), include_color=True)
    assert '<span style="color: green;">+$10.50</span>' == result


def test_format_variance_negative():
    """Test that format_variance correctly formats negative variances (over budget)"""
    # Test cases without color
    test_cases = [
        (Decimal('-1'), '($1.00)'),
        (Decimal('-10.5'), '($10.50)'),
        (Decimal('-100.25'), '($100.25)'),
    ]
    
    # Test each case without color
    for variance, expected in test_cases:
        result = format_variance(variance, include_color=False)
        assert result == expected, f"Expected {expected} but got {result} for variance {variance}"
    
    # Test with color should include span tags with red color
    result = format_variance(Decimal('-10.5'), include_color=True)
    assert '<span style="color: red;">($10.50)</span>' == result


def test_format_variance_zero():
    """Test that format_variance correctly formats zero variances (on budget)"""
    # Zero variance without color
    result = format_variance(Decimal('0'), include_color=False)
    assert result == '$0.00'
    
    # Zero variance with color - should not apply color for zero
    result = format_variance(Decimal('0'), include_color=True)
    assert result == '$0.00'


def test_format_budget_status_surplus():
    """Test that format_budget_status correctly formats budget surplus status"""
    # Test cases without color
    test_cases = [
        (Decimal('0'), '$0.00 under budget'),
        (Decimal('1'), '$1.00 under budget'),
        (Decimal('10.5'), '$10.50 under budget'),
        (Decimal('100.25'), '$100.25 under budget'),
    ]
    
    # Test each case without color
    for variance, expected in test_cases:
        result = format_budget_status(variance, include_color=False)
        assert result == expected, f"Expected {expected} but got {result} for variance {variance}"
    
    # Test with color should include span tags with green color
    result = format_budget_status(Decimal('10.5'), include_color=True)
    assert '<span style="color: green;">$10.50 under budget</span>' == result


def test_format_budget_status_deficit():
    """Test that format_budget_status correctly formats budget deficit status"""
    # Test cases without color
    test_cases = [
        (Decimal('-1'), '$1.00 over budget'),
        (Decimal('-10.5'), '$10.50 over budget'),
        (Decimal('-100.25'), '$100.25 over budget'),
    ]
    
    # Test each case without color
    for variance, expected in test_cases:
        result = format_budget_status(variance, include_color=False)
        assert result == expected, f"Expected {expected} but got {result} for variance {variance}"
    
    # Test with color should include span tags with red color
    result = format_budget_status(Decimal('-10.5'), include_color=True)
    assert '<span style="color: red;">$10.50 over budget</span>' == result


def test_format_budget_status_balanced():
    """Test that format_budget_status correctly formats balanced budget status"""
    # Zero variance without color
    result = format_budget_status(Decimal('0'), include_color=False)
    assert result == '$0.00 under budget'
    
    # Zero variance with color
    result = format_budget_status(Decimal('0'), include_color=True)
    assert '<span style="color: green;">$0.00 under budget</span>' == result


def test_format_email_subject_surplus():
    """Test that format_email_subject correctly formats email subject for budget surplus"""
    # Test cases
    test_cases = [
        (Decimal('0'), 'Budget Update: $0.00 under budget this week'),
        (Decimal('1'), 'Budget Update: $1.00 under budget this week'),
        (Decimal('10.5'), 'Budget Update: $10.50 under budget this week'),
        (Decimal('100.25'), 'Budget Update: $100.25 under budget this week'),
    ]
    
    # Test each case
    for variance, expected in test_cases:
        result = format_email_subject(variance)
        assert result == expected, f"Expected {expected} but got {result} for variance {variance}"


def test_format_email_subject_deficit():
    """Test that format_email_subject correctly formats email subject for budget deficit"""
    # Test cases
    test_cases = [
        (Decimal('-1'), 'Budget Update: $1.00 over budget this week'),
        (Decimal('-10.5'), 'Budget Update: $10.50 over budget this week'),
        (Decimal('-100.25'), 'Budget Update: $100.25 over budget this week'),
    ]
    
    # Test each case
    for variance, expected in test_cases:
        result = format_email_subject(variance)
        assert result == expected, f"Expected {expected} but got {result} for variance {variance}"


def test_format_category_for_sheets():
    """Test that format_category_for_sheets standardizes category names correctly"""
    # Test cases
    test_cases = [
        ('groceries', 'Groceries'),
        ('DINING OUT', 'Dining Out'),
        ('  entertainment  ', 'Entertainment'),
        ('home & utilities', 'Home  Utilities'),  # Special chars removed
        ('transportation/commute', 'Transportation Commute'),  # Special chars removed
        ('miscellaneous-expenses', 'Miscellaneous-expenses'),  # Hyphens preserved
        ('', 'Unknown Category'),  # Empty string handling
    ]
    
    # Test each case
    for category, expected in test_cases:
        result = format_category_for_sheets(category)
        assert result == expected, f"Expected {expected} but got {result} for category {category}"
    
    # Test non-string input
    result = format_category_for_sheets(123)
    assert result == '123'


def test_format_transaction_for_sheets():
    """Test that format_transaction_for_sheets correctly formats a transaction for Google Sheets"""
    # Create test transaction
    transaction = {
        'location': 'Grocery Store',
        'amount': Decimal('25.50'),
        'timestamp': datetime.datetime(2023, 7, 15, 14, 30, 0)
    }
    
    # Expected result (location, amount as string, timestamp as string, empty category)
    expected = ['Grocery Store', '25.50', '2023-07-15 14:30:00', '']
    
    # Test formatting
    result = format_transaction_for_sheets(transaction)
    assert result == expected, f"Expected {expected} but got {result}"
    
    # Test with additional fields that should be ignored
    transaction['extra'] = 'This should be ignored'
    result = format_transaction_for_sheets(transaction)
    assert result == expected, "Additional fields should be ignored"
    
    # Test with missing fields
    incomplete_transaction = {'location': 'Grocery Store'}
    result = format_transaction_for_sheets(incomplete_transaction)
    assert result[0] == 'Grocery Store', "Location should be preserved"
    assert result[1] == '0.00', "Missing amount should default to 0.00"
    assert result[3] == '', "Category should be empty"


def test_format_transactions_for_sheets():
    """Test that format_transactions_for_sheets correctly formats multiple transactions for Google Sheets"""
    # Create test transactions
    transactions = [
        {
            'location': 'Grocery Store',
            'amount': Decimal('25.50'),
            'timestamp': datetime.datetime(2023, 7, 15, 14, 30, 0)
        },
        {
            'location': 'Gas Station',
            'amount': Decimal('45.00'),
            'timestamp': datetime.datetime(2023, 7, 16, 10, 15, 0)
        }
    ]
    
    # Expected result
    expected = [
        ['Grocery Store', '25.50', '2023-07-15 14:30:00', ''],
        ['Gas Station', '45.00', '2023-07-16 10:15:00', '']
    ]
    
    # Test formatting
    result = format_transactions_for_sheets(transactions)
    assert result == expected, f"Expected {expected} but got {result}"
    
    # Test with empty list
    result = format_transactions_for_sheets([])
    assert result == [], "Empty list should return empty list"
    
    # Test with non-list input
    result = format_transactions_for_sheets("not a list")
    assert result == [], "Non-list input should return empty list"


def test_format_budget_analysis_for_ai():
    """Test that format_budget_analysis_for_ai correctly formats budget data for AI prompt"""
    # Create test budget analysis data
    budget_analysis = {
        'total_budget': Decimal('500.00'),
        'total_spent': Decimal('450.25'),
        'total_variance': Decimal('49.75'),
        'category_analysis': {
            'Groceries': {
                'budget_amount': Decimal('100.00'),
                'actual_amount': Decimal('95.50'),
                'variance_amount': Decimal('4.50'),
                'variance_percentage': Decimal('4.5')
            },
            'Dining Out': {
                'budget_amount': Decimal('75.00'),
                'actual_amount': Decimal('85.00'),
                'variance_amount': Decimal('-10.00'),
                'variance_percentage': Decimal('-13.33')
            }
        }
    }
    
    # Format budget analysis
    result = format_budget_analysis_for_ai(budget_analysis)
    
    # Verify result is a string
    assert isinstance(result, str)
    
    # Verify it contains key components
    assert "TOTAL BUDGET STATUS:" in result
    assert "Total Budget: $500.00" in result
    assert "Total Spent: $450.25" in result
    assert "Variance: $49.75 (Surplus)" in result
    
    assert "CATEGORY BREAKDOWN:" in result
    assert "Category: Groceries" in result
    assert "Budget: $100.00" in result
    assert "Actual: $95.50" in result
    assert "+$4.50" in result  # Positive variance
    
    assert "Category: Dining Out" in result
    assert "Budget: $75.00" in result
    assert "Actual: $85.00" in result
    assert "-$10.00" in result or "($10.00)" in result  # Negative variance


def test_truncate_text_no_truncation_needed():
    """Test that truncate_text returns the original text when no truncation is needed"""
    # Test cases
    test_cases = [
        ('Short text', 100, 'Short text'),
        ('', 10, ''),
        ('Exactly ten', 10, 'Exactly ten'),
    ]
    
    # Test each case
    for text, max_length, expected in test_cases:
        result = truncate_text(text, max_length)
        assert result == expected, f"Expected {expected} but got {result}"


def test_truncate_text_with_truncation():
    """Test that truncate_text correctly truncates text and adds ellipsis"""
    # Test cases
    test_cases = [
        ('This text is too long', 10, 'This te...'),
        ('Another long example that needs truncation', 20, 'Another long exam...'),
        ('Just a bit too long', 15, 'Just a bit t...'),
    ]
    
    # Test each case
    for text, max_length, expected in test_cases:
        result = truncate_text(text, max_length)
        assert result == expected, f"Expected {expected} but got {result}"
        assert len(result) <= max_length, f"Result should not exceed max_length {max_length}"


def test_clean_html_valid_content():
    """Test that clean_html correctly sanitizes valid HTML content"""
    # Test cases with allowed tags and attributes
    test_cases = [
        ('<p>Simple paragraph</p>', '<p>Simple paragraph</p>'),
        ('<h1>Heading</h1><p>Paragraph</p>', '<h1>Heading</h1><p>Paragraph</p>'),
        ('<span style="color: red;">Red text</span>', '<span style="color: red;">Red text</span>'),
        ('<strong>Bold</strong> and <em>italic</em>', '<strong>Bold</strong> and <em>italic</em>'),
        ('<ul><li>Item 1</li><li>Item 2</li></ul>', '<ul><li>Item 1</li><li>Item 2</li></ul>'),
    ]
    
    # Test each case
    for html_content, expected in test_cases:
        result = clean_html(html_content)
        assert result == expected, f"Expected {expected} but got {result}"


def test_clean_html_invalid_content():
    """Test that clean_html correctly removes disallowed HTML content"""
    # Test cases with disallowed tags and attributes
    test_cases = [
        ('<script>alert("XSS")</script>', ''),
        ('<p onclick="alert()">Click me</p>', '<p>Click me</p>'),
        ('<img src="image.jpg" onerror="alert()">', ''),
        ('<a href="javascript:alert()">Link</a>', ''),
        ('<iframe src="https://example.com"></iframe>', ''),
    ]
    
    # Test each case
    for html_content, expected in test_cases:
        result = clean_html(html_content)
        assert result == expected, f"Expected {expected} but got {result}"


def test_format_list_for_html():
    """Test that format_list_for_html correctly converts a list to HTML unordered list"""
    # Test with simple list
    items = ['Item 1', 'Item 2', 'Item 3']
    expected = '<ul>\n  <li>Item 1</li>\n  <li>Item 2</li>\n  <li>Item 3</li>\n</ul>'
    result = format_list_for_html(items)
    assert result == expected, f"Expected {expected} but got {result}"
    
    # Test with empty list
    result = format_list_for_html([])
    assert result == '', "Empty list should return empty string"
    
    # Test with non-string items
    items = [1, 2.5, True, None]
    result = format_list_for_html(items)
    assert '<li>1</li>' in result
    assert '<li>2.5</li>' in result
    assert '<li>True</li>' in result
    assert '<li>None</li>' in result
    
    # Test with non-list input
    result = format_list_for_html('Not a list')
    assert '<li>Not a list</li>' in result, "Non-list input should be treated as a single item"


def test_format_dict_for_sheets():
    """Test that format_dict_for_sheets correctly formats a dictionary for Google Sheets"""
    # Create test dictionary
    data = {
        'category1': Decimal('100.00'),
        'category2': 200,
        'category3': 150.50,
        'category4': 'Not a number'
    }
    
    # Format dictionary
    result = format_dict_for_sheets(data)
    
    # Verify result is a list of lists
    assert isinstance(result, list)
    for row in result:
        assert isinstance(row, list)
        assert len(row) == 2  # Each row should be [key, value]
    
    # Check specific entries
    assert ['category1', '100.00'] in result
    assert ['category2', '200'] in result
    assert ['category3', '150.50'] in result or ['category3', '150.5'] in result
    assert ['category4', 'Not a number'] in result
    
    # Test with empty dict
    result = format_dict_for_sheets({})
    assert result == [], "Empty dict should return empty list"
    
    # Test with non-dict input
    result = format_dict_for_sheets('Not a dict')
    assert result == [], "Non-dict input should return empty list"