"""
Utility module for formatting Google Sheets in the Budget Management Application.

This module provides functions to apply consistent formatting, styling, and layout to
the Master Budget and Weekly Spending sheets, ensuring proper visualization of financial data.
"""

import os
import json
from typing import Dict, List, Optional, Any

import googleapiclient.errors

# Internal imports
from ..config.logging_setup import get_logger
from ..config.script_settings import SCRIPT_SETTINGS
from .sheet_operations import (
    get_sheets_service,
    format_sheet, 
    get_sheet_id_by_name
)

# Set up logger
logger = get_logger(__name__)

# Constants
WEEKLY_SPENDING_SHEET_NAME = "Weekly Spending"
MASTER_BUDGET_SHEET_NAME = "Master Budget"

# Formatting constants
HEADER_FORMAT = {
    "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
    "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 12}
}

CURRENCY_FORMAT = {
    "numberFormat": {"type": "CURRENCY", "pattern": "$#,##0.00"}
}

DATE_FORMAT = {
    "numberFormat": {"type": "DATE_TIME", "pattern": "MM/dd/yyyy h:mm:ss am/pm"}
}

CATEGORY_FORMAT = {
    "textFormat": {"bold": True}
}

POSITIVE_VARIANCE_FORMAT = {
    "backgroundColor": {"red": 0.7, "green": 0.9, "blue": 0.7},
    "textFormat": {"foregroundColor": {"red": 0.0, "green": 0.5, "blue": 0.0}}
}

NEGATIVE_VARIANCE_FORMAT = {
    "backgroundColor": {"red": 0.9, "green": 0.7, "blue": 0.7},
    "textFormat": {"foregroundColor": {"red": 0.8, "green": 0.0, "blue": 0.0}}
}

NEUTRAL_VARIANCE_FORMAT = {
    "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
}


