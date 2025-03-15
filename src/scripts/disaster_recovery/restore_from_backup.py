#!/usr/bin/env python3
"""
Script for restoring Google Sheets data from backups in the Budget Management Application.

This script provides functionality to restore both the Master Budget and Weekly Spending sheets 
from JSON backup files or in-spreadsheet backup sheets. Supports restoring from the latest backup
or a specific date.

Usage:
    python restore_from_backup.py [options]

Options:
    --json-only              Restore only from JSON backups
    --sheet-only             Restore only from in-spreadsheet backups
    --backup-dir DIR         Specify custom backup directory
    --date YYYY-MM-DD        Restore from backups nearest to this date
    --master-budget-only     Restore only Master Budget sheet
    --weekly-spending-only   Restore only Weekly Spending sheet

Examples:
    # Restore both sheets from latest backups (either JSON or sheet)
    python restore_from_backup.py

    # Restore both sheets from JSON backups only
    python restore_from_backup.py --json-only

    # Restore from backups closest to specific date
    python restore_from_backup.py --date 2023-07-15

    # Restore only Master Budget from latest backups
    python restore_from_backup.py --master-budget-only
"""

import os
import argparse
import datetime
import sys
import json
import re
from typing import List, Dict, Optional, Any, Tuple, Union

# Internal imports
from ..config.logging_setup import get_logger
from ..config.path_constants import BACKUP_DIR, ensure_dir_exists
from ...backend.config.settings import APP_SETTINGS
from ..utils.sheet_operations import (
    get_sheets_service, 
    import_json_to_sheet, 
    list_sheets,
    copy_sheet_data,
    clear_sheet_range
)

# Set up logger
logger = get_logger(__name__)

# Constants
WEEKLY_SPENDING_SHEET_NAME = "Weekly Spending"
MASTER_BUDGET_SHEET_NAME = "Master Budget"
BACKUP_FILE_PATTERN = re.compile(r'(.+)_backup_(\d{8}_\d{6})\.json')
BACKUP_SHEET_PATTERN = re.compile(r'Backup_(.+)_(\d{8}_\d{6})')


def find_latest_backup(sheet_name: str, backup_dir: str) -> Optional[str]:
    """
    Finds the latest backup file for a specific sheet
    
    Args:
        sheet_name: Name of the sheet to find backup for
        backup_dir: Directory containing backup files
        
    Returns:
        Path to the latest backup file or None if not found
    """
    # Ensure backup directory exists
    ensure_dir_exists(backup_dir)
    
    # List all files in the backup directory
    backup_files = []
    try:
        for filename in os.listdir(backup_dir):
            # Check if the file is a backup for the requested sheet
            match = BACKUP_FILE_PATTERN.match(filename)
            if match and match.group(1) == sheet_name:
                # Extract timestamp and add to list
                timestamp = match.group(2)
                backup_files.append((filename, timestamp))
    except Exception as e:
        logger.error(f"Error searching for backup files: {str(e)}")
        return None
    
    # If no backups found, return None
    if not backup_files:
        logger.warning(f"No backup files found for {sheet_name}")
        return None
    
    # Sort by timestamp (newest first)
    backup_files.sort(key=lambda x: x[1], reverse=True)
    
    # Return the path to the latest backup file
    latest_backup = os.path.join(backup_dir, backup_files[0][0])
    logger.info(f"Found latest backup for {sheet_name}: {latest_backup}")
    return latest_backup


