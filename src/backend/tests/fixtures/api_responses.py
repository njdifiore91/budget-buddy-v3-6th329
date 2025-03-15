"""
Provides mock API responses for testing the Budget Management Application's integration
with external services. This module loads and formats test fixture data to simulate
responses from Capital One, Google Sheets, Gemini AI, and Gmail APIs, enabling
reliable and consistent testing without making actual API calls.
"""

import os  # version: standard library
import json  # version: standard library
from typing import Dict, Any, Optional, Union  # version: standard library

# Define paths to fixture directories
FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(FIXTURES_DIR, 'data')
API_RESPONSES_DIR = os.path.join(DATA_DIR, 'api_responses')
CAPITAL_ONE_DIR = os.path.join(API_RESPONSES_DIR, 'capital_one')
GOOGLE_SHEETS_DIR = os.path.join(API_RESPONSES_DIR, 'google_sheets')
GEMINI_DIR = os.path.join(API_RESPONSES_DIR, 'gemini')
GMAIL_DIR = os.path.join(API_RESPONSES_DIR, 'gmail')


def load_json_fixture(file_path: str) -> Dict[str, Any]:
    """
    Loads JSON data from a fixture file.
    
    Args:
        file_path: Path to the JSON fixture file
        
    Returns:
        Dict[str, Any]: Parsed JSON data from the fixture file
        
    Raises:
        FileNotFoundError: If the fixture file is not found
        json.JSONDecodeError: If the fixture file contains invalid JSON
    """
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Fixture file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in fixture file {file_path}: {str(e)}", e.doc, e.pos)


class MockResponse:
    """
    Mock implementation of the requests.Response class for testing API interactions.
    """
    
    def __init__(self, data: Dict[str, Any], status_code: int, headers: Optional[Dict[str, str]] = None):
        """
        Initialize the mock HTTP response.
        
        Args:
            data: The response data
            status_code: The HTTP status code
            headers: Optional HTTP headers
        """
        self.data = data
        self.status_code = status_code
        self.headers = headers or {}
        
    def json(self) -> Dict[str, Any]:
        """
        Return the response data as JSON.
        
        Returns:
            Dict[str, Any]: Response data
        """
        return self.data
        
    def raise_for_status(self) -> None:
        """
        Raise an exception if the response status indicates an error.
        
        Raises:
            HTTPError: If the status code is 4XX or 5XX
        """
        if 400 <= self.status_code < 600:
            # In a real test environment, we would raise requests.HTTPError here,
            # but for simplicity, we'll just use Exception since we don't want to
            # import requests just for this
            msg = f"Mock HTTP Error: {self.status_code}"
            raise Exception(msg)
            
    @property
    def text(self) -> str:
        """
        Return the response data as a string.
        
        Returns:
            str: JSON-encoded response data as a string
        """
        return json.dumps(self.data)


def create_mock_api_response(data: Dict[str, Any], status_code: int = 200) -> MockResponse:
    """
    Creates a mock HTTP response object with the specified data and status code.
    
    Args:
        data: The response data
        status_code: The HTTP status code (default: 200)
        
    Returns:
        MockResponse: Mock HTTP response object
    """
    return MockResponse(data, status_code)


def create_mock_error_response(error_message: str, status_code: int = 400) -> MockResponse:
    """
    Creates a mock HTTP error response with the specified error message and status code.
    
    Args:
        error_message: The error message
        status_code: The HTTP status code (default: 400)
        
    Returns:
        MockResponse: Mock HTTP error response object
    """
    data = {"error": {"message": error_message}}
    return MockResponse(data, status_code)


def load_capital_one_transactions_response() -> Dict[str, Any]:
    """
    Loads mock Capital One transactions response data.
    
    Returns:
        Dict[str, Any]: Mock Capital One transactions response data
    """
    file_path = os.path.join(CAPITAL_ONE_DIR, 'capital_one_transactions.json')
    return load_json_fixture(file_path)


def load_capital_one_accounts_response() -> Dict[str, Any]:
    """
    Loads mock Capital One accounts response data.
    
    Returns:
        Dict[str, Any]: Mock Capital One accounts response data
    """
    file_path = os.path.join(CAPITAL_ONE_DIR, 'capital_one_accounts.json')
    return load_json_fixture(file_path)