def format_weekly_spending_sheet(spreadsheet_id: str, service=None) -> bool:
    """
    Applies standard formatting to the Weekly Spending sheet
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        service: Google Sheets API service (will be created if None)
        
    Returns:
        True if formatting was successful, False otherwise
    """
    try:
        if service is None:
            service = get_sheets_service()
            
        # Get sheet ID for Weekly Spending sheet
        sheet_id = get_sheet_id_by_name(spreadsheet_id, WEEKLY_SPENDING_SHEET_NAME, service)
        
        if sheet_id is None:
            logger.error(f"Sheet '{WEEKLY_SPENDING_SHEET_NAME}' not found")
            return False
            
        # Format header row with HEADER_FORMAT
        header_range = f"{WEEKLY_SPENDING_SHEET_NAME}!A1:D1"
        format_sheet(spreadsheet_id, header_range, HEADER_FORMAT, service)
        
        # Format transaction amount column with CURRENCY_FORMAT
        amount_range = f"{WEEKLY_SPENDING_SHEET_NAME}!B:B"
        format_sheet(spreadsheet_id, amount_range, CURRENCY_FORMAT, service)
        
        # Format transaction time column with DATE_FORMAT
        time_range = f"{WEEKLY_SPENDING_SHEET_NAME}!C:C"
        format_sheet(spreadsheet_id, time_range, DATE_FORMAT, service)
        
        # Format category column with CATEGORY_FORMAT
        category_range = f"{WEEKLY_SPENDING_SHEET_NAME}!D:D"
        format_sheet(spreadsheet_id, category_range, CATEGORY_FORMAT, service)
        
        # Apply alternating row colors for better readability
        apply_alternating_row_colors(
            spreadsheet_id,
            sheet_id,
            f"{WEEKLY_SPENDING_SHEET_NAME}!A2:D",
            {"backgroundColor": {"red": 0.95, "green": 0.95, "blue": 0.95}},
            {"backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}},
            service
        )
        
        # Add data validation for categories (dropdown from Master Budget)
        master_budget_categories = get_master_budget_categories(spreadsheet_id, service)
        if master_budget_categories:
            add_data_validation(
                spreadsheet_id,
                sheet_id,
                f"{WEEKLY_SPENDING_SHEET_NAME}!D2:D",
                "ONE_OF_LIST",
                {"values": master_budget_categories},
                service
            )
        
        # Freeze header row
        freeze_rows(spreadsheet_id, sheet_id, 1, service)
        
        # Auto-resize columns to fit content
        auto_resize_columns(spreadsheet_id, sheet_id, [0, 1, 2, 3], service)
        
        logger.info(f"Successfully formatted {WEEKLY_SPENDING_SHEET_NAME} sheet")
        return True
        
    except Exception as e:
        logger.error(f"Error formatting Weekly Spending sheet: {str(e)}")
        return False


def format_master_budget_sheet(spreadsheet_id: str, service=None) -> bool:
    """
    Applies standard formatting to the Master Budget sheet
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        service: Google Sheets API service (will be created if None)
        
    Returns:
        True if formatting was successful, False otherwise
    """
    try:
        if service is None:
            service = get_sheets_service()
            
        # Get sheet ID for Master Budget sheet
        sheet_id = get_sheet_id_by_name(spreadsheet_id, MASTER_BUDGET_SHEET_NAME, service)
        
        if sheet_id is None:
            logger.error(f"Sheet '{MASTER_BUDGET_SHEET_NAME}' not found")
            return False
            
        # Format header row with HEADER_FORMAT
        header_range = f"{MASTER_BUDGET_SHEET_NAME}!A1:B1"
        format_sheet(spreadsheet_id, header_range, HEADER_FORMAT, service)
        
        # Format budget amount column with CURRENCY_FORMAT
        amount_range = f"{MASTER_BUDGET_SHEET_NAME}!B:B"
        format_sheet(spreadsheet_id, amount_range, CURRENCY_FORMAT, service)
        
        # Format category column with CATEGORY_FORMAT
        category_range = f"{MASTER_BUDGET_SHEET_NAME}!A:A"
        format_sheet(spreadsheet_id, category_range, CATEGORY_FORMAT, service)
        
        # Apply alternating row colors for better readability
        apply_alternating_row_colors(
            spreadsheet_id,
            sheet_id,
            f"{MASTER_BUDGET_SHEET_NAME}!A2:B",
            {"backgroundColor": {"red": 0.95, "green": 0.95, "blue": 0.95}},
            {"backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}},
            service
        )
        
        # Freeze header row
        freeze_rows(spreadsheet_id, sheet_id, 1, service)
        
        # Auto-resize columns to fit content
        auto_resize_columns(spreadsheet_id, sheet_id, [0, 1], service)
        
        logger.info(f"Successfully formatted {MASTER_BUDGET_SHEET_NAME} sheet")
        return True
        
    except Exception as e:
        logger.error(f"Error formatting Master Budget sheet: {str(e)}")
        return False


def format_budget_analysis_sheet(spreadsheet_id: str, service=None) -> bool:
    """
    Creates and formats a Budget Analysis sheet with variance highlighting
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        service: Google Sheets API service (will be created if None)
        
    Returns:
        True if formatting was successful, False otherwise
    """
    try:
        if service is None:
            service = get_sheets_service()
        
        budget_analysis_sheet_name = "Budget Analysis"
        
        # Check if Budget Analysis sheet exists, create if not
        sheet_id = get_sheet_id_by_name(spreadsheet_id, budget_analysis_sheet_name, service)
        if sheet_id is None:
            # Create the sheet
            request = {
                'addSheet': {
                    'properties': {
                        'title': budget_analysis_sheet_name
                    }
                }
            }
            
            response = service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': [request]}
            ).execute()
            
            sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
            logger.info(f"Created new sheet '{budget_analysis_sheet_name}'")
        
        # Format header row with HEADER_FORMAT
        header_range = f"{budget_analysis_sheet_name}!A1:E1"
        format_sheet(spreadsheet_id, header_range, HEADER_FORMAT, service)
        
        # Set up headers
        headers = [["Category", "Budget Amount", "Actual Amount", "Variance Amount", "Variance %"]]
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{budget_analysis_sheet_name}!A1:E1",
            valueInputOption="RAW",
            body={"values": headers}
        ).execute()
        
        # Format currency columns
        format_sheet(spreadsheet_id, f"{budget_analysis_sheet_name}!B:B", CURRENCY_FORMAT, service)
        format_sheet(spreadsheet_id, f"{budget_analysis_sheet_name}!C:C", CURRENCY_FORMAT, service)
        format_sheet(spreadsheet_id, f"{budget_analysis_sheet_name}!D:D", CURRENCY_FORMAT, service)
        
        # Format percentage column
        percentage_format = {
            "numberFormat": {"type": "PERCENT", "pattern": "0.00%"}
        }
        format_sheet(spreadsheet_id, f"{budget_analysis_sheet_name}!E:E", percentage_format, service)
        
        # Apply conditional formatting for variances
        # Positive variance (under budget): Green
        apply_conditional_formatting(
            spreadsheet_id,
            sheet_id,
            f"{budget_analysis_sheet_name}!D2:D",
            {
                "type": "NUMBER_GREATER",
                "values": [{"userEnteredValue": "0"}],
                "format": POSITIVE_VARIANCE_FORMAT
            },
            service
        )
        
        # Negative variance (over budget): Red
        apply_conditional_formatting(
            spreadsheet_id,
            sheet_id,
            f"{budget_analysis_sheet_name}!D2:D",
            {
                "type": "NUMBER_LESS",
                "values": [{"userEnteredValue": "0"}],
                "format": NEGATIVE_VARIANCE_FORMAT
            },
            service
        )
        
        # Zero variance (on budget): Gray
        apply_conditional_formatting(
            spreadsheet_id,
            sheet_id,
            f"{budget_analysis_sheet_name}!D2:D",
            {
                "type": "NUMBER_EQ",
                "values": [{"userEnteredValue": "0"}],
                "format": NEUTRAL_VARIANCE_FORMAT
            },
            service
        )
        
        # Add summary section at top
        summary_range = f"{budget_analysis_sheet_name}!G1:H4"
        summary_values = [
            ["Budget Summary", ""],
            ["Total Budget", "=SUM(B2:B)"],
            ["Total Spent", "=SUM(C2:C)"],
            ["Total Variance", "=SUM(D2:D)"]
        ]
        
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=summary_range,
            valueInputOption="USER_ENTERED",
            body={"values": summary_values}
        ).execute()
        
        # Format summary section
        format_sheet(spreadsheet_id, f"{budget_analysis_sheet_name}!G1:H1", HEADER_FORMAT, service)
        format_sheet(spreadsheet_id, f"{budget_analysis_sheet_name}!G2:G4", CATEGORY_FORMAT, service)
        format_sheet(spreadsheet_id, f"{budget_analysis_sheet_name}!H2:H4", CURRENCY_FORMAT, service)
        
        # Apply conditional formatting to total variance
        apply_conditional_formatting(
            spreadsheet_id,
            sheet_id,
            f"{budget_analysis_sheet_name}!H4",
            {
                "type": "NUMBER_GREATER",
                "values": [{"userEnteredValue": "0"}],
                "format": POSITIVE_VARIANCE_FORMAT
            },
            service
        )
        
        apply_conditional_formatting(
            spreadsheet_id,
            sheet_id,
            f"{budget_analysis_sheet_name}!H4",
            {
                "type": "NUMBER_LESS",
                "values": [{"userEnteredValue": "0"}],
                "format": NEGATIVE_VARIANCE_FORMAT
            },
            service
        )
        
        # Freeze header row
        freeze_rows(spreadsheet_id, sheet_id, 1, service)
        
        # Auto-resize columns
        auto_resize_columns(spreadsheet_id, sheet_id, [0, 1, 2, 3, 4, 6, 7], service)
        
        logger.info(f"Successfully formatted {budget_analysis_sheet_name} sheet")
        return True
        
    except Exception as e:
        logger.error(f"Error formatting Budget Analysis sheet: {str(e)}")
        return False


