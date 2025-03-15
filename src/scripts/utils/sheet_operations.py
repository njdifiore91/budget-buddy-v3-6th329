"""
Utility module providing helper functions for Google Sheets operations in the Budget Management Application's utility scripts.

This module offers a comprehensive set of functions for interacting with Google Sheets, including:
- Reading, writing, and appending data
- Converting between sheet data and pandas DataFrames
- Sheet creation, deletion, and formatting
- Data validation and backup
- Search and metadata functions
- Testing utilities

These functions support maintenance scripts, testing workflows, and development tools
throughout the application.
"""

import os
import json
import datetime
from typing import List, Dict, Optional, Any, Tuple, Union

import pandas as pd
from google.oauth2 import service_account
import googleapiclient.discovery
import googleapiclient.errors

# Internal imports
from ..config.logging_setup import get_logger
from ..config.script_settings import (
    SCRIPT_SETTINGS, API_TEST_SETTINGS, get_credential_path
)
from ...backend.api_clients.google_sheets_client import (
    build_sheets_service, parse_sheet_range, format_sheet_range
)

# Set up logger
logger = get_logger(__name__)

# Constants
SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
VALUE_INPUT_OPTION = "USER_ENTERED"
VALUE_RENDER_OPTION = "FORMATTED_VALUE"
INSERT_DATA_OPTION = "INSERT_ROWS"
DEFAULT_MAJOR_DIMENSION = "ROWS"


def get_sheets_service(credentials_path: str = None):
    """
    Creates an authenticated Google Sheets API service using service account credentials
    
    Args:
        credentials_path: Path to the service account credentials JSON file
        
    Returns:
        Authenticated Google Sheets API service object
    """
    try:
        if credentials_path is None:
            credentials_path = get_credential_path('sheets_credentials.json')
            
        if not credentials_path:
            logger.error("No credentials path provided and default path not found")
            raise ValueError("No credentials path provided and default path not found")
            
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SHEETS_SCOPES)
            
        service = build_sheets_service(credentials)
        
        logger.debug(f"Successfully created Google Sheets service using credentials from {credentials_path}")
        return service
        
    except Exception as e:
        logger.error(f"Failed to create Google Sheets service: {str(e)}")
        raise


def read_sheet(spreadsheet_id: str, range_name: str, 
               service=None, value_render_option: str = VALUE_RENDER_OPTION,
               major_dimension: str = DEFAULT_MAJOR_DIMENSION) -> List[List[Any]]:
    """
    Reads data from a Google Sheet range
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        range_name: Range to read (e.g., 'Sheet1!A1:B10')
        service: Google Sheets API service (will be created if None)
        value_render_option: How values should be rendered
        major_dimension: Major dimension of the values ('ROWS' or 'COLUMNS')
        
    Returns:
        Sheet data as a list of rows
    """
    try:
        if service is None:
            service = get_sheets_service()
            
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueRenderOption=value_render_option,
            majorDimension=major_dimension
        ).execute()
        
        values = result.get('values', [])
        
        logger.debug(f"Read {len(values)} rows from {range_name} in spreadsheet {spreadsheet_id}")
        return values
        
    except googleapiclient.errors.HttpError as error:
        logger.error(f"Google Sheets API error while reading sheet: {str(error)}")
        raise
    except Exception as e:
        logger.error(f"Error reading sheet: {str(e)}")
        raise


def write_sheet(spreadsheet_id: str, range_name: str, values: List[List[Any]],
                service=None, value_input_option: str = VALUE_INPUT_OPTION) -> dict:
    """
    Writes data to a Google Sheet range, replacing existing values
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        range_name: Range to write to (e.g., 'Sheet1!A1:B10')
        values: Values to write as a list of rows
        service: Google Sheets API service (will be created if None)
        value_input_option: How input should be interpreted
        
    Returns:
        API response with update details
    """
    try:
        if service is None:
            service = get_sheets_service()
            
        body = {
            'values': values
        }
        
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption=value_input_option,
            body=body
        ).execute()
        
        logger.debug(f"Updated {result.get('updatedCells')} cells in {range_name}")
        return result
        
    except googleapiclient.errors.HttpError as error:
        logger.error(f"Google Sheets API error while writing to sheet: {str(error)}")
        raise
    except Exception as e:
        logger.error(f"Error writing to sheet: {str(e)}")
        raise


