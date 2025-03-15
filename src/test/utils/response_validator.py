"""
response_validator.py - Utility module for validating API responses in the Budget Management Application test suite.

This module provides functions to validate response structures, content, and error conditions 
for all external API integrations (Capital One, Google Sheets, Gemini, Gmail).
Includes schema validation, content verification, and error pattern matching.
"""

import json  # standard library
import logging  # standard library
import re  # standard library
from typing import Dict, List, Any, Optional, Union, Callable  # standard library

import jsonschema  # jsonschema 4.17.0+

from .fixture_loader import load_fixture, load_api_response_fixture
from .assertion_helpers import assert_dict_subset

# Set up logger
logger = logging.getLogger(__name__)

# JSON schemas for validating API responses
API_SCHEMAS = {
    "capital_one": {
        "transactions": {
            "type": "object",
            "required": ["transactions"],
            "properties": {"transactions": {"type": "array"}}
        },
        "account": {
            "type": "object",
            "required": ["account_id", "balance"],
            "properties": {
                "account_id": {"type": "string"},
                "balance": {"type": "number"}
            }
        }
    },
    "google_sheets": {
        "values": {
            "type": "object",
            "required": ["values"],
            "properties": {"values": {"type": "array"}}
        }
    },
    "gemini": {
        "completion": {
            "type": "object",
            "required": ["candidates"],
            "properties": {"candidates": {"type": "array"}}
        }
    },
    "gmail": {
        "send": {
            "type": "object",
            "required": ["id"],
            "properties": {"id": {"type": "string"}}
        }
    }
}

# Error patterns for validating API error responses
ERROR_PATTERNS = {
    "capital_one": {
        "authentication": ["unauthorized", "invalid_token"],
        "rate_limit": ["rate limit", "too many requests"],
        "not_found": ["not found", "no record"]
    },
    "google_sheets": {
        "authentication": ["unauthorized", "invalid credentials"],
        "permission": ["permission denied", "insufficient permissions"],
        "not_found": ["not found", "no such sheet"]
    },
    "gemini": {
        "authentication": ["invalid api key", "unauthorized"],
        "rate_limit": ["quota exceeded", "rate limit"],
        "content_policy": ["content policy violation", "unsafe content"]
    },
    "gmail": {
        "authentication": ["unauthorized", "invalid credentials"],
        "permission": ["permission denied", "insufficient permissions"],
        "rate_limit": ["quota exceeded", "rate limit"]
    }
}

def validate_response_schema(response: Dict[str, Any], api_name: str, response_type: str) -> bool:
    """
    Validate an API response against its JSON schema.
    
    Args:
        response: API response to validate
        api_name: Name of the API (e.g., 'capital_one', 'gemini')
        response_type: Type of response (e.g., 'transactions', 'completion')
        
    Returns:
        True if validation passes, False otherwise
    """
    try:
        # Get the appropriate schema
        schema = API_SCHEMAS.get(api_name, {}).get(response_type)
        
        if not schema:
            logger.warning(f"No schema defined for {api_name}/{response_type}")
            return True  # Skip validation if no schema
        
        # Validate against schema
        jsonschema.validate(response, schema)
        logger.debug(f"Schema validation passed for {api_name}/{response_type}")
        return True
    except jsonschema.ValidationError as e:
        logger.error(f"Schema validation failed for {api_name}/{response_type}: {e}")
        return False

def validate_response_content(response: Dict[str, Any], expected_content: Dict[str, Any]) -> bool:
    """
    Validate that an API response contains expected content.
    
    Args:
        response: API response to validate
        expected_content: Expected content to check for
        
    Returns:
        True if validation passes, False otherwise
    """
    try:
        assert_dict_subset(response, expected_content)
        logger.debug("Content validation passed")
        return True
    except AssertionError as e:
        logger.error(f"Content validation failed: {e}")
        return False

