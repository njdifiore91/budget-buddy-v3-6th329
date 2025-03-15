"""
Utility script for importing data into the Budget Management Application from various formats 
(JSON, CSV, Excel) to Google Sheets. Provides functions to import transaction data, budget data, 
and restore from backups with proper validation and formatting.
"""

import os
import sys
import argparse
import datetime
import json
import csv
from typing import List, Dict, Optional, Any, Union

import pandas as pd

# Internal imports
from ..config.logging_setup import get_logger
from ..config.path_constants import BACKUP_DIR, DATA_DIR, ensure_dir_exists
from ..config.script_settings import SCRIPT_SETTINGS
from .sheet_operations import (
    get_sheets_service,
    write_sheet,
    clear_sheet_range,
    import_json_to_sheet,
    validate_sheet_structure
)
from ...backend.models.transaction import create_transaction
from ...backend.models.category import create_category

# Set up logger
logger = get_logger(__name__)

# Constants
SUPPORTED_IMPORT_FORMATS = ["json", "csv", "excel"]
WEEKLY_SPENDING_SHEET_ID = os.getenv("WEEKLY_SPENDING_SHEET_ID", "")
MASTER_BUDGET_SHEET_ID = os.getenv("MASTER_BUDGET_SHEET_ID", "")
WEEKLY_SPENDING_RANGE = "Weekly Spending!A1:D"
MASTER_BUDGET_RANGE = "Master Budget!A1:B"
WEEKLY_SPENDING_HEADERS = ["Transaction Location", "Transaction Amount", "Transaction Time", "Corresponding Category"]
MASTER_BUDGET_HEADERS = ["Spending Category", "Weekly Amount"]


def import_from_json(input_path: str) -> Union[List, Dict]:
    """
    Imports data from a JSON file
    
    Args:
        input_path: Path to the JSON file
        
    Returns:
        Imported data as list or dictionary
    """
    try:
        with open(input_path, 'r') as file:
            data = json.load(file)
        logger.info(f"Successfully imported data from JSON file: {input_path}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON file {input_path}: {str(e)}")
        return None
    except FileNotFoundError:
        logger.error(f"File not found: {input_path}")
        return None
    except Exception as e:
        logger.error(f"Error importing JSON file {input_path}: {str(e)}")
        return None


def import_from_csv(input_path: str, delimiter: str = ',', has_header: bool = True) -> pd.DataFrame:
    """
    Imports data from a CSV file
    
    Args:
        input_path: Path to the CSV file
        delimiter: CSV delimiter character
        has_header: Whether the CSV has a header row
        
    Returns:
        Imported data as DataFrame
    """
    try:
        header = 0 if has_header else None
        df = pd.read_csv(input_path, delimiter=delimiter, header=header)
        logger.info(f"Successfully imported data from CSV file: {input_path}")
        return df
    except pd.errors.EmptyDataError:
        logger.error(f"CSV file is empty: {input_path}")
        return None
    except FileNotFoundError:
        logger.error(f"File not found: {input_path}")
        return None
    except Exception as e:
        logger.error(f"Error importing CSV file {input_path}: {str(e)}")
        return None


def import_from_excel(input_path: str, sheet_name: str = 0, has_header: bool = True) -> pd.DataFrame:
    """
    Imports data from an Excel file
    
    Args:
        input_path: Path to the Excel file
        sheet_name: Name or index of the sheet to import
        has_header: Whether the sheet has a header row
        
    Returns:
        Imported data as DataFrame
    """
    try:
        header = 0 if has_header else None
        df = pd.read_excel(input_path, sheet_name=sheet_name, header=header)
        logger.info(f"Successfully imported data from Excel file: {input_path}, sheet: {sheet_name}")
        return df
    except FileNotFoundError:
        logger.error(f"File not found: {input_path}")
        return None
    except ValueError as e:
        logger.error(f"Sheet {sheet_name} not found in Excel file {input_path}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error importing Excel file {input_path}: {str(e)}")
        return None