def append_to_sheet(spreadsheet_id: str, range_name: str, values: List[List[Any]],
                   service=None, value_input_option: str = VALUE_INPUT_OPTION,
                   insert_data_option: str = INSERT_DATA_OPTION) -> dict:
    """
    Appends rows to a Google Sheet
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        range_name: Range to append to (e.g., 'Sheet1!A:B')
        values: Values to append as a list of rows
        service: Google Sheets API service (will be created if None)
        value_input_option: How input should be interpreted
        insert_data_option: How the input should be inserted
        
    Returns:
        API response with append details
    """
    try:
        if service is None:
            service = get_sheets_service()
            
        body = {
            'values': values
        }
        
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption=value_input_option,
            insertDataOption=insert_data_option,
            body=body
        ).execute()
        
        logger.debug(f"Appended {len(values)} rows to {range_name}")
        return result
        
    except googleapiclient.errors.HttpError as error:
        logger.error(f"Google Sheets API error while appending to sheet: {str(error)}")
        raise
    except Exception as e:
        logger.error(f"Error appending to sheet: {str(e)}")
        raise


def clear_sheet_range(spreadsheet_id: str, range_name: str, service=None) -> dict:
    """
    Clears values from a Google Sheet range
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        range_name: Range to clear (e.g., 'Sheet1!A1:B10')
        service: Google Sheets API service (will be created if None)
        
    Returns:
        API response with clear details
    """
    try:
        if service is None:
            service = get_sheets_service()
            
        result = service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            body={}
        ).execute()
        
        logger.debug(f"Cleared range {range_name}")
        return result
        
    except googleapiclient.errors.HttpError as error:
        logger.error(f"Google Sheets API error while clearing sheet range: {str(error)}")
        raise
    except Exception as e:
        logger.error(f"Error clearing sheet range: {str(e)}")
        raise


def get_sheet_as_dataframe(spreadsheet_id: str, range_name: str, 
                          service=None, header: bool = True) -> pd.DataFrame:
    """
    Reads a Google Sheet range and converts it to a pandas DataFrame
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        range_name: Range to read (e.g., 'Sheet1!A1:B10')
        service: Google Sheets API service (will be created if None)
        header: Whether to use the first row as column names
        
    Returns:
        Sheet data as a DataFrame
    """
    try:
        # Read sheet data
        data = read_sheet(spreadsheet_id, range_name, service)
        
        if not data:
            logger.warning(f"No data found in range {range_name}")
            return pd.DataFrame()
            
        # Convert to DataFrame
        if header and len(data) > 0:
            # Use first row as column names
            df = pd.DataFrame(data[1:], columns=data[0])
        else:
            # Generate default column names
            df = pd.DataFrame(data)
            
        logger.debug(f"Created DataFrame with shape {df.shape} from sheet data")
        return df
        
    except Exception as e:
        logger.error(f"Error converting sheet to DataFrame: {str(e)}")
        raise


def write_dataframe_to_sheet(spreadsheet_id: str, range_name: str, df: pd.DataFrame,
                            service=None, include_header: bool = True, 
                            clear_first: bool = False) -> dict:
    """
    Writes a pandas DataFrame to a Google Sheet range
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        range_name: Range to write to (e.g., 'Sheet1!A1')
        df: DataFrame to write
        service: Google Sheets API service (will be created if None)
        include_header: Whether to include column names as first row
        clear_first: Whether to clear the range before writing
        
    Returns:
        API response with update details
    """
    try:
        if service is None:
            service = get_sheets_service()
            
        # Convert DataFrame to list of lists
        if include_header:
            values = [df.columns.tolist()] + df.values.tolist()
        else:
            values = df.values.tolist()
            
        # Clear range if requested
        if clear_first:
            clear_sheet_range(spreadsheet_id, range_name, service)
            
        # Write to sheet
        result = write_sheet(spreadsheet_id, range_name, values, service)
        
        return result
        
    except Exception as e:
        logger.error(f"Error writing DataFrame to sheet: {str(e)}")
        raise


