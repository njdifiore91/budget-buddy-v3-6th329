"""
Script for creating backups of Google Sheets data used by the Budget Management Application.
Provides functionality to backup both the Master Budget and Weekly Spending sheets to JSON files
and create timestamped backup sheets within the same spreadsheets.
"""

import os
import argparse
import datetime
import sys
from typing import List, Dict, Optional, Any

# Internal imports
from ..config.logging_setup import get_logger
from ..config.path_constants import BACKUP_DIR, ensure_dir_exists
from ..config.script_settings import MAINTENANCE_SETTINGS
from ...backend.config.settings import APP_SETTINGS
from ..utils.sheet_operations import (
    get_sheets_service,
    export_sheet_to_json,
    create_backup_sheet,
    list_sheets
)

# Set up logger
logger = get_logger(__name__)

# Constants
WEEKLY_SPENDING_SHEET_NAME = "Weekly Spending"
MASTER_BUDGET_SHEET_NAME = "Master Budget"
DEFAULT_BACKUP_SHEETS_LIMIT = 5


def backup_sheet_to_json(spreadsheet_id: str, sheet_name: str, service, backup_dir: str) -> str:
    """
    Backs up a Google Sheet to a JSON file with timestamp
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        sheet_name: Name of the sheet to backup
        service: Google Sheets API service
        backup_dir: Directory to store the backup file
        
    Returns:
        Path to the created backup file
    """
    try:
        # Generate timestamp for the backup file name
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create backup file name
        backup_file_name = f"{sheet_name}_backup_{timestamp}.json"
        
        # Ensure backup directory exists
        ensure_dir_exists(backup_dir)
        
        # Create full backup file path
        backup_file_path = os.path.join(backup_dir, backup_file_name)
        
        # Export sheet to JSON
        export_success = export_sheet_to_json(
            spreadsheet_id,
            sheet_name,
            backup_file_path,
            service
        )
        
        if not export_success:
            logger.error(f"Failed to export {sheet_name} to JSON file")
            return ""
        
        logger.info(f"Successfully backed up {sheet_name} to {backup_file_path}")
        return backup_file_path
    
    except Exception as e:
        logger.error(f"Error backing up {sheet_name} to JSON: {str(e)}")
        return ""


def create_in_spreadsheet_backup(spreadsheet_id: str, sheet_name: str, service) -> str:
    """
    Creates a backup sheet within the same spreadsheet with timestamp
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        sheet_name: Name of the sheet to backup
        service: Google Sheets API service
        
    Returns:
        Name of the created backup sheet
    """
    try:
        # Create backup sheet within the spreadsheet
        backup_sheet_name = create_backup_sheet(spreadsheet_id, sheet_name, service)
        
        if not backup_sheet_name:
            logger.error(f"Failed to create backup sheet for {sheet_name}")
            return ""
        
        logger.info(f"Successfully created backup sheet {backup_sheet_name}")
        return backup_sheet_name
    
    except Exception as e:
        logger.error(f"Error creating in-spreadsheet backup for {sheet_name}: {str(e)}")
        return ""


def cleanup_old_backup_sheets(spreadsheet_id: str, original_sheet_name: str, service, keep_limit: int) -> int:
    """
    Removes old backup sheets keeping only the most recent ones
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        original_sheet_name: Name of the original sheet
        service: Google Sheets API service
        keep_limit: Number of backup sheets to keep
        
    Returns:
        Number of backup sheets removed
    """
    try:
        # Get list of all sheets in the spreadsheet
        all_sheets = list_sheets(spreadsheet_id, service)
        if not all_sheets:
            logger.warning(f"No sheets found in spreadsheet {spreadsheet_id}")
            return 0
        
        # Find backup sheets for the original sheet
        backup_prefix = f"Backup_{original_sheet_name}_"
        backup_sheets = []
        
        for sheet_name, sheet_id in all_sheets.items():
            if sheet_name.startswith(backup_prefix):
                # Extract timestamp from sheet name
                try:
                    timestamp_str = sheet_name.replace(backup_prefix, "")
                    timestamp = datetime.datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    backup_sheets.append((sheet_name, sheet_id, timestamp))
                except ValueError:
                    # Skip sheets with invalid timestamp format
                    logger.warning(f"Skipping sheet with invalid timestamp format: {sheet_name}")
                    continue
        
        # Sort backup sheets by timestamp (newest first)
        backup_sheets.sort(key=lambda x: x[2], reverse=True)
        
        # If we have more backups than the keep limit, delete the oldest ones
        sheets_to_remove = backup_sheets[keep_limit:] if len(backup_sheets) > keep_limit else []
        removed_count = 0
        
        for sheet_name, sheet_id, _ in sheets_to_remove:
            try:
                # Delete sheet from spreadsheet
                delete_request = {
                    'deleteSheet': {
                        'sheetId': sheet_id
                    }
                }
                
                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={'requests': [delete_request]}
                ).execute()
                
                logger.info(f"Deleted old backup sheet: {sheet_name}")
                removed_count += 1
            except Exception as e:
                logger.error(f"Error deleting backup sheet {sheet_name}: {str(e)}")
        
        return removed_count
    
    except Exception as e:
        logger.error(f"Error cleaning up old backup sheets: {str(e)}")
        return 0