def convert_to_sheet_format(data: Union[pd.DataFrame, List, Dict], import_format: str) -> List[List[Any]]:
    """
    Converts imported data to Google Sheets format
    
    Args:
        data: Data imported from file
        import_format: Format of the imported data (json, csv, excel)
        
    Returns:
        Data formatted for Google Sheets
    """
    try:
        if data is None:
            logger.error("Cannot convert None data to sheet format")
            return []
            
        # Handle DataFrame (from CSV or Excel)
        if isinstance(data, pd.DataFrame):
            # Convert DataFrame to list of lists including column headers
            sheet_data = [data.columns.tolist()] + data.values.tolist()
            return sheet_data
            
        # Handle JSON as dictionary
        elif isinstance(data, dict):
            # Convert dict to list of lists with headers
            headers = list(data.keys())
            values = [list(data.values())]
            return [headers] + values
            
        # Handle JSON as list of dictionaries
        elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            # Get all unique keys as headers
            headers = []
            for item in data:
                for key in item.keys():
                    if key not in headers:
                        headers.append(key)
                        
            # Create rows with headers
            sheet_data = [headers]
            for item in data:
                row = [item.get(key, "") for key in headers]
                sheet_data.append(row)
            return sheet_data
            
        # Handle JSON as list of lists
        elif isinstance(data, list):
            return data
            
        else:
            logger.error(f"Unsupported data type for conversion: {type(data)}")
            return []
            
    except Exception as e:
        logger.error(f"Error converting data to sheet format: {str(e)}")
        return []


def import_data_to_sheet(input_path: str, import_format: str, spreadsheet_id: str, 
                          range_name: str, clear_first: bool = True, service=None) -> bool:
    """
    Imports data from a file to a Google Sheet
    
    Args:
        input_path: Path to the input file
        import_format: Format of the import file (json, csv, excel)
        spreadsheet_id: ID of the target Google Sheet
        range_name: Range to import data to
        clear_first: Whether to clear the range before importing
        service: Google Sheets API service (will be created if None)
        
    Returns:
        True if import was successful
    """
    try:
        # Validate import format
        if import_format not in SUPPORTED_IMPORT_FORMATS:
            logger.error(f"Unsupported import format: {import_format}")
            return False
            
        # Create service if not provided
        if service is None:
            service = get_sheets_service()
            
        # Import data based on format
        if import_format == "json":
            data = import_from_json(input_path)
        elif import_format == "csv":
            data = import_from_csv(input_path)
        elif import_format == "excel":
            data = import_from_excel(input_path)
        else:
            logger.error(f"Unhandled import format: {import_format}")
            return False
            
        if data is None:
            logger.error(f"Failed to import data from {input_path}")
            return False
            
        # Convert data to sheet format
        sheet_data = convert_to_sheet_format(data, import_format)
        
        if not sheet_data:
            logger.error("No valid data to import")
            return False
            
        # Clear the range if requested
        if clear_first:
            logger.info(f"Clearing range {range_name} before import")
            clear_sheet_range(spreadsheet_id, range_name, service)
            
        # Write data to sheet
        write_sheet(spreadsheet_id, range_name, sheet_data, service)
        
        logger.info(f"Successfully imported data from {input_path} to {range_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error importing data to sheet: {str(e)}")
        return False


def import_weekly_spending(input_path: str, import_format: str, clear_first: bool = True, service=None) -> bool:
    """
    Imports Weekly Spending data from a file
    
    Args:
        input_path: Path to the input file
        import_format: Format of the import file (json, csv, excel)
        clear_first: Whether to clear the sheet before importing
        service: Google Sheets API service (will be created if None)
        
    Returns:
        True if import was successful
    """
    try:
        # Validate sheet ID is available
        if not WEEKLY_SPENDING_SHEET_ID:
            logger.error("WEEKLY_SPENDING_SHEET_ID environment variable not set")
            return False
            
        # Validate input file exists
        if not os.path.exists(input_path):
            logger.error(f"Input file not found: {input_path}")
            return False
            
        # Validate import format
        if import_format not in SUPPORTED_IMPORT_FORMATS:
            logger.error(f"Unsupported import format: {import_format}")
            return False
            
        # Import data to sheet
        result = import_data_to_sheet(
            input_path,
            import_format,
            WEEKLY_SPENDING_SHEET_ID,
            WEEKLY_SPENDING_RANGE,
            clear_first,
            service
        )
        
        # Validate structure after import
        if result:
            if not validate_sheet_structure(
                WEEKLY_SPENDING_SHEET_ID, 
                WEEKLY_SPENDING_RANGE.split('!')[0]+"!A1:D1", 
                WEEKLY_SPENDING_HEADERS,
                service
            ):
                logger.error("Weekly Spending sheet structure validation failed after import")
                return False
                
        return result
        
    except Exception as e:
        logger.error(f"Error importing Weekly Spending data: {str(e)}")
        return False


