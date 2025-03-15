"""
mock_google_sheets_client.py - Mock implementation of the Google Sheets API client for testing purposes.

This module provides a mock implementation of the GoogleSheetsClient class for testing
the Budget Management Application without making actual API calls to Google Sheets.
It simulates the behavior of reading, writing, and updating data in Google Sheets.
"""

from typing import List, Dict, Optional, Any
import decimal
from decimal import Decimal
import copy

# Internal imports
from ...api_clients.google_sheets_client import GoogleSheetsClient
from ...models.transaction import Transaction, create_transactions_from_sheet_data
from ...models.budget import create_budget_from_sheet_data
from ...utils.error_handlers import APIError
from ..fixtures.transactions import load_transaction_data
from ..fixtures.budget import load_budget_data

# Constants for mock sheet IDs and names
DEFAULT_WEEKLY_SPENDING_SHEET_ID = "mock-weekly-spending-sheet-id"
DEFAULT_MASTER_BUDGET_SHEET_ID = "mock-master-budget-sheet-id"
WEEKLY_SPENDING_SHEET_NAME = "Weekly Spending"
MASTER_BUDGET_SHEET_NAME = "Master Budget"


def create_mock_sheet_response(values: list) -> dict:
    """
    Creates a mock API response for sheet data retrieval
    
    Args:
        values: Sheet data as a list of rows
        
    Returns:
        Mock API response with sheet values
    """
    return {
        'values': values
    }


def create_mock_append_response(values: list) -> dict:
    """
    Creates a mock API response for appending rows
    
    Args:
        values: Values that were appended
        
    Returns:
        Mock API response for append operation
    """
    # Calculate metrics for the mock response
    updated_rows = len(values)
    updated_columns = len(values[0]) if values and values[0] else 0
    
    return {
        'updatedRange': f"{WEEKLY_SPENDING_SHEET_NAME}!A1:D{updated_rows}",
        'updatedRows': updated_rows,
        'updatedColumns': updated_columns,
        'updatedCells': updated_rows * updated_columns
    }


def create_mock_update_response(values: list) -> dict:
    """
    Creates a mock API response for updating cells
    
    Args:
        values: Values that were updated
        
    Returns:
        Mock API response for update operation
    """
    # Calculate metrics for the mock response
    updated_rows = len(values)
    updated_columns = len(values[0]) if values and values[0] else 0
    
    return {
        'spreadsheetId': DEFAULT_WEEKLY_SPENDING_SHEET_ID,
        'updatedRange': f"{WEEKLY_SPENDING_SHEET_NAME}!A1:D{updated_rows}",
        'updatedRows': updated_rows,
        'updatedColumns': updated_columns,
        'updatedCells': updated_rows * updated_columns
    }


def create_mock_batch_update_response(requests: list) -> dict:
    """
    Creates a mock API response for batch update
    
    Args:
        requests: List of update requests
        
    Returns:
        Mock API response for batch update operation
    """
    # Create a response with one response per request
    responses = [{'spreadsheetId': DEFAULT_WEEKLY_SPENDING_SHEET_ID} for _ in requests]
    
    return {
        'spreadsheetId': DEFAULT_WEEKLY_SPENDING_SHEET_ID,
        'responses': responses
    }


