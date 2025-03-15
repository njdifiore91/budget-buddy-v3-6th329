"""
api_responses.py - Provides test fixture data for API responses to be used in unit and integration tests for the Budget Management Application.

This module contains functions to load and access mock API responses for Capital One, Google Sheets, Gemini AI, and Gmail APIs, enabling consistent and reliable testing without making actual API calls.
"""

import json
import copy
from typing import Dict, List, Any, Optional

from ..utils.fixture_loader import load_fixture, get_fixture_path

# Capital One API mock responses
CAPITAL_ONE_TRANSACTIONS = load_fixture('api_responses/capital_one/transactions')
CAPITAL_ONE_ACCOUNTS = load_fixture('api_responses/capital_one/accounts')
CAPITAL_ONE_TRANSFER = load_fixture('api_responses/capital_one/transfer')
CAPITAL_ONE_ERROR_RESPONSES = load_fixture('api_responses/capital_one/error_responses')

# Google Sheets API mock responses
GOOGLE_SHEETS_BUDGET_DATA = load_fixture('api_responses/google_sheets/budget_data')
GOOGLE_SHEETS_TRANSACTION_DATA = load_fixture('api_responses/google_sheets/transaction_data')
GOOGLE_SHEETS_ERROR_RESPONSES = load_fixture('api_responses/google_sheets/error_responses')

# Gemini AI API mock responses
GEMINI_CATEGORIZATION = load_fixture('api_responses/gemini/categorization')
GEMINI_INSIGHTS = load_fixture('api_responses/gemini/insights')
GEMINI_ERROR_RESPONSES = load_fixture('api_responses/gemini/error_responses')

# Gmail API mock responses
GMAIL_EMAIL_CONFIRMATION = load_fixture('api_responses/gmail/email_confirmation')
GMAIL_ERROR_RESPONSES = load_fixture('api_responses/gmail/error_responses')


def get_capital_one_response(response_type: str) -> Dict[str, Any]:
    """
    Retrieves a Capital One API mock response by type.
    
    Args:
        response_type: Type of response ('transactions', 'accounts', 'transfer', or 'error')
        
    Returns:
        Dict[str, Any]: Mock API response for Capital One
        
    Raises:
        ValueError: If response_type is not recognized
    """
    if not isinstance(response_type, str):
        raise TypeError(f"response_type must be a string, got {type(response_type)}")
    
    valid_types = ['transactions', 'accounts', 'transfer', 'error']
    response_type = response_type.lower()
    
    if response_type == 'transactions':
        return copy.deepcopy(CAPITAL_ONE_TRANSACTIONS)
    elif response_type == 'accounts':
        return copy.deepcopy(CAPITAL_ONE_ACCOUNTS)
    elif response_type == 'transfer':
        return copy.deepcopy(CAPITAL_ONE_TRANSFER)
    elif response_type == 'error':
        # Default to first error response
        if isinstance(CAPITAL_ONE_ERROR_RESPONSES, list) and CAPITAL_ONE_ERROR_RESPONSES:
            return copy.deepcopy(CAPITAL_ONE_ERROR_RESPONSES[0])
        return copy.deepcopy(CAPITAL_ONE_ERROR_RESPONSES)
    else:
        raise ValueError(
            f"Unknown Capital One response type: '{response_type}'. "
            f"Valid types are: {', '.join(f"'{t}'" for t in valid_types)}"
        )


def get_google_sheets_response(response_type: str) -> Dict[str, Any]:
    """
    Retrieves a Google Sheets API mock response by type.
    
    Args:
        response_type: Type of response ('budget', 'transactions', or 'error')
        
    Returns:
        Dict[str, Any]: Mock API response for Google Sheets
        
    Raises:
        ValueError: If response_type is not recognized
    """
    if not isinstance(response_type, str):
        raise TypeError(f"response_type must be a string, got {type(response_type)}")
    
    valid_types = ['budget', 'transactions', 'error']
    response_type = response_type.lower()
    
    if response_type == 'budget':
        return copy.deepcopy(GOOGLE_SHEETS_BUDGET_DATA)
    elif response_type == 'transactions':
        return copy.deepcopy(GOOGLE_SHEETS_TRANSACTION_DATA)
    elif response_type == 'error':
        # Default to first error response
        if isinstance(GOOGLE_SHEETS_ERROR_RESPONSES, list) and GOOGLE_SHEETS_ERROR_RESPONSES:
            return copy.deepcopy(GOOGLE_SHEETS_ERROR_RESPONSES[0])
        return copy.deepcopy(GOOGLE_SHEETS_ERROR_RESPONSES)
    else:
        raise ValueError(
            f"Unknown Google Sheets response type: '{response_type}'. "
            f"Valid types are: {', '.join(f"'{t}'" for t in valid_types)}"
        )


