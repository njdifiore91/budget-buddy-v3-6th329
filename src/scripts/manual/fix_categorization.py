#!/usr/bin/env python
"""
Utility script that provides a command-line interface for fixing incorrectly categorized transactions
in the Budget Management Application. This script allows users to select specific transactions and 
update their categories when the automated AI categorization has assigned incorrect categories.

Usage:
    python fix_categorization.py [--weekly-spending-id SHEET_ID] [--master-budget-id SHEET_ID] [--credentials PATH]
"""

import os
import sys
import argparse
import pandas as pd
from typing import List, Dict, Optional, Tuple
from tabulate import tabulate
from colorama import Fore, Style, init as colorama_init

# Internal imports
from ..config.logging_setup import get_logger
from ..config.script_settings import SCRIPT_SETTINGS, MAX_RETRIES
from ..utils.sheet_operations import (
    get_sheets_service, read_sheet, write_sheet, get_sheet_as_dataframe
)
from ..utils.categorize_manually import (
    get_valid_categories, display_categories, prompt_for_category
)
from ...backend.models.transaction import (
    Transaction, create_transactions_from_sheet_data
)
from ...backend.utils.validation import is_valid_category

# Configure logger
logger = get_logger(__name__)

# Default sheet IDs from environment variables
DEFAULT_WEEKLY_SPENDING_SHEET_ID = os.getenv('WEEKLY_SPENDING_SHEET_ID')
DEFAULT_MASTER_BUDGET_SHEET_ID = os.getenv('MASTER_BUDGET_SHEET_ID')

# Constants for sheet names and column indices
WEEKLY_SPENDING_SHEET_NAME = "Weekly Spending"
MASTER_BUDGET_SHEET_NAME = "Master Budget"
TRANSACTION_LOCATION_COL = 0
TRANSACTION_AMOUNT_COL = 1
TRANSACTION_TIME_COL = 2
TRANSACTION_CATEGORY_COL = 3

def get_categorized_transactions(spreadsheet_id: str, service) -> List[Transaction]:
    """
    Retrieves transactions with assigned categories from the Weekly Spending sheet
    
    Args:
        spreadsheet_id: ID of the Weekly Spending spreadsheet
        service: Google Sheets API service
        
    Returns:
        List of categorized Transaction objects
    """
    logger.info("Retrieving categorized transactions")
    
    # Read data from the Weekly Spending sheet
    data = read_sheet(spreadsheet_id, f"{WEEKLY_SPENDING_SHEET_NAME}!A:D", service)
    
    # Skip header row and create Transaction objects
    if len(data) <= 1:  # Only header or empty
        logger.warning("No transaction data found in Weekly Spending sheet")
        return []
    
    # Create Transaction objects from the sheet data (skipping header)
    transactions = create_transactions_from_sheet_data(data[1:])
    
    # Filter out transactions that don't have categories
    categorized = [t for t in transactions if t.category]
    
    logger.info(f"Found {len(categorized)} categorized transactions")
    return categorized

def display_transaction_with_category(transaction: Transaction, index: int):
    """
    Displays a transaction with its current category in the terminal
    
    Args:
        transaction: Transaction object to display
        index: Index of the transaction in the list
    """
    # Format the transaction details with colors
    location = Fore.CYAN + transaction.location + Style.RESET_ALL
    amount = Fore.YELLOW + f"${transaction.amount:.2f}" + Style.RESET_ALL
    timestamp = Fore.WHITE + str(transaction.timestamp) + Style.RESET_ALL
    category = Fore.GREEN + transaction.category + Style.RESET_ALL
    
    # Display transaction details
    print(f"\nTransaction #{index + 1}:")
    print(f"  Location: {location}")
    print(f"  Amount:   {amount}")
    print(f"  Time:     {timestamp}")
    print(f"  Current Category: {category}")

def select_transaction(transactions: List[Transaction]) -> Optional[Tuple[int, Transaction]]:
    """
    Prompts the user to select a transaction to fix
    
    Args:
        transactions: List of Transaction objects
        
    Returns:
        Selected transaction index and object, or None if cancelled
    """
    print("\nSelect a transaction to fix (enter number, or 'q' to quit):")
    
    while True:
        selection = input("> ").strip()
        
        # Check if the user wants to quit
        if selection.lower() == 'q':
            return None
        
        # Try to interpret as a number (index)
        try:
            index = int(selection) - 1  # Adjust for 1-based user input to 0-based index
            if 0 <= index < len(transactions):
                return (index, transactions[index])
            else:
                print(f"Invalid selection. Please enter a number between 1 and {len(transactions)}")
        except ValueError:
            print("Invalid input. Please enter a transaction number or 'q' to quit")