def create_sheet(spreadsheet_id: str, sheet_title: str, service=None) -> int:
    """
    Creates a new sheet within an existing spreadsheet
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        sheet_title: Title for the new sheet
        service: Google Sheets API service (will be created if None)
        
    Returns:
        ID of the newly created sheet
    """
    try:
        if service is None:
            service = get_sheets_service()
            
        # Create the new sheet
        request = {
            'addSheet': {
                'properties': {
                    'title': sheet_title
                }
            }
        }
        
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': [request]}
        ).execute()
        
        # Extract the new sheet ID
        sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
        
        logger.info(f"Created new sheet '{sheet_title}' with ID {sheet_id}")
        return sheet_id
        
    except googleapiclient.errors.HttpError as error:
        if 'already exists' in str(error):
            logger.warning(f"Sheet '{sheet_title}' already exists")
            # Return the ID of the existing sheet
            return get_sheet_id_by_name(spreadsheet_id, sheet_title, service)
        logger.error(f"Google Sheets API error while creating sheet: {str(error)}")
        raise
    except Exception as e:
        logger.error(f"Error creating sheet: {str(e)}")
        raise


def delete_sheet(spreadsheet_id: str, sheet_id: int, service=None) -> bool:
    """
    Deletes a sheet from a spreadsheet by sheet ID
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        sheet_id: ID of the sheet to delete
        service: Google Sheets API service (will be created if None)
        
    Returns:
        True if deletion was successful
    """
    try:
        if service is None:
            service = get_sheets_service()
            
        # Delete the sheet
        request = {
            'deleteSheet': {
                'sheetId': sheet_id
            }
        }
        
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': [request]}
        ).execute()
        
        logger.info(f"Deleted sheet with ID {sheet_id}")
        return True
        
    except googleapiclient.errors.HttpError as error:
        logger.error(f"Google Sheets API error while deleting sheet: {str(error)}")
        return False
    except Exception as e:
        logger.error(f"Error deleting sheet: {str(e)}")
        return False


def get_sheet_id_by_name(spreadsheet_id: str, sheet_name: str, service=None) -> Optional[int]:
    """
    Gets the sheet ID for a sheet with the specified name
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        sheet_name: Name of the sheet to find
        service: Google Sheets API service (will be created if None)
        
    Returns:
        Sheet ID if found, None otherwise
    """
    try:
        if service is None:
            service = get_sheets_service()
            
        # Get spreadsheet metadata
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        
        # Find the sheet with matching title
        for sheet in spreadsheet.get('sheets', []):
            properties = sheet.get('properties', {})
            if properties.get('title') == sheet_name:
                sheet_id = properties.get('sheetId')
                logger.debug(f"Found sheet '{sheet_name}' with ID {sheet_id}")
                return sheet_id
                
        logger.warning(f"Sheet '{sheet_name}' not found in spreadsheet")
        return None
        
    except googleapiclient.errors.HttpError as error:
        logger.error(f"Google Sheets API error while getting sheet ID: {str(error)}")
        raise
    except Exception as e:
        logger.error(f"Error getting sheet ID: {str(e)}")
        raise


def format_sheet(spreadsheet_id: str, range_name: str, format_json: dict, service=None) -> dict:
    """
    Applies formatting to a range in a Google Sheet
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        range_name: Range to format (e.g., 'Sheet1!A1:B10')
        format_json: JSON representation of the cell format
        service: Google Sheets API service (will be created if None)
        
    Returns:
        API response with formatting details
    """
    try:
        if service is None:
            service = get_sheets_service()
            
        # Parse the range to get sheet name and cell range
        sheet_name, start_cell, end_cell = parse_sheet_range(range_name)
        
        # Get the sheet ID
        sheet_id = get_sheet_id_by_name(spreadsheet_id, sheet_name, service)
        
        if sheet_id is None:
            logger.error(f"Sheet '{sheet_name}' not found for formatting")
            raise ValueError(f"Sheet '{sheet_name}' not found")
            
        # Create the formatting request
        # This is a simplified implementation that applies formatting to the specified range
        request = {
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    # Note: In a full implementation, we would parse start_cell and end_cell
                    # to determine exact row and column indices
                },
                'cell': {
                    'userEnteredFormat': format_json
                },
                'fields': 'userEnteredFormat'
            }
        }
        
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': [request]}
        ).execute()
        
        logger.debug(f"Applied formatting to range {range_name}")
        return response
        
    except googleapiclient.errors.HttpError as error:
        logger.error(f"Google Sheets API error while formatting sheet: {str(error)}")
        raise
    except Exception as e:
        logger.error(f"Error formatting sheet: {str(e)}")
        raise


