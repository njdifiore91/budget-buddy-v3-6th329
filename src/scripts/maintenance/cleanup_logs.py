#!/usr/bin/env python3
"""
Maintenance script that cleans up old log files from the application's logs directory
based on the configured retention period. Helps manage disk space and maintain system
performance by removing outdated logs that are no longer needed.
"""

import os
import datetime
import argparse
import sys

from ../../scripts.config.logging_setup import get_logger, LoggingContext
from ../../scripts.config.path_constants import LOGS_DIR
from ../../scripts.config.script_settings import MAINTENANCE_SETTINGS

# Set up logger
logger = get_logger('cleanup_logs')


def get_file_age_days(file_path):
    """
    Calculates the age of a file in days based on its modification time.
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        float: Age of the file in days
    """
    # Get the file's modification time
    mod_time = os.path.getmtime(file_path)
    # Convert to datetime object
    mod_datetime = datetime.datetime.fromtimestamp(mod_time)
    # Get current time
    current_datetime = datetime.datetime.now()
    # Calculate difference
    age_delta = current_datetime - mod_datetime
    # Return age in days
    return age_delta.total_seconds() / (24 * 3600)


def is_log_file(file_name):
    """
    Checks if a file is a log file based on its extension.
    
    Args:
        file_name (str): Name of the file
        
    Returns:
        bool: True if the file is a log file, False otherwise
    """
    # Common log file extensions
    log_extensions = ['.log', '.json']
    # Check if the file has a log extension
    return any(file_name.lower().endswith(ext) for ext in log_extensions)


def cleanup_logs(retention_days, dry_run=False):
    """
    Cleans up log files older than the specified retention period.
    
    Args:
        retention_days (int): Retention period in days
        dry_run (bool): If True, only simulate deletion without actually removing files
        
    Returns:
        tuple: (int, int) - Count of deleted files and total size freed
    """
    logger.info(f"Starting log cleanup with retention period of {retention_days} days")
    
    # Initialize counters
    deleted_count = 0
    freed_space = 0
    
    # Ensure LOGS_DIR exists
    if not os.path.exists(LOGS_DIR):
        logger.warning(f"Logs directory {LOGS_DIR} does not exist")
        return 0, 0
    
    # Iterate through files in the logs directory
    for filename in os.listdir(LOGS_DIR):
        file_path = os.path.join(LOGS_DIR, filename)
        
        # Skip directories
        if os.path.isdir(file_path):
            continue
        
        # Check if it's a log file
        if is_log_file(filename):
            try:
                # Calculate file age
                file_age_days = get_file_age_days(file_path)
                
                # If the file is older than the retention period, delete it
                if file_age_days > retention_days:
                    # Get file size before deletion
                    file_size = os.path.getsize(file_path)
                    
                    if dry_run:
                        logger.info(f"Would delete: {filename} (Age: {file_age_days:.1f} days, Size: {file_size/1024:.1f} KB)")
                    else:
                        # Delete the file
                        os.remove(file_path)
                        logger.info(f"Deleted: {filename} (Age: {file_age_days:.1f} days, Size: {file_size/1024:.1f} KB)")
                        
                        # Update counters
                        deleted_count += 1
                        freed_space += file_size
            except Exception as e:
                logger.error(f"Error processing file {filename}: {str(e)}")
    
    # Log summary
    if dry_run:
        logger.info(f"Dry run completed. Would have deleted {deleted_count} files, freeing {freed_space/1024/1024:.2f} MB")
    else:
        logger.info(f"Cleanup completed. Deleted {deleted_count} files, freed {freed_space/1024/1024:.2f} MB")
    
    return deleted_count, freed_space


def parse_arguments():
    """
    Parses command-line arguments for the script.
    
    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Clean up old log files to free disk space"
    )
    
    parser.add_argument(
        "--retention-days",
        type=int,
        default=MAINTENANCE_SETTINGS.get('LOG_RETENTION_DAYS', 30),
        help="Number of days to retain log files (default: %(default)s)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate deletion without actually removing files"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args()


def main():
    """
    Main entry point for the script.
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Parse command-line arguments
    args = parse_arguments()
    
    try:
        # Use LoggingContext for consistent logging
        with LoggingContext(logger, operation="cleanup_logs"):
            logger.info(f"Starting log cleanup with retention period of {args.retention_days} days")
            logger.info(f"Dry run mode: {args.dry_run}")
            
            # Call cleanup_logs function
            deleted_count, freed_space = cleanup_logs(
                retention_days=args.retention_days,
                dry_run=args.dry_run
            )
            
            logger.info(f"Log cleanup completed. " +
                       f"{'Would have deleted' if args.dry_run else 'Deleted'} " +
                       f"{deleted_count} files, " +
                       f"{'would have freed' if args.dry_run else 'freed'} " +
                       f"{freed_space/1024/1024:.2f} MB")
        
        return 0
    except Exception as e:
        logger.error(f"Error during log cleanup: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())