def validate_error_response(response: Dict[str, Any], api_name: str, expected_error_type: str) -> bool:
    """
    Validate that an error response contains expected error information.
    
    Args:
        response: API error response to validate
        api_name: Name of the API (e.g., 'capital_one', 'gemini')
        expected_error_type: Type of error expected (e.g., 'authentication', 'rate_limit')
        
    Returns:
        True if validation passes, False otherwise
    """
    # Get error patterns for this API and error type
    error_patterns = ERROR_PATTERNS.get(api_name, {}).get(expected_error_type, [])
    
    if not error_patterns:
        logger.warning(f"No error patterns defined for {api_name}/{expected_error_type}")
        return False
    
    # Extract error message from response (format varies by API)
    error_message = extract_error_message(response, api_name)
    
    # Check if any pattern matches
    for pattern in error_patterns:
        if pattern.lower() in error_message.lower():
            logger.debug(f"Error response matches {expected_error_type} pattern")
            return True
    
    logger.warning(f"Error response does not match {expected_error_type} patterns. Message: {error_message}")
    return False

def validate_response_against_fixture(response: Dict[str, Any], fixture_path: str) -> bool:
    """
    Validate an API response against a fixture file.
    
    Args:
        response: API response to validate
        fixture_path: Path to the fixture file
        
    Returns:
        True if validation passes, False otherwise
    """
    try:
        expected_data = load_fixture(fixture_path)
        validation_result = validate_response_content(response, expected_data)
        logger.debug(f"Fixture validation {'passed' if validation_result else 'failed'} for {fixture_path}")
        return validation_result
    except Exception as e:
        logger.error(f"Fixture validation error: {e}")
        return False

def extract_error_message(response: Dict[str, Any], api_name: str) -> str:
    """
    Extract error message from an API error response.
    
    Args:
        response: API error response
        api_name: Name of the API (e.g., 'capital_one', 'gemini')
        
    Returns:
        Extracted error message or empty string if not found
    """
    error_message = ""
    
    try:
        if api_name == "capital_one":
            error_message = response.get("error", {}).get("message", "")
        elif api_name == "google_sheets":
            error_message = response.get("error", {}).get("message", "")
        elif api_name == "gemini":
            error_message = response.get("error", {}).get("message", "")
        elif api_name == "gmail":
            error_message = response.get("error", {}).get("message", "")
        else:
            # Generic fallback
            error_message = str(response.get("error", response.get("message", "")))
    
        logger.debug(f"Extracted error message: {error_message}")
        return error_message
    except Exception as e:
        logger.warning(f"Error extracting error message: {e}")
        return ""

def check_response_success(response: Dict[str, Any], api_name: str) -> bool:
    """
    Check if an API response indicates success.
    
    Args:
        response: API response to check
        api_name: Name of the API (e.g., 'capital_one', 'gemini')
        
    Returns:
        True if response indicates success, False otherwise
    """
    try:
        if api_name == "capital_one":
            success = "error" not in response
        elif api_name == "google_sheets":
            success = "error" not in response
        elif api_name == "gemini":
            success = "error" not in response and "candidates" in response
        elif api_name == "gmail":
            success = "error" not in response and "id" in response
        else:
            # Generic fallback
            success = "error" not in response
        
        logger.debug(f"Response success check: {success}")
        return success
    except Exception as e:
        logger.warning(f"Error checking response success: {e}")
        return False

def get_response_data(response: Dict[str, Any], api_name: str, data_key: str) -> Any:
    """
    Extract relevant data from an API response.
    
    Args:
        response: API response
        api_name: Name of the API (e.g., 'capital_one', 'gemini')
        data_key: Key for the data to extract
        
    Returns:
        Extracted data or None if not found
    """
    # First check if response indicates success
    if not check_response_success(response, api_name):
        logger.warning(f"Cannot extract data from error response")
        return None
    
    try:
        data = response.get(data_key)
        logger.debug(f"Extracted data for key '{data_key}'")
        return data
    except Exception as e:
        logger.warning(f"Error extracting data for key '{data_key}': {e}")
        return None