def copy_sheet_data(source_spreadsheet_id: str, source_range: str, 
                   destination_spreadsheet_id: str, destination_range: str,
                   service=None) -> dict:
    """
    Copies data from one sheet range to another, optionally in a different spreadsheet
    
    Args:
        source_spreadsheet_id: ID of the source spreadsheet
        source_range: Range to copy from (e.g., 'Sheet1!A1:B10')
        destination_spreadsheet_id: ID of the destination spreadsheet
        destination_range: Range to copy to (e.g., 'Sheet2!A1')
        service: Google Sheets API service (will be created if None)
        
    Returns:
        API response with copy details
    """
    try:
        if service is None:
            service = get_sheets_service()
            
        # Read data from source range
        data = read_sheet(source_spreadsheet_id, source_range, service)
        
        if not data:
            logger.warning(f"No data found in source range {source_range}")
            return {"updatedCells": 0}
            
        # Write data to destination range
        result = write_sheet(
            destination_spreadsheet_id, 
            destination_range, 
            data, 
            service
        )
        
        logger.info(f"Copied data from {source_range} to {destination_range}")
        return result
        
    except Exception as e:
        logger.error(f"Error copying sheet data: {str(e)}")
        raise


def export_sheet_to_json(spreadsheet_id: str, range_name: str, output_file: str,
                        service=None, pretty_print: bool = True) -> bool:
    """
    Exports Google Sheet data to a JSON file
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        range_name: Range to export (e.g., 'Sheet1!A1:B10')
        output_file: Path to output JSON file
        service: Google Sheets API service (will be created if None)
        pretty_print: Whether to format JSON with indentation
        
    Returns:
        True if export was successful
    """
    try:
        # Read sheet data
        data = read_sheet(spreadsheet_id, range_name, service)
        
        if not data:
            logger.warning(f"No data found in range {range_name}")
            return False
            
        # Convert data to JSON format
        if len(data) > 0:
            headers = data[0]
            json_data = []
            
            for row in data[1:]:
                # Create a dictionary using headers as keys
                row_dict = {}
                for i, header in enumerate(headers):
                    if i < len(row):
                        row_dict[header] = row[i]
                    else:
                        row_dict[header] = ""
                json_data.append(row_dict)
                
            # Write to JSON file
            with open(output_file, 'w') as f:
                if pretty_print:
                    json.dump(json_data, f, indent=2)
                else:
                    json.dump(json_data, f)
                    
            logger.info(f"Exported {len(json_data)} records to {output_file}")
            return True
        else:
            logger.warning(f"No data with headers found in range {range_name}")
            return False
            
    except Exception as e:
        logger.error(f"Error exporting sheet to JSON: {str(e)}")
        return False


