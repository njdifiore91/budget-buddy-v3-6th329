#!/usr/bin/env python3
"""
Script for initializing the Google Sheets required by the Budget Management Application.
Creates and configures the Master Budget and Weekly Spending sheets with appropriate structure,
formatting, and initial data to support the budget tracking and analysis functionality.
"""

import os
import sys
import argparse
import json
from dotenv import load_dotenv
from googleapiclient.errors import HttpError

# Internal imports
from ..config.logging_setup import get_script_logger, log_script_start, log_script_end
from ..config.script_settings import SCRIPT_SETTINGS
from ...backend.config.settings import APP_SETTINGS
from ..utils.sheet_operations import (
    get_sheets_service, create_sheet, write_sheet, format_sheet,
    get_sheet_id_by_name, validate_sheet_structure
)
from .configure_credentials import configure_google_sheets
from .verify_api_access import verify_google_sheets_access

# Set up logger
logger = get_script_logger('initialize_sheets')

# Constants
MASTER_BUDGET_SHEET_NAME = "Master Budget"
WEEKLY_SPENDING_SHEET_NAME = "Weekly Spending"
MASTER_BUDGET_HEADERS = ["Spending Category", "Weekly Amount"]
WEEKLY_SPENDING_HEADERS = ["Transaction Location", "Transaction Amount", "Transaction Time", "Corresponding Category"]

def parse_arguments():
    """
    Parse command-line arguments for the sheet initialization script
    
    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Initialize Google Sheets for Budget Management Application"
    )
    
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force overwrite of existing sheets"
    )
    
    parser.add_argument(
        "--spreadsheet-id",
        help="Specify a custom spreadsheet ID (overrides settings)"
    )
    
    parser.add_argument(
        "--categories-file",
        help="Specify a JSON file with custom categories and amounts"
    )
    
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode without prompts"
    )
    
    return parser.parse_args()

def load_categories_from_file(file_path):
    """
    Load budget categories and amounts from a JSON file
    
    Args:
        file_path (str): Path to the JSON file
        
    Returns:
        tuple: (categories, amounts) lists from the file
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"Categories file not found: {file_path}")
            return None, None
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        categories = data.get('categories', [])
        amounts = data.get('amounts', [])
        
        # Validate that the lists have the same length
        if len(categories) != len(amounts):
            logger.error(f"Mismatch between categories and amounts in {file_path}")
            return None, None
        
        logger.info(f"Loaded {len(categories)} categories from {file_path}")
        return categories, amounts
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {file_path}: {e}")
        return None, None
    
    except Exception as e:
        logger.error(f"Error loading categories from file: {e}")
        return None, None

def check_sheet_exists(service, spreadsheet_id, sheet_name):
    """
    Check if a sheet with the given name exists in the spreadsheet
    
    Args:
        service (object): Google Sheets API service
        spreadsheet_id (str): ID of the spreadsheet
        sheet_name (str): Name of the sheet to check
        
    Returns:
        bool: True if sheet exists, False otherwise
    """
    try:
        sheet_id = get_sheet_id_by_name(spreadsheet_id, sheet_name, service)
        return sheet_id is not None
    
    except Exception as e:
        logger.error(f"Error checking if sheet exists: {e}")
        return False