def find_backup_by_date(sheet_name: str, target_date: datetime.datetime, backup_dir: str) -> Optional[str]:
    """
    Finds a backup file closest to a specific date
    
    Args:
        sheet_name: Name of the sheet to find backup for
        target_date: Target date to find closest backup to
        backup_dir: Directory containing backup files
        
    Returns:
        Path to the closest backup file or None if not found
    """
    # Ensure backup directory exists
    ensure_dir_exists(backup_dir)
    
    # List all files in the backup directory
    backup_files = []
    try:
        for filename in os.listdir(backup_dir):
            # Check if the file is a backup for the requested sheet
            match = BACKUP_FILE_PATTERN.match(filename)
            if match and match.group(1) == sheet_name:
                # Extract timestamp and convert to datetime
                timestamp_str = match.group(2)
                try:
                    timestamp = datetime.datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    backup_files.append((filename, timestamp))
                except ValueError:
                    logger.warning(f"Invalid timestamp format in filename: {filename}")
                    continue
    except Exception as e:
        logger.error(f"Error searching for backup files: {str(e)}")
        return None
    
    # If no backups found, return None
    if not backup_files:
        logger.warning(f"No backup files found for {sheet_name}")
        return None
    
    # Find the backup with timestamp closest to target_date
    closest_backup = min(backup_files, key=lambda x: abs(x[1] - target_date))
    
    # Return the path to the closest backup file
    closest_backup_path = os.path.join(backup_dir, closest_backup[0])
    logger.info(f"Found backup for {sheet_name} closest to {target_date}: {closest_backup_path}")
    return closest_backup_path


def find_latest_backup_sheet(spreadsheet_id: str, original_sheet_name: str, service) -> Optional[str]:
    """
    Finds the latest backup sheet in a spreadsheet
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        original_sheet_name: Name of the original sheet
        service: Google Sheets API service
        
    Returns:
        Name of the latest backup sheet or None if not found
    """
    try:
        # Get list of all sheets in the spreadsheet
        sheets = list_sheets(spreadsheet_id, service)
        
        # Find backup sheets for the original sheet
        backup_sheets = []
        for sheet_name in sheets.keys():
            match = BACKUP_SHEET_PATTERN.match(sheet_name)
            if match and match.group(1) == original_sheet_name:
                # Extract timestamp and add to list
                timestamp = match.group(2)
                backup_sheets.append((sheet_name, timestamp))
        
        # If no backup sheets found, return None
        if not backup_sheets:
            logger.warning(f"No backup sheets found for {original_sheet_name}")
            return None
        
        # Sort by timestamp (newest first)
        backup_sheets.sort(key=lambda x: x[1], reverse=True)
        
        # Return the name of the latest backup sheet
        latest_backup = backup_sheets[0][0]
        logger.info(f"Found latest backup sheet for {original_sheet_name}: {latest_backup}")
        return latest_backup
        
    except Exception as e:
        logger.error(f"Error finding backup sheets: {str(e)}")
        return None


def find_backup_sheet_by_date(spreadsheet_id: str, original_sheet_name: str, 
                             target_date: datetime.datetime, service) -> Optional[str]:
    """
    Finds a backup sheet closest to a specific date
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        original_sheet_name: Name of the original sheet
        target_date: Target date to find closest backup to
        service: Google Sheets API service
        
    Returns:
        Name of the closest backup sheet or None if not found
    """
    try:
        # Get list of all sheets in the spreadsheet
        sheets = list_sheets(spreadsheet_id, service)
        
        # Find backup sheets for the original sheet
        backup_sheets = []
        for sheet_name in sheets.keys():
            match = BACKUP_SHEET_PATTERN.match(sheet_name)
            if match and match.group(1) == original_sheet_name:
                # Extract timestamp and convert to datetime
                timestamp_str = match.group(2)
                try:
                    timestamp = datetime.datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    backup_sheets.append((sheet_name, timestamp))
                except ValueError:
                    logger.warning(f"Invalid timestamp format in sheet name: {sheet_name}")
                    continue
        
        # If no backup sheets found, return None
        if not backup_sheets:
            logger.warning(f"No backup sheets found for {original_sheet_name}")
            return None
        
        # Find the backup with timestamp closest to target_date
        closest_backup = min(backup_sheets, key=lambda x: abs(x[1] - target_date))
        
        # Return the name of the closest backup sheet
        closest_backup_name = closest_backup[0]
        logger.info(f"Found backup sheet for {original_sheet_name} closest to {target_date}: {closest_backup_name}")
        return closest_backup_name
        
    except Exception as e:
        logger.error(f"Error finding backup sheets by date: {str(e)}")
        return None