def backup_master_budget(service, json_backup: bool, sheet_backup: bool, backup_dir: str) -> bool:
    """
    Creates backups of the Master Budget sheet
    
    Args:
        service: Google Sheets API service
        json_backup: Whether to create JSON backup
        sheet_backup: Whether to create in-spreadsheet backup
        backup_dir: Directory to store JSON backups
        
    Returns:
        True if backup was successful
    """
    try:
        logger.info("Starting Master Budget backup")
        spreadsheet_id = APP_SETTINGS.get('MASTER_BUDGET_SHEET_ID')
        
        if not spreadsheet_id:
            logger.error("Master Budget spreadsheet ID not found in settings")
            return False
        
        success = True
        
        # Create JSON backup if requested
        if json_backup:
            json_path = backup_sheet_to_json(
                spreadsheet_id,
                MASTER_BUDGET_SHEET_NAME,
                service,
                backup_dir
            )
            if not json_path:
                logger.warning("JSON backup of Master Budget failed")
                success = False
        
        # Create in-spreadsheet backup if requested
        if sheet_backup:
            backup_sheet_name = create_in_spreadsheet_backup(
                spreadsheet_id,
                MASTER_BUDGET_SHEET_NAME,
                service
            )
            if not backup_sheet_name:
                logger.warning("In-spreadsheet backup of Master Budget failed")
                success = False
            else:
                # Cleanup old backup sheets
                removed_count = cleanup_old_backup_sheets(
                    spreadsheet_id,
                    MASTER_BUDGET_SHEET_NAME,
                    service,
                    DEFAULT_BACKUP_SHEETS_LIMIT
                )
                logger.info(f"Removed {removed_count} old Master Budget backup sheets")
        
        logger.info("Master Budget backup completed successfully")
        return success
    
    except Exception as e:
        logger.error(f"Error during Master Budget backup: {str(e)}")
        return False


def backup_weekly_spending(service, json_backup: bool, sheet_backup: bool, backup_dir: str) -> bool:
    """
    Creates backups of the Weekly Spending sheet
    
    Args:
        service: Google Sheets API service
        json_backup: Whether to create JSON backup
        sheet_backup: Whether to create in-spreadsheet backup
        backup_dir: Directory to store JSON backups
        
    Returns:
        True if backup was successful
    """
    try:
        logger.info("Starting Weekly Spending backup")
        spreadsheet_id = APP_SETTINGS.get('WEEKLY_SPENDING_SHEET_ID')
        
        if not spreadsheet_id:
            logger.error("Weekly Spending spreadsheet ID not found in settings")
            return False
        
        success = True
        
        # Create JSON backup if requested
        if json_backup:
            json_path = backup_sheet_to_json(
                spreadsheet_id,
                WEEKLY_SPENDING_SHEET_NAME,
                service,
                backup_dir
            )
            if not json_path:
                logger.warning("JSON backup of Weekly Spending failed")
                success = False
        
        # Create in-spreadsheet backup if requested
        if sheet_backup:
            backup_sheet_name = create_in_spreadsheet_backup(
                spreadsheet_id,
                WEEKLY_SPENDING_SHEET_NAME,
                service
            )
            if not backup_sheet_name:
                logger.warning("In-spreadsheet backup of Weekly Spending failed")
                success = False
            else:
                # Cleanup old backup sheets
                removed_count = cleanup_old_backup_sheets(
                    spreadsheet_id,
                    WEEKLY_SPENDING_SHEET_NAME,
                    service,
                    DEFAULT_BACKUP_SHEETS_LIMIT
                )
                logger.info(f"Removed {removed_count} old Weekly Spending backup sheets")
        
        logger.info("Weekly Spending backup completed successfully")
        return success
    
    except Exception as e:
        logger.error(f"Error during Weekly Spending backup: {str(e)}")
        return False


def parse_args():
    """
    Parses command line arguments for the backup script
    
    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Create backups of Google Sheets data used by the Budget Management Application"
    )
    
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Only create JSON backups (skip in-spreadsheet backups)"
    )
    
    parser.add_argument(
        "--sheet-only",
        action="store_true",
        help="Only create in-spreadsheet backups (skip JSON backups)"
    )
    
    parser.add_argument(
        "--backup-dir",
        type=str,
        help=f"Directory to store JSON backups (default: {BACKUP_DIR})"
    )
    
    parser.add_argument(
        "--keep-limit",
        type=int,
        default=DEFAULT_BACKUP_SHEETS_LIMIT,
        help=f"Number of backup sheets to keep (default: {DEFAULT_BACKUP_SHEETS_LIMIT})"
    )
    
    return parser.parse_args()


def main() -> int:
    """
    Main function to execute the backup process
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Parse command line arguments
        args = parse_args()
        
        # Determine backup types based on arguments
        json_backup = not args.sheet_only
        sheet_backup = not args.json_only
        
        # If both are specified, disable both (no backups would be created)
        if args.json_only and args.sheet_only:
            logger.error("Cannot specify both --json-only and --sheet-only")
            return 1
        
        # Set backup directory
        backup_dir = args.backup_dir if args.backup_dir else BACKUP_DIR
        
        # Ensure backup directory exists
        ensure_dir_exists(backup_dir)
        logger.info(f"Using backup directory: {backup_dir}")
        
        # Create Google Sheets service
        service = get_sheets_service()
        if not service:
            logger.error("Failed to create Google Sheets service")
            return 1
        
        # Backup Master Budget
        master_budget_success = backup_master_budget(service, json_backup, sheet_backup, backup_dir)
        
        # Backup Weekly Spending
        weekly_spending_success = backup_weekly_spending(service, json_backup, sheet_backup, backup_dir)
        
        # Return success if both backups succeeded
        if master_budget_success and weekly_spending_success:
            logger.info("All backups completed successfully")
            return 0
        else:
            logger.error("Some backups failed")
            return 1
    
    except Exception as e:
        logger.error(f"Unhandled error in backup script: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())