def import_master_budget(input_path: str, import_format: str, clear_first: bool = True, service=None) -> bool:
    """
    Imports Master Budget data from a file
    
    Args:
        input_path: Path to the input file
        import_format: Format of the import file (json, csv, excel)
        clear_first: Whether to clear the sheet before importing
        service: Google Sheets API service (will be created if None)
        
    Returns:
        True if import was successful
    """
    try:
        # Validate sheet ID is available
        if not MASTER_BUDGET_SHEET_ID:
            logger.error("MASTER_BUDGET_SHEET_ID environment variable not set")
            return False
            
        # Validate input file exists
        if not os.path.exists(input_path):
            logger.error(f"Input file not found: {input_path}")
            return False
            
        # Validate import format
        if import_format not in SUPPORTED_IMPORT_FORMATS:
            logger.error(f"Unsupported import format: {import_format}")
            return False
            
        # Import data to sheet
        result = import_data_to_sheet(
            input_path,
            import_format,
            MASTER_BUDGET_SHEET_ID,
            MASTER_BUDGET_RANGE,
            clear_first,
            service
        )
        
        # Validate structure after import
        if result:
            if not validate_sheet_structure(
                MASTER_BUDGET_SHEET_ID, 
                MASTER_BUDGET_RANGE.split('!')[0]+"!A1:B1", 
                MASTER_BUDGET_HEADERS,
                service
            ):
                logger.error("Master Budget sheet structure validation failed after import")
                return False
                
        return result
        
    except Exception as e:
        logger.error(f"Error importing Master Budget data: {str(e)}")
        return False


def find_latest_backup(sheet_name: str, import_format: str, backup_dir: str = None) -> str:
    """
    Finds the latest backup file for a specific sheet and format
    
    Args:
        sheet_name: Name of the sheet to find backup for
        import_format: Format of the backup file
        backup_dir: Directory to search for backups (defaults to BACKUP_DIR)
        
    Returns:
        Path to the latest backup file
    """
    try:
        # Use default backup directory if not specified
        if backup_dir is None:
            backup_dir = BACKUP_DIR
            
        # Ensure backup directory exists
        ensure_dir_exists(backup_dir)
        
        # List all files in backup directory
        all_files = os.listdir(backup_dir)
        
        # Pattern for backup files: {sheet_name}_{timestamp}.{format}
        backup_files = []
        for file in all_files:
            if file.startswith(f"{sheet_name}_") and file.endswith(f".{import_format}"):
                backup_files.append(file)
                
        if not backup_files:
            logger.warning(f"No backup files found for {sheet_name} in {import_format} format")
            return ""
            
        # Sort backup files by timestamp (assuming filename format is consistent)
        backup_files.sort(reverse=True)
        
        # Return the path to the latest backup file
        latest_backup = os.path.join(backup_dir, backup_files[0])
        logger.info(f"Found latest backup for {sheet_name}: {latest_backup}")
        return latest_backup
        
    except Exception as e:
        logger.error(f"Error finding latest backup: {str(e)}")
        return ""


def restore_from_backup(sheets: List[str] = None, import_format: str = None, backup_dir: str = None) -> Dict[str, bool]:
    """
    Restores data from the latest backup files
    
    Args:
        sheets: List of sheets to restore ('weekly_spending', 'master_budget')
        import_format: Format of the backup files
        backup_dir: Directory containing backups
        
    Returns:
        Dictionary mapping sheet names to restore status
    """
    try:
        # Use defaults if not specified
        if sheets is None or not sheets:
            sheets = ['weekly_spending', 'master_budget']
            
        if import_format is None:
            import_format = 'json'
            
        if backup_dir is None:
            backup_dir = BACKUP_DIR
            
        # Initialize Google Sheets service
        service = get_sheets_service()
        
        # Initialize results dictionary
        results = {}
        
        # Process each sheet
        for sheet in sheets:
            try:
                # Find latest backup file
                latest_backup = find_latest_backup(sheet, import_format, backup_dir)
                
                if not latest_backup:
                    logger.warning(f"No backup found for {sheet}, skipping restore")
                    results[sheet] = False
                    continue
                    
                # Restore from backup based on sheet type
                if sheet == 'weekly_spending':
                    success = import_weekly_spending(latest_backup, import_format, True, service)
                elif sheet == 'master_budget':
                    success = import_master_budget(latest_backup, import_format, True, service)
                else:
                    logger.warning(f"Unknown sheet type: {sheet}, skipping restore")
                    success = False
                    
                results[sheet] = success
                logger.info(f"Restore {'successful' if success else 'failed'} for {sheet}")
                
            except Exception as sheet_error:
                logger.error(f"Error restoring {sheet}: {str(sheet_error)}")
                results[sheet] = False
                
        # Log overall restore status
        successful = sum(1 for status in results.values() if status)
        logger.info(f"Restore completed: {successful}/{len(results)} sheets restored successfully")
        
        return results
        
    except Exception as e:
        logger.error(f"Error during restore operation: {str(e)}")
        return {sheet: False for sheet in sheets} if sheets else {}


