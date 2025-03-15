#!/usr/bin/env python3
"""
Utility script for validating the structure and content of budget data in the Budget Management Application.

This script validates Master Budget and Weekly Spending sheets to ensure they conform to expected
formats and contain valid data before being used in the main application.
"""

import os
import sys
import argparse
import decimal
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any

# Internal imports
from ..config.logging_setup import get_logger
from ..config.script_settings import SCRIPT_SETTINGS
from .sheet_operations import get_sheets_service, read_sheet, validate_sheet_structure
from ...backend.models.category import Category, create_categories_from_sheet_data
from ...backend.utils.validation import is_valid_amount, validate_budget_data

# Set up logger
logger = get_logger(__name__)

# Expected headers for sheets
MASTER_BUDGET_EXPECTED_HEADERS = ['Spending Category', 'Weekly Amount']
WEEKLY_SPENDING_EXPECTED_HEADERS = ['Transaction Location', 'Transaction Amount', 'Transaction Time', 'Corresponding Category']


def validate_master_budget(spreadsheet_id: str, range_name: str, service=None) -> Tuple[bool, List[str]]:
    """
    Validates the structure and content of the Master Budget sheet.
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        range_name: Range to validate (e.g., 'Master Budget!A1:B')
        service: Google Sheets API service (will be created if None)
        
    Returns:
        Tuple of (success, errors) where success is a boolean and errors is a list of error messages
    """
    errors = []
    
    # Get sheets service if not provided
    if service is None:
        service = get_sheets_service()
    
    # Read data from sheet
    data = read_sheet(spreadsheet_id, range_name, service)
    
    # Validate sheet structure (headers)
    if not validate_sheet_structure(spreadsheet_id, range_name, MASTER_BUDGET_EXPECTED_HEADERS, service):
        errors.append(f"Master Budget sheet does not have the expected headers: {MASTER_BUDGET_EXPECTED_HEADERS}")
        return False, errors
    
    # Check if there's data beyond headers
    if len(data) <= 1:
        errors.append("Master Budget sheet has no data beyond headers")
        return False, errors
    
    # Validate each row
    categories = set()
    for i, row in enumerate(data[1:], start=2):  # Start from row 2 (after header)
        if len(row) < 2:
            errors.append(f"Row {i} in Master Budget does not have enough columns")
            continue
        
        # Validate category name
        category_name = row[0]
        if not category_name or not isinstance(category_name, str) or not category_name.strip():
            errors.append(f"Row {i} has an invalid category name: {category_name}")
        
        # Check for duplicate categories
        if category_name in categories:
            errors.append(f"Duplicate category found: {category_name}")
        else:
            categories.add(category_name)
        
        # Validate amount
        amount = row[1]
        try:
            if not is_valid_amount(amount):
                errors.append(f"Row {i} has an invalid amount: {amount}")
        except (decimal.InvalidOperation, ValueError) as e:
            errors.append(f"Row {i} has an invalid amount format: {amount}, Error: {str(e)}")
    
    # Return success (True if no errors) and list of errors
    return len(errors) == 0, errors


def validate_weekly_spending(spreadsheet_id: str, range_name: str, valid_categories: List[str], service=None) -> Tuple[bool, List[str]]:
    """
    Validates the structure and content of the Weekly Spending sheet.
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        range_name: Range to validate (e.g., 'Weekly Spending!A1:D')
        valid_categories: List of valid category names from Master Budget
        service: Google Sheets API service (will be created if None)
        
    Returns:
        Tuple of (success, errors) where success is a boolean and errors is a list of error messages
    """
    errors = []
    
    # Get sheets service if not provided
    if service is None:
        service = get_sheets_service()
    
    # Read data from sheet
    data = read_sheet(spreadsheet_id, range_name, service)
    
    # Validate sheet structure (headers)
    if not validate_sheet_structure(spreadsheet_id, range_name, WEEKLY_SPENDING_EXPECTED_HEADERS, service):
        errors.append(f"Weekly Spending sheet does not have the expected headers: {WEEKLY_SPENDING_EXPECTED_HEADERS}")
        return False, errors
    
    # Check if there's data beyond headers
    if len(data) <= 1:
        # This is not necessarily an error for Weekly Spending, as it might be empty at the start of a week
        logger.warning("Weekly Spending sheet has no data beyond headers")
    
    # Validate each row
    for i, row in enumerate(data[1:], start=2):  # Start from row 2 (after header)
        if len(row) < 3:
            errors.append(f"Row {i} in Weekly Spending does not have enough columns")
            continue
        
        # Validate location
        location = row[0]
        if not location or not isinstance(location, str) or not location.strip():
            errors.append(f"Row {i} has an invalid transaction location: {location}")
        
        # Validate amount
        amount = row[1]
        try:
            if not is_valid_amount(amount):
                errors.append(f"Row {i} has an invalid amount: {amount}")
        except (decimal.InvalidOperation, ValueError) as e:
            errors.append(f"Row {i} has an invalid amount format: {amount}, Error: {str(e)}")
        
        # Validate timestamp
        timestamp = row[2]
        if not timestamp:
            errors.append(f"Row {i} has a missing timestamp")
        
        # Validate category if present
        if len(row) > 3 and row[3]:
            category = row[3]
            if category not in valid_categories:
                errors.append(f"Row {i} has an invalid category: {category} (not in Master Budget)")
    
    # Return success (True if no errors) and list of errors
    return len(errors) == 0, errors


