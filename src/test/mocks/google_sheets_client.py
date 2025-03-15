"""
google_sheets_client.py - Mock implementation of the Google Sheets API client for testing the Budget Management Application

This mock simulates the behavior of the real GoogleSheetsClient without making actual API calls,
allowing for controlled testing of components that depend on Google Sheets integration.
"""

import logging
import copy
from typing import List, Dict, Any, Optional, Union

from ..contracts.google_sheets_contract import GoogleSheetsClientProtocol, SheetResponseContract
from ...backend.models.transaction import Transaction, create_transactions_from_sheet_data
from ...backend.models.budget import Budget, create_budget_from_sheet_data
from ..utils.fixture_loader import load_fixture

# Set up logger
logger = logging.getLogger(__name__)

# Constants
WEEKLY_SPENDING_SHEET_NAME = "Weekly Spending"
MASTER_BUDGET_SHEET_NAME = "Master Budget"


class MockGoogleSheetsClient:
    """
    Mock implementation of Google Sheets API client for testing
    
    This mock simulates the behavior of the real GoogleSheetsClient without
    making actual API calls, allowing for controlled testing of components
    that depend on Google Sheets integration.
    """
    
    def __init__(self, credentials_file: Optional[str] = None, weekly_spending_id: Optional[str] = None, 
                 master_budget_id: Optional[str] = None, authentication_should_fail: bool = False):
        """
        Initialize the mock Google Sheets client
        
        Args:
            credentials_file: Optional path to credentials file (not used in mock)
            weekly_spending_id: ID for Weekly Spending sheet
            master_budget_id: ID for Master Budget sheet
            authentication_should_fail: If True, authentication attempts will fail
        """
        self.authenticated = False
        self.authentication_should_fail = authentication_should_fail
        self.weekly_spending_id = weekly_spending_id or "mock_weekly_spending_id"
        self.master_budget_id = master_budget_id or "mock_master_budget_id"
        self.sheet_data = {}  # Dictionary to store mock sheet data
        self.response_templates = {}  # Dictionary to store API response templates
        self.call_history = []  # List to track API calls
        
        logger.debug(f"Initialized mock Google Sheets client with weekly_spending_id={self.weekly_spending_id}, "
                     f"master_budget_id={self.master_budget_id}")
    
    def authenticate(self) -> bool:
        """
        Mock authentication with Google Sheets API
        
        Returns:
            True if authentication successful, False otherwise
        """
        if self.authentication_should_fail:
            logger.warning("Mock authentication failed (deliberately)")
            return False
        
        self.authenticated = True
        logger.debug("Mock authentication successful")
        return True
    
    def ensure_authenticated(self) -> bool:
        """
        Ensure client is authenticated before operations
        
        Returns:
            True if authenticated, False otherwise
        """
        if not self.authenticated:
            return self.authenticate()
        return self.authenticated
    
    def set_authentication_failure(self, should_fail: bool) -> None:
        """
        Configure the mock to simulate authentication failure
        
        Args:
            should_fail: If True, authentication attempts will fail
        """
        self.authentication_should_fail = should_fail
        logger.debug(f"Mock authentication failure set to {should_fail}")
    
    def set_sheet_data(self, sheet_name: str, data: List[List[Any]]) -> None:
        """
        Set mock data for a specific sheet
        
        Args:
            sheet_name: Name of the sheet
            data: List of rows for the sheet
        """
        self.sheet_data[sheet_name] = copy.deepcopy(data)
        logger.debug(f"Set mock data for sheet '{sheet_name}' with {len(data)} rows")
    
    def get_sheet_data(self, sheet_name: str) -> List[List[Any]]:
        """
        Get the mock data for a specific sheet
        
        Args:
            sheet_name: Name of the sheet
            
        Returns:
            List of rows for the sheet or empty list if sheet doesn't exist
        """
        data = copy.deepcopy(self.sheet_data.get(sheet_name, []))
        logger.debug(f"Retrieved mock data for sheet '{sheet_name}' with {len(data)} rows")
        return data
    
    def set_response_template(self, operation: str, template: Dict[str, Any]) -> None:
        """
        Set a template for API responses
        
        Args:
            operation: The API operation (e.g., 'read_sheet', 'append_rows')
            template: Response template dictionary
        """
        self.response_templates[operation] = template
        logger.debug(f"Set response template for operation '{operation}'")
    
    def read_sheet(self, spreadsheet_id: str, range_name: str, 
                  value_render_option: str = "FORMATTED_VALUE") -> List[List[Any]]:
        """
        Mock reading data from a Google Sheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: A1 notation of the range to read
            value_render_option: How values should be rendered in the output
            
        Returns:
            Sheet data as a list of rows
        """
        # Record this call
        self.call_history.append({
            "method": "read_sheet",
            "spreadsheet_id": spreadsheet_id,
            "range_name": range_name,
            "value_render_option": value_render_option
        })
        
        # Ensure we're authenticated
        if not self.ensure_authenticated():
            logger.error("Cannot read sheet: Not authenticated")
            return []
        
        # Parse sheet name from range_name
        sheet_name = range_name.split("!")[0] if "!" in range_name else range_name
        
        # Get data for the sheet
        data = self.get_sheet_data(sheet_name)
        
        logger.debug(f"Read {len(data)} rows from sheet '{sheet_name}'")
        return data
    
    def append_rows(self, spreadsheet_id: str, range_name: str, values: List[List[Any]], 
                   value_input_option: str = "USER_ENTERED", 
                   insert_data_option: str = "INSERT_ROWS") -> dict:
        """
        Mock appending rows to a Google Sheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: A1 notation of the range to append to
            values: Values to append
            value_input_option: How input data should be interpreted
            insert_data_option: How the input data should be inserted
            
        Returns:
            API response
        """
        # Record this call
        self.call_history.append({
            "method": "append_rows",
            "spreadsheet_id": spreadsheet_id,
            "range_name": range_name,
            "values": values,
            "value_input_option": value_input_option,
            "insert_data_option": insert_data_option
        })
        
        # Ensure we're authenticated
        if not self.ensure_authenticated():
            logger.error("Cannot append rows: Not authenticated")
            return {"error": "Not authenticated"}
        
        # Parse sheet name from range_name
        sheet_name = range_name.split("!")[0] if "!" in range_name else range_name
        
        # Initialize the sheet if it doesn't exist
        if sheet_name not in self.sheet_data:
            self.sheet_data[sheet_name] = []
        
        # Append the values to the sheet
        self.sheet_data[sheet_name].extend(copy.deepcopy(values))
        
        # Create response mimicking Google Sheets API
        response = {
            "spreadsheetId": spreadsheet_id,
            "tableRange": range_name,
            "updates": {
                "spreadsheetId": spreadsheet_id,
                "updatedRange": f"{sheet_name}!A{len(self.sheet_data[sheet_name])-len(values)+1}:Z{len(self.sheet_data[sheet_name])}",
                "updatedRows": len(values),
                "updatedColumns": max([len(row) for row in values]) if values else 0,
                "updatedCells": sum([len(row) for row in values])
            }
        }
        
        logger.debug(f"Appended {len(values)} rows to sheet '{sheet_name}'")
        return response
    
    def update_values(self, spreadsheet_id: str, range_name: str, values: List[List[Any]], 
                     value_input_option: str = "USER_ENTERED") -> dict:
        """
        Mock updating values in a Google Sheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: A1 notation of the range to update
            values: Values to update
            value_input_option: How input data should be interpreted
            
        Returns:
            API response
        """
        # Record this call
        self.call_history.append({
            "method": "update_values",
            "spreadsheet_id": spreadsheet_id,
            "range_name": range_name,
            "values": values,
            "value_input_option": value_input_option
        })
        
        # Ensure we're authenticated
        if not self.ensure_authenticated():
            logger.error("Cannot update values: Not authenticated")
            return {"error": "Not authenticated"}
        
        # Parse sheet name from range_name
        sheet_name = range_name.split("!")[0] if "!" in range_name else range_name
        
        # Initialize the sheet if it doesn't exist
        if sheet_name not in self.sheet_data:
            self.sheet_data[sheet_name] = []
        
        # In a real implementation, we would need to handle the range more correctly
        # For simplicity in the mock, we'll just count the cells updated
        
        # Create response mimicking Google Sheets API
        response = {
            "spreadsheetId": spreadsheet_id,
            "updatedRange": range_name,
            "updatedRows": len(values),
            "updatedColumns": max([len(row) for row in values]) if values else 0,
            "updatedCells": sum([len(row) for row in values])
        }
        
        logger.debug(f"Updated {response['updatedCells']} cells in sheet '{sheet_name}'")
        return response
    
    def batch_update(self, spreadsheet_id: str, requests: List[Dict]) -> dict:
        """
        Mock batch update operations on a Google Sheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            requests: List of update request objects
            
        Returns:
            API response
        """
        # Record this call
        self.call_history.append({
            "method": "batch_update",
            "spreadsheet_id": spreadsheet_id,
            "requests": requests
        })
        
        # Ensure we're authenticated
        if not self.ensure_authenticated():
            logger.error("Cannot perform batch update: Not authenticated")
            return {"error": "Not authenticated"}
        
        # In a real implementation, we would process each request
        # For the mock, we'll just return a simple response
        
        # Create response mimicking Google Sheets API
        response = {
            "spreadsheetId": spreadsheet_id,
            "responses": [{"key": f"request_{i}"} for i in range(len(requests))]
        }
        
        logger.debug(f"Processed {len(requests)} batch update requests")
        return response
    
    def get_weekly_spending_data(self) -> List[List[Any]]:
        """
        Get transaction data from Weekly Spending sheet
        
        Returns:
            Transaction data as a list of rows
        """
        # Ensure we're authenticated
        if not self.ensure_authenticated():
            logger.error("Cannot get weekly spending data: Not authenticated")
            return []
        
        # Get data for the Weekly Spending sheet
        data = self.get_sheet_data(WEEKLY_SPENDING_SHEET_NAME)
        logger.debug(f"Retrieved {len(data)} rows from Weekly Spending sheet")
        return data
    
    def get_master_budget_data(self) -> List[List[Any]]:
        """
        Get budget data from Master Budget sheet
        
        Returns:
            Budget data as a list of rows
        """
        # Ensure we're authenticated
        if not self.ensure_authenticated():
            logger.error("Cannot get master budget data: Not authenticated")
            return []
        
        # Get data for the Master Budget sheet
        data = self.get_sheet_data(MASTER_BUDGET_SHEET_NAME)
        logger.debug(f"Retrieved {len(data)} rows from Master Budget sheet")
        return data
    
    def append_transactions(self, transactions: List[Transaction]) -> int:
        """
        Mock appending transactions to Weekly Spending sheet
        
        Args:
            transactions: List of Transaction objects
            
        Returns:
            Number of transactions appended
        """
        # Ensure we're authenticated
        if not self.ensure_authenticated():
            logger.error("Cannot append transactions: Not authenticated")
            return 0
        
        # Convert transactions to sheet format
        formatted_transactions = [transaction.to_sheets_format() for transaction in transactions]
        
        # Append to Weekly Spending sheet
        if WEEKLY_SPENDING_SHEET_NAME not in self.sheet_data:
            self.sheet_data[WEEKLY_SPENDING_SHEET_NAME] = []
        
        self.sheet_data[WEEKLY_SPENDING_SHEET_NAME].extend(formatted_transactions)
        
        logger.debug(f"Appended {len(transactions)} transactions to Weekly Spending sheet")
        return len(transactions)
    
    def update_transaction_categories(self, transactions: List[Transaction], 
                                    location_to_category_map: Dict[str, str]) -> int:
        """
        Mock updating transaction categories in Weekly Spending sheet
        
        Args:
            transactions: List of Transaction objects
            location_to_category_map: Mapping of transaction locations to categories
            
        Returns:
            Number of transactions updated
        """
        # Ensure we're authenticated
        if not self.ensure_authenticated():
            logger.error("Cannot update transaction categories: Not authenticated")
            return 0
        
        # Get weekly spending data
        weekly_spending_data = self.get_sheet_data(WEEKLY_SPENDING_SHEET_NAME)
        
        # Update the categories in the data
        updated_count = 0
        for i, row in enumerate(weekly_spending_data):
            if len(row) >= 1:  # Ensure row has a location
                location = row[0]
                if location in location_to_category_map:
                    category = location_to_category_map[location]
                    
                    # Ensure row has enough elements for category (should be at index 3)
                    while len(row) < 4:
                        row.append("")
                    
                    row[3] = category
                    updated_count += 1
        
        # Update the sheet data
        self.sheet_data[WEEKLY_SPENDING_SHEET_NAME] = weekly_spending_data
        
        logger.debug(f"Updated categories for {updated_count} transactions in Weekly Spending sheet")
        return updated_count
    
    def get_transactions(self) -> List[Transaction]:
        """
        Get transactions from Weekly Spending sheet as Transaction objects
        
        Returns:
            List of Transaction objects
        """
        # Ensure we're authenticated
        if not self.ensure_authenticated():
            logger.error("Cannot get transactions: Not authenticated")
            return []
        
        # Get weekly spending data
        weekly_spending_data = self.get_sheet_data(WEEKLY_SPENDING_SHEET_NAME)
        
        # Convert to Transaction objects
        transactions = create_transactions_from_sheet_data(weekly_spending_data)
        
        logger.debug(f"Retrieved {len(transactions)} transactions from Weekly Spending sheet")
        return transactions
    
    def get_budget(self, actual_spending: Dict[str, Any]) -> Budget:
        """
        Get budget data from Master Budget sheet as a Budget object
        
        Args:
            actual_spending: Dictionary of actual spending by category
            
        Returns:
            Budget object with categories and actual spending
        """
        # Ensure we're authenticated
        if not self.ensure_authenticated():
            logger.error("Cannot get budget: Not authenticated")
            return None
        
        # Get master budget data
        master_budget_data = self.get_sheet_data(MASTER_BUDGET_SHEET_NAME)
        
        # Convert to Budget object
        budget = create_budget_from_sheet_data(master_budget_data, actual_spending)
        
        logger.debug("Retrieved budget from Master Budget sheet")
        return budget
    
    def reset(self) -> None:
        """
        Reset the mock to its initial state
        """
        self.authenticated = False
        self.sheet_data = {}
        self.call_history = []
        logger.debug("Reset mock Google Sheets client")
    
    def get_call_history(self) -> List[Dict]:
        """
        Get the history of calls made to this mock
        
        Returns:
            List of recorded API calls
        """
        return copy.deepcopy(self.call_history)