def get_gemini_response(response_type: str) -> Dict[str, Any]:
    """
    Retrieves a Gemini AI API mock response by type.
    
    Args:
        response_type: Type of response ('categorization', 'insights', or 'error')
        
    Returns:
        Dict[str, Any]: Mock API response for Gemini AI
        
    Raises:
        ValueError: If response_type is not recognized
    """
    if not isinstance(response_type, str):
        raise TypeError(f"response_type must be a string, got {type(response_type)}")
    
    valid_types = ['categorization', 'insights', 'error']
    response_type = response_type.lower()
    
    if response_type == 'categorization':
        return copy.deepcopy(GEMINI_CATEGORIZATION)
    elif response_type == 'insights':
        return copy.deepcopy(GEMINI_INSIGHTS)
    elif response_type == 'error':
        # Default to first error response
        if isinstance(GEMINI_ERROR_RESPONSES, list) and GEMINI_ERROR_RESPONSES:
            return copy.deepcopy(GEMINI_ERROR_RESPONSES[0])
        return copy.deepcopy(GEMINI_ERROR_RESPONSES)
    else:
        raise ValueError(
            f"Unknown Gemini AI response type: '{response_type}'. "
            f"Valid types are: {', '.join(f"'{t}'" for t in valid_types)}"
        )


def get_gmail_response(response_type: str) -> Dict[str, Any]:
    """
    Retrieves a Gmail API mock response by type.
    
    Args:
        response_type: Type of response ('confirmation' or 'error')
        
    Returns:
        Dict[str, Any]: Mock API response for Gmail
        
    Raises:
        ValueError: If response_type is not recognized
    """
    if not isinstance(response_type, str):
        raise TypeError(f"response_type must be a string, got {type(response_type)}")
    
    valid_types = ['confirmation', 'error']
    response_type = response_type.lower()
    
    if response_type == 'confirmation':
        return copy.deepcopy(GMAIL_EMAIL_CONFIRMATION)
    elif response_type == 'error':
        # Default to first error response
        if isinstance(GMAIL_ERROR_RESPONSES, list) and GMAIL_ERROR_RESPONSES:
            return copy.deepcopy(GMAIL_ERROR_RESPONSES[0])
        return copy.deepcopy(GMAIL_ERROR_RESPONSES)
    else:
        raise ValueError(
            f"Unknown Gmail response type: '{response_type}'. "
            f"Valid types are: {', '.join(f"'{t}'" for t in valid_types)}"
        )


def get_api_response(api_name: str, response_type: str) -> Dict[str, Any]:
    """
    Retrieves a mock API response for any supported API.
    
    Args:
        api_name: Name of the API ('capital_one', 'google_sheets', 'gemini', or 'gmail')
        response_type: Type of response specific to the API
        
    Returns:
        Dict[str, Any]: Mock API response
        
    Raises:
        ValueError: If api_name is not recognized
    """
    if not isinstance(api_name, str):
        raise TypeError(f"api_name must be a string, got {type(api_name)}")
    
    valid_apis = ['capital_one', 'google_sheets', 'gemini', 'gmail']
    api_name = api_name.lower()
    
    if api_name == 'capital_one':
        return get_capital_one_response(response_type)
    elif api_name == 'google_sheets':
        return get_google_sheets_response(response_type)
    elif api_name == 'gemini':
        return get_gemini_response(response_type)
    elif api_name == 'gmail':
        return get_gmail_response(response_type)
    else:
        raise ValueError(
            f"Unknown API name: '{api_name}'. "
            f"Valid APIs are: {', '.join(f"'{api}'" for api in valid_apis)}"
        )


def get_error_response(api_name: str, error_type: str) -> Dict[str, Any]:
    """
    Retrieves an error response for a specific API and error type.
    
    Args:
        api_name: Name of the API ('capital_one', 'google_sheets', 'gemini', or 'gmail')
        error_type: Type of error (e.g., 'authentication', 'rate_limit', 'server_error')
        
    Returns:
        Dict[str, Any]: Mock API error response
        
    Raises:
        ValueError: If api_name is not recognized or error_type is not found
    """
    if not isinstance(api_name, str) or not isinstance(error_type, str):
        raise TypeError("api_name and error_type must be strings")
    
    # Dictionary mapping APIs to their error response globals
    error_responses = {
        'capital_one': CAPITAL_ONE_ERROR_RESPONSES,
        'google_sheets': GOOGLE_SHEETS_ERROR_RESPONSES,
        'gemini': GEMINI_ERROR_RESPONSES,
        'gmail': GMAIL_ERROR_RESPONSES
    }
    
    api_name = api_name.lower()
    error_type = error_type.lower()
    
    if api_name not in error_responses:
        valid_apis = list(error_responses.keys())
        raise ValueError(
            f"Unknown API name: '{api_name}'. "
            f"Valid APIs are: {', '.join(f"'{api}'" for api in valid_apis)}"
        )
    
    # Get the error responses for the specified API
    api_errors = error_responses[api_name]
    
    # Check if error responses is a list or a single dictionary
    if isinstance(api_errors, list):
        # Search for the specific error type
        for error in api_errors:
            if error.get('error_type', '').lower() == error_type:
                return copy.deepcopy(error)
        
        # If error type not found, return a generic error
        return {
            'error_type': 'generic_error',
            'error_message': f"Error occurred in {api_name}",
            'status_code': 500
        }
    else:
        # If it's a dictionary, just return it
        return copy.deepcopy(api_errors)


