"""
google_sheets_contract.py - Defines the protocol interface and response contracts for the Google Sheets API client.

This file establishes the expected behavior and data structures for Google Sheets interactions,
enabling consistent testing and mocking of the Google Sheets integration in the Budget Management Application.
"""

from typing import Protocol, List, Dict, Any, Optional  # standard library
from dataclasses import dataclass  # standard library

from ...backend.models.transaction import Transaction
from ...backend.models.budget import Budget

# Schema for validating Google Sheets read response
SHEET_READ_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "range": {"type": "string"},
        "majorDimension": {"type": "string", "enum": ["ROWS", "COLUMNS"]},
        "values": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}}
    },
    "required": ["range", "values"]
}

# Schema for validating Google Sheets append response
SHEET_APPEND_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "spreadsheetId": {"type": "string"},
        "tableRange": {"type": "string"},
        "updates": {
            "type": "object",
            "properties": {
                "spreadsheetId": {"type": "string"},
                "updatedRange": {"type": "string"},
                "updatedRows": {"type": "integer"},
                "updatedColumns": {"type": "integer"},
                "updatedCells": {"type": "integer"}
            },
            "required": ["spreadsheetId", "updatedRange", "updatedRows", "updatedColumns", "updatedCells"]
        }
    },
    "required": ["spreadsheetId", "updates"]
}

# Schema for validating Google Sheets update response
SHEET_UPDATE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "spreadsheetId": {"type": "string"},
        "updatedRange": {"type": "string"},
        "updatedRows": {"type": "integer"},
        "updatedColumns": {"type": "integer"},
        "updatedCells": {"type": "integer"}
    },
    "required": ["spreadsheetId", "updatedRange", "updatedRows", "updatedColumns", "updatedCells"]
}

# Schema for validating Google Sheets batch update response
SHEET_BATCH_UPDATE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "spreadsheetId": {"type": "string"},
        "responses": {"type": "array", "items": {"type": "object"}}
    },
    "required": ["spreadsheetId", "responses"]
}

# Schema for validating Google Sheets clear response
SHEET_CLEAR_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "spreadsheetId": {"type": "string"},
        "clearedRange": {"type": "string"}
    },
    "required": ["spreadsheetId", "clearedRange"]
}

# Schema for validating Master Budget structure
MASTER_BUDGET_SCHEMA = {
    "type": "array",
    "items": {
        "type": "array",
        "minItems": 2,
        "maxItems": 2,
        "items": [
            {"type": "string", "description": "Category name"},
            {"type": "string", "description": "Weekly budget amount"}
        ]
    }
}

# Schema for validating Weekly Spending structure
WEEKLY_SPENDING_SCHEMA = {
    "type": "array",
    "items": {
        "type": "array",
        "minItems": 3,
        "maxItems": 4,
        "items": [
            {"type": "string", "description": "Transaction location"},
            {"type": "string", "description": "Transaction amount"},
            {"type": "string", "description": "Transaction timestamp"},
            {"type": "string", "description": "Corresponding category (optional)"}
        ]
    }
}


