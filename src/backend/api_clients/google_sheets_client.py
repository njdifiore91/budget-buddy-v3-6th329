"""
google_sheets_client.py - Client for interacting with the Google Sheets API

This module provides a client for reading and writing budget and transaction data to Google Sheets.
It includes functionality for retrieving transactions, updating categories, and analyzing budget data.
"""

import logging
from typing import List, Dict, Optional, Any
import decimal  # standard library

# Google API client imports
import googleapiclient.discovery  # google-api-python-client 2.100.0+
import googleapiclient.errors  # google-api-python-client 2.100.0+

# Internal imports
from ..config.settings import API_SETTINGS, APP_SETTINGS
from ..services.authentication_service import AuthenticationService
from ..utils.error_handlers import retry_with_backoff, handle_api_error, APIError
from ..models.transaction import Transaction, create_transactions_from_sheet_data
from ..models.budget import create_budget_from_sheet_data

# Set up logger
logger = logging.getLogger(__name__)

# Constants for sheet names and column indices
WEEKLY_SPENDING_SHEET_NAME = "Weekly Spending"
MASTER_BUDGET_SHEET_NAME = "Master Budget"
TRANSACTION_LOCATION_COL = 0
TRANSACTION_AMOUNT_COL = 1
TRANSACTION_TIME_COL = 2
TRANSACTION_CATEGORY_COL = 3
BUDGET_CATEGORY_COL = 0
BUDGET_AMOUNT_COL = 1


def build_sheets_service(credentials):
    """
    Builds and returns a Google Sheets API service object
    
    Args:
        credentials: Google OAuth2 credentials object
        
    Returns:
        Google Sheets API service object
    """
    try:
        service = googleapiclient.discovery.build(
            'sheets', 
            API_SETTINGS['GOOGLE_SHEETS']['API_VERSION'],
            credentials=credentials
        )
        return service
    except Exception as e:
        logger.error(f"Failed to build Google Sheets service: {str(e)}")
        raise APIError(
            f"Failed to build Google Sheets service: {str(e)}",
            "Google Sheets",
            "build_service"
        )


def parse_sheet_range(range_string: str) -> tuple:
    """
    Parses a sheet range string into components
    
    Args:
        range_string: Sheet range string (e.g., 'Sheet1!A1:B10')
        
    Returns:
        Tuple of (sheet_name, start_cell, end_cell)
    """
    # Split by '!' to separate sheet name from cell range
    parts = range_string.split('!')
    sheet_name = parts[0].strip("'")
    
    # Extract cell range and split by ':' if it has a range
    if len(parts) > 1:
        cell_range = parts[1]
        if ':' in cell_range:
            start_cell, end_cell = cell_range.split(':')
        else:
            start_cell = cell_range
            end_cell = None
    else:
        start_cell = 'A1'
        end_cell = None
    
    return (sheet_name, start_cell, end_cell)


def format_sheet_range(sheet_name: str, start_cell: str, end_cell: Optional[str] = None) -> str:
    """
    Formats a sheet range from components
    
    Args:
        sheet_name: Name of the sheet
        start_cell: Starting cell reference
        end_cell: Ending cell reference (optional)
        
    Returns:
        Formatted range string
    """
    # Add quotes around sheet name if it contains spaces
    if ' ' in sheet_name:
        sheet_name = f"'{sheet_name}'"
    
    # Format the range string
    if end_cell:
        return f"{sheet_name}!{start_cell}:{end_cell}"
    else:
        return f"{sheet_name}!{start_cell}"


@retry_with_backoff(googleapiclient.errors.HttpError, max_retries=3)
def get_sheet_id(service, spreadsheet_id: str, sheet_name: str) -> int:
    """
    Gets the sheet ID for a named sheet within a spreadsheet
    
    Args:
        service: Google Sheets API service object
        spreadsheet_id: ID of the spreadsheet
        sheet_name: Name of the sheet
        
    Returns:
        Sheet ID
    """
    try:
        # Get spreadsheet metadata
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        
        # Find the sheet with matching title
        for sheet in spreadsheet.get('sheets', []):
            properties = sheet.get('properties', {})
            if properties.get('title') == sheet_name:
                return properties.get('sheetId')
        
        # If no matching sheet found, raise an error
        raise APIError(
            f"Sheet '{sheet_name}' not found in spreadsheet",
            "Google Sheets",
            "get_sheet_id"
        )
    except googleapiclient.errors.HttpError as e:
        logger.error(f"Failed to get sheet ID: {str(e)}")
        raise