def create_custom_response(api_name: str, base_response_type: str, modifications: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a custom API response by modifying a base response.
    
    Args:
        api_name: Name of the API ('capital_one', 'google_sheets', 'gemini', or 'gmail')
        base_response_type: Type of base response to modify
        modifications: Dictionary of modifications to apply
        
    Returns:
        Dict[str, Any]: Customized API response
        
    Raises:
        ValueError: If api_name or base_response_type is not recognized
        TypeError: If modifications is not a dictionary
    """
    if not isinstance(modifications, dict):
        raise TypeError(f"modifications must be a dictionary, got {type(modifications)}")
    
    # Get the base response
    base_response = get_api_response(api_name, base_response_type)
    
    # Create a deep copy of the base response to avoid modifying the original
    custom_response = copy.deepcopy(base_response)
    
    # Apply modifications
    for path, value in modifications.items():
        # Handle nested paths using dot notation (e.g., 'data.items.0.name')
        parts = path.split('.')
        current = custom_response
        
        # Navigate to the nested location
        for i, part in enumerate(parts[:-1]):
            try:
                # Handle array indices
                if part.isdigit():
                    part = int(part)
                
                # If this is a new key, initialize it
                if isinstance(current, dict) and part not in current:
                    # Initialize as dict or list based on next part
                    next_part = parts[i + 1]
                    if next_part.isdigit():
                        current[part] = []
                    else:
                        current[part] = {}
                
                current = current[part]
            except (KeyError, TypeError, IndexError):
                # If path doesn't exist, create it
                if isinstance(current, list):
                    # Extend list if needed
                    while len(current) <= int(part):
                        current.append({})
                    current = current[int(part)]
                else:
                    current[part] = {}
                    current = current[part]
        
        # Set the value at the final location
        final_part = parts[-1]
        if final_part.isdigit() and isinstance(current, list):
            final_part = int(final_part)
            # Extend list if needed
            while len(current) <= final_part:
                current.append(None)
        
        current[final_part] = value
    
    return custom_response


class MockAPIResponseFactory:
    """
    Factory class for creating and managing mock API responses.
    
    This class provides methods to get mock API responses for testing, with optional
    caching to improve test performance.
    """
    
    def __init__(self, use_cache: bool = True):
        """
        Initialize the MockAPIResponseFactory with optional caching.
        
        Args:
            use_cache: Whether to cache API responses (default: True)
        """
        self._cache = {} if use_cache else None
    
    def get_response(self, api_name: str, response_type: str) -> Dict[str, Any]:
        """
        Get a mock API response with optional caching.
        
        Args:
            api_name: Name of the API
            response_type: Type of response
            
        Returns:
            Dict[str, Any]: Mock API response
        """
        # Create cache key
        cache_key = f"{api_name}:{response_type}"
        
        # Check cache if enabled
        if self._cache is not None and cache_key in self._cache:
            # Return a deep copy to prevent modification of cached response
            return copy.deepcopy(self._cache[cache_key])
        
        # Get the response
        response = get_api_response(api_name, response_type)
        
        # Cache the response if caching is enabled
        if self._cache is not None:
            # Store a deep copy to prevent cache modification
            self._cache[cache_key] = copy.deepcopy(response)
        
        return response
    
    def get_capital_one_response(self, response_type: str) -> Dict[str, Any]:
        """
        Get a Capital One API mock response.
        
        Args:
            response_type: Type of response
            
        Returns:
            Dict[str, Any]: Capital One API mock response
        """
        return self.get_response('capital_one', response_type)
    
    def get_google_sheets_response(self, response_type: str) -> Dict[str, Any]:
        """
        Get a Google Sheets API mock response.
        
        Args:
            response_type: Type of response
            
        Returns:
            Dict[str, Any]: Google Sheets API mock response
        """
        return self.get_response('google_sheets', response_type)
    
    def get_gemini_response(self, response_type: str) -> Dict[str, Any]:
        """
        Get a Gemini AI API mock response.
        
        Args:
            response_type: Type of response
            
        Returns:
            Dict[str, Any]: Gemini AI API mock response
        """
        return self.get_response('gemini', response_type)
    
    def get_gmail_response(self, response_type: str) -> Dict[str, Any]:
        """
        Get a Gmail API mock response.
        
        Args:
            response_type: Type of response
            
        Returns:
            Dict[str, Any]: Gmail API mock response
        """
        return self.get_response('gmail', response_type)
    
    def create_custom_response(self, api_name: str, base_response_type: str, modifications: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a custom API response with modifications.
        
        Args:
            api_name: Name of the API
            base_response_type: Type of base response to modify
            modifications: Dictionary of modifications to apply
            
        Returns:
            Dict[str, Any]: Customized API response
        """
        return create_custom_response(api_name, base_response_type, modifications)
    
    def clear_cache(self) -> None:
        """
        Clear the response cache.
        """
        if self._cache is not None:
            self._cache.clear()