def validate_backup(backup_file: str) -> bool:
    """
    Validates that a backup file contains valid data
    
    Args:
        backup_file: Path to backup file
        
    Returns:
        True if backup is valid, False otherwise
    """
    try:
        # Check if file exists
        if not os.path.isfile(backup_file):
            logger.error(f"Backup file does not exist: {backup_file}")
            return False
        
        # Try to parse the JSON file
        with open(backup_file, 'r') as f:
            data = json.load(f)
        
        # Validate that it's a list of dictionaries
        if not isinstance(data, list):
            logger.error(f"Invalid backup format: expected a list, got {type(data)}")
            return False
        
        # Check if there's at least one item and it's a dictionary
        if len(data) > 0 and not isinstance(data[0], dict):
            logger.error(f"Invalid backup format: expected list of dictionaries")
            return False
        
        logger.info(f"Backup file validated successfully: {backup_file}")
        return True
        
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in backup file: {backup_file}")
        return False
    except Exception as e:
        logger.error(f"Error validating backup file: {str(e)}")
        return False


def restore_from_json_backup(spreadsheet_id: str, sheet_name: str, backup_file: str, service) -> bool:
    """
    Restores a sheet from a JSON backup file
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        sheet_name: Name of the sheet to restore
        backup_file: Path to backup file
        service: Google Sheets API service
        
    Returns:
        True if restoration was successful, False otherwise
    """
    try:
        # Validate the backup file
        if not validate_backup(backup_file):
            return False
        
        # Clear the target sheet
        range_name = f"{sheet_name}!A:Z"
        clear_sheet_range(spreadsheet_id, range_name, service)
        
        # Import JSON data to sheet
        success = import_json_to_sheet(spreadsheet_id, f"{sheet_name}!A1", backup_file, service, clear_first=False)
        
        if success:
            logger.info(f"Successfully restored {sheet_name} from {backup_file}")
        else:
            logger.error(f"Failed to restore {sheet_name} from {backup_file}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error restoring from JSON backup: {str(e)}")
        return False


def restore_from_backup_sheet(spreadsheet_id: str, target_sheet_name: str, backup_sheet_name: str, service) -> bool:
    """
    Restores a sheet from an in-spreadsheet backup sheet
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        target_sheet_name: Name of the sheet to restore
        backup_sheet_name: Name of the backup sheet
        service: Google Sheets API service
        
    Returns:
        True if restoration was successful, False otherwise
    """
    try:
        # Clear the target sheet
        target_range = f"{target_sheet_name}!A:Z"
        clear_sheet_range(spreadsheet_id, target_range, service)
        
        # Copy data from backup sheet to target sheet
        source_range = f"{backup_sheet_name}!A:Z"
        target_range = f"{target_sheet_name}!A1"
        
        result = copy_sheet_data(
            spreadsheet_id, source_range, 
            spreadsheet_id, target_range, 
            service
        )
        
        # The copy_sheet_data function returns a dictionary with API response details
        if result and isinstance(result, dict) and result.get('updatedCells', 0) > 0:
            logger.info(f"Successfully restored {target_sheet_name} from backup sheet {backup_sheet_name}")
            return True
        else:
            logger.error(f"Failed to restore {target_sheet_name} from backup sheet {backup_sheet_name}")
            return False
        
    except Exception as e:
        logger.error(f"Error restoring from backup sheet: {str(e)}")
        return False


