#!/usr/bin/env python3
"""
Manages the scheduling of Google Sheets backups for the Budget Management Application.

This script determines when backups should be performed based on configured intervals,
executes the backup process, and tracks backup history to ensure regular data protection.
"""

import os
import sys
import argparse
import datetime
import json
from typing import List, Dict, Optional, Any

# Internal imports
from ..config.logging_setup import get_logger
from ..config.script_settings import MAINTENANCE_SETTINGS
from ..config.path_constants import BACKUP_DIR, ensure_dir_exists
from ..maintenance.backup_sheets import main as backup_sheets_main

# Set up logger
logger = get_logger(__name__)

# Global constants
BACKUP_HISTORY_FILE = os.path.join(BACKUP_DIR, 'backup_history.json')
DEFAULT_BACKUP_TYPES = ['json', 'sheet']


def load_backup_history() -> dict:
    """
    Loads the backup history from the JSON file

    Returns:
        dict: Backup history containing last backup timestamps
    """
    try:
        # Ensure the backup directory exists
        ensure_dir_exists(BACKUP_DIR)

        # Check if the backup history file exists
        if os.path.exists(BACKUP_HISTORY_FILE):
            with open(BACKUP_HISTORY_FILE, 'r') as f:
                history = json.load(f)
                logger.debug(f"Loaded backup history from {BACKUP_HISTORY_FILE}")
                return history
        else:
            # If file doesn't exist, create default history structure
            logger.info(f"Backup history file not found. Creating new history.")
            return {
                "last_backup": {
                    "json": None,
                    "sheet": None
                }
            }
    except Exception as e:
        logger.error(f"Error loading backup history: {str(e)}")
        # Return a default history structure in case of error
        return {
            "last_backup": {
                "json": None,
                "sheet": None
            }
        }


def save_backup_history(history: dict) -> bool:
    """
    Saves the backup history to the JSON file

    Args:
        history: Backup history to save

    Returns:
        bool: True if save was successful
    """
    try:
        # Ensure the backup directory exists
        ensure_dir_exists(BACKUP_DIR)

        # Write history to JSON file with pretty formatting
        with open(BACKUP_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=4)
        
        logger.debug(f"Saved backup history to {BACKUP_HISTORY_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error saving backup history: {str(e)}")
        return False


def update_backup_history(backup_type: str) -> bool:
    """
    Updates the backup history with a new successful backup

    Args:
        backup_type: Type of backup performed (json or sheet)

    Returns:
        bool: True if update was successful
    """
    try:
        # Load current backup history
        history = load_backup_history()
        
        # Get current timestamp in ISO format
        current_time = datetime.datetime.now().isoformat()
        
        # Update the last backup timestamp for the specified type
        if "last_backup" not in history:
            history["last_backup"] = {}
        
        history["last_backup"][backup_type] = current_time
        
        # Save updated history
        success = save_backup_history(history)
        
        if success:
            logger.info(f"Updated backup history for {backup_type} backup")
        
        return success
    except Exception as e:
        logger.error(f"Error updating backup history: {str(e)}")
        return False


def is_backup_due(backup_type: str) -> bool:
    """
    Checks if a backup is due based on the configured interval

    Args:
        backup_type: Type of backup to check (json or sheet)

    Returns:
        bool: True if backup is due, False otherwise
    """
    try:
        # Load backup history
        history = load_backup_history()
        
        # Get the backup interval from settings (in days)
        backup_interval = MAINTENANCE_SETTINGS.get('BACKUP_INTERVAL', 7)
        
        # Get the last backup timestamp for the specified type
        last_backup = None
        if "last_backup" in history and backup_type in history["last_backup"]:
            last_backup = history["last_backup"][backup_type]
        
        # If no previous backup exists, a backup is due
        if not last_backup:
            logger.info(f"No previous {backup_type} backup found. Backup is due.")
            return True
        
        # Parse the last backup timestamp to datetime object
        last_backup_time = datetime.datetime.fromisoformat(last_backup)
        
        # Calculate the time elapsed since last backup
        now = datetime.datetime.now()
        elapsed_days = (now - last_backup_time).total_seconds() / (24 * 3600)  # Convert to days
        
        # Check if elapsed time exceeds the configured interval
        is_due = elapsed_days >= backup_interval
        
        if is_due:
            logger.info(f"{backup_type} backup is due. Last backup was {elapsed_days:.1f} days ago.")
        else:
            logger.debug(f"{backup_type} backup is not due. Last backup was {elapsed_days:.1f} days ago.")
        
        return is_due
    except Exception as e:
        logger.error(f"Error checking if backup is due: {str(e)}")
        # In case of error, assume backup is due as a safety measure
        return True