def load_capital_one_transfer_response() -> Dict[str, Any]:
    """
    Loads mock Capital One transfer response data.
    
    Returns:
        Dict[str, Any]: Mock Capital One transfer response data
    """
    file_path = os.path.join(CAPITAL_ONE_DIR, 'capital_one_transfer.json')
    return load_json_fixture(file_path)


def load_capital_one_error_response() -> Dict[str, Any]:
    """
    Loads mock Capital One error response data.
    
    Returns:
        Dict[str, Any]: Mock Capital One error response data
    """
    file_path = os.path.join(CAPITAL_ONE_DIR, 'capital_one_error_responses.json')
    return load_json_fixture(file_path)


def load_google_sheets_budget_response() -> Dict[str, Any]:
    """
    Loads mock Google Sheets budget response data.
    
    Returns:
        Dict[str, Any]: Mock Google Sheets budget response data
    """
    file_path = os.path.join(GOOGLE_SHEETS_DIR, 'budget_data.json')
    return load_json_fixture(file_path)


def load_google_sheets_transactions_response() -> Dict[str, Any]:
    """
    Loads mock Google Sheets transactions response data.
    
    Returns:
        Dict[str, Any]: Mock Google Sheets transactions response data
    """
    file_path = os.path.join(GOOGLE_SHEETS_DIR, 'transaction_data.json')
    return load_json_fixture(file_path)


def load_google_sheets_error_response() -> Dict[str, Any]:
    """
    Loads mock Google Sheets error response data.
    
    Returns:
        Dict[str, Any]: Mock Google Sheets error response data
    """
    file_path = os.path.join(GOOGLE_SHEETS_DIR, 'error_responses.json')
    return load_json_fixture(file_path)


def load_gemini_categorization_response() -> Dict[str, Any]:
    """
    Loads mock Gemini AI categorization response data.
    
    Returns:
        Dict[str, Any]: Mock Gemini categorization response data
    """
    file_path = os.path.join(GEMINI_DIR, 'categorization.json')
    return load_json_fixture(file_path)


def load_gemini_insights_response() -> Dict[str, Any]:
    """
    Loads mock Gemini AI insights response data.
    
    Returns:
        Dict[str, Any]: Mock Gemini insights response data
    """
    file_path = os.path.join(GEMINI_DIR, 'insights.json')
    return load_json_fixture(file_path)


def load_gemini_error_response() -> Dict[str, Any]:
    """
    Loads mock Gemini AI error response data.
    
    Returns:
        Dict[str, Any]: Mock Gemini error response data
    """
    file_path = os.path.join(GEMINI_DIR, 'error_responses.json')
    return load_json_fixture(file_path)


def load_gmail_confirmation_response() -> Dict[str, Any]:
    """
    Loads mock Gmail confirmation response data.
    
    Returns:
        Dict[str, Any]: Mock Gmail confirmation response data
    """
    file_path = os.path.join(GMAIL_DIR, 'email_confirmation.json')
    return load_json_fixture(file_path)


def load_gmail_error_response() -> Dict[str, Any]:
    """
    Loads mock Gmail error response data.
    
    Returns:
        Dict[str, Any]: Mock Gmail error response data
    """
    file_path = os.path.join(GMAIL_DIR, 'error_responses.json')
    return load_json_fixture(file_path)


# Pre-loaded responses for common use cases
CAPITAL_ONE_TRANSACTIONS_RESPONSE = load_capital_one_transactions_response()
CAPITAL_ONE_ACCOUNTS_RESPONSE = load_capital_one_accounts_response()
CAPITAL_ONE_TRANSFER_RESPONSE = load_capital_one_transfer_response()
GOOGLE_SHEETS_BUDGET_RESPONSE = load_google_sheets_budget_response()
GOOGLE_SHEETS_TRANSACTIONS_RESPONSE = load_google_sheets_transactions_response()
GEMINI_CATEGORIZATION_RESPONSE = load_gemini_categorization_response()
GEMINI_INSIGHTS_RESPONSE = load_gemini_insights_response()
GMAIL_CONFIRMATION_RESPONSE = load_gmail_confirmation_response()