def apply_conditional_formatting(spreadsheet_id: str, sheet_id: str, range_name: str, 
                               conditions: Dict, service) -> bool:
    """
    Applies conditional formatting to a range based on cell values
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        sheet_id: ID of the sheet
        range_name: Range to apply formatting to
        conditions: Conditions and formatting to apply
        service: Google Sheets API service
        
    Returns:
        True if conditional formatting was applied successfully
    """
    try:
        # Parse range to get sheet name and grid range
        parts = range_name.split('!')
        sheet_name = parts[0]
        cell_range = parts[1] if len(parts) > 1 else "A1"
        
        # Create grid range from sheet_id
        grid_range = {"sheetId": sheet_id}
        
        # Add start/end row/column indices if needed
        # This is a simplified approach - in a full implementation,
        # we would parse the A1 notation more precisely
        
        # Create the conditional format rule
        rule = {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [grid_range],
                    "booleanRule": {
                        "condition": {
                            "type": conditions["type"],
                            "values": conditions["values"]
                        },
                        "format": conditions["format"]
                    }
                },
                "index": 0
            }
        }
        
        # Apply the conditional format rule
        request_body = {"requests": [rule]}
        
        max_retries = SCRIPT_SETTINGS.get('MAX_RETRIES', 3)
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=request_body
                ).execute()
                
                logger.debug(f"Applied conditional formatting to {range_name}")
                return True
            except googleapiclient.errors.HttpError as error:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                logger.warning(f"Retry {retry_count}/{max_retries} after error: {error}")
                import time
                time.sleep(1 * (2 ** (retry_count - 1)))  # Exponential backoff
        
        return False
        
    except googleapiclient.errors.HttpError as error:
        logger.error(f"Google Sheets API error while applying conditional formatting: {str(error)}")
        return False
    except Exception as e:
        logger.error(f"Error applying conditional formatting: {str(e)}")
        return False