class MockGoogleSheetsClient:
    """Mock implementation of the Google Sheets API client for testing"""
    
    def __init__(self, auth_success: bool = True, api_error: bool = False,
                 weekly_spending_id: Optional[str] = None,
                 master_budget_id: Optional[str] = None,
                 initial_data: Optional[Dict] = None):
        """
        Initialize the mock Google Sheets client
        
        Args:
            auth_success: Whether authentication should succeed
            api_error: Whether API calls should raise errors
            weekly_spending_id: ID for Weekly Spending sheet
            master_budget_id: ID for Master Budget sheet
            initial_data: Initial data to populate sheets with
        """
        # Set sheet IDs, using defaults if not provided
        self.weekly_spending_id = weekly_spending_id or DEFAULT_WEEKLY_SPENDING_SHEET_ID
        self.master_budget_id = master_budget_id or DEFAULT_MASTER_BUDGET_SHEET_ID
        
        # Set authentication and error simulation flags
        self.auth_success = auth_success
        self.api_error = api_error
        
        # Initialize storage for mock sheet data
        self.sheets_data = {}
        
        # Initialize operation counters
        self.append_count = 0
        self.update_count = 0
        self.batch_update_count = 0
        
        # Initialize sheets data with provided data or empty sheets
        if initial_data:
            self.sheets_data = copy.deepcopy(initial_data)
        else:
            self.sheets_data = {
                WEEKLY_SPENDING_SHEET_NAME: [],
                MASTER_BUDGET_SHEET_NAME: []
            }
    
    def authenticate(self) -> bool:
        """
        Mock authentication with Google Sheets API
        
        Returns:
            True if authentication successful, False otherwise
        """
        return self.auth_success
    
    def ensure_authenticated(self) -> bool:
        """
        Ensure client is authenticated before making API calls
        
        Returns:
            True if authenticated, False otherwise
            
        Raises:
            APIError: If api_error is True
        """
        if not self.auth_success:
            return False
        
        if self.api_error:
            raise APIError(
                "Simulated API error",
                "Google Sheets",
                "mock_operation"
            )
        
        return True
    
    def set_sheet_data(self, sheet_name: str, data: list) -> None:
        """
        Set mock data for a specific sheet
        
        Args:
            sheet_name: Name of the sheet
            data: Sheet data as a list of rows
        """
        self.sheets_data[sheet_name] = copy.deepcopy(data)
    
    def get_sheet_data(self, sheet_name: str) -> list:
        """
        Get mock data for a specific sheet
        
        Args:
            sheet_name: Name of the sheet
            
        Returns:
            Sheet data as a list of rows
        """
        return self.sheets_data.get(sheet_name, [])
    
    def set_api_error(self, error_state: bool) -> None:
        """
        Set API error flag for testing error scenarios
        
        Args:
            error_state: Whether API calls should raise errors
        """
        self.api_error = error_state
    
    def read_sheet(self, spreadsheet_id: str, range_name: str, 
                  value_render_option: str = 'UNFORMATTED_VALUE') -> List[List[Any]]:
        """
        Mock reading data from a Google Sheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: Range to read (e.g., 'Sheet1!A1:B10')
            value_render_option: How values should be rendered
            
        Returns:
            Sheet data as a list of rows
            
        Raises:
            APIError: If api_error is True
        """
        # Ensure client is authenticated
        if not self.ensure_authenticated():
            raise APIError(
                "Client not authenticated",
                "Google Sheets",
                "read_sheet"
            )
        
        # Extract sheet name from range
        sheet_name = range_name.split('!')[0].strip("'")
        
        # Get data for the sheet
        data = self.get_sheet_data(sheet_name)
        
        return data
    
    def append_rows(self, spreadsheet_id: str, range_name: str, values: List[List[Any]], 
                  value_input_option: str = 'USER_ENTERED', 
                  insert_data_option: str = 'INSERT_ROWS') -> dict:
        """
        Mock appending rows to a Google Sheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: Range to append to (e.g., 'Sheet1!A:B')
            values: Values to append as a list of rows
            value_input_option: How input should be interpreted
            insert_data_option: How the input should be inserted
            
        Returns:
            API response
            
        Raises:
            APIError: If api_error is True
        """
        # Ensure client is authenticated
        if not self.ensure_authenticated():
            raise APIError(
                "Client not authenticated",
                "Google Sheets",
                "append_rows"
            )
        
        # Extract sheet name from range
        sheet_name = range_name.split('!')[0].strip("'")
        
        # Get current data for the sheet
        current_data = self.get_sheet_data(sheet_name)
        
        # Append the new values to the current data
        updated_data = current_data + copy.deepcopy(values)
        
        # Update sheet data
        self.set_sheet_data(sheet_name, updated_data)
        
        # Increment append counter
        self.append_count += 1
        
        # Return mock API response
        return create_mock_append_response(values)
    
    def update_values(self, spreadsheet_id: str, range_name: str, values: List[List[Any]], 
                    value_input_option: str = 'USER_ENTERED') -> dict:
        """
        Mock updating values in a Google Sheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: Range to update (e.g., 'Sheet1!A1:B10')
            values: Values to update as a list of rows
            value_input_option: How input should be interpreted
            
        Returns:
            API response
            
        Raises:
            APIError: If api_error is True
        """
        # Ensure client is authenticated
        if not self.ensure_authenticated():
            raise APIError(
                "Client not authenticated",
                "Google Sheets",
                "update_values"
            )
        
        # Extract sheet name and cell range from range_name
        parts = range_name.split('!')
        sheet_name = parts[0].strip("'")
        
        # Parse the cell range to determine start row and column
        if len(parts) > 1:
            cell_range = parts[1]
            # Simple parsing - assumes ranges like 'A1:B2' or 'A1'
            start_cell = cell_range.split(':')[0]
            # Extract row number from start cell (e.g., 'A1' -> 1)
            if any(c.isdigit() for c in start_cell):
                start_row = int(''.join(c for c in start_cell if c.isdigit())) - 1
            else:
                start_row = 0
        else:
            start_row = 0
        
        # Get current data for the sheet
        current_data = self.get_sheet_data(sheet_name)
        
        # Extend current_data if needed to accommodate the update
        while len(current_data) < start_row + len(values):
            current_data.append([])
        
        # Update the cells with the new values
        for i, row in enumerate(values):
            row_index = start_row + i
            
            # Extend the row if needed
            while len(current_data[row_index]) < len(row):
                current_data[row_index].append(None)
            
            # Update the cells in the row
            for j, value in enumerate(row):
                current_data[row_index][j] = value
        
        # Update sheet data
        self.set_sheet_data(sheet_name, current_data)
        
        # Increment update counter
        self.update_count += 1
        
        # Return mock API response
        return create_mock_update_response(values)
    
    def batch_update(self, spreadsheet_id: str, requests: List[Dict]) -> dict:
        """
        Mock batch update operations on a Google Sheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            requests: List of update requests
            
        Returns:
            API response
            
        Raises:
            APIError: If api_error is True
        """
        # Ensure client is authenticated
        if not self.ensure_authenticated():
            raise APIError(
                "Client not authenticated",
                "Google Sheets",
                "batch_update"
            )
        
        # Process each request
        for request in requests:
            # In a real implementation, we would process different request types
            # For the mock, we'll just increment the counter
            pass
        
        # Increment batch update counter
        self.batch_update_count += 1
        
        # Return mock API response
        return create_mock_batch_update_response(requests)
    
    def get_weekly_spending_data(self) -> List[List[Any]]:
        """
        Mock retrieval of transaction data from Weekly Spending sheet
        
        Returns:
            Transaction data as a list of rows
            
        Raises:
            APIError: If api_error is True
        """
        # Ensure client is authenticated
        if not self.ensure_authenticated():
            raise APIError(
                "Client not authenticated",
                "Google Sheets",
                "get_weekly_spending_data"
            )
        
        # Return data for Weekly Spending sheet
        return self.get_sheet_data(WEEKLY_SPENDING_SHEET_NAME)
    
    def get_master_budget_data(self) -> List[List[Any]]:
        """
        Mock retrieval of budget data from Master Budget sheet
        
        Returns:
            Budget data as a list of rows
            
        Raises:
            APIError: If api_error is True
        """
        # Ensure client is authenticated
        if not self.ensure_authenticated():
            raise APIError(
                "Client not authenticated",
                "Google Sheets",
                "get_master_budget_data"
            )
        
        # Return data for Master Budget sheet
        return self.get_sheet_data(MASTER_BUDGET_SHEET_NAME)
    
    def append_transactions(self, transactions: List[Transaction]) -> int:
        """
        Mock appending transactions to Weekly Spending sheet
        
        Args:
            transactions: List of Transaction objects to append
            
        Returns:
            Number of transactions appended
            
        Raises:
            APIError: If api_error is True
        """
        # Ensure client is authenticated
        if not self.ensure_authenticated():
            raise APIError(
                "Client not authenticated",
                "Google Sheets",
                "append_transactions"
            )
        
        # Convert transactions to sheet format
        values = [transaction.to_sheets_format() for transaction in transactions]
        
        if not values:
            return 0
        
        # Get current data for Weekly Spending sheet
        current_data = self.get_sheet_data(WEEKLY_SPENDING_SHEET_NAME)
        
        # Append the new values to the current data
        updated_data = current_data + values
        
        # Update sheet data
        self.set_sheet_data(WEEKLY_SPENDING_SHEET_NAME, updated_data)
        
        # Increment append counter
        self.append_count += 1
        
        # Return the number of transactions appended
        return len(values)
    
    def update_transaction_categories(self, transactions: List[Transaction], 
                                     location_to_category_map: Dict[str, str]) -> int:
        """
        Mock updating transaction categories in Weekly Spending sheet
        
        Args:
            transactions: List of Transaction objects
            location_to_category_map: Mapping of transaction locations to categories
            
        Returns:
            Number of transactions updated
            
        Raises:
            APIError: If api_error is True
        """
        # Ensure client is authenticated
        if not self.ensure_authenticated():
            raise APIError(
                "Client not authenticated",
                "Google Sheets",
                "update_transaction_categories"
            )
        
        # Get current data for Weekly Spending sheet
        sheet_data = self.get_sheet_data(WEEKLY_SPENDING_SHEET_NAME)
        
        # Count updates made
        update_count = 0
        
        # Update categories in sheet data
        for i, row in enumerate(sheet_data):
            if len(row) >= 1:  # Ensure row has at least a location
                location = row[0]
                if location in location_to_category_map:
                    # Ensure row has enough elements for category
                    while len(row) < 4:
                        row.append(None)
                    
                    # Update category (index 3)
                    row[3] = location_to_category_map[location]
                    update_count += 1
        
        # Update sheet data
        self.set_sheet_data(WEEKLY_SPENDING_SHEET_NAME, sheet_data)
        
        # Increment update counter
        self.update_count += 1
        
        # Return the number of transactions updated
        return update_count
    
    def get_transactions(self) -> List[Transaction]:
        """
        Mock retrieval of transactions from Weekly Spending sheet as Transaction objects
        
        Returns:
            List of Transaction objects
            
        Raises:
            APIError: If api_error is True
        """
        # Ensure client is authenticated
        if not self.ensure_authenticated():
            raise APIError(
                "Client not authenticated",
                "Google Sheets",
                "get_transactions"
            )
        
        # Get data for Weekly Spending sheet
        sheet_data = self.get_sheet_data(WEEKLY_SPENDING_SHEET_NAME)
        
        # Convert to Transaction objects
        transactions = create_transactions_from_sheet_data(sheet_data)
        
        return transactions
    
    def get_budget(self, actual_spending: Dict[str, decimal.Decimal]):
        """
        Mock retrieval of budget data from Master Budget sheet as a Budget object
        
        Args:
            actual_spending: Dictionary mapping categories to actual spending amounts
            
        Returns:
            Budget object with categories and actual spending
            
        Raises:
            APIError: If api_error is True
        """
        # Ensure client is authenticated
        if not self.ensure_authenticated():
            raise APIError(
                "Client not authenticated",
                "Google Sheets",
                "get_budget"
            )
        
        # Get data for Master Budget sheet
        sheet_data = self.get_sheet_data(MASTER_BUDGET_SHEET_NAME)
        
        # Convert to Budget object
        budget = create_budget_from_sheet_data(sheet_data, actual_spending)
        
        return budget
    
    def test_connectivity(self) -> bool:
        """
        Mock test of connectivity to Google Sheets API
        
        Returns:
            True if connection successful, False otherwise
        """
        return not self.api_error