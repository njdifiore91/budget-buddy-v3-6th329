"""
formatters.py - Utility module providing formatting functions for data presentation

This module provides formatting functions for currency values, percentages, and text content
throughout the Budget Management Application. It handles formatting for reports, emails,
Google Sheets data, and AI prompts.
"""

import decimal  # standard library
from decimal import Decimal  # standard library
import re  # standard library
import html  # standard library
import logging  # standard library
import bleach  # bleach 6.0.0+

from ..config.settings import APP_SETTINGS  # Access application settings for email formatting
from .error_handlers import ValidationError  # Raise validation errors for formatting issues
from .validation import parse_amount  # Parse string amounts to Decimal for formatting

# Set up logger
logger = logging.getLogger(__name__)

# Constants
CURRENCY_SYMBOL = '$'
ALLOWED_HTML_TAGS = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'em', 'b', 'i', 'br', 'span', 'div']
ALLOWED_HTML_ATTRIBUTES = {'span': ['style'], 'div': ['style']}


def format_currency(amount):
    """
    Formats a numeric value as a currency string with dollar sign and two decimal places.
    
    Args:
        amount: Value to format as currency (Decimal, float, int, or str)
        
    Returns:
        str: Formatted currency string (e.g., '$123.45')
    """
    try:
        # Use parse_amount to safely convert to Decimal
        if not isinstance(amount, Decimal):
            amount = parse_amount(amount)
        
        # Format with negative values in parentheses
        if amount < 0:
            return f"({CURRENCY_SYMBOL}{abs(amount):.2f})"
        else:
            return f"{CURRENCY_SYMBOL}{amount:.2f}"
    except Exception as e:
        logger.error(f"Error formatting currency: {str(e)}")
        # Return a safe fallback if formatting fails
        return f"{CURRENCY_SYMBOL}0.00"


def format_percentage(value, decimal_places=2):
    """
    Formats a numeric value as a percentage string with specified decimal places.
    
    Args:
        value: Value to format as percentage (0.42 becomes 42.00%)
        decimal_places: Number of decimal places to include
        
    Returns:
        str: Formatted percentage string (e.g., '42.00%')
    """
    try:
        # Convert to float for percentage calculation
        float_value = float(value) * 100
        # Format with specified decimal places
        format_string = f"{{:.{decimal_places}f}}%"
        return format_string.format(float_value)
    except Exception as e:
        logger.error(f"Error formatting percentage: {str(e)}")
        # Return a safe fallback if formatting fails
        return f"0.{'0' * decimal_places}%"


def format_variance(variance, include_color=False):
    """
    Formats budget variance with appropriate sign and color coding.
    
    Args:
        variance: Budget variance amount (negative means over budget)
        include_color: Whether to include HTML color styling
        
    Returns:
        str: Formatted variance string with optional HTML color styling
    """
    try:
        # Ensure variance is a Decimal
        if not isinstance(variance, Decimal):
            variance = parse_amount(variance)
        
        # Format the variance amount
        formatted_amount = format_currency(variance)
        
        # Add plus sign for positive values
        if variance > 0:
            formatted_amount = "+" + formatted_amount
        
        # Add color coding if requested
        if include_color:
            if variance >= 0:
                # Green for under budget (positive variance)
                return f'<span style="color: green;">{formatted_amount}</span>'
            else:
                # Red for over budget (negative variance)
                return f'<span style="color: red;">{formatted_amount}</span>'
        
        return formatted_amount
    
    except Exception as e:
        logger.error(f"Error formatting variance: {str(e)}")
        return format_currency(0)


def format_budget_status(total_variance, include_color=False):
    """
    Formats overall budget status for display in reports and emails.
    
    Args:
        total_variance: Total budget variance (positive means under budget)
        include_color: Whether to include HTML color styling
        
    Returns:
        str: Formatted budget status string with descriptive text
    """
    try:
        # Ensure total_variance is a Decimal
        if not isinstance(total_variance, Decimal):
            total_variance = parse_amount(total_variance)
        
        # Format the variance amount
        formatted_amount = format_currency(abs(total_variance))
        
        # Determine status text
        if total_variance >= 0:
            status_text = f"{formatted_amount} under budget"
            color = "green"
        else:
            status_text = f"{formatted_amount} over budget"
            color = "red"
        
        # Add color coding if requested
        if include_color:
            return f'<span style="color: {color};">{status_text}</span>'
        
        return status_text
    
    except Exception as e:
        logger.error(f"Error formatting budget status: {str(e)}")
        return "Budget status unavailable"