def add_data_validation(spreadsheet_id: str, sheet_id: str, range_name: str, 
                      validation_type: str, validation_params: Dict, service) -> bool:
    """
    Adds data validation to a range (e.g., dropdown for categories)
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        sheet_id: ID of the sheet
        range_name: Range to apply validation to
        validation_type: Type of validation (e.g., ONE_OF_LIST)
        validation_params: Parameters for the validation
        service: Google Sheets API service
        
    Returns:
        True if data validation was added successfully
    """
    try:
        # Parse range to get sheet name and grid range
        parts = range_name.split('!')
        sheet_name = parts[0]
        cell_range = parts[1] if len(parts) > 1 else "A1"
        
        # Create grid range from sheet_id
        grid_range = {"sheetId": sheet_id}
        
        # Add start/end row/column indices if needed
        # This is a simplified approach - in a full implementation,
        # we would parse the A1 notation more precisely
        
        # Create the validation rule
        validation_rule = {
            "setDataValidation": {
                "range": grid_range,
                "rule": {
                    "condition": {
                        "type": validation_type,
                    },
                    "inputMessage": "Select a valid category",
                    "strict": True,
                    "showCustomUi": True
                }
            }
        }
        
        # Add values if it's a list validation
        if validation_type == "ONE_OF_LIST":
            validation_rule["setDataValidation"]["rule"]["condition"]["values"] = [
                {"userEnteredValue": value} for value in validation_params["values"]
            ]
        elif validation_type == "NUMBER_BETWEEN":
            validation_rule["setDataValidation"]["rule"]["condition"]["values"] = [
                {"userEnteredValue": str(validation_params["min_value"])},
                {"userEnteredValue": str(validation_params["max_value"])}
            ]
        
        # Apply the validation rule
        request_body = {"requests": [validation_rule]}
        
        max_retries = SCRIPT_SETTINGS.get('MAX_RETRIES', 3)
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=request_body
                ).execute()
                
                logger.debug(f"Added data validation to {range_name}")
                return True
            except googleapiclient.errors.HttpError as error:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                logger.warning(f"Retry {retry_count}/{max_retries} after error: {error}")
                import time
                time.sleep(1 * (2 ** (retry_count - 1)))  # Exponential backoff
        
        return False
        
    except googleapiclient.errors.HttpError as error:
        logger.error(f"Google Sheets API error while adding data validation: {str(error)}")
        return False
    except Exception as e:
        logger.error(f"Error adding data validation: {str(e)}")
        return False


def auto_resize_columns(spreadsheet_id: str, sheet_id: str, column_indexes: List[int], service) -> bool:
    """
    Auto-resizes columns to fit content
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        sheet_id: ID of the sheet
        column_indexes: List of column indexes to resize
        service: Google Sheets API service
        
    Returns:
        True if columns were auto-resized successfully
    """
    try:
        requests = []
        
        for column_index in column_indexes:
            requests.append({
                "autoResizeDimensions": {
                    "dimensions": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": column_index,
                        "endIndex": column_index + 1
                    }
                }
            })
        
        # Apply the auto-resize requests
        request_body = {"requests": requests}
        
        max_retries = SCRIPT_SETTINGS.get('MAX_RETRIES', 3)
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=request_body
                ).execute()
                
                logger.debug(f"Auto-resized columns {column_indexes} in sheet {sheet_id}")
                return True
            except googleapiclient.errors.HttpError as error:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                logger.warning(f"Retry {retry_count}/{max_retries} after error: {error}")
                import time
                time.sleep(1 * (2 ** (retry_count - 1)))  # Exponential backoff
        
        return False
        
    except googleapiclient.errors.HttpError as error:
        logger.error(f"Google Sheets API error while auto-resizing columns: {str(error)}")
        return False
    except Exception as e:
        logger.error(f"Error auto-resizing columns: {str(e)}")
        return False