def restore_master_budget(service, use_json_backup: bool, 
                         backup_file: Optional[str] = None, 
                         backup_sheet_name: Optional[str] = None) -> bool:
    """
    Restores the Master Budget sheet from backup
    
    Args:
        service: Google Sheets API service
        use_json_backup: Whether to use JSON backup file (True) or backup sheet (False)
        backup_file: Path to specific backup file (optional)
        backup_sheet_name: Name of specific backup sheet (optional)
        
    Returns:
        True if restoration was successful, False otherwise
    """
    try:
        logger.info(f"Starting Master Budget restoration from {'JSON backup' if use_json_backup else 'backup sheet'}")
        spreadsheet_id = APP_SETTINGS['MASTER_BUDGET_SHEET_ID']
        
        if use_json_backup:
            # If no specific backup file is provided, find the latest one
            if not backup_file:
                backup_file = find_latest_backup(MASTER_BUDGET_SHEET_NAME, BACKUP_DIR)
                if not backup_file:
                    logger.error("No backup file found for Master Budget")
                    return False
            
            # Restore from JSON backup
            result = restore_from_json_backup(spreadsheet_id, MASTER_BUDGET_SHEET_NAME, backup_file, service)
        else:
            # If no specific backup sheet is provided, find the latest one
            if not backup_sheet_name:
                backup_sheet_name = find_latest_backup_sheet(spreadsheet_id, MASTER_BUDGET_SHEET_NAME, service)
                if not backup_sheet_name:
                    logger.error("No backup sheet found for Master Budget")
                    return False
            
            # Restore from backup sheet
            result = restore_from_backup_sheet(spreadsheet_id, MASTER_BUDGET_SHEET_NAME, backup_sheet_name, service)
        
        if result:
            logger.info("Master Budget restoration completed successfully")
        else:
            logger.error("Master Budget restoration failed")
        
        return result
        
    except Exception as e:
        logger.error(f"Error restoring Master Budget: {str(e)}")
        return False


def restore_weekly_spending(service, use_json_backup: bool, 
                           backup_file: Optional[str] = None, 
                           backup_sheet_name: Optional[str] = None) -> bool:
    """
    Restores the Weekly Spending sheet from backup
    
    Args:
        service: Google Sheets API service
        use_json_backup: Whether to use JSON backup file (True) or backup sheet (False)
        backup_file: Path to specific backup file (optional)
        backup_sheet_name: Name of specific backup sheet (optional)
        
    Returns:
        True if restoration was successful, False otherwise
    """
    try:
        logger.info(f"Starting Weekly Spending restoration from {'JSON backup' if use_json_backup else 'backup sheet'}")
        spreadsheet_id = APP_SETTINGS['WEEKLY_SPENDING_SHEET_ID']
        
        if use_json_backup:
            # If no specific backup file is provided, find the latest one
            if not backup_file:
                backup_file = find_latest_backup(WEEKLY_SPENDING_SHEET_NAME, BACKUP_DIR)
                if not backup_file:
                    logger.error("No backup file found for Weekly Spending")
                    return False
            
            # Restore from JSON backup
            result = restore_from_json_backup(spreadsheet_id, WEEKLY_SPENDING_SHEET_NAME, backup_file, service)
        else:
            # If no specific backup sheet is provided, find the latest one
            if not backup_sheet_name:
                backup_sheet_name = find_latest_backup_sheet(spreadsheet_id, WEEKLY_SPENDING_SHEET_NAME, service)
                if not backup_sheet_name:
                    logger.error("No backup sheet found for Weekly Spending")
                    return False
            
            # Restore from backup sheet
            result = restore_from_backup_sheet(spreadsheet_id, WEEKLY_SPENDING_SHEET_NAME, backup_sheet_name, service)
        
        if result:
            logger.info("Weekly Spending restoration completed successfully")
        else:
            logger.error("Weekly Spending restoration failed")
        
        return result
        
    except Exception as e:
        logger.error(f"Error restoring Weekly Spending: {str(e)}")
        return False