def initialize_master_budget(service, spreadsheet_id, categories, amounts, force=False):
    """
    Initialize the Master Budget sheet with categories and amounts
    
    Args:
        service (object): Google Sheets API service
        spreadsheet_id (str): ID of the spreadsheet
        categories (list): List of budget categories
        amounts (list): List of budget amounts
        force (bool): Whether to overwrite existing sheet
        
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    try:
        # Check if sheet already exists
        sheet_exists = check_sheet_exists(service, spreadsheet_id, MASTER_BUDGET_SHEET_NAME)
        
        if sheet_exists and not force:
            logger.info(f"{MASTER_BUDGET_SHEET_NAME} sheet already exists, skipping initialization")
            return True
        
        # Create the sheet if it doesn't exist or force is True
        if not sheet_exists:
            logger.info(f"Creating {MASTER_BUDGET_SHEET_NAME} sheet")
            create_sheet(spreadsheet_id, MASTER_BUDGET_SHEET_NAME, service)
        
        # Prepare data to write to the sheet
        data = [MASTER_BUDGET_HEADERS]  # Start with headers
        for i in range(len(categories)):
            data.append([categories[i], amounts[i]])
        
        # Write data to the sheet
        range_name = f"{MASTER_BUDGET_SHEET_NAME}!A1:{chr(65 + len(MASTER_BUDGET_HEADERS) - 1)}{len(data)}"
        write_sheet(spreadsheet_id, range_name, data, service)
        
        # Get the sheet ID for formatting
        sheet_id = get_sheet_id_by_name(spreadsheet_id, MASTER_BUDGET_SHEET_NAME, service)
        
        # Apply header formatting (bold)
        header_format = {
            "textFormat": {
                "bold": True
            }
        }
        
        # Format headers
        header_range = f"{MASTER_BUDGET_SHEET_NAME}!A1:B1"
        format_sheet(spreadsheet_id, header_range, header_format, service)
        
        # Format amount column as currency
        currency_format = {
            "numberFormat": {
                "type": "CURRENCY",
                "pattern": "$#,##0.00"
            }
        }
        
        # Format amounts column
        amount_range = f"{MASTER_BUDGET_SHEET_NAME}!B2:B{len(data)}"
        format_sheet(spreadsheet_id, amount_range, currency_format, service)
        
        logger.info(f"Successfully initialized {MASTER_BUDGET_SHEET_NAME} sheet with {len(categories)} categories")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing Master Budget sheet: {e}")
        return False

def initialize_weekly_spending(service, spreadsheet_id, force=False):
    """
    Initialize the Weekly Spending sheet with headers
    
    Args:
        service (object): Google Sheets API service
        spreadsheet_id (str): ID of the spreadsheet
        force (bool): Whether to overwrite existing sheet
        
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    try:
        # Check if sheet already exists
        sheet_exists = check_sheet_exists(service, spreadsheet_id, WEEKLY_SPENDING_SHEET_NAME)
        
        if sheet_exists and not force:
            logger.info(f"{WEEKLY_SPENDING_SHEET_NAME} sheet already exists, skipping initialization")
            return True
        
        # Create the sheet if it doesn't exist or force is True
        if not sheet_exists:
            logger.info(f"Creating {WEEKLY_SPENDING_SHEET_NAME} sheet")
            create_sheet(spreadsheet_id, WEEKLY_SPENDING_SHEET_NAME, service)
        
        # Prepare data to write to the sheet (just headers for this sheet)
        data = [WEEKLY_SPENDING_HEADERS]
        
        # Write data to the sheet
        range_name = f"{WEEKLY_SPENDING_SHEET_NAME}!A1:{chr(65 + len(WEEKLY_SPENDING_HEADERS) - 1)}1"
        write_sheet(spreadsheet_id, range_name, data, service)
        
        # Get the sheet ID for formatting
        sheet_id = get_sheet_id_by_name(spreadsheet_id, WEEKLY_SPENDING_SHEET_NAME, service)
        
        # Apply header formatting (bold)
        header_format = {
            "textFormat": {
                "bold": True
            }
        }
        
        # Format headers
        format_sheet(spreadsheet_id, range_name, header_format, service)
        
        # Set column formats (currency for amount column)
        currency_format = {
            "numberFormat": {
                "type": "CURRENCY",
                "pattern": "$#,##0.00"
            }
        }
        
        # Format amount column (column B)
        amount_range = f"{WEEKLY_SPENDING_SHEET_NAME}!B:B"
        format_sheet(spreadsheet_id, amount_range, currency_format, service)
        
        # Set date format for timestamp column
        date_format = {
            "numberFormat": {
                "type": "DATE_TIME",
                "pattern": "yyyy-mm-dd hh:mm:ss"
            }
        }
        
        # Format timestamp column (column C)
        date_range = f"{WEEKLY_SPENDING_SHEET_NAME}!C:C"
        format_sheet(spreadsheet_id, date_range, date_format, service)
        
        logger.info(f"Successfully initialized {WEEKLY_SPENDING_SHEET_NAME} sheet")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing Weekly Spending sheet: {e}")
        return False