def get_next_backup_time(backup_type: str) -> datetime.datetime:
    """
    Calculates the next scheduled backup time

    Args:
        backup_type: Type of backup to check (json or sheet)

    Returns:
        datetime.datetime: Next scheduled backup time
    """
    try:
        # Load backup history
        history = load_backup_history()
        
        # Get the backup interval from settings (in days)
        backup_interval = MAINTENANCE_SETTINGS.get('BACKUP_INTERVAL', 7)
        
        # Get the last backup timestamp for the specified type
        last_backup = None
        if "last_backup" in history and backup_type in history["last_backup"]:
            last_backup = history["last_backup"][backup_type]
        
        # If no previous backup exists, return current time (backup should happen now)
        if not last_backup:
            return datetime.datetime.now()
        
        # Parse the last backup timestamp to datetime object
        last_backup_time = datetime.datetime.fromisoformat(last_backup)
        
        # Calculate next backup time by adding the interval
        next_backup_time = last_backup_time + datetime.timedelta(days=backup_interval)
        
        return next_backup_time
    except Exception as e:
        logger.error(f"Error calculating next backup time: {str(e)}")
        # In case of error, return current time (backup should happen now as a safety measure)
        return datetime.datetime.now()


def perform_backup(backup_types: List[str] = None, force: bool = False) -> bool:
    """
    Performs backup if due based on the configured interval

    Args:
        backup_types: Types of backup to perform (json, sheet, or both)
        force: Force backup regardless of schedule

    Returns:
        bool: True if backup was performed
    """
    try:
        # Use default backup types if none specified
        if not backup_types:
            backup_types = DEFAULT_BACKUP_TYPES
        
        # Check if any backup type is due
        backup_due = force or any(is_backup_due(backup_type) for backup_type in backup_types)
        
        if not backup_due:
            logger.info("No backup is currently due. Use --force to override.")
            return False
        
        # Prepare arguments for backup_sheets_main
        args = []
        
        # Set backup types based on input
        if 'json' in backup_types and 'sheet' not in backup_types:
            args.append('--json-only')
        elif 'sheet' in backup_types and 'json' not in backup_types:
            args.append('--sheet-only')
        
        logger.info(f"Executing backup with types: {', '.join(backup_types)}")
        
        # Execute backup using backup_sheets_main
        original_argv = sys.argv
        sys.argv = [original_argv[0]] + args
        backup_result = backup_sheets_main()
        sys.argv = original_argv
        
        # Check if backup was successful (exit code 0)
        if backup_result == 0:
            logger.info("Backup completed successfully")
            
            # Update backup history for each type
            for backup_type in backup_types:
                update_backup_history(backup_type)
            
            return True
        else:
            logger.error(f"Backup failed with exit code {backup_result}")
            return False
    except Exception as e:
        logger.error(f"Error performing backup: {str(e)}")
        return False


def parse_args():
    """
    Parses command line arguments for the backup schedule script

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Schedule and manage Google Sheets backups for the Budget Management Application"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force backup regardless of schedule"
    )
    
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check if backup is due, don't perform backup"
    )
    
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Only perform JSON backup (skip in-spreadsheet backup)"
    )
    
    parser.add_argument(
        "--sheet-only",
        action="store_true",
        help="Only perform in-spreadsheet backup (skip JSON backup)"
    )
    
    return parser.parse_args()


def main() -> int:
    """
    Main function to execute the backup scheduling process

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        # Parse command line arguments
        args = parse_args()
        
        # Determine backup types based on arguments
        backup_types = []
        if args.json_only:
            backup_types = ['json']
        elif args.sheet_only:
            backup_types = ['sheet']
        else:
            backup_types = DEFAULT_BACKUP_TYPES
        
        # If check-only flag is set, just check if backup is due and exit
        if args.check_only:
            due_types = [t for t in backup_types if is_backup_due(t)]
            if due_types:
                logger.info(f"Backup is due for types: {', '.join(due_types)}")
                for t in due_types:
                    next_time = get_next_backup_time(t)
                    logger.info(f"Next scheduled {t} backup: {next_time.isoformat()}")
                return 0
            else:
                logger.info("No backup is currently due")
                for t in backup_types:
                    next_time = get_next_backup_time(t)
                    logger.info(f"Next scheduled {t} backup: {next_time.isoformat()}")
                return 0
        
        # Perform backup with specified types and force flag
        success = perform_backup(backup_types, args.force)
        
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Unhandled error in backup schedule script: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())