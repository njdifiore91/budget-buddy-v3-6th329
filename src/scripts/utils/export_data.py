"""
Utility script for exporting data from the Budget Management Application's Google Sheets to various formats
(JSON, CSV, Excel) for backup, analysis, or reporting purposes. Provides functions to export transaction data,
budget data, and analysis results with proper formatting and data validation.
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
from ..config.path_constants import BACKUP_DIR, ensure_dir_exists
from ..config.script_settings import SCRIPT_SETTINGS, MAINTENANCE_SETTINGS, MAX_RETRIES
from .sheet_operations import (
    get_sheets_service, 
    read_sheet, 
    get_sheet_as_dataframe, 
    export_sheet_to_json
)

# Set up logger
logger = get_logger(__name__)

# Global constants
DEFAULT_EXPORT_FORMATS = ["json", "csv", "excel"]
WEEKLY_SPENDING_SHEET_ID = os.getenv("WEEKLY_SPENDING_SHEET_ID", "")
MASTER_BUDGET_SHEET_ID = os.getenv("MASTER_BUDGET_SHEET_ID", "")
WEEKLY_SPENDING_RANGE = "Weekly Spending!A1:D"
MASTER_BUDGET_RANGE = "Master Budget!A1:B"


def generate_export_filename(base_name: str, export_format: str, 
                           timestamp: Optional[datetime.datetime] = None) -> str:
    """
    Generates a filename for exported data with timestamp
    
    Args:
        base_name: Base name for the file
        export_format: Export format extension
        timestamp: Timestamp to use (defaults to current time)
        
    Returns:
        Formatted filename with timestamp
    """
    if timestamp is None:
        timestamp = datetime.datetime.now()
    
    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp_str}.{export_format}"


def export_to_json(df: pd.DataFrame, output_path: str, pretty_print: bool = True) -> bool:
    """
    Exports data to a JSON file
    
    Args:
        df: DataFrame to export
        output_path: Path to output file
        pretty_print: Whether to format JSON with indentation
        
    Returns:
        True if export was successful
    """
    try:
        # Convert DataFrame to dictionary records
        records = df.to_dict(orient='records')
        
        # Write to JSON file
        with open(output_path, 'w') as file:
            if pretty_print:
                json.dump(records, file, indent=2)
            else:
                json.dump(records, file)
                
        logger.info(f"Successfully exported data to JSON: {output_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error exporting to JSON: {str(e)}")
        return False


def export_to_csv(df: pd.DataFrame, output_path: str, 
                delimiter: str = ',', include_header: bool = True) -> bool:
    """
    Exports data to a CSV file
    
    Args:
        df: DataFrame to export
        output_path: Path to output file
        delimiter: CSV delimiter character
        include_header: Whether to include column headers
        
    Returns:
        True if export was successful
    """
    try:
        # Use pandas to_csv method
        df.to_csv(output_path, sep=delimiter, index=False, header=include_header)
        
        logger.info(f"Successfully exported data to CSV: {output_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error exporting to CSV: {str(e)}")
        return False


def export_to_excel(df: pd.DataFrame, output_path: str, 
                  sheet_name: str = 'Sheet1', include_header: bool = True) -> bool:
    """
    Exports data to an Excel file
    
    Args:
        df: DataFrame to export
        output_path: Path to output file
        sheet_name: Name of the sheet in the Excel file
        include_header: Whether to include column headers
        
    Returns:
        True if export was successful
    """
    try:
        # Use pandas to_excel method
        df.to_excel(output_path, sheet_name=sheet_name, index=False, header=include_header)
        
        logger.info(f"Successfully exported data to Excel: {output_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error exporting to Excel: {str(e)}")
        return False


def export_sheet_data(spreadsheet_id: str, range_name: str, export_format: str, 
                     output_dir: str, base_filename: str, service=None) -> str:
    """
    Exports Google Sheet data to specified format
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        range_name: Range to export (e.g., 'Sheet1!A1:D10')
        export_format: Format to export to (json, csv, excel)
        output_dir: Directory to save the exported file
        base_filename: Base name for the exported file
        service: Google Sheets API service (created if None)
        
    Returns:
        Path to exported file if successful, empty string otherwise
    """
    try:
        # If service is None, create service using get_sheets_service()
        if service is None:
            service = get_sheets_service()
        
        # Get sheet data as DataFrame using get_sheet_as_dataframe
        df = get_sheet_as_dataframe(spreadsheet_id, range_name, service=service)
        
        # If data is empty, log warning and return empty string
        if df.empty:
            logger.warning(f"No data found in range {range_name}")
            return ""
        
        # Ensure output_dir exists using ensure_dir_exists
        ensure_dir_exists(output_dir)
        
        # Generate filename using generate_export_filename
        filename = generate_export_filename(base_filename, export_format)
        
        # Create full output path by joining output_dir and filename
        output_path = os.path.join(output_dir, filename)
        
        # Export data based on export_format (json, csv, excel)
        success = False
        if export_format.lower() == 'json':
            success = export_to_json(df, output_path, pretty_print=True)
        elif export_format.lower() == 'csv':
            success = export_to_csv(df, output_path)
        elif export_format.lower() == 'excel':
            success = export_to_excel(df, output_path, sheet_name=base_filename)
        else:
            logger.error(f"Unsupported export format: {export_format}")
            return ""
        
        # Log success message with export format and path
        if success:
            logger.info(f"Successfully exported {range_name} to {export_format} format: {output_path}")
            return output_path
        
        # Return the path to exported file if successful
        return ""
    
    except Exception as e:
        # Handle and log any errors during export
        logger.error(f"Error exporting sheet data: {str(e)}")
        return ""


def export_weekly_spending(export_format: str, output_dir: str, service=None) -> str:
    """
    Exports Weekly Spending sheet data to specified format
    
    Args:
        export_format: Format to export to (json, csv, excel)
        output_dir: Directory to save the exported file
        service: Google Sheets API service (created if None)
        
    Returns:
        Path to exported file if successful, empty string otherwise
    """
    try:
        # If WEEKLY_SPENDING_SHEET_ID is empty, log error and return empty string
        if not WEEKLY_SPENDING_SHEET_ID:
            logger.error("WEEKLY_SPENDING_SHEET_ID environment variable is not set")
            return ""
            
        # Call export_sheet_data with Weekly Spending parameters
        return export_sheet_data(
            WEEKLY_SPENDING_SHEET_ID, 
            WEEKLY_SPENDING_RANGE,
            export_format,
            output_dir,
            "weekly_spending",
            service
        )
    except Exception as e:
        # Handle and log any errors during export
        logger.error(f"Error exporting Weekly Spending sheet: {str(e)}")
        return ""


def export_master_budget(export_format: str, output_dir: str, service=None) -> str:
    """
    Exports Master Budget sheet data to specified format
    
    Args:
        export_format: Format to export to (json, csv, excel)
        output_dir: Directory to save the exported file
        service: Google Sheets API service (created if None)
        
    Returns:
        Path to exported file if successful, empty string otherwise
    """
    try:
        # If MASTER_BUDGET_SHEET_ID is empty, log error and return empty string
        if not MASTER_BUDGET_SHEET_ID:
            logger.error("MASTER_BUDGET_SHEET_ID environment variable is not set")
            return ""
            
        # Call export_sheet_data with Master Budget parameters
        return export_sheet_data(
            MASTER_BUDGET_SHEET_ID,
            MASTER_BUDGET_RANGE,
            export_format,
            output_dir,
            "master_budget",
            service
        )
    except Exception as e:
        # Handle and log any errors during export
        logger.error(f"Error exporting Master Budget sheet: {str(e)}")
        return ""


def export_all_sheets(export_format: str, output_dir: str, service=None) -> Dict[str, str]:
    """
    Exports all budget-related sheets to specified format
    
    Args:
        export_format: Format to export to (json, csv, excel)
        output_dir: Directory to save the exported file
        service: Google Sheets API service (created if None)
        
    Returns:
        Dictionary mapping sheet names to export paths
    """
    try:
        # Initialize empty dictionary for results
        results = {}
        
        # Export Weekly Spending sheet using export_weekly_spending
        weekly_spending_path = export_weekly_spending(export_format, output_dir, service)
        if weekly_spending_path:
            results["weekly_spending"] = weekly_spending_path
        
        # Export Master Budget sheet using export_master_budget
        master_budget_path = export_master_budget(export_format, output_dir, service)
        if master_budget_path:
            results["master_budget"] = master_budget_path
        
        # Return the dictionary of export results
        return results
    except Exception as e:
        # Handle and log any errors during export
        logger.error(f"Error exporting all sheets: {str(e)}")
        return {}


def create_backup(formats: List[str] = None, backup_dir: str = None) -> Dict[str, Dict[str, str]]:
    """
    Creates a backup of all budget sheets in multiple formats
    
    Args:
        formats: List of formats to export (defaults to DEFAULT_EXPORT_FORMATS)
        backup_dir: Directory to save backups (defaults to BACKUP_DIR)
        
    Returns:
        Nested dictionary of backup results
    """
    try:
        # If formats is None or empty, use DEFAULT_EXPORT_FORMATS
        if formats is None or not formats:
            formats = DEFAULT_EXPORT_FORMATS
        
        # If backup_dir is None, use BACKUP_DIR
        if backup_dir is None:
            backup_dir = BACKUP_DIR
        
        # Create timestamp-based subdirectory in backup_dir
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_subdir = os.path.join(backup_dir, f"backup_{timestamp}")
        ensure_dir_exists(backup_subdir)
        
        # Initialize Google Sheets service
        service = get_sheets_service()
        
        # Initialize empty dictionary for results
        results = {}
        
        # For each format, export all sheets using export_all_sheets
        for export_format in formats:
            format_results = export_all_sheets(export_format, backup_subdir, service)
            if format_results:
                results[export_format] = format_results
        
        # Log backup completion with summary
        logger.info(f"Backup completed successfully to {backup_subdir} in formats: {', '.join(formats)}")
        return results
    except Exception as e:
        # Handle and log any errors during backup
        logger.error(f"Error creating backup: {str(e)}")
        return {}


def parse_args():
    """
    Parses command-line arguments for the script
    
    Returns:
        Parsed command-line arguments
    """
    # Create ArgumentParser with description
    parser = argparse.ArgumentParser(
        description="Export data from Budget Management Application's Google Sheets"
    )
    
    # Add format argument with choices from DEFAULT_EXPORT_FORMATS
    parser.add_argument(
        "--format", 
        choices=DEFAULT_EXPORT_FORMATS,
        default="json",
        help="Format to export data (default: json)"
    )
    
    # Add output_dir argument with default BACKUP_DIR
    parser.add_argument(
        "--output-dir",
        default=BACKUP_DIR,
        help=f"Directory to save exported files (default: {BACKUP_DIR})"
    )
    
    # Add sheet argument with choices ('weekly', 'budget', 'all')
    parser.add_argument(
        "--sheet",
        choices=["weekly", "budget", "all"],
        default="all",
        help="Which sheet to export (default: all)"
    )
    
    # Add pretty argument for JSON formatting
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty print JSON output (only applicable for JSON format)"
    )
    
    # Parse and return command-line arguments
    return parser.parse_args()


def main():
    """
    Main function for the export_data script
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Parse command-line arguments using parse_args
        args = parse_args()
        
        # Initialize Google Sheets service
        service = get_sheets_service()
        
        # Process the sheet argument to determine which sheets to export
        if args.sheet == "weekly":
            # If sheet is 'weekly', export Weekly Spending sheet
            path = export_weekly_spending(args.format, args.output_dir, service)
            if path:
                logger.info(f"Successfully exported Weekly Spending sheet to {path}")
            else:
                logger.error("Failed to export Weekly Spending sheet")
                return 1
        
        elif args.sheet == "budget":
            # If sheet is 'budget', export Master Budget sheet
            path = export_master_budget(args.format, args.output_dir, service)
            if path:
                logger.info(f"Successfully exported Master Budget sheet to {path}")
            else:
                logger.error("Failed to export Master Budget sheet")
                return 1
        
        else:  # args.sheet == "all"
            # If sheet is 'all', export all sheets
            results = export_all_sheets(args.format, args.output_dir, service)
            if results:
                logger.info(f"Successfully exported all sheets to {args.format} format")
                for sheet_name, path in results.items():
                    logger.info(f"  - {sheet_name}: {path}")
            else:
                logger.error("Failed to export all sheets")
                return 1
        
        # Log export completion with summary
        logger.info("Export completed successfully")
        return 0
    
    except KeyboardInterrupt:
        logger.warning("Export interrupted by user")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        # Handle and log any errors during execution
        logger.error(f"Error in main: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())