def update_transaction_category(transaction: Transaction, new_category: str, 
                               spreadsheet_id: str, service) -> bool:
    """
    Updates a transaction's category in the Weekly Spending sheet
    
    Args:
        transaction: Transaction object to update
        new_category: New category to assign
        spreadsheet_id: ID of the Weekly Spending spreadsheet
        service: Google Sheets API service
        
    Returns:
        True if update was successful, False otherwise
    """
    logger.info(f"Updating category for transaction: {transaction.location} from {transaction.category} to {new_category}")
    
    try:
        # Read data from the Weekly Spending sheet to find the row for this transaction
        data = read_sheet(spreadsheet_id, f"{WEEKLY_SPENDING_SHEET_NAME}!A:D", service)
        
        # Skip header row
        if len(data) <= 1:
            logger.error("No transaction data found in Weekly Spending sheet")
            return False
        
        # Find the row that matches this transaction (by location and time)
        row_index = None
        for i, row in enumerate(data[1:], start=2):  # Start at row 2 (after header)
            if (len(row) > TRANSACTION_TIME_COL and 
                row[TRANSACTION_LOCATION_COL] == transaction.location and
                str(row[TRANSACTION_TIME_COL]) == str(transaction.timestamp)):
                row_index = i
                break
        
        if row_index is None:
            logger.error(f"Could not find transaction in sheet: {transaction.location}")
            return False
        
        # Ensure row has enough cells
        while len(data[row_index-1]) <= TRANSACTION_CATEGORY_COL:
            data[row_index-1].append("")
        
        # Update the category in the data
        data[row_index-1][TRANSACTION_CATEGORY_COL] = new_category
        
        # Write the updated row back to the sheet
        range_name = f"{WEEKLY_SPENDING_SHEET_NAME}!A{row_index}:D{row_index}"
        write_sheet(spreadsheet_id, range_name, [data[row_index-1]], service)
        
        logger.info(f"Successfully updated category for transaction at row {row_index}")
        return True
    
    except Exception as e:
        logger.error(f"Error updating transaction category: {str(e)}")
        return False

def fix_transaction_categories(weekly_spending_id: str, master_budget_id: str, 
                              credentials_path: str) -> int:
    """
    Main function to interactively fix transaction categories
    
    Args:
        weekly_spending_id: ID of the Weekly Spending spreadsheet
        master_budget_id: ID of the Master Budget spreadsheet
        credentials_path: Path to Google Sheets credentials file
        
    Returns:
        Number of transactions fixed
    """
    logger.info("Starting category fixing process")
    
    # Get authenticated service
    service = get_sheets_service(credentials_path)
    
    # Get categorized transactions
    transactions = get_categorized_transactions(weekly_spending_id, service)
    
    if not transactions:
        print("No categorized transactions found!")
        return 0
    
    # Get valid categories
    valid_categories = get_valid_categories(master_budget_id, service)
    
    if not valid_categories:
        print("No valid categories found in Master Budget!")
        return 0
    
    # Display valid categories for reference
    display_categories(valid_categories)
    
    # Initialize counter for fixed transactions
    fixed_count = 0
    
    # Display all transactions with their current categories
    print("\nCategorized Transactions:")
    for i, transaction in enumerate(transactions):
        print(f"{i+1}. {transaction.location} - ${transaction.amount:.2f} - {transaction.category}")
    
    # Enter interactive loop
    while True:
        # Prompt user to select a transaction
        selection = select_transaction(transactions)
        
        if selection is None:
            # User chose to quit
            break
        
        index, transaction = selection
        
        # Display the selected transaction details
        display_transaction_with_category(transaction, index)
        
        # Prompt for new category
        print("\nSelect a new category (or 's' to skip):")
        new_category = prompt_for_category(valid_categories)
        
        if new_category and new_category != transaction.category:
            # Update the transaction with the new category
            if update_transaction_category(transaction, new_category, weekly_spending_id, service):
                transaction.set_category(new_category)
                fixed_count += 1
                print(f"{Fore.GREEN}Category updated successfully!{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Failed to update category.{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}Skipped or same category selected.{Style.RESET_ALL}")
    
    logger.info(f"Completed category fixing: {fixed_count} transactions updated")
    return fixed_count

def parse_arguments():
    """
    Parses command-line arguments for the script
    
    Returns:
        Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Fix incorrectly categorized transactions in the Weekly Spending sheet"
    )
    
    parser.add_argument(
        "--weekly-spending-id",
        default=DEFAULT_WEEKLY_SPENDING_SHEET_ID,
        help="Google Sheet ID for the Weekly Spending sheet"
    )
    
    parser.add_argument(
        "--master-budget-id",
        default=DEFAULT_MASTER_BUDGET_SHEET_ID,
        help="Google Sheet ID for the Master Budget sheet"
    )
    
    parser.add_argument(
        "--credentials",
        help="Path to Google Sheets credentials JSON file"
    )
    
    return parser.parse_args()

def main():
    """
    Main entry point for the script
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Initialize colorama for cross-platform colored output
    colorama_init()
    
    try:
        # Parse command-line arguments
        args = parse_arguments()
        
        # Validate required args
        if not args.weekly_spending_id:
            print(f"{Fore.RED}Error: Weekly Spending Sheet ID is required.{Style.RESET_ALL}")
            print("Provide it via --weekly-spending-id argument or WEEKLY_SPENDING_SHEET_ID environment variable.")
            return 1
        
        if not args.master_budget_id:
            print(f"{Fore.RED}Error: Master Budget Sheet ID is required.{Style.RESET_ALL}")
            print("Provide it via --master-budget-id argument or MASTER_BUDGET_SHEET_ID environment variable.")
            return 1
        
        # Call the main category fixing function
        fixed_count = fix_transaction_categories(
            args.weekly_spending_id,
            args.master_budget_id,
            args.credentials
        )
        
        # Print summary
        print(f"\n{Fore.GREEN}Category fixing complete!{Style.RESET_ALL}")
        print(f"Fixed {fixed_count} transaction categories.")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
        return 1

if __name__ == "__main__":
    sys.exit(main())