def validate_sheets(service, spreadsheet_id):
    """
    Validate that both sheets have the expected structure
    
    Args:
        service (object): Google Sheets API service
        spreadsheet_id (str): ID of the spreadsheet
        
    Returns:
        bool: True if both sheets are valid, False otherwise
    """
    try:
        # Validate Master Budget sheet
        master_range = f"{MASTER_BUDGET_SHEET_NAME}!A1:B1"
        master_valid = validate_sheet_structure(
            spreadsheet_id, 
            master_range, 
            MASTER_BUDGET_HEADERS,
            service
        )
        
        # Validate Weekly Spending sheet
        weekly_range = f"{WEEKLY_SPENDING_SHEET_NAME}!A1:D1"
        weekly_valid = validate_sheet_structure(
            spreadsheet_id,
            weekly_range, 
            WEEKLY_SPENDING_HEADERS,
            service
        )
        
        if master_valid and weekly_valid:
            logger.info("Both sheets have valid structure")
            return True
        else:
            if not master_valid:
                logger.error(f"{MASTER_BUDGET_SHEET_NAME} sheet has invalid structure")
            if not weekly_valid:
                logger.error(f"{WEEKLY_SPENDING_SHEET_NAME} sheet has invalid structure")
            return False
            
    except Exception as e:
        logger.error(f"Error validating sheets: {e}")
        return False

def main():
    """
    Main function to orchestrate sheet initialization
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Parse command-line arguments
    args = parse_arguments()
    
    # Log script start
    log_script_start()
    
    try:
        # Check if Google Sheets credentials are configured
        # and configure them if not
        sheets_verification = verify_google_sheets_access(verbose=False, use_mocks=False)
        if sheets_verification.get('status') != 'success':
            logger.info("Google Sheets credentials not configured or invalid")
            if not args.non_interactive:
                logger.info("Configuring Google Sheets credentials")
                if not configure_google_sheets():
                    logger.error("Failed to configure Google Sheets credentials")
                    return 1
            else:
                logger.error("Cannot proceed without valid Google Sheets credentials in non-interactive mode")
                return 1
        
        # Get spreadsheet ID from arguments or settings
        spreadsheet_id = args.spreadsheet_id
        if not spreadsheet_id:
            spreadsheet_id = APP_SETTINGS.get('MASTER_BUDGET_SHEET_ID')
            if not spreadsheet_id:
                logger.error("No spreadsheet ID provided and none found in settings")
                return 1
            
        # Get default categories and amounts from script settings
        categories = SCRIPT_SETTINGS.get('DEFAULT_BUDGET_CATEGORIES', [
            "Groceries", "Dining Out", "Transportation", "Entertainment", 
            "Shopping", "Utilities", "Housing", "Health", "Miscellaneous"
        ])
        
        amounts = SCRIPT_SETTINGS.get('DEFAULT_WEEKLY_AMOUNTS', [
            "150.00", "75.00", "50.00", "50.00", 
            "100.00", "75.00", "500.00", "40.00", "50.00"
        ])
        
        # Load custom categories if specified
        if args.categories_file:
            custom_categories, custom_amounts = load_categories_from_file(args.categories_file)
            if custom_categories and custom_amounts:
                categories = custom_categories
                amounts = custom_amounts
        
        # Get authenticated service
        service = get_sheets_service()
        
        # Initialize Master Budget sheet
        master_success = initialize_master_budget(
            service, spreadsheet_id, categories, amounts, args.force
        )
        
        # Initialize Weekly Spending sheet
        weekly_success = initialize_weekly_spending(
            service, spreadsheet_id, args.force
        )
        
        # Validate sheet structure
        validation_success = validate_sheets(service, spreadsheet_id)
        
        # Determine overall success
        success = master_success and weekly_success and validation_success
        
        # Log script end
        log_script_end()
        
        return 0 if success else 1
        
    except Exception as e:
        logger.critical(f"Unexpected error in sheet initialization: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())