def import_transactions_from_json(input_path: str) -> List:
    """
    Imports transaction data from a JSON file and creates Transaction objects
    
    Args:
        input_path: Path to the JSON file
        
    Returns:
        List of Transaction objects
    """
    try:
        # Import JSON data
        data = import_from_json(input_path)
        
        if not data:
            logger.error(f"Failed to import transaction data from {input_path}")
            return []
            
        # Validate that data is a list of transaction dictionaries
        if not isinstance(data, list):
            logger.error(f"Expected list of transactions, got {type(data)}")
            return []
            
        # Create Transaction objects
        transactions = []
        for i, item in enumerate(data):
            try:
                transaction = create_transaction(item)
                transactions.append(transaction)
            except Exception as tx_error:
                logger.warning(f"Error creating transaction at index {i}: {str(tx_error)}")
                
        logger.info(f"Imported {len(transactions)} transactions from {input_path}")
        return transactions
        
    except Exception as e:
        logger.error(f"Error importing transactions from JSON: {str(e)}")
        return []


def import_categories_from_json(input_path: str) -> List:
    """
    Imports category data from a JSON file and creates Category objects
    
    Args:
        input_path: Path to the JSON file
        
    Returns:
        List of Category objects
    """
    try:
        # Import JSON data
        data = import_from_json(input_path)
        
        if not data:
            logger.error(f"Failed to import category data from {input_path}")
            return []
            
        # Validate that data is a list of category dictionaries
        if not isinstance(data, list):
            logger.error(f"Expected list of categories, got {type(data)}")
            return []
            
        # Create Category objects
        categories = []
        for i, item in enumerate(data):
            try:
                category = create_category(item)
                categories.append(category)
            except Exception as cat_error:
                logger.warning(f"Error creating category at index {i}: {str(cat_error)}")
                
        logger.info(f"Imported {len(categories)} categories from {input_path}")
        return categories
        
    except Exception as e:
        logger.error(f"Error importing categories from JSON: {str(e)}")
        return []


def parse_args():
    """
    Parses command-line arguments for the script
    
    Returns:
        Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Import data to Budget Management Application from various formats"
    )
    
    parser.add_argument(
        "--input_file",
        "-i",
        help="Path to input file",
        required=False
    )
    
    parser.add_argument(
        "--format",
        "-f",
        choices=SUPPORTED_IMPORT_FORMATS,
        default="json",
        help="Format of input file"
    )
    
    parser.add_argument(
        "--sheet",
        "-s",
        choices=["weekly", "budget", "restore"],
        required=True,
        help="Target sheet or operation"
    )
    
    parser.add_argument(
        "--clear",
        "-c",
        action="store_true",
        help="Clear sheet before importing"
    )
    
    parser.add_argument(
        "--backup_dir",
        "-b",
        help="Backup directory for restore operation"
    )
    
    return parser.parse_args()


def main() -> int:
    """
    Main function for the import_data script
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Parse command-line arguments
        args = parse_args()
        
        # Create sheets service
        service = get_sheets_service()
        
        # Process based on sheet argument
        if args.sheet == "weekly":
            if not args.input_file:
                logger.error("Input file is required for weekly spending import")
                return 1
                
            success = import_weekly_spending(
                args.input_file,
                args.format,
                args.clear,
                service
            )
            
        elif args.sheet == "budget":
            if not args.input_file:
                logger.error("Input file is required for master budget import")
                return 1
                
            success = import_master_budget(
                args.input_file,
                args.format,
                args.clear,
                service
            )
            
        elif args.sheet == "restore":
            sheets_to_restore = []
            
            if args.input_file:
                # If input file specified, restore only that sheet type
                if "weekly" in args.input_file:
                    sheets_to_restore.append("weekly_spending")
                elif "budget" in args.input_file:
                    sheets_to_restore.append("master_budget")
                else:
                    logger.warning(f"Cannot determine sheet type from filename: {args.input_file}")
                    sheets_to_restore = ['weekly_spending', 'master_budget']
            else:
                # Restore both sheet types if not specified
                sheets_to_restore = ['weekly_spending', 'master_budget']
                
            results = restore_from_backup(
                sheets_to_restore,
                args.format,
                args.backup_dir
            )
            
            success = any(results.values())
            
        else:
            logger.error(f"Unknown sheet type: {args.sheet}")
            return 1
            
        # Return appropriate exit code
        logger.info(f"Import operation {'successful' if success else 'failed'}")
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())