def freeze_rows(spreadsheet_id: str, sheet_id: str, freeze_row_count: int, service) -> bool:
    """
    Freezes a specified number of rows at the top of a sheet
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        sheet_id: ID of the sheet
        freeze_row_count: Number of rows to freeze
        service: Google Sheets API service
        
    Returns:
        True if rows were frozen successfully
    """
    try:
        request = {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {
                        "frozenRowCount": freeze_row_count
                    }
                },
                "fields": "gridProperties.frozenRowCount"
            }
        }
        
        # Apply the freeze rows request
        request_body = {"requests": [request]}
        
        max_retries = SCRIPT_SETTINGS.get('MAX_RETRIES', 3)
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=request_body
                ).execute()
                
                logger.debug(f"Froze {freeze_row_count} rows in sheet {sheet_id}")
                return True
            except googleapiclient.errors.HttpError as error:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                logger.warning(f"Retry {retry_count}/{max_retries} after error: {error}")
                import time
                time.sleep(1 * (2 ** (retry_count - 1)))  # Exponential backoff
        
        return False
        
    except googleapiclient.errors.HttpError as error:
        logger.error(f"Google Sheets API error while freezing rows: {str(error)}")
        return False
    except Exception as e:
        logger.error(f"Error freezing rows: {str(e)}")
        return False


def apply_alternating_row_colors(spreadsheet_id: str, sheet_id: str, range_name: str, 
                               even_row_format: Dict, odd_row_format: Dict, service) -> bool:
    """
    Applies alternating row colors for better readability
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        sheet_id: ID of the sheet
        range_name: Range to apply alternating colors to
        even_row_format: Format for even rows
        odd_row_format: Format for odd rows
        service: Google Sheets API service
        
    Returns:
        True if alternating colors were applied successfully
    """
    try:
        # Parse range to get sheet name and grid range
        parts = range_name.split('!')
        sheet_name = parts[0]
        cell_range = parts[1] if len(parts) > 1 else "A1"
        
        # Create grid range from sheet_id
        grid_range = {"sheetId": sheet_id}
        
        # Add start/end row/column indices if needed
        # This is a simplified approach - in a full implementation,
        # we would parse the A1 notation more precisely
        
        # Create the banding request
        banding_request = {
            "addBanding": {
                "bandedRange": {
                    "range": grid_range,
                    "rowProperties": {
                        "firstBandColor": even_row_format,
                        "secondBandColor": odd_row_format
                    }
                }
            }
        }
        
        # Apply the banding request
        request_body = {"requests": [banding_request]}
        
        max_retries = SCRIPT_SETTINGS.get('MAX_RETRIES', 3)
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=request_body
                ).execute()
                
                logger.debug(f"Applied alternating row colors to {range_name}")
                return True
            except googleapiclient.errors.HttpError as error:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                logger.warning(f"Retry {retry_count}/{max_retries} after error: {error}")
                import time
                time.sleep(1 * (2 ** (retry_count - 1)))  # Exponential backoff
        
        return False
        
    except googleapiclient.errors.HttpError as error:
        logger.error(f"Google Sheets API error while applying alternating row colors: {str(error)}")
        return False
    except Exception as e:
        logger.error(f"Error applying alternating row colors: {str(e)}")
        return False


def get_master_budget_categories(spreadsheet_id: str, service=None) -> List[str]:
    """
    Gets the list of categories from the Master Budget sheet
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        service: Google Sheets API service
        
    Returns:
        List of category names
    """
    try:
        if service is None:
            service = get_sheets_service()
            
        # Get categories from Master Budget sheet (column A, starting from row 2)
        range_name = f"{MASTER_BUDGET_SHEET_NAME}!A2:A"
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        # Extract category names (flatten the list of lists)
        categories = [item[0] for item in values if item and item[0]]
        
        logger.debug(f"Retrieved {len(categories)} categories from Master Budget sheet")
        return categories
        
    except Exception as e:
        logger.error(f"Error getting Master Budget categories: {str(e)}")
        return []


def format_all_sheets(spreadsheet_id: str, service=None) -> bool:
    """
    Applies standard formatting to all relevant sheets in the spreadsheet
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        service: Google Sheets API service
        
    Returns:
        True if all sheets were formatted successfully
    """
    try:
        if service is None:
            service = get_sheets_service()
            
        # Format all sheets
        weekly_result = format_weekly_spending_sheet(spreadsheet_id, service)
        master_result = format_master_budget_sheet(spreadsheet_id, service)
        analysis_result = format_budget_analysis_sheet(spreadsheet_id, service)
        
        # Check if all formatting was successful
        all_success = weekly_result and master_result and analysis_result
        
        if all_success:
            logger.info("Successfully formatted all sheets")
        else:
            logger.warning("Some sheets were not formatted successfully")
            
        return all_success
        
    except Exception as e:
        logger.error(f"Error formatting all sheets: {str(e)}")
        return False