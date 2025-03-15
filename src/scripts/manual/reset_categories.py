#!/usr/bin/env python3
"""
reset_categories.py - Utility script to reset category assignments in the Weekly Spending sheet

This script allows users to reset or clear all category assignments in the Weekly Spending sheet.
This is useful for troubleshooting, testing the categorization process, or starting fresh with
transaction categorization when the automated AI categorization needs to be redone.
"""

import os
import sys
import argparse
from typing import List, Dict, Optional, Any

from colorama import Fore, Style, init

# Internal imports
from ..config.logging_setup import get_logger
from ..config.script_settings import SCRIPT_SETTINGS
from ..utils.sheet_operations import (
    get_sheets_service, read_sheet, write_sheet, 
    clear_sheet_range, create_backup_sheet
)

# Set up logger
logger = get_logger(__name__)

# Default values
DEFAULT_WEEKLY_SPENDING_SHEET_ID = os.getenv('WEEKLY_SPENDING_SHEET_ID')
WEEKLY_SPENDING_SHEET_NAME = "Weekly Spending"
TRANSACTION_CATEGORY_COL = 3  # 0-based index for the category column (typically column D)

def reset_categories(spreadsheet_id: str, create_backup: bool = True, service=None) -> int:
    """
    Resets all category assignments in the Weekly Spending sheet
    
    Args:
        spreadsheet_id: ID of the Google Sheet containing Weekly Spending
        create_backup: Whether to create a backup before making changes
        service: Google Sheets API service (will be created if None)
        
    Returns:
        Number of transactions affected
    """
    logger.info(f"Starting reset of all category assignments in sheet {spreadsheet_id}")
    
    # Get sheets service if not provided
    if service is None:
        service = get_sheets_service()
    
    # Create backup if requested
    if create_backup:
        backup_name = create_backup_sheet(spreadsheet_id, WEEKLY_SPENDING_SHEET_NAME, service)
        logger.info(f"Created backup sheet: {backup_name}")
    
    # Read data from Weekly Spending sheet
    data = read_sheet(spreadsheet_id, f"{WEEKLY_SPENDING_SHEET_NAME}!A:D", service)
    
    if not data or len(data) <= 1:  # If no data or only header row
        logger.warning("No transaction data found in Weekly Spending sheet")
        return 0
    
    # Count transactions with categories assigned
    transactions_with_categories = 0
    for i in range(1, len(data)):  # Skip header row
        row = data[i]
        if len(row) > TRANSACTION_CATEGORY_COL and row[TRANSACTION_CATEGORY_COL]:
            transactions_with_categories += 1
            # Clear the category
            if len(row) <= TRANSACTION_CATEGORY_COL:
                row.extend([''] * (TRANSACTION_CATEGORY_COL + 1 - len(row)))
            row[TRANSACTION_CATEGORY_COL] = ''
    
    # Write updated data back to sheet
    write_sheet(spreadsheet_id, f"{WEEKLY_SPENDING_SHEET_NAME}!A1:D{len(data)}", data, service)
    
    logger.info(f"Reset {transactions_with_categories} category assignments")
    return transactions_with_categories

def reset_specific_category(spreadsheet_id: str, category: str, create_backup: bool = True, service=None) -> int:
    """
    Resets category assignments for transactions with a specific category
    
    Args:
        spreadsheet_id: ID of the Google Sheet containing Weekly Spending
        category: Category name to reset
        create_backup: Whether to create a backup before making changes
        service: Google Sheets API service (will be created if None)
        
    Returns:
        Number of transactions affected
    """
    logger.info(f"Starting reset of '{category}' category assignments in sheet {spreadsheet_id}")
    
    # Get sheets service if not provided
    if service is None:
        service = get_sheets_service()
    
    # Create backup if requested
    if create_backup:
        backup_name = create_backup_sheet(spreadsheet_id, WEEKLY_SPENDING_SHEET_NAME, service)
        logger.info(f"Created backup sheet: {backup_name}")
    
    # Read data from Weekly Spending sheet
    data = read_sheet(spreadsheet_id, f"{WEEKLY_SPENDING_SHEET_NAME}!A:D", service)
    
    if not data or len(data) <= 1:  # If no data or only header row
        logger.warning("No transaction data found in Weekly Spending sheet")
        return 0
    
    # Reset specific category
    affected_count = 0
    for i in range(1, len(data)):  # Skip header row
        row = data[i]
        if len(row) > TRANSACTION_CATEGORY_COL and row[TRANSACTION_CATEGORY_COL] == category:
            # Clear the category
            row[TRANSACTION_CATEGORY_COL] = ''
            affected_count += 1
    
    # Write updated data back to sheet
    write_sheet(spreadsheet_id, f"{WEEKLY_SPENDING_SHEET_NAME}!A1:D{len(data)}", data, service)
    
    logger.info(f"Reset {affected_count} transactions with category '{category}'")
    return affected_count

def confirm_reset(message: str) -> bool:
    """
    Prompts the user to confirm the reset operation
    
    Args:
        message: Confirmation message to display
        
    Returns:
        True if user confirms, False otherwise
    """
    print(f"{Fore.RED}{Style.BRIGHT}WARNING: This operation will reset category assignments and cannot be undone.{Style.RESET_ALL}")
    print(message)
    print(f"Type {Fore.YELLOW}'YES'{Style.RESET_ALL} to confirm: ", end="")
    
    confirmation = input().strip().upper()
    return confirmation == "YES"

def parse_arguments():
    """
    Parses command-line arguments for the script
    
    Returns:
        Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Reset transaction category assignments in the Weekly Spending sheet"
    )
    
    parser.add_argument(
        "--sheet-id",
        default=DEFAULT_WEEKLY_SPENDING_SHEET_ID,
        help="Google Sheet ID for Weekly Spending (default: from environment variable)"
    )
    
    parser.add_argument(
        "--credentials",
        help="Path to Google Sheets credentials file"
    )
    
    parser.add_argument(
        "--category",
        help="Specific category to reset (if not specified, all categories will be reset)"
    )
    
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating a backup sheet before making changes"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    return parser.parse_args()

def main() -> int:
    """
    Main entry point for the script
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Initialize colorama for cross-platform colored output
    init()
    
    try:
        # Parse command-line arguments
        args = parse_arguments()
        
        # Check if sheet ID is provided
        if not args.sheet_id:
            print(f"{Fore.RED}Error: No sheet ID provided. Set WEEKLY_SPENDING_SHEET_ID environment variable or use --sheet-id.{Style.RESET_ALL}")
            return 1
        
        # Get authenticated sheets service
        service = get_sheets_service(args.credentials)
        
        # Prepare reset message based on category
        if args.category:
            message = f"This will reset all transactions with category '{args.category}' in the Weekly Spending sheet."
        else:
            message = "This will reset ALL category assignments in the Weekly Spending sheet."
        
        # Confirm unless force flag is used
        if not args.force and not confirm_reset(message):
            print(f"{Fore.YELLOW}Operation cancelled.{Style.RESET_ALL}")
            return 1
        
        # Perform reset operation
        if args.category:
            affected = reset_specific_category(
                args.sheet_id,
                args.category,
                not args.no_backup,
                service
            )
        else:
            affected = reset_categories(
                args.sheet_id,
                not args.no_backup,
                service
            )
        
        # Print summary
        print(f"{Fore.GREEN}Successfully reset {affected} category assignments.{Style.RESET_ALL}")
        return 0
        
    except Exception as e:
        logger.error(f"Error during category reset: {str(e)}", exc_info=True)
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
        return 1

if __name__ == "__main__":
    sys.exit(main())