def import_json_to_sheet(spreadsheet_id: str, range_name: str, input_file: str,
                        service=None, clear_first: bool = True) -> bool:
    """
    Imports data from a JSON file to a Google Sheet
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        range_name: Range to import to (e.g., 'Sheet1!A1')
        input_file: Path to input JSON file
        service: Google Sheets API service (will be created if None)
        clear_first: Whether to clear the range before importing
        
    Returns:
        True if import was successful
    """
    try:
        # Read JSON data
        with open(input_file, 'r') as f:
            json_data = json.load(f)
            
        if not json_data:
            logger.warning(f"No data found in JSON file {input_file}")
            return False
            
        # Convert JSON data to sheet format
        if isinstance(json_data, list):
            if len(json_data) > 0 and isinstance(json_data[0], dict):
                # Get all unique keys as headers
                headers = []
                for item in json_data:
                    for key in item.keys():
                        if key not in headers:
                            headers.append(key)
                
                # Create rows with headers
                values = [headers]
                
                # Add data rows
                for item in json_data:
                    row = []
                    for header in headers:
                        row.append(item.get(header, ""))
                    values.append(row)
            else:
                # Simple list of values
                values = json_data
        else:
            logger.error(f"JSON data must be a list, got {type(json_data)}")
            return False
            
        # Clear the range if requested
        if clear_first:
            clear_sheet_range(spreadsheet_id, range_name, service)
            
        # Write data to sheet
        write_sheet(spreadsheet_id, range_name, values, service)
        
        logger.info(f"Imported {len(values)} rows to {range_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error importing JSON to sheet: {str(e)}")
        return False


def validate_sheet_structure(spreadsheet_id: str, range_name: str, 
                            expected_headers: List[str], service=None) -> bool:
    """
    Validates that a sheet has the expected structure (columns)
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        range_name: Range to validate (e.g., 'Sheet1!A1:Z1')
        expected_headers: List of expected column headers
        service: Google Sheets API service (will be created if None)
        
    Returns:
        True if sheet structure is valid
    """
    try:
        # Read the first row to get headers
        data = read_sheet(spreadsheet_id, range_name, service)
        
        if not data or len(data) == 0:
            logger.error(f"No data found in range {range_name}")
            return False
            
        headers = data[0]
        
        # Check if all expected headers are present
        missing_headers = [h for h in expected_headers if h not in headers]
        if missing_headers:
            logger.error(f"Missing expected headers: {missing_headers}")
            return False
            
        # Check if headers are in the expected order
        for i, expected in enumerate(expected_headers):
            if i >= len(headers) or headers[i] != expected:
                logger.error(f"Header at position {i} should be '{expected}' but is '{headers[i] if i < len(headers) else 'missing'}'")
                return False
                
        logger.info(f"Sheet structure validated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error validating sheet structure: {str(e)}")
        return False


def create_backup_sheet(spreadsheet_id: str, source_sheet_name: str, service=None) -> str:
    """
    Creates a backup of a sheet with timestamp in the name
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        source_sheet_name: Name of the sheet to backup
        service: Google Sheets API service (will be created if None)
        
    Returns:
        Name of the created backup sheet
    """
    try:
        if service is None:
            service = get_sheets_service()
            
        # Create backup sheet name with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_sheet_name = f"Backup_{source_sheet_name}_{timestamp}"
        
        # Create new sheet
        sheet_id = create_sheet(spreadsheet_id, backup_sheet_name, service)
        
        # Get the full data range of the source sheet
        source_range = f"{source_sheet_name}!A1:Z1000"  # Adjust this as needed
        destination_range = f"{backup_sheet_name}!A1"
        
        # Copy data from source to backup
        copy_sheet_data(
            spreadsheet_id, 
            source_range, 
            spreadsheet_id, 
            destination_range, 
            service
        )
        
        logger.info(f"Created backup sheet '{backup_sheet_name}'")
        return backup_sheet_name
        
    except Exception as e:
        logger.error(f"Error creating backup sheet: {str(e)}")
        raise


def find_in_sheet(spreadsheet_id: str, range_name: str, search_value: Any, 
                 service=None, exact_match: bool = True) -> List[Tuple[int, int]]:
    """
    Searches for a value in a sheet and returns matching cell positions
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        range_name: Range to search in (e.g., 'Sheet1!A1:B10')
        search_value: Value to search for
        service: Google Sheets API service (will be created if None)
        exact_match: Whether to require exact match or substring match (for strings)
        
    Returns:
        List of (row, column) positions where value was found
    """
    try:
        # Read sheet data
        data = read_sheet(spreadsheet_id, range_name, service)
        
        if not data:
            logger.warning(f"No data found in range {range_name}")
            return []
            
        # Convert search_value to string for comparison
        if not isinstance(search_value, str):
            search_value = str(search_value)
            
        # Search in each cell
        positions = []
        for row_idx, row in enumerate(data):
            for col_idx, cell in enumerate(row):
                cell_str = str(cell)
                
                if exact_match and cell_str == search_value:
                    positions.append((row_idx, col_idx))
                elif not exact_match and search_value in cell_str:
                    positions.append((row_idx, col_idx))
                    
        logger.debug(f"Found {len(positions)} matches for '{search_value}' in {range_name}")
        return positions
        
    except Exception as e:
        logger.error(f"Error searching in sheet: {str(e)}")
        return []