def restore_from_latest(use_json_backup: bool, backup_dir: str) -> bool:
    """
    Restores both sheets from their latest backups
    
    Args:
        use_json_backup: Whether to use JSON backup files (True) or backup sheets (False)
        backup_dir: Directory containing backup files
        
    Returns:
        True if restoration was successful, False otherwise
    """
    try:
        logger.info(f"Starting restoration from latest {'JSON backups' if use_json_backup else 'backup sheets'}")
        
        # Create Google Sheets service
        service = get_sheets_service()
        
        # Restore Master Budget
        master_result = restore_master_budget(service, use_json_backup)
        
        # Restore Weekly Spending
        weekly_result = restore_weekly_spending(service, use_json_backup)
        
        # Return success if both restorations were successful
        overall_result = master_result and weekly_result
        logger.info(f"Overall restoration {'successful' if overall_result else 'failed'}")
        return overall_result
        
    except Exception as e:
        logger.error(f"Error in restoration process: {str(e)}")
        return False


def restore_from_specific_date(target_date: datetime.datetime, use_json_backup: bool, backup_dir: str) -> bool:
    """
    Restores both sheets from backups closest to a specific date
    
    Args:
        target_date: Target date to find closest backups to
        use_json_backup: Whether to use JSON backup files (True) or backup sheets (False)
        backup_dir: Directory containing backup files
        
    Returns:
        True if restoration was successful, False otherwise
    """
    try:
        logger.info(f"Starting restoration from {'JSON backups' if use_json_backup else 'backup sheets'} close to {target_date}")
        
        # Create Google Sheets service
        service = get_sheets_service()
        
        master_budget_id = APP_SETTINGS['MASTER_BUDGET_SHEET_ID']
        weekly_spending_id = APP_SETTINGS['WEEKLY_SPENDING_SHEET_ID']
        
        if use_json_backup:
            # Find backup files closest to target date
            master_backup = find_backup_by_date(MASTER_BUDGET_SHEET_NAME, target_date, backup_dir)
            weekly_backup = find_backup_by_date(WEEKLY_SPENDING_SHEET_NAME, target_date, backup_dir)
            
            # Restore Master Budget
            master_result = False
            if master_backup:
                master_result = restore_master_budget(service, True, backup_file=master_backup)
            else:
                logger.error(f"No Master Budget backup found near {target_date}")
            
            # Restore Weekly Spending
            weekly_result = False
            if weekly_backup:
                weekly_result = restore_weekly_spending(service, True, backup_file=weekly_backup)
            else:
                logger.error(f"No Weekly Spending backup found near {target_date}")
        else:
            # Find backup sheets closest to target date
            master_backup = find_backup_sheet_by_date(master_budget_id, MASTER_BUDGET_SHEET_NAME, target_date, service)
            weekly_backup = find_backup_sheet_by_date(weekly_spending_id, WEEKLY_SPENDING_SHEET_NAME, target_date, service)
            
            # Restore Master Budget
            master_result = False
            if master_backup:
                master_result = restore_master_budget(service, False, backup_sheet_name=master_backup)
            else:
                logger.error(f"No Master Budget backup sheet found near {target_date}")
            
            # Restore Weekly Spending
            weekly_result = False
            if weekly_backup:
                weekly_result = restore_weekly_spending(service, False, backup_sheet_name=weekly_backup)
            else:
                logger.error(f"No Weekly Spending backup sheet found near {target_date}")
        
        # Return success if both restorations were successful
        overall_result = master_result and weekly_result
        logger.info(f"Overall restoration {'successful' if overall_result else 'failed'}")
        return overall_result
        
    except Exception as e:
        logger.error(f"Error in date-specific restoration process: {str(e)}")
        return False