def format_email_subject(total_variance):
    """
    Creates email subject line with budget status.
    
    Args:
        total_variance: Total budget variance (positive means under budget)
        
    Returns:
        str: Email subject line with budget status
    """
    try:
        # Ensure total_variance is a Decimal
        if not isinstance(total_variance, Decimal):
            total_variance = parse_amount(total_variance)
        
        # Format the variance amount
        formatted_amount = format_currency(abs(total_variance))
        
        # Determine status text
        if total_variance >= 0:
            return f"Budget Update: {formatted_amount} under budget this week"
        else:
            return f"Budget Update: {formatted_amount} over budget this week"
    
    except Exception as e:
        logger.error(f"Error formatting email subject: {str(e)}")
        return "Weekly Budget Update"


def format_category_for_sheets(category):
    """
    Standardizes category names for Google Sheets.
    
    Args:
        category: Category name to standardize
        
    Returns:
        str: Standardized category name
    """
    try:
        if not isinstance(category, str):
            logger.warning(f"Non-string category provided: {type(category)}")
            return str(category)
        
        # Trim whitespace
        category = category.strip()
        
        # Capitalize first letter of each word
        category = ' '.join(word.capitalize() for word in category.split())
        
        # Remove any problematic characters for Sheets
        category = re.sub(r'[^\w\s\-]', '', category)
        
        return category
    
    except Exception as e:
        logger.error(f"Error formatting category name: {str(e)}")
        return "Unknown Category"


def format_transaction_for_sheets(transaction):
    """
    Formats a single transaction for Google Sheets insertion.
    
    Args:
        transaction: Dictionary containing transaction data
        
    Returns:
        list: Row of values formatted for Google Sheets
    """
    try:
        # Extract required fields
        location = transaction.get('location', 'Unknown Location')
        amount = transaction.get('amount', 0)
        timestamp = transaction.get('timestamp', '')
        
        # Format amount as string without currency symbol for Sheets
        if not isinstance(amount, Decimal):
            amount = parse_amount(amount)
        formatted_amount = f"{amount:.2f}"
        
        # Return row in the format expected by Sheets
        return [location, formatted_amount, str(timestamp), '']  # Empty string for category to be filled later
    
    except Exception as e:
        logger.error(f"Error formatting transaction for sheets: {str(e)}")
        # Return a safe fallback
        return ["Error processing transaction", "0.00", "", ""]


def format_transactions_for_sheets(transactions):
    """
    Formats multiple transactions for Google Sheets batch insertion.
    
    Args:
        transactions: List of transaction dictionaries
        
    Returns:
        list: List of rows formatted for Google Sheets
    """
    try:
        if not isinstance(transactions, list):
            logger.warning("Non-list provided to format_transactions_for_sheets")
            return []
        
        formatted_rows = []
        for transaction in transactions:
            formatted_row = format_transaction_for_sheets(transaction)
            formatted_rows.append(formatted_row)
        
        return formatted_rows
    
    except Exception as e:
        logger.error(f"Error formatting transactions batch: {str(e)}")
        return []


