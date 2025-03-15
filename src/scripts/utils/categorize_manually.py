#!/usr/bin/env python
"""
Utility script that provides a command-line interface for manually categorizing transactions
in the Budget Management Application. This tool allows users to review uncategorized transactions
and assign categories when the automated AI categorization is insufficient or needs correction.

Usage:
    python categorize_manually.py [--weekly-spending-id SHEET_ID] [--master-budget-id SHEET_ID] [--credentials PATH]
"""

import os
import sys
import argparse
import pandas as pd
from typing import List, Dict, Optional
from tabulate import tabulate
from colorama import Fore, Style, init as colorama_init

# Internal imports
from ..config.logging_setup import get_logger
from ..config.script_settings import SCRIPT_SETTINGS
from .sheet_operations import (
    get_sheets_service, read_sheet, write_sheet, get_sheet_as_dataframe
)
from ...backend.models.transaction import (
    Transaction, create_transactions_from_sheet_data
)
from ...backend.models.category import (
    get_category_names, create_categories_from_sheet_data
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
BUDGET_CATEGORY_COL = 0
BUDGET_AMOUNT_COL = 1

def get_uncategorized_transactions(spreadsheet_id: str, service) -> List[Transaction]:
    """
    Retrieves transactions without assigned categories from the Weekly Spending sheet
    
    Args:
        spreadsheet_id: ID of the Weekly Spending spreadsheet
        service: Google Sheets API service
        
    Returns:
        List of uncategorized Transaction objects
    """
    logger.info("Retrieving uncategorized transactions")
    
    # Read data from the Weekly Spending sheet
    data = read_sheet(spreadsheet_id, f"{WEEKLY_SPENDING_SHEET_NAME}!A:D", service)
    
    # Skip header row and create Transaction objects
    if len(data) <= 1:  # Only header or empty
        logger.warning("No transaction data found in Weekly Spending sheet")
        return []
    
    # Create Transaction objects from the sheet data (skipping header)
    transactions = create_transactions_from_sheet_data(data[1:])
    
    # Filter out transactions that already have categories
    uncategorized = [t for t in transactions if not t.category]
    
    logger.info(f"Found {len(uncategorized)} uncategorized transactions")
    return uncategorized

def get_valid_categories(spreadsheet_id: str, service) -> List[str]:
    """
    Retrieves valid budget categories from the Master Budget sheet
    
    Args:
        spreadsheet_id: ID of the Master Budget spreadsheet
        service: Google Sheets API service
        
    Returns:
        List of valid category names
    """
    logger.info("Retrieving valid categories from Master Budget")
    
    # Read data from the Master Budget sheet
    data = read_sheet(spreadsheet_id, f"{MASTER_BUDGET_SHEET_NAME}!A:B", service)
    
    # Skip header row and create Category objects
    if len(data) <= 1:  # Only header or empty
        logger.warning("No category data found in Master Budget sheet")
        return []
    
    # Create Category objects from the sheet data (skipping header)
    categories = create_categories_from_sheet_data(data[1:])
    
    # Extract just the category names
    category_names = get_category_names(categories)
    
    logger.info(f"Found {len(category_names)} valid categories")
    return category_names

def display_transaction(transaction: Transaction, index: int):
    """
    Displays a transaction with formatted output in the terminal
    
    Args:
        transaction: Transaction object to display
        index: Index of the transaction in the list
    """
    # Format the transaction details with colors
    location = Fore.CYAN + transaction.location + Style.RESET_ALL
    amount = Fore.YELLOW + f"${transaction.amount:.2f}" + Style.RESET_ALL
    timestamp = Fore.WHITE + str(transaction.timestamp) + Style.RESET_ALL
    
    # Display transaction details
    print(f"\nTransaction #{index + 1}:")
    print(f"  Location: {location}")
    print(f"  Amount:   {amount}")
    print(f"  Time:     {timestamp}")
    
    # Display category if one exists
    if transaction.category:
        category = Fore.GREEN + transaction.category + Style.RESET_ALL
        print(f"  Category: {category}")
    else:
        category = Fore.RED + "Uncategorized" + Style.RESET_ALL
        print(f"  Category: {category}")

def display_categories(categories: List[str]):
    """
    Displays available categories in a formatted table
    
    Args:
        categories: List of category names
    """
    # Create a list with index numbers and category names
    indexed_categories = [(i, cat) for i, cat in enumerate(categories)]
    
    # Split into multiple columns for better display
    num_cols = 3  # Adjust based on expected terminal width
    rows = []
    
    for i in range(0, len(indexed_categories), num_cols):
        row = indexed_categories[i:i + num_cols]
        # Ensure all columns have a value, even if empty
        while len(row) < num_cols:
            row.append(("", ""))
        rows.append(row)
    
    # Flatten rows into a list of values for tabulate
    tabulated_data = []
    for row in rows:
        tabulated_row = []
        for idx, cat in row:
            if cat:  # Only format if there's a value
                tabulated_row.extend([f"{idx}.", cat])
            else:
                tabulated_row.extend(["", ""])
        tabulated_data.append(tabulated_row)
    
    # Display categories table
    headers = ["#", "Category"] * num_cols
    print("\nAvailable Categories:")
    print(tabulate(tabulated_data, headers=headers, tablefmt="simple"))

def prompt_for_category(valid_categories: List[str]) -> Optional[str]:
    """
    Prompts the user to select a category for a transaction
    
    Args:
        valid_categories: List of valid category names
        
    Returns:
        Selected category name or None if skipped
    """
    print("\nSelect a category (enter number or name, 's' to skip):")
    selection = input("> ").strip()
    
    # Skip this transaction
    if selection.lower() == 's':
        return None
    
    # Try to interpret as a number (index)
    try:
        index = int(selection)
        if 0 <= index < len(valid_categories):
            return valid_categories[index]
        else:
            print(f"Invalid category number. Please enter 0-{len(valid_categories)-1}")
            return prompt_for_category(valid_categories)
    except ValueError:
        # Not a number, check if it's a valid category name
        if selection in valid_categories:
            return selection
        
        # Check if it's a partial match or case-insensitive match
        lower_selection = selection.lower()
        matches = [cat for cat in valid_categories if cat.lower() == lower_selection]
        
        if matches:
            return matches[0]
        
        # Check for partial matches
        partial_matches = [cat for cat in valid_categories if lower_selection in cat.lower()]
        
        if len(partial_matches) == 1:
            confirm = input(f"Did you mean '{partial_matches[0]}'? (y/n): ").strip().lower()
            if confirm == 'y':
                return partial_matches[0]
        elif partial_matches:
            print("Multiple matches found:")
            for i, match in enumerate(partial_matches):
                print(f"  {i}. {match}")
            sub_selection = input("Please select a number or 'n' to try again: ").strip().lower()
            if sub_selection == 'n':
                return prompt_for_category(valid_categories)
            try:
                index = int(sub_selection)
                if 0 <= index < len(partial_matches):
                    return partial_matches[index]
            except ValueError:
                pass
        
        print("Invalid category. Please enter a valid category number or name.")
        return prompt_for_category(valid_categories)

def update_transaction_category(transaction: Transaction, category: str, 
                                spreadsheet_id: str, service) -> bool:
    """
    Updates a transaction's category in the Weekly Spending sheet
    
    Args:
        transaction: Transaction object to update
        category: Category to assign
        spreadsheet_id: ID of the Weekly Spending spreadsheet
        service: Google Sheets API service
        
    Returns:
        True if update was successful, False otherwise
    """
    logger.info(f"Updating category for transaction: {transaction.location} to {category}")
    
    try:
        # Read all data from the Weekly Spending sheet to find the row for this transaction
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
        data[row_index-1][TRANSACTION_CATEGORY_COL] = category
        
        # Write the updated row back to the sheet
        range_name = f"{WEEKLY_SPENDING_SHEET_NAME}!A{row_index}:D{row_index}"
        write_sheet(spreadsheet_id, range_name, [data[row_index-1]], service)
        
        logger.info(f"Successfully updated category for transaction at row {row_index}")
        return True
    
    except Exception as e:
        logger.error(f"Error updating transaction category: {str(e)}")
        return False

def categorize_transactions_manually(weekly_spending_id: str, master_budget_id: str, 
                                    credentials_path: str) -> int:
    """
    Main function to interactively categorize transactions
    
    Args:
        weekly_spending_id: ID of the Weekly Spending spreadsheet
        master_budget_id: ID of the Master Budget spreadsheet
        credentials_path: Path to Google Sheets credentials file
        
    Returns:
        Number of transactions categorized
    """
    logger.info("Starting manual categorization process")
    
    # Get authenticated service
    service = get_sheets_service(credentials_path)
    
    # Get uncategorized transactions
    transactions = get_uncategorized_transactions(weekly_spending_id, service)
    
    if not transactions:
        print("No uncategorized transactions found!")
        return 0
    
    # Get valid categories
    valid_categories = get_valid_categories(master_budget_id, service)
    
    if not valid_categories:
        print("No valid categories found in Master Budget!")
        return 0
    
    # Display categories once
    display_categories(valid_categories)
    
    # Initialize counter for categorized transactions
    categorized_count = 0
    
    # Process each uncategorized transaction
    for i, transaction in enumerate(transactions):
        # Display the transaction
        display_transaction(transaction, i)
        
        # Prompt for category
        category = prompt_for_category(valid_categories)
        
        if category:
            # Update the transaction with the selected category
            if update_transaction_category(transaction, category, weekly_spending_id, service):
                transaction.set_category(category)
                categorized_count += 1
                print(f"{Fore.GREEN}Updated successfully!{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Failed to update category.{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}Skipped.{Style.RESET_ALL}")
    
    logger.info(f"Completed manual categorization: {categorized_count}/{len(transactions)} categorized")
    return categorized_count

def parse_arguments():
    """
    Parses command-line arguments for the script
    
    Returns:
        Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Manually categorize transactions in the Weekly Spending sheet"
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
        
        # Call the main categorization function
        categorized_count = categorize_transactions_manually(
            args.weekly_spending_id,
            args.master_budget_id,
            args.credentials
        )
        
        # Print summary
        print(f"\n{Fore.GREEN}Categorization complete!{Style.RESET_ALL}")
        print(f"Categorized {categorized_count} transactions.")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
        return 1

if __name__ == "__main__":
    sys.exit(main())