def parse_args():
    """
    Parses command line arguments for the restore script
    
    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Restore Google Sheets data from backups'
    )
    
    # Backup type options
    parser.add_argument('--json-only', action='store_true', 
                       help='Restore only from JSON backup files')
    parser.add_argument('--sheet-only', action='store_true', 
                       help='Restore only from in-spreadsheet backup sheets')
    
    # Backup directory
    parser.add_argument('--backup-dir', type=str, default=BACKUP_DIR,
                       help='Directory containing backup files')
    
    # Date option
    parser.add_argument('--date', type=str, 
                       help='Restore from backups closest to this date (YYYY-MM-DD)')
    
    # Sheet selection options
    parser.add_argument('--master-budget-only', action='store_true',
                       help='Restore only Master Budget sheet')
    parser.add_argument('--weekly-spending-only', action='store_true',
                       help='Restore only Weekly Spending sheet')
    
    return parser.parse_args()


def main() -> int:
    """
    Main function to execute the restoration process
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Parse command line arguments
        args = parse_args()
        
        # Determine backup type
        use_json_backup = True
        if args.json_only and args.sheet_only:
            logger.error("Cannot use both --json-only and --sheet-only at the same time")
            return 1
        elif args.sheet_only:
            use_json_backup = False
        
        # Get backup directory
        backup_dir = args.backup_dir
        ensure_dir_exists(backup_dir)
        
        # Create Google Sheets service
        service = get_sheets_service()
        
        # Restore from specific date if provided
        if args.date:
            try:
                target_date = datetime.datetime.strptime(args.date, "%Y-%m-%d")
                
                # Handle sheet selection
                if args.master_budget_only:
                    if use_json_backup:
                        backup_file = find_backup_by_date(MASTER_BUDGET_SHEET_NAME, target_date, backup_dir)
                        if not backup_file:
                            logger.error(f"No Master Budget backup found near {target_date}")
                            return 1
                        result = restore_master_budget(service, True, backup_file=backup_file)
                    else:
                        spreadsheet_id = APP_SETTINGS['MASTER_BUDGET_SHEET_ID']
                        backup_sheet = find_backup_sheet_by_date(spreadsheet_id, MASTER_BUDGET_SHEET_NAME, target_date, service)
                        if not backup_sheet:
                            logger.error(f"No Master Budget backup sheet found near {target_date}")
                            return 1
                        result = restore_master_budget(service, False, backup_sheet_name=backup_sheet)
                elif args.weekly_spending_only:
                    if use_json_backup:
                        backup_file = find_backup_by_date(WEEKLY_SPENDING_SHEET_NAME, target_date, backup_dir)
                        if not backup_file:
                            logger.error(f"No Weekly Spending backup found near {target_date}")
                            return 1
                        result = restore_weekly_spending(service, True, backup_file=backup_file)
                    else:
                        spreadsheet_id = APP_SETTINGS['WEEKLY_SPENDING_SHEET_ID']
                        backup_sheet = find_backup_sheet_by_date(spreadsheet_id, WEEKLY_SPENDING_SHEET_NAME, target_date, service)
                        if not backup_sheet:
                            logger.error(f"No Weekly Spending backup sheet found near {target_date}")
                            return 1
                        result = restore_weekly_spending(service, False, backup_sheet_name=backup_sheet)
                else:
                    # Restore both sheets
                    result = restore_from_specific_date(target_date, use_json_backup, backup_dir)
            except ValueError:
                logger.error(f"Invalid date format: {args.date}. Use YYYY-MM-DD.")
                return 1
        else:
            # Restore from latest backups
            if args.master_budget_only:
                result = restore_master_budget(service, use_json_backup)
            elif args.weekly_spending_only:
                result = restore_weekly_spending(service, use_json_backup)
            else:
                # Restore both sheets
                result = restore_from_latest(use_json_backup, backup_dir)
        
        if result:
            logger.info("Restoration completed successfully")
            return 0
        else:
            logger.error("Restoration failed")
            return 1
        
    except Exception as e:
        logger.error(f"Unhandled error in restoration process: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())