def format_budget_analysis_for_ai(budget_analysis):
    """
    Formats budget data for AI prompt generation.
    
    Args:
        budget_analysis: Dictionary containing budget analysis results
        
    Returns:
        str: Formatted budget analysis text for AI prompt
    """
    try:
        # Extract key values
        total_budget = budget_analysis.get('total_budget', Decimal('0'))
        total_spent = budget_analysis.get('total_spent', Decimal('0'))
        total_variance = budget_analysis.get('total_variance', Decimal('0'))
        category_analysis = budget_analysis.get('category_analysis', {})
        
        # Format as currency strings
        total_budget_str = format_currency(total_budget)
        total_spent_str = format_currency(total_spent)
        total_variance_str = format_currency(abs(total_variance))
        
        # Determine budget status
        status = "Surplus" if total_variance >= 0 else "Deficit"
        
        # Start with the overall budget status
        formatted_text = f"TOTAL BUDGET STATUS:\n"
        formatted_text += f"Total Budget: {total_budget_str}\n"
        formatted_text += f"Total Spent: {total_spent_str}\n"
        formatted_text += f"Variance: {total_variance_str} ({status})\n\n"
        
        # Add category breakdown
        formatted_text += "CATEGORY BREAKDOWN:\n"
        for category, details in category_analysis.items():
            budget_amount = format_currency(details.get('budget_amount', 0))
            actual_amount = format_currency(details.get('actual_amount', 0))
            variance_amount = details.get('variance_amount', 0)
            variance_percentage = details.get('variance_percentage', 0)
            
            # Format variance with sign
            if variance_amount >= 0:
                var_str = f"+{format_currency(variance_amount)}"
            else:
                var_str = format_currency(variance_amount)
            
            formatted_text += f"Category: {category}\n"
            formatted_text += f"Budget: {budget_amount}\n"
            formatted_text += f"Actual: {actual_amount}\n"
            formatted_text += f"Variance: {var_str} ({format_percentage(variance_percentage/100)})\n\n"
        
        return formatted_text
    
    except Exception as e:
        logger.error(f"Error formatting budget analysis for AI: {str(e)}")
        return "Error generating budget analysis text."


def truncate_text(text, max_length=100):
    """
    Truncates text to specified length with ellipsis.
    
    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        
    Returns:
        str: Truncated text with ellipsis if needed
    """
    try:
        if not isinstance(text, str):
            text = str(text)
        
        if len(text) <= max_length:
            return text
        
        return text[:max_length-3] + "..."
    
    except Exception as e:
        logger.error(f"Error truncating text: {str(e)}")
        return text[:max_length] if isinstance(text, str) else ""


def clean_html(html_content):
    """
    Sanitizes HTML content for email.
    
    Args:
        html_content: Raw HTML content to sanitize
        
    Returns:
        str: Sanitized HTML content
    """
    try:
        if not html_content:
            return ""
        
        # Use bleach to sanitize HTML
        sanitized = bleach.clean(
            html_content,
            tags=ALLOWED_HTML_TAGS,
            attributes=ALLOWED_HTML_ATTRIBUTES,
            strip=True
        )
        
        return sanitized
    
    except Exception as e:
        logger.error(f"Error sanitizing HTML: {str(e)}")
        # Return as plain text if sanitization fails
        return html.escape(html_content) if html_content else ""


def format_list_for_html(items):
    """
    Converts a list to HTML unordered list.
    
    Args:
        items: List of items to format as HTML
        
    Returns:
        str: HTML unordered list
    """
    try:
        if not items:
            return ""
        
        if not isinstance(items, list):
            items = [str(items)]
        
        # Create HTML list
        html_list = "<ul>\n"
        for item in items:
            html_list += f"  <li>{html.escape(str(item))}</li>\n"
        html_list += "</ul>"
        
        return html_list
    
    except Exception as e:
        logger.error(f"Error formatting list to HTML: {str(e)}")
        return ""


def format_dict_for_sheets(data):
    """
    Formats a dictionary for Google Sheets insertion.
    
    Args:
        data: Dictionary to format for Sheets
        
    Returns:
        list: List of [key, value] pairs for Sheets
    """
    try:
        if not isinstance(data, dict):
            logger.warning("Non-dictionary provided to format_dict_for_sheets")
            return []
        
        formatted_rows = []
        for key, value in data.items():
            # Format values appropriately
            if isinstance(value, Decimal):
                formatted_value = f"{value:.2f}"
            elif isinstance(value, (int, float)):
                formatted_value = str(value)
            else:
                formatted_value = str(value)
            
            formatted_rows.append([str(key), formatted_value])
        
        return formatted_rows
    
    except Exception as e:
        logger.error(f"Error formatting dictionary for sheets: {str(e)}")
        return []