def validate_budget_consistency(master_budget_id: str, master_budget_range: str, 
                               weekly_spending_id: str, weekly_spending_range: str, 
                               service=None) -> Tuple[bool, List[str]]:
    """
    Validates consistency between Master Budget and Weekly Spending sheets.
    
    Args:
        master_budget_id: ID of the Master Budget spreadsheet
        master_budget_range: Range for Master Budget data
        weekly_spending_id: ID of the Weekly Spending spreadsheet
        weekly_spending_range: Range for Weekly Spending data
        service: Google Sheets API service (will be created if None)
        
    Returns:
        Tuple of (success, errors) where success is a boolean and errors is a list of error messages
    """
    errors = []
    
    # Get sheets service if not provided
    if service is None:
        service = get_sheets_service()
    
    # Validate Master Budget
    master_budget_valid, master_budget_errors = validate_master_budget(master_budget_id, master_budget_range, service)
    errors.extend(master_budget_errors)
    
    if not master_budget_valid:
        logger.error("Master Budget validation failed, cannot validate consistency")
        return False, errors
    
    # Get valid categories from Master Budget
    master_budget_data = read_sheet(master_budget_id, master_budget_range, service)
    valid_categories = [row[0] for row in master_budget_data[1:] if len(row) > 0 and row[0]]
    
    # Validate Weekly Spending with valid categories
    weekly_spending_valid, weekly_spending_errors = validate_weekly_spending(
        weekly_spending_id, weekly_spending_range, valid_categories, service
    )
    errors.extend(weekly_spending_errors)
    
    # Return success (True if no errors) and list of errors
    return len(errors) == 0, errors


def print_validation_results(is_valid: bool, errors: List[str], sheet_name: str) -> None:
    """
    Prints validation results in a user-friendly format.
    
    Args:
        is_valid: Whether validation passed
        errors: List of validation errors
        sheet_name: Name of the sheet being validated
    """
    print(f"\n{'=' * 80}")
    print(f" VALIDATION RESULTS FOR {sheet_name.upper()}")
    print(f"{'=' * 80}")
    
    if is_valid:
        print(f"\n✅ {sheet_name} validation PASSED! No errors found.\n")
    else:
        print(f"\n❌ {sheet_name} validation FAILED with {len(errors)} errors:\n")
        for i, error in enumerate(errors, start=1):
            print(f"  {i}. {error}")
    
    print(f"\n{'=' * 80}\n")


def parse_arguments():
    """
    Parses command-line arguments for the script.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Validate budget data structure and content in Google Sheets"
    )
    
    parser.add_argument(
        "--master-budget-id",
        help="Google Sheets spreadsheet ID for the Master Budget",
        required=True
    )
    
    parser.add_argument(
        "--master-budget-range",
        help="Range for Master Budget data (e.g., 'Master Budget!A1:B')",
        default="Master Budget!A1:B"
    )
    
    parser.add_argument(
        "--weekly-spending-id",
        help="Google Sheets spreadsheet ID for the Weekly Spending",
        required=True
    )
    
    parser.add_argument(
        "--weekly-spending-range",
        help="Range for Weekly Spending data (e.g., 'Weekly Spending!A1:D')",
        default="Weekly Spending!A1:D"
    )
    
    parser.add_argument(
        "--credentials",
        help="Path to Google Sheets API credentials file",
        default=None
    )
    
    parser.add_argument(
        "--verbose",
        help="Show detailed validation output",
        action="store_true"
    )
    
    return parser.parse_args()


def main() -> int:
    """
    Main function to run the budget validation script.
    
    Returns:
        Exit code (0 for success, 1 for validation failure, 2 for errors)
    """
    # Parse command-line arguments
    args = parse_arguments()
    
    try:
        # Get sheets service with provided credentials
        service = get_sheets_service(args.credentials)
        
        # Validate budget consistency
        is_valid, errors = validate_budget_consistency(
            args.master_budget_id,
            args.master_budget_range,
            args.weekly_spending_id,
            args.weekly_spending_range,
            service
        )
        
        # Print validation results
        print_validation_results(is_valid, errors, "Budget Data")
        
        if SCRIPT_SETTINGS.get('DEBUG') or args.verbose:
            logger.info(f"Validation completed with result: {is_valid}")
            if not is_valid:
                for error in errors:
                    logger.warning(f"Validation error: {error}")
        
        # Return exit code based on validation result
        return 0 if is_valid else 1
        
    except Exception as e:
        error_message = f"Error validating budget data: {str(e)}"
        logger.error(error_message, exc_info=True)
        print(f"Error: {error_message}")
        return 2


if __name__ == "__main__":
    sys.exit(main())