class GoogleSheetsClient:
    """Client for interacting with Google Sheets API"""
    
    def __init__(self, auth_service: Optional[AuthenticationService] = None):
        """
        Initialize the Google Sheets client
        
        Args:
            auth_service: Authentication service instance (optional)
        """
        # Initialize authentication service
        self.auth_service = auth_service or AuthenticationService()
        self.service = None
        
        # Set spreadsheet IDs from settings
        self.weekly_spending_id = APP_SETTINGS['WEEKLY_SPENDING_SHEET_ID']
        self.master_budget_id = APP_SETTINGS['MASTER_BUDGET_SHEET_ID']
        
        logger.info("Google Sheets client initialized")
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Sheets API
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Get credentials from authentication service
            credentials = self.auth_service.authenticate_google_sheets()
            
            # Build the service
            self.service = build_sheets_service(credentials)
            
            logger.info("Successfully authenticated with Google Sheets API")
            return True
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Sheets API: {str(e)}")
            return False
    
    def ensure_authenticated(self) -> bool:
        """
        Ensure client is authenticated before making API calls
        
        Returns:
            True if authenticated, False otherwise
        """
        if self.service is None:
            return self.authenticate()
        return True
    
    @retry_with_backoff(googleapiclient.errors.HttpError, max_retries=3)
    def read_sheet(self, spreadsheet_id: str, range_name: str, value_render_option: str = 'UNFORMATTED_VALUE') -> List[List[Any]]:
        """
        Read data from a Google Sheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: Range to read (e.g., 'Sheet1!A1:B10')
            value_render_option: How values should be rendered
            
        Returns:
            Sheet data as a list of rows
        """
        # Ensure client is authenticated
        if not self.ensure_authenticated():
            raise APIError(
                "Failed to authenticate with Google Sheets API",
                "Google Sheets",
                "read_sheet"
            )
        
        try:
            # Call the Sheets API to get values
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueRenderOption=value_render_option
            ).execute()
            
            # Extract values
            values = result.get('values', [])
            
            logger.debug(f"Read {len(values)} rows from {range_name}")
            return values
        except googleapiclient.errors.HttpError as e:
            error_details = {
                "spreadsheet_id": spreadsheet_id,
                "range": range_name,
                "error": str(e)
            }
            logger.error(f"Failed to read sheet: {str(e)}", extra={"context": error_details})
            raise
    
    @retry_with_backoff(googleapiclient.errors.HttpError, max_retries=3)
    def append_rows(self, spreadsheet_id: str, range_name: str, values: List[List[Any]], 
                  value_input_option: str = 'USER_ENTERED', 
                  insert_data_option: str = 'INSERT_ROWS') -> dict:
        """
        Append rows to a Google Sheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: Range to append to (e.g., 'Sheet1!A:B')
            values: Values to append as a list of rows
            value_input_option: How input should be interpreted
            insert_data_option: How the input should be inserted
            
        Returns:
            API response
        """
        # Ensure client is authenticated
        if not self.ensure_authenticated():
            raise APIError(
                "Failed to authenticate with Google Sheets API",
                "Google Sheets",
                "append_rows"
            )
        
        try:
            # Prepare request body
            body = {
                'values': values
            }
            
            # Call the Sheets API to append values
            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                insertDataOption=insert_data_option,
                body=body
            ).execute()
            
            logger.info(f"Appended {len(values)} rows to {range_name}")
            return result
        except googleapiclient.errors.HttpError as e:
            error_details = {
                "spreadsheet_id": spreadsheet_id,
                "range": range_name,
                "num_rows": len(values),
                "error": str(e)
            }
            logger.error(f"Failed to append rows: {str(e)}", extra={"context": error_details})
            raise
    
    @retry_with_backoff(googleapiclient.errors.HttpError, max_retries=3)
    def update_values(self, spreadsheet_id: str, range_name: str, values: List[List[Any]], 
                    value_input_option: str = 'USER_ENTERED') -> dict:
        """
        Update values in a Google Sheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: Range to update (e.g., 'Sheet1!A1:B10')
            values: Values to update as a list of rows
            value_input_option: How input should be interpreted
            
        Returns:
            API response
        """
        # Ensure client is authenticated
        if not self.ensure_authenticated():
            raise APIError(
                "Failed to authenticate with Google Sheets API",
                "Google Sheets",
                "update_values"
            )
        
        try:
            # Prepare request body
            body = {
                'values': values
            }
            
            # Call the Sheets API to update values
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=body
            ).execute()
            
            logger.info(f"Updated {len(values)} rows in {range_name}")
            return result
        except googleapiclient.errors.HttpError as e:
            error_details = {
                "spreadsheet_id": spreadsheet_id,
                "range": range_name,
                "num_rows": len(values),
                "error": str(e)
            }
            logger.error(f"Failed to update values: {str(e)}", extra={"context": error_details})
            raise
    
    @retry_with_backoff(googleapiclient.errors.HttpError, max_retries=3)
    def batch_update(self, spreadsheet_id: str, requests: List[Dict]) -> dict:
        """
        Perform batch update operations on a Google Sheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            requests: List of update requests
            
        Returns:
            API response
        """
        # Ensure client is authenticated
        if not self.ensure_authenticated():
            raise APIError(
                "Failed to authenticate with Google Sheets API",
                "Google Sheets",
                "batch_update"
            )
        
        try:
            # Prepare request body
            body = {
                'requests': requests
            }
            
            # Call the Sheets API to perform batch update
            result = self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            logger.info(f"Performed batch update with {len(requests)} requests")
            return result
        except googleapiclient.errors.HttpError as e:
            error_details = {
                "spreadsheet_id": spreadsheet_id,
                "num_requests": len(requests),
                "error": str(e)
            }
            logger.error(f"Failed to perform batch update: {str(e)}", extra={"context": error_details})
            raise
    
    def get_weekly_spending_data(self) -> List[List[Any]]:
        """
        Get transaction data from Weekly Spending sheet
        
        Returns:
            Transaction data as a list of rows
        """
        # Ensure client is authenticated
        if not self.ensure_authenticated():
            raise APIError(
                "Failed to authenticate with Google Sheets API",
                "Google Sheets",
                "get_weekly_spending_data"
            )
        
        # Construct range string to get all transactions (starting from row 2 to skip header)
        range_name = format_sheet_range(WEEKLY_SPENDING_SHEET_NAME, 'A2', 'D')
        
        # Read sheet data
        data = self.read_sheet(self.weekly_spending_id, range_name)
        
        logger.info(f"Retrieved {len(data)} transactions from Weekly Spending sheet")
        return data
    
    def get_master_budget_data(self) -> List[List[Any]]:
        """
        Get budget data from Master Budget sheet
        
        Returns:
            Budget data as a list of rows
        """
        # Ensure client is authenticated
        if not self.ensure_authenticated():
            raise APIError(
                "Failed to authenticate with Google Sheets API",
                "Google Sheets",
                "get_master_budget_data"
            )
        
        # Construct range string to get all budget categories (starting from row 2 to skip header)
        range_name = format_sheet_range(MASTER_BUDGET_SHEET_NAME, 'A2', 'B')
        
        # Read sheet data
        data = self.read_sheet(self.master_budget_id, range_name)
        
        logger.info(f"Retrieved {len(data)} budget categories from Master Budget sheet")
        return data
    
    def append_transactions(self, transactions: List[Transaction]) -> int:
        """
        Append transactions to Weekly Spending sheet
        
        Args:
            transactions: List of Transaction objects to append
            
        Returns:
            Number of transactions appended
        """
        # Ensure client is authenticated
        if not self.ensure_authenticated():
            raise APIError(
                "Failed to authenticate with Google Sheets API",
                "Google Sheets",
                "append_transactions"
            )
        
        # Convert transactions to sheet format
        values = [transaction.to_sheets_format() for transaction in transactions]
        
        if not values:
            logger.info("No transactions to append")
            return 0
        
        # Construct range string for appending
        range_name = format_sheet_range(WEEKLY_SPENDING_SHEET_NAME, 'A', 'D')
        
        # Append rows to sheet
        result = self.append_rows(
            self.weekly_spending_id,
            range_name,
            values,
            'USER_ENTERED',
            'INSERT_ROWS'
        )
        
        # Get number of transactions appended
        num_appended = len(values)
        logger.info(f"Successfully appended {num_appended} transactions to Weekly Spending sheet")
        
        return num_appended
    
    def update_transaction_categories(self, transactions: List[Transaction], location_to_category_map: Dict[str, str]) -> int:
        """
        Update transaction categories in Weekly Spending sheet
        
        Args:
            transactions: List of Transaction objects
            location_to_category_map: Mapping of transaction locations to categories
            
        Returns:
            Number of transactions updated
        """
        # Ensure client is authenticated
        if not self.ensure_authenticated():
            raise APIError(
                "Failed to authenticate with Google Sheets API",
                "Google Sheets",
                "update_transaction_categories"
            )
        
        # Get existing transaction data
        sheet_data = self.get_weekly_spending_data()
        
        # Track updates to be made
        updates = []
        row_index = 2  # Start at row 2 (after header)
        
        # Process each row in the sheet
        for i, row in enumerate(sheet_data):
            # Skip rows with insufficient data
            if len(row) < 3:
                row_index += 1
                continue
            
            # Get location from row
            location = row[TRANSACTION_LOCATION_COL]
            
            # Check if this location has a category mapping
            if location in location_to_category_map:
                # Get the category to assign
                category = location_to_category_map[location]
                
                # Construct update record
                updates.append({
                    'row': row_index,
                    'category': category
                })
            
            # Increment row index
            row_index += 1
        
        # If no updates needed, return
        if not updates:
            logger.info("No transaction categories to update")
            return 0
        
        # Group updates by contiguous ranges where possible for efficiency
        current_range_start = None
        current_range_values = []
        range_updates = []
        
        for update in sorted(updates, key=lambda u: u['row']):
            if current_range_start is None:
                # Start a new range
                current_range_start = update['row']
                current_range_values = [[update['category']]]
            elif update['row'] == current_range_start + len(current_range_values):
                # Continue the current range
                current_range_values.append([update['category']])
            else:
                # Finish current range and start a new one
                range_name = format_sheet_range(
                    WEEKLY_SPENDING_SHEET_NAME, 
                    f'D{current_range_start}', 
                    f'D{current_range_start + len(current_range_values) - 1}'
                )
                range_updates.append((range_name, current_range_values))
                
                # Start a new range
                current_range_start = update['row']
                current_range_values = [[update['category']]]
        
        # Add the last range
        if current_range_start is not None:
            range_name = format_sheet_range(
                WEEKLY_SPENDING_SHEET_NAME, 
                f'D{current_range_start}', 
                f'D{current_range_start + len(current_range_values) - 1}'
            )
            range_updates.append((range_name, current_range_values))
        
        # Perform updates
        for range_name, values in range_updates:
            self.update_values(
                self.weekly_spending_id,
                range_name,
                values,
                'USER_ENTERED'
            )
        
        # Return the number of transactions updated
        num_updated = len(updates)
        logger.info(f"Successfully updated categories for {num_updated} transactions")
        
        return num_updated
    
    def get_transactions(self) -> List[Transaction]:
        """
        Get transactions from Weekly Spending sheet as Transaction objects
        
        Returns:
            List of Transaction objects
        """
        # Get raw transaction data
        data = self.get_weekly_spending_data()
        
        # Convert to Transaction objects
        transactions = create_transactions_from_sheet_data(data)
        
        logger.info(f"Retrieved {len(transactions)} transactions as objects")
        return transactions
    
    def get_budget(self, actual_spending: Dict[str, decimal.Decimal]):
        """
        Get budget data from Master Budget sheet as a Budget object
        
        Args:
            actual_spending: Dictionary mapping categories to actual spending amounts
            
        Returns:
            Budget object with categories and actual spending
        """
        # Get raw budget data
        data = self.get_master_budget_data()
        
        # Convert to Budget object
        budget = create_budget_from_sheet_data(data, actual_spending)
        
        logger.info("Retrieved budget from Master Budget sheet")
        return budget