class ResponseValidator:
    """
    Class for validating API responses with specific validation rules for each API.
    """
    
    @staticmethod
    def validate_capital_one_response(response: Dict[str, Any], response_type: str, 
                                     expected_content: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate a Capital One API response.
        
        Args:
            response: API response to validate
            response_type: Type of response (e.g., 'transactions', 'account')
            expected_content: Optional expected content to check for
            
        Returns:
            True if validation passes, False otherwise
        """
        # Validate schema
        if not validate_response_schema(response, "capital_one", response_type):
            return False
        
        # Validate content if provided
        if expected_content and not validate_response_content(response, expected_content):
            return False
        
        logger.debug(f"Capital One {response_type} response validation passed")
        return True
    
    @staticmethod
    def validate_google_sheets_response(response: Dict[str, Any], response_type: str,
                                       expected_content: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate a Google Sheets API response.
        
        Args:
            response: API response to validate
            response_type: Type of response (e.g., 'values')
            expected_content: Optional expected content to check for
            
        Returns:
            True if validation passes, False otherwise
        """
        # Validate schema
        if not validate_response_schema(response, "google_sheets", response_type):
            return False
        
        # Validate content if provided
        if expected_content and not validate_response_content(response, expected_content):
            return False
        
        logger.debug(f"Google Sheets {response_type} response validation passed")
        return True
    
    @staticmethod
    def validate_gemini_response(response: Dict[str, Any], response_type: str,
                               expected_content: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate a Gemini API response.
        
        Args:
            response: API response to validate
            response_type: Type of response (e.g., 'completion')
            expected_content: Optional expected content to check for
            
        Returns:
            True if validation passes, False otherwise
        """
        # Validate schema
        if not validate_response_schema(response, "gemini", response_type):
            return False
        
        # Validate content if provided
        if expected_content and not validate_response_content(response, expected_content):
            return False
        
        logger.debug(f"Gemini {response_type} response validation passed")
        return True
    
    @staticmethod
    def validate_gmail_response(response: Dict[str, Any], response_type: str,
                              expected_content: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate a Gmail API response.
        
        Args:
            response: API response to validate
            response_type: Type of response (e.g., 'send')
            expected_content: Optional expected content to check for
            
        Returns:
            True if validation passes, False otherwise
        """
        # Validate schema
        if not validate_response_schema(response, "gmail", response_type):
            return False
        
        # Validate content if provided
        if expected_content and not validate_response_content(response, expected_content):
            return False
        
        logger.debug(f"Gmail {response_type} response validation passed")
        return True
    
    @staticmethod
    def validate_error_response(response: Dict[str, Any], api_name: str, expected_error_type: str) -> bool:
        """
        Validate an error response from any API.
        
        Args:
            response: API error response to validate
            api_name: Name of the API (e.g., 'capital_one', 'gemini')
            expected_error_type: Type of error expected (e.g., 'authentication', 'rate_limit')
            
        Returns:
            True if validation passes, False otherwise
        """
        return validate_error_response(response, api_name, expected_error_type)
    
    @staticmethod
    def validate_response(response: Dict[str, Any], api_name: str, response_type: str,
                         expected_content: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate any API response based on API name.
        
        Args:
            response: API response to validate
            api_name: Name of the API (e.g., 'capital_one', 'gemini')
            response_type: Type of response (e.g., 'transactions', 'completion')
            expected_content: Optional expected content to check for
            
        Returns:
            True if validation passes, False otherwise
        """
        if api_name == "capital_one":
            return ResponseValidator.validate_capital_one_response(response, response_type, expected_content)
        elif api_name == "google_sheets":
            return ResponseValidator.validate_google_sheets_response(response, response_type, expected_content)
        elif api_name == "gemini":
            return ResponseValidator.validate_gemini_response(response, response_type, expected_content)
        elif api_name == "gmail":
            return ResponseValidator.validate_gmail_response(response, response_type, expected_content)
        else:
            logger.warning(f"Unknown API: {api_name}")
            return False