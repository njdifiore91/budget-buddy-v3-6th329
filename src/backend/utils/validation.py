"""
validation.py - Utility module providing validation functions for data integrity and error checking

This module implements validation functions for transactions, categories, budget data,
amounts, and API responses to ensure data consistency and reliability throughout
the Budget Management Application.
"""

import re  # standard library
import decimal  # standard library
from decimal import Decimal  # standard library
import datetime  # standard library
import logging  # standard library

from ..config.settings import APP_SETTINGS
from .error_handlers import ValidationError

# Set up logger
logger = logging.getLogger(__name__)

# Regular expression for email validation
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# Required fields for transaction validation
REQUIRED_TRANSACTION_FIELDS = ['location', 'amount', 'timestamp']


def is_valid_transaction(transaction):
    """
    Validates if a transaction dictionary has all required fields and correct data types.
    
    Args:
        transaction (dict): Transaction dictionary to validate
        
    Returns:
        bool: True if transaction is valid, False otherwise
    """
    # Check if transaction is a dictionary
    if not isinstance(transaction, dict):
        logger.warning("Transaction validation failed: Not a dictionary")
        return False
    
    # Check for required fields
    for field in REQUIRED_TRANSACTION_FIELDS:
        if field not in transaction:
            logger.warning(f"Transaction validation failed: Missing required field '{field}'")
            return False
    
    # Validate location is a non-empty string
    if not isinstance(transaction['location'], str) or not transaction['location'].strip():
        logger.warning("Transaction validation failed: Location must be a non-empty string")
        return False
    
    # Validate amount can be converted to Decimal and is not negative
    try:
        amount = Decimal(str(transaction['amount']))
        if amount < 0:
            logger.warning("Transaction validation failed: Amount cannot be negative")
            return False
    except (decimal.InvalidOperation, TypeError, ValueError):
        logger.warning("Transaction validation failed: Invalid amount format")
        return False
    
    # Validate timestamp is in a recognized format
    if isinstance(transaction['timestamp'], str):
        try:
            # Try to parse the timestamp string
            datetime.datetime.fromisoformat(transaction['timestamp'].replace('Z', '+00:00'))
        except ValueError:
            try:
                # Try other common date formats
                datetime.datetime.strptime(transaction['timestamp'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                logger.warning("Transaction validation failed: Invalid timestamp format")
                return False
    elif not isinstance(transaction['timestamp'], (datetime.datetime, datetime.date)):
        logger.warning("Transaction validation failed: Timestamp must be a datetime object or valid string")
        return False
    
    return True


def validate_transactions(transactions, raise_on_invalid=False):
    """
    Filters and validates a list of transactions, returning only valid ones.
    
    Args:
        transactions (list): List of transaction dictionaries to validate
        raise_on_invalid (bool): If True, raise ValidationError when invalid transactions found
        
    Returns:
        list: List of valid transactions
        
    Raises:
        ValidationError: If raise_on_invalid is True and invalid transactions are found
    """
    if not isinstance(transactions, list):
        logger.error("validate_transactions called with non-list argument")
        if raise_on_invalid:
            raise ValidationError("Transactions must be a list", "transactions")
        return []
    
    valid_transactions = []
    invalid_transactions = []
    
    for transaction in transactions:
        if is_valid_transaction(transaction):
            valid_transactions.append(transaction)
        else:
            invalid_transactions.append(transaction)
    
    if invalid_transactions:
        logger.warning(
            f"Found {len(invalid_transactions)} invalid transactions out of {len(transactions)} total",
            extra={"invalid_count": len(invalid_transactions), "total_count": len(transactions)}
        )
        
        if raise_on_invalid:
            raise ValidationError(
                f"{len(invalid_transactions)} invalid transactions found",
                "transactions",
                validation_errors={"invalid_count": len(invalid_transactions)}
            )
    
    return valid_transactions


def is_valid_category(category, valid_categories):
    """
    Checks if a category name exists in the master budget categories.
    
    Args:
        category (str): Category name to validate
        valid_categories (list): List of valid category names from master budget
        
    Returns:
        bool: True if category is valid, False otherwise
    """
    # Check if category is a non-empty string
    if not isinstance(category, str) or not category.strip():
        logger.warning("Category validation failed: Category must be a non-empty string")
        return False
    
    # Check if valid_categories is a list
    if not isinstance(valid_categories, list):
        logger.warning("Category validation failed: valid_categories must be a list")
        return False
    
    # Case-insensitive match against valid categories
    category_lower = category.lower().strip()
    valid_lower = [c.lower().strip() for c in valid_categories if isinstance(c, str)]
    
    if category_lower in valid_lower:
        return True
    
    logger.warning(f"Category validation failed: '{category}' not in valid categories list")
    return False


def validate_categorization_results(categorization_results, valid_categories, transaction_locations):
    """
    Validates AI categorization results against valid categories.
    
    Args:
        categorization_results (dict): Mapping of transaction locations to categories
        valid_categories (list): List of valid category names from master budget
        transaction_locations (list): List of transaction locations to categorize
        
    Returns:
        dict: Validated categorization results
        
    Raises:
        ValidationError: If categorization results are severely invalid
    """
    if not isinstance(categorization_results, dict):
        logger.error("Categorization results must be a dictionary")
        raise ValidationError("Categorization results must be a dictionary", "categorization")
    
    # Check for missing transactions
    missing_locations = set(transaction_locations) - set(categorization_results.keys())
    if missing_locations:
        logger.warning(f"Missing categories for {len(missing_locations)} transaction locations")
    
    # Validate each assigned category
    valid_results = {}
    invalid_assignments = {}
    
    for location, category in categorization_results.items():
        if is_valid_category(category, valid_categories):
            valid_results[location] = category
        else:
            invalid_assignments[location] = category
            logger.warning(f"Invalid category assignment: '{location}' -> '{category}'")
    
    if invalid_assignments:
        logger.warning(
            f"Found {len(invalid_assignments)} invalid category assignments out of {len(categorization_results)} total",
            extra={"invalid_count": len(invalid_assignments), "total_count": len(categorization_results)}
        )
    
    return valid_results


def is_categorization_successful(categorization_results, transaction_locations, threshold=None):
    """
    Determines if categorization met the success threshold.
    
    Args:
        categorization_results (dict): Mapping of transaction locations to categories
        transaction_locations (list): List of all transaction locations that needed categorization
        threshold (float, optional): Success threshold percentage (0.0-1.0)
        
    Returns:
        bool: True if categorization success rate meets threshold
    """
    if threshold is None:
        threshold = APP_SETTINGS.get('CATEGORIZATION_THRESHOLD', 0.95)
    
    if not transaction_locations:
        logger.warning("No transaction locations provided for categorization success check")
        return False
    
    # Calculate success percentage
    categorized_count = len(categorization_results)
    total_count = len(transaction_locations)
    
    if total_count == 0:
        return False
    
    success_rate = categorized_count / total_count
    
    logger.info(
        f"Categorization success rate: {success_rate:.2%} ({categorized_count}/{total_count})",
        extra={"success_rate": success_rate, "threshold": threshold}
    )
    
    return success_rate >= threshold


def is_valid_amount(amount):
    """
    Validates if a string or number can be converted to a valid Decimal amount.
    
    Args:
        amount: Value to validate (string, int, float, or Decimal)
        
    Returns:
        bool: True if amount is valid, False otherwise
    """
    try:
        # Try to convert to Decimal
        decimal_amount = Decimal(str(amount)) if not isinstance(amount, Decimal) else amount
        
        # Check if not negative
        if decimal_amount < 0:
            logger.warning(f"Amount validation failed: Amount cannot be negative ({amount})")
            return False
        
        return True
    except (decimal.InvalidOperation, TypeError, ValueError):
        logger.warning(f"Amount validation failed: Cannot convert to Decimal ({amount})")
        return False


def parse_amount(amount):
    """
    Parses a string or number into a Decimal object for financial calculations.
    
    Args:
        amount: Value to parse (string, int, float, or Decimal)
        
    Returns:
        decimal.Decimal: Parsed amount as Decimal
        
    Raises:
        ValueError: If amount cannot be parsed as Decimal
    """
    # If already a Decimal, return it
    if isinstance(amount, Decimal):
        return amount
    
    # Handle string amounts (possibly with currency symbols)
    if isinstance(amount, str):
        # Remove currency symbols, commas, etc.
        clean_amount = amount.strip().replace('$', '').replace(',', '')
        try:
            return Decimal(clean_amount)
        except decimal.InvalidOperation:
            raise ValueError(f"Could not parse '{amount}' as Decimal")
    
    # Handle numeric types
    if isinstance(amount, (int, float)):
        return Decimal(str(amount))
    
    # If we get here, the type is not supported
    raise ValueError(f"Unsupported type for amount: {type(amount)}")


def is_valid_email(email):
    """
    Validates an email address format using regex.
    
    Args:
        email (str): Email address to validate
        
    Returns:
        bool: True if email format is valid, False otherwise
    """
    if not isinstance(email, str):
        return False
    
    return bool(EMAIL_REGEX.match(email))


def validate_email_list(emails, raise_on_invalid=False):
    """
    Filters and validates a list of email addresses.
    
    Args:
        emails (list): List of email addresses to validate
        raise_on_invalid (bool): If True, raise ValidationError when invalid emails found
        
    Returns:
        list: List of valid email addresses
        
    Raises:
        ValidationError: If raise_on_invalid is True and invalid emails are found
    """
    if not isinstance(emails, list):
        logger.error("validate_email_list called with non-list argument")
        if raise_on_invalid:
            raise ValidationError("Emails must be a list", "emails")
        return []
    
    valid_emails = []
    invalid_emails = []
    
    for email in emails:
        if is_valid_email(email):
            valid_emails.append(email)
        else:
            invalid_emails.append(email)
    
    if invalid_emails:
        logger.warning(
            f"Found {len(invalid_emails)} invalid email addresses out of {len(emails)} total",
            extra={"invalid_count": len(invalid_emails), "total_count": len(emails)}
        )
        
        if raise_on_invalid:
            raise ValidationError(
                f"{len(invalid_emails)} invalid email addresses found",
                "emails",
                validation_errors={"invalid_emails": invalid_emails}
            )
    
    return valid_emails


def is_valid_transfer_amount(amount, min_amount=None):
    """
    Validates if an amount is valid for savings transfer.
    
    Args:
        amount: Transfer amount to validate
        min_amount (decimal.Decimal, optional): Minimum allowed transfer amount
        
    Returns:
        bool: True if transfer amount is valid, False otherwise
    """
    # Use default from settings if not provided
    if min_amount is None:
        min_amount = APP_SETTINGS.get('MIN_TRANSFER_AMOUNT', Decimal('1.00'))
    
    try:
        # Parse the amount to Decimal
        decimal_amount = parse_amount(amount)
        
        # Check minimum transfer amount
        if decimal_amount < min_amount:
            logger.warning(
                f"Transfer amount ({decimal_amount}) below minimum ({min_amount})",
                extra={"amount": str(decimal_amount), "min_amount": str(min_amount)}
            )
            return False
        
        return True
    except ValueError:
        logger.warning(f"Invalid transfer amount format: {amount}")
        return False


def validate_budget_data(budget_data):
    """
    Validates budget data structure and values.
    
    Args:
        budget_data (dict): Budget data to validate
        
    Returns:
        bool: True if budget data is valid, False otherwise
    """
    if not isinstance(budget_data, dict):
        logger.error("Budget data must be a dictionary")
        return False
    
    # Check for required keys
    required_keys = ['categories', 'amounts']
    for key in required_keys:
        if key not in budget_data:
            logger.warning(f"Budget data validation failed: Missing required key '{key}'")
            return False
    
    categories = budget_data.get('categories', [])
    amounts = budget_data.get('amounts', {})
    
    # Validate categories is a list of strings
    if not isinstance(categories, list):
        logger.warning("Budget data validation failed: 'categories' must be a list")
        return False
    
    # Validate each category is a non-empty string
    for category in categories:
        if not isinstance(category, str) or not category.strip():
            logger.warning("Budget data validation failed: Each category must be a non-empty string")
            return False
    
    # Validate amounts is a dictionary
    if not isinstance(amounts, dict):
        logger.warning("Budget data validation failed: 'amounts' must be a dictionary")
        return False
    
    # Validate each amount can be converted to Decimal and is not negative
    for category, amount in amounts.items():
        try:
            decimal_amount = Decimal(str(amount))
            if decimal_amount < 0:
                logger.warning(f"Budget data validation failed: Amount for '{category}' cannot be negative")
                return False
        except (decimal.InvalidOperation, TypeError, ValueError):
            logger.warning(f"Budget data validation failed: Invalid amount format for '{category}'")
            return False
    
    return True


def validate_api_response(response, required_fields, api_name):
    """
    Validates API response structure against expected schema.
    
    Args:
        response (dict): API response to validate
        required_fields (list): List of required field names
        api_name (str): Name of the API for logging purposes
        
    Returns:
        bool: True if response is valid, False otherwise
    """
    if not isinstance(response, dict):
        logger.error(f"{api_name} API response validation failed: Response is not a dictionary")
        return False
    
    # Check all required fields are present
    missing_fields = [field for field in required_fields if field not in response]
    
    if missing_fields:
        logger.warning(
            f"{api_name} API response validation failed: Missing required fields {missing_fields}",
            extra={"missing_fields": missing_fields, "api_name": api_name}
        )
        return False
    
    logger.debug(f"{api_name} API response validation successful")
    return True


def is_duplicate_transaction(transaction, existing_transactions):
    """
    Checks if a transaction is a duplicate of another based on key attributes.
    
    Args:
        transaction (dict): Transaction to check
        existing_transactions (list): List of existing transactions to check against
        
    Returns:
        bool: True if transaction is a duplicate, False otherwise
    """
    if not is_valid_transaction(transaction):
        return False
    
    # Extract key attributes for comparison
    loc = transaction['location'].strip().lower()
    amt = Decimal(str(transaction['amount']))
    
    # Normalize timestamp for comparison
    if isinstance(transaction['timestamp'], str):
        try:
            # Try to parse as ISO format
            ts = datetime.datetime.fromisoformat(transaction['timestamp'].replace('Z', '+00:00'))
        except ValueError:
            try:
                # Try other format
                ts = datetime.datetime.strptime(transaction['timestamp'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                # If parsing fails, use string comparison
                ts = transaction['timestamp']
    else:
        ts = transaction['timestamp']
    
    # Check against existing transactions
    for existing in existing_transactions:
        if not is_valid_transaction(existing):
            continue
        
        # Compare key attributes
        existing_loc = existing['location'].strip().lower()
        existing_amt = Decimal(str(existing['amount']))
        
        # Normalize existing timestamp
        if isinstance(existing['timestamp'], str):
            try:
                existing_ts = datetime.datetime.fromisoformat(existing['timestamp'].replace('Z', '+00:00'))
            except ValueError:
                try:
                    existing_ts = datetime.datetime.strptime(existing['timestamp'], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    existing_ts = existing['timestamp']
        else:
            existing_ts = existing['timestamp']
        
        # Compare all attributes
        if loc == existing_loc and amt == existing_amt:
            # For timestamps, if they're datetime objects, compare just the date
            if isinstance(ts, datetime.datetime) and isinstance(existing_ts, datetime.datetime):
                if ts.date() == existing_ts.date():
                    return True
            # Otherwise compare directly
            elif ts == existing_ts:
                return True
    
    return False


def filter_duplicates(transactions):
    """
    Removes duplicate transactions from a list.
    
    Args:
        transactions (list): List of transaction dictionaries
        
    Returns:
        list: List with duplicates removed
    """
    if not isinstance(transactions, list):
        logger.error("filter_duplicates called with non-list argument")
        return []
    
    unique_transactions = []
    
    for transaction in transactions:
        if not is_duplicate_transaction(transaction, unique_transactions):
            unique_transactions.append(transaction)
    
    duplicates_count = len(transactions) - len(unique_transactions)
    if duplicates_count > 0:
        logger.info(f"Removed {duplicates_count} duplicate transactions")
    
    return unique_transactions


def validate_calculation_results(category_totals, category_variances, total_budget, total_spent, total_variance):
    """
    Verifies mathematical accuracy of budget calculations.
    
    Args:
        category_totals (dict): Dictionary mapping categories to spent amounts
        category_variances (dict): Dictionary mapping categories to variance amounts
        total_budget (decimal.Decimal): Total budget amount
        total_spent (decimal.Decimal): Total spent amount
        total_variance (decimal.Decimal): Total variance amount
        
    Returns:
        bool: True if calculations are accurate, False otherwise
    """
    # Convert all values to Decimal for precise comparison
    try:
        if not isinstance(total_budget, Decimal):
            total_budget = Decimal(str(total_budget))
        
        if not isinstance(total_spent, Decimal):
            total_spent = Decimal(str(total_spent))
        
        if not isinstance(total_variance, Decimal):
            total_variance = Decimal(str(total_variance))
        
        # Calculate sum of category totals
        calculated_total_spent = sum(Decimal(str(amount)) for amount in category_totals.values())
        
        # Calculate sum of category variances
        calculated_total_variance = sum(Decimal(str(amount)) for amount in category_variances.values())
        
        # Calculate expected total variance
        expected_total_variance = total_budget - total_spent
        
        # Allow for small rounding differences (less than 1 cent)
        epsilon = Decimal('0.01')
        
        # Verify calculations
        if abs(calculated_total_spent - total_spent) >= epsilon:
            logger.warning(
                f"Sum of category totals ({calculated_total_spent}) doesn't match total spent ({total_spent})",
                extra={"difference": str(abs(calculated_total_spent - total_spent))}
            )
            return False
        
        if abs(expected_total_variance - total_variance) >= epsilon:
            logger.warning(
                f"Calculated total variance ({expected_total_variance}) doesn't match reported total variance ({total_variance})",
                extra={"difference": str(abs(expected_total_variance - total_variance))}
            )
            return False
        
        if abs(calculated_total_variance - total_variance) >= epsilon:
            logger.warning(
                f"Sum of category variances ({calculated_total_variance}) doesn't match total variance ({total_variance})",
                extra={"difference": str(abs(calculated_total_variance - total_variance))}
            )
            return False
        
        return True
    
    except (decimal.InvalidOperation, TypeError, ValueError) as e:
        logger.error(f"Error during calculation validation: {str(e)}")
        return False