class GoogleSheetsClientProtocol(Protocol):
    """Protocol defining the interface for Google Sheets API client"""
    
    def __init__(self, auth_service: Optional[object] = None):
        """
        Initialize the Google Sheets client
        
        Args:
            auth_service: Optional authentication service for Google Sheets API
        """
        ...
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Sheets API
        
        Returns:
            True if authentication successful, False otherwise
        """
        ...
    
    def ensure_authenticated(self) -> bool:
        """
        Ensure client is authenticated before making API calls
        
        Returns:
            True if authenticated, False otherwise
        """
        ...
    
    def read_sheet(self, spreadsheet_id: str, range_name: str, value_render_option: str = "FORMATTED_VALUE") -> List[List[Any]]:
        """
        Read data from a Google Sheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: A1 notation of the range to read
            value_render_option: How values should be rendered in the output
        
        Returns:
            Sheet data as a list of rows
        """
        ...
    
    def append_rows(self, spreadsheet_id: str, range_name: str, values: List[List[Any]], 
                   value_input_option: str = "USER_ENTERED", insert_data_option: str = "INSERT_ROWS") -> dict:
        """
        Append rows to a Google Sheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: A1 notation of the range to append to
            values: Values to append
            value_input_option: How input data should be interpreted
            insert_data_option: How the input data should be inserted
        
        Returns:
            API response
        """
        ...
    
    def update_values(self, spreadsheet_id: str, range_name: str, values: List[List[Any]], 
                     value_input_option: str = "USER_ENTERED") -> dict:
        """
        Update values in a Google Sheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: A1 notation of the range to update
            values: Values to update
            value_input_option: How input data should be interpreted
        
        Returns:
            API response
        """
        ...
    
    def batch_update(self, spreadsheet_id: str, requests: List[Dict]) -> dict:
        """
        Perform batch update operations on a Google Sheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            requests: List of update request objects
        
        Returns:
            API response
        """
        ...
    
    def get_weekly_spending_data(self) -> List[List[Any]]:
        """
        Get transaction data from Weekly Spending sheet
        
        Returns:
            Transaction data as a list of rows
        """
        ...
    
    def get_master_budget_data(self) -> List[List[Any]]:
        """
        Get budget data from Master Budget sheet
        
        Returns:
            Budget data as a list of rows
        """
        ...
    
    def append_transactions(self, transactions: List[Transaction]) -> int:
        """
        Append transactions to Weekly Spending sheet
        
        Args:
            transactions: List of Transaction objects
        
        Returns:
            Number of transactions appended
        """
        ...
    
    def update_transaction_categories(self, transactions: List[Transaction], 
                                    location_to_category_map: Dict[str, str]) -> int:
        """
        Update transaction categories in Weekly Spending sheet
        
        Args:
            transactions: List of Transaction objects
            location_to_category_map: Mapping of transaction locations to categories
        
        Returns:
            Number of transactions updated
        """
        ...
    
    def get_transactions(self) -> List[Transaction]:
        """
        Get transactions from Weekly Spending sheet as Transaction objects
        
        Returns:
            List of Transaction objects
        """
        ...
    
    def get_budget(self, actual_spending: Dict[str, Any]) -> Budget:
        """
        Get budget data from Master Budget sheet as a Budget object
        
        Args:
            actual_spending: Dictionary of actual spending by category
        
        Returns:
            Budget object with categories and actual spending
        """
        ...


@dataclass
class SheetResponseContract:
    """Contract for Google Sheets API responses"""
    spreadsheet_id: str
    range: str
    values: Optional[List[List[Any]]] = None
    updates: Optional[Dict] = None
    updated_rows: Optional[int] = None
    updated_columns: Optional[int] = None
    updated_cells: Optional[int] = None
    cleared_range: Optional[str] = None


@dataclass
class MasterBudgetContract:
    """Contract for Master Budget sheet structure"""
    rows: List[List[str]]
    
    def validate(self) -> bool:
        """
        Validate that the data conforms to the Master Budget schema
        
        Returns:
            True if valid, False otherwise
        """
        # Check that we have data
        if not self.rows or not isinstance(self.rows, list):
            return False
        
        # Check each row has expected structure
        for row in self.rows:
            if not isinstance(row, list) or len(row) < 2:
                return False
            
            # Category name must be a non-empty string
            if not isinstance(row[0], str) or not row[0].strip():
                return False
            
            # Budget amount must be convertible to decimal
            try:
                amount = str(row[1]).strip()
                if not amount or amount.startswith('-'):
                    return False
            except:
                return False
        
        return True
    
    def to_categories(self) -> List[object]:
        """
        Convert the budget data to Category objects
        
        Returns:
            List of Category objects
        """
        from ...backend.models.category import create_categories_from_sheet_data
        return create_categories_from_sheet_data(self.rows)


@dataclass
class WeeklySpendingContract:
    """Contract for Weekly Spending sheet structure"""
    rows: List[List[str]]
    
    def validate(self) -> bool:
        """
        Validate that the data conforms to the Weekly Spending schema
        
        Returns:
            True if valid, False otherwise
        """
        # Check that we have data
        if not self.rows or not isinstance(self.rows, list):
            return False
        
        # Check each row has expected structure
        for row in self.rows:
            if not isinstance(row, list) or len(row) < 3:
                return False
            
            # Location must be a string
            if not isinstance(row[0], str):
                return False
            
            # Amount must be convertible to decimal
            try:
                amount = str(row[1]).strip()
                if not amount:
                    return False
            except:
                return False
            
            # Timestamp must be a string
            if not isinstance(row[2], str) or not row[2].strip():
                return False
        
        return True
    
    def to_transactions(self) -> List[Transaction]:
        """
        Convert the transaction data to Transaction objects
        
        Returns:
            List of Transaction objects
        """
        from ...backend.models.transaction import create_transactions_from_sheet_data
        return create_transactions_from_sheet_data(self.rows)