def get_sheet_metadata(spreadsheet_id: str, service=None) -> dict:
    """
    Gets metadata about a spreadsheet including sheets, named ranges, etc.
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        service: Google Sheets API service (will be created if None)
        
    Returns:
        Spreadsheet metadata
    """
    try:
        if service is None:
            service = get_sheets_service()
            
        # Get spreadsheet metadata
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        
        logger.debug(f"Retrieved metadata for spreadsheet {spreadsheet_id}")
        return spreadsheet
        
    except googleapiclient.errors.HttpError as error:
        logger.error(f"Google Sheets API error while getting metadata: {str(error)}")
        raise
    except Exception as e:
        logger.error(f"Error getting spreadsheet metadata: {str(e)}")
        raise


def list_sheets(spreadsheet_id: str, service=None) -> Dict[str, int]:
    """
    Lists all sheets in a spreadsheet with their IDs
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        service: Google Sheets API service (will be created if None)
        
    Returns:
        Dictionary mapping sheet names to sheet IDs
    """
    try:
        # Get spreadsheet metadata
        metadata = get_sheet_metadata(spreadsheet_id, service)
        
        # Extract sheet information
        sheets = {}
        for sheet in metadata.get('sheets', []):
            properties = sheet.get('properties', {})
            title = properties.get('title')
            sheet_id = properties.get('sheetId')
            
            if title and sheet_id is not None:
                sheets[title] = sheet_id
                
        logger.info(f"Found {len(sheets)} sheets in spreadsheet {spreadsheet_id}")
        return sheets
        
    except Exception as e:
        logger.error(f"Error listing sheets: {str(e)}")
        raise


def create_test_sheet(spreadsheet_id: str = None, sheet_name: str = None, 
                     sample_data: List[List[Any]] = None, service=None) -> bool:
    """
    Creates a test sheet with sample data for testing purposes
    
    Args:
        spreadsheet_id: ID of the spreadsheet (uses test ID from settings if None)
        sheet_name: Name for the test sheet (uses 'TestSheet_timestamp' if None)
        sample_data: Test data to populate the sheet with
        service: Google Sheets API service (will be created if None)
        
    Returns:
        True if test sheet was created successfully
    """
    try:
        if service is None:
            service = get_sheets_service()
            
        # Use default spreadsheet ID if none provided
        if spreadsheet_id is None:
            spreadsheet_id = API_TEST_SETTINGS.get('SHEETS_TEST_SPREADSHEET_ID')
            if not spreadsheet_id:
                logger.error("No spreadsheet ID provided and no default test spreadsheet ID configured")
                return False
                
        # Generate test sheet name if none provided
        if sheet_name is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            sheet_name = f"TestSheet_{timestamp}"
            
        # Generate sample data if none provided
        if sample_data is None:
            sample_data = [
                ["Header1", "Header2", "Header3"],
                ["Value1A", "Value1B", "Value1C"],
                ["Value2A", "Value2B", "Value2C"],
                ["Value3A", "Value3B", "Value3C"]
            ]
            
        # Create the test sheet
        create_sheet(spreadsheet_id, sheet_name, service)
        
        # Write sample data to the sheet
        range_name = f"{sheet_name}!A1"
        write_sheet(spreadsheet_id, range_name, sample_data, service)
        
        logger.info(f"Created test sheet '{sheet_name}' with sample data")
        return True
        
    except Exception as e:
        logger.error(f"Error creating test sheet: {str(e)}")
        return False