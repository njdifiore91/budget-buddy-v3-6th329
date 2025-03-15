"""
Utility module for testing API integrations with external services used by the Budget Management Application.
Provides functions to test connectivity, validate responses, and perform basic operations with
Capital One, Google Sheets, Gemini AI, and Gmail APIs.
"""

import os  # standard library
import json  # standard library
import time  # standard library
import requests  # requests 2.31.0+
from typing import Dict, List, Optional, Union, Any  # standard library

from ..config.script_settings import (
    API_TEST_SETTINGS, SCRIPT_SETTINGS,
    get_credential_path
)
from ..config.logging_setup import get_logger, LoggingContext
from ../../backend.services.authentication_service import AuthenticationService
from ../../backend.api_clients.capital_one_client import CapitalOneClient
from ../../backend.api_clients.google_sheets_client import GoogleSheetsClient
from ../../backend.api_clients.gemini_client import GeminiClient
from ../../backend.api_clients.gmail_client import GmailClient

# Set up logger
logger = get_logger('api_testing')


def load_mock_response(api_name: str, operation: str) -> Dict[str, Any]:
    """
    Loads a mock API response from a JSON file
    
    Args:
        api_name: Name of the API (capital_one, google_sheets, gemini, gmail)
        operation: Name of the operation being tested
        
    Returns:
        Mock response data or empty dict if file not found
    """
    try:
        # Construct mock response file path
        file_path = os.path.join(
            API_TEST_SETTINGS['MOCK_RESPONSE_DIR'],
            api_name,
            f"{operation}.json"
        )
        
        # Check if file exists
        if not os.path.exists(file_path):
            logger.warning(f"Mock response file not found: {file_path}")
            return {}
        
        # Load and return the JSON data
        with open(file_path, 'r') as f:
            return json.load(f)
            
    except Exception as e:
        logger.error(f"Error loading mock response: {str(e)}")
        return {}


def test_capital_one_api(auth_service: Optional[AuthenticationService] = None) -> Dict[str, Any]:
    """
    Tests connectivity and basic operations with Capital One API
    
    Args:
        auth_service: Optional authentication service to use
        
    Returns:
        Test results with status and details
    """
    # Create auth service if not provided
    if auth_service is None:
        auth_service = AuthenticationService()
    
    # Initialize results
    results = {
        'status': 'pending',
        'details': {}
    }
    
    with LoggingContext(logger, 'test_capital_one_api'):
        try:
            # Check if using mock responses
            if API_TEST_SETTINGS['USE_MOCK_RESPONSES']:
                mock_response = load_mock_response('capital_one', 'test')
                if mock_response:
                    logger.info("Using mock response for Capital One API test")
                    return mock_response
            
            # Create Capital One client
            client = CapitalOneClient(auth_service)
            
            # Test authentication
            auth_result = auth_service.authenticate_capital_one()
            results['details']['authentication'] = {
                'status': 'success' if auth_result else 'failed'
            }
            
            # If authentication successful, test transaction retrieval
            if auth_result:
                # Use test account from settings
                account_id = API_TEST_SETTINGS['CAPITAL_ONE_TEST_ACCOUNT']
                if not account_id:
                    results['details']['transactions'] = {
                        'status': 'skipped',
                        'message': 'No test account ID provided'
                    }
                else:
                    # Get transactions for last 7 days
                    end_date = time.strftime('%Y-%m-%d')
                    start_date = time.strftime('%Y-%m-%d', time.localtime(time.time() - 7*24*60*60))
                    
                    transactions = client.get_transactions(account_id, start_date, end_date)
                    results['details']['transactions'] = {
                        'status': 'success' if transactions else 'failed',
                        'count': len(transactions) if transactions else 0
                    }
                    
                    # Test account details retrieval
                    account_details = client.get_account_details(account_id)
                    results['details']['account_details'] = {
                        'status': 'success' if account_details else 'failed'
                    }
            
            # Determine overall status
            results['status'] = 'success'
            for operation, operation_results in results['details'].items():
                if operation_results.get('status') == 'failed':
                    results['status'] = 'failed'
                    break
                    
        except Exception as e:
            logger.error(f"Capital One API test failed: {str(e)}")
            results['status'] = 'failed'
            results['error'] = str(e)
        
        logger.info(f"Capital One API test completed with status: {results['status']}")
        return results


def test_google_sheets_api(auth_service: Optional[AuthenticationService] = None) -> Dict[str, Any]:
    """
    Tests connectivity and basic operations with Google Sheets API
    
    Args:
        auth_service: Optional authentication service to use
        
    Returns:
        Test results with status and details
    """
    # Create auth service if not provided
    if auth_service is None:
        auth_service = AuthenticationService()
    
    # Initialize results
    results = {
        'status': 'pending',
        'details': {}
    }
    
    with LoggingContext(logger, 'test_google_sheets_api'):
        try:
            # Check if using mock responses
            if API_TEST_SETTINGS['USE_MOCK_RESPONSES']:
                mock_response = load_mock_response('google_sheets', 'test')
                if mock_response:
                    logger.info("Using mock response for Google Sheets API test")
                    return mock_response
            
            # Create Google Sheets client
            client = GoogleSheetsClient(auth_service)
            
            # Test authentication
            auth_result = auth_service.authenticate_google_sheets()
            results['details']['authentication'] = {
                'status': 'success' if auth_result else 'failed'
            }
            
            # If authentication successful, test reading from a spreadsheet
            if auth_result:
                # Use test spreadsheet from settings
                spreadsheet_id = API_TEST_SETTINGS['SHEETS_TEST_SPREADSHEET_ID']
                sheet_range = API_TEST_SETTINGS['SHEETS_TEST_RANGE']
                
                if not spreadsheet_id:
                    results['details']['read_sheet'] = {
                        'status': 'skipped',
                        'message': 'No test spreadsheet ID provided'
                    }
                else:
                    # Read test spreadsheet
                    data = client.read_sheet(spreadsheet_id, sheet_range)
                    results['details']['read_sheet'] = {
                        'status': 'success' if data is not None else 'failed',
                        'rows': len(data) if data else 0
                    }
            
            # Determine overall status
            results['status'] = 'success'
            for operation, operation_results in results['details'].items():
                if operation_results.get('status') == 'failed':
                    results['status'] = 'failed'
                    break
                    
        except Exception as e:
            logger.error(f"Google Sheets API test failed: {str(e)}")
            results['status'] = 'failed'
            results['error'] = str(e)
        
        logger.info(f"Google Sheets API test completed with status: {results['status']}")
        return results


def test_gemini_api(auth_service: Optional[AuthenticationService] = None) -> Dict[str, Any]:
    """
    Tests connectivity and basic operations with Gemini AI API
    
    Args:
        auth_service: Optional authentication service to use
        
    Returns:
        Test results with status and details
    """
    # Create auth service if not provided
    if auth_service is None:
        auth_service = AuthenticationService()
    
    # Initialize results
    results = {
        'status': 'pending',
        'details': {}
    }
    
    with LoggingContext(logger, 'test_gemini_api'):
        try:
            # Check if using mock responses
            if API_TEST_SETTINGS['USE_MOCK_RESPONSES']:
                mock_response = load_mock_response('gemini', 'test')
                if mock_response:
                    logger.info("Using mock response for Gemini API test")
                    return mock_response
            
            # Create Gemini client
            client = GeminiClient(auth_service)
            
            # Test authentication
            auth_result = auth_service.authenticate_gemini()
            results['details']['authentication'] = {
                'status': 'success' if auth_result else 'failed'
            }
            
            # If authentication successful, test generating a completion
            if auth_result:
                # Use test prompt from settings
                prompt = API_TEST_SETTINGS['GEMINI_TEST_PROMPT']
                
                # Generate completion
                completion = client.generate_completion(prompt)
                results['details']['generate_completion'] = {
                    'status': 'success' if completion else 'failed',
                    'prompt_length': len(prompt),
                    'response_length': len(completion) if completion else 0
                }
            
            # Determine overall status
            results['status'] = 'success'
            for operation, operation_results in results['details'].items():
                if operation_results.get('status') == 'failed':
                    results['status'] = 'failed'
                    break
                    
        except Exception as e:
            logger.error(f"Gemini API test failed: {str(e)}")
            results['status'] = 'failed'
            results['error'] = str(e)
        
        logger.info(f"Gemini API test completed with status: {results['status']}")
        return results


def test_gmail_api(auth_service: Optional[AuthenticationService] = None) -> Dict[str, Any]:
    """
    Tests connectivity and basic operations with Gmail API
    
    Args:
        auth_service: Optional authentication service to use
        
    Returns:
        Test results with status and details
    """
    # Create auth service if not provided
    if auth_service is None:
        auth_service = AuthenticationService()
    
    # Initialize results
    results = {
        'status': 'pending',
        'details': {}
    }
    
    with LoggingContext(logger, 'test_gmail_api'):
        try:
            # Check if using mock responses
            if API_TEST_SETTINGS['USE_MOCK_RESPONSES']:
                mock_response = load_mock_response('gmail', 'test')
                if mock_response:
                    logger.info("Using mock response for Gmail API test")
                    return mock_response
            
            # Create Gmail client
            client = GmailClient(auth_service)
            
            # Test authentication
            auth_result = auth_service.authenticate_gmail()
            results['details']['authentication'] = {
                'status': 'success' if auth_result else 'failed'
            }
            
            # If authentication successful, test sending an email (if enabled)
            if auth_result:
                # Note: We'll usually skip actual email sending in tests
                # but make it configurable
                send_test_email = os.getenv('SEND_TEST_EMAIL', 'false').lower() == 'true'
                
                if not send_test_email:
                    results['details']['send_email'] = {
                        'status': 'skipped',
                        'message': 'Test email sending disabled'
                    }
                else:
                    # Use test email settings from config
                    recipient = API_TEST_SETTINGS['GMAIL_TEST_RECIPIENT']
                    subject = API_TEST_SETTINGS['GMAIL_TEST_SUBJECT']
                    body = API_TEST_SETTINGS['GMAIL_TEST_BODY']
                    
                    # Send test email
                    email_result = client.send_email(recipient, subject, body)
                    results['details']['send_email'] = {
                        'status': 'success' if email_result else 'failed',
                        'recipient': recipient
                    }
            
            # Determine overall status
            results['status'] = 'success'
            for operation, operation_results in results['details'].items():
                if operation_results.get('status') == 'failed':
                    results['status'] = 'failed'
                    break
                    
        except Exception as e:
            logger.error(f"Gmail API test failed: {str(e)}")
            results['status'] = 'failed'
            results['error'] = str(e)
        
        logger.info(f"Gmail API test completed with status: {results['status']}")
        return results


def test_all_apis() -> Dict[str, Dict[str, Any]]:
    """
    Tests connectivity and basic operations with all APIs
    
    Returns:
        Test results for all APIs
    """
    # Create a single authentication service for all tests
    auth_service = AuthenticationService()
    
    # Initialize results
    results = {}
    
    # Test each API
    results['capital_one'] = test_capital_one_api(auth_service)
    results['google_sheets'] = test_google_sheets_api(auth_service)
    results['gemini'] = test_gemini_api(auth_service)
    results['gmail'] = test_gmail_api(auth_service)
    
    # Calculate overall status
    overall_status = 'success'
    for api, api_results in results.items():
        if api_results.get('status') == 'failed':
            overall_status = 'failed'
            break
    
    logger.info(f"All API tests completed with overall status: {overall_status}")
    return results


def validate_api_response(response: Dict[str, Any], 
                         required_fields: List[str],
                         expected_values: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Validates an API response against expected structure and values
    
    Args:
        response: API response to validate
        required_fields: List of fields that must be present
        expected_values: Dictionary of field-value pairs that must match
        
    Returns:
        Validation results with status and details
    """
    validation_results = {
        'status': 'pending',
        'details': {}
    }
    
    # Check if response is None or empty
    if not response:
        validation_results['status'] = 'failed'
        validation_results['details']['empty_response'] = {
            'status': 'failed',
            'message': 'Response is None or empty'
        }
        return validation_results
    
    # Check required fields
    missing_fields = []
    for field in required_fields:
        if field not in response:
            missing_fields.append(field)
    
    if missing_fields:
        validation_results['details']['required_fields'] = {
            'status': 'failed',
            'missing_fields': missing_fields
        }
    else:
        validation_results['details']['required_fields'] = {
            'status': 'success'
        }
    
    # Check expected values
    if expected_values:
        value_mismatches = []
        for field, expected_value in expected_values.items():
            if field in response:
                actual_value = response[field]
                if actual_value != expected_value:
                    value_mismatches.append({
                        'field': field,
                        'expected': expected_value,
                        'actual': actual_value
                    })
        
        if value_mismatches:
            validation_results['details']['expected_values'] = {
                'status': 'failed',
                'mismatches': value_mismatches
            }
        else:
            validation_results['details']['expected_values'] = {
                'status': 'success'
            }
    
    # Determine overall status
    validation_results['status'] = 'success'
    for check, check_results in validation_results['details'].items():
        if check_results.get('status') == 'failed':
            validation_results['status'] = 'failed'
            break
    
    return validation_results


def format_test_results(results: Dict[str, Any], verbose: bool = False) -> str:
    """
    Formats API test results for display or logging
    
    Args:
        results: Test results to format
        verbose: Whether to include detailed results
        
    Returns:
        Formatted test results string
    """
    output = "API Test Results\n===============\n\n"
    
    # Add overall status if present
    if 'overall_status' in results:
        output += f"Overall Status: {results['overall_status']}\n\n"
        
        # Format individual API results
        for api, api_results in results.get('apis', {}).items():
            output += f"API: {api}\n"
            output += f"Status: {api_results.get('status', 'unknown')}\n"
            
            if verbose and 'details' in api_results:
                output += "Details:\n"
                for operation, operation_results in api_results['details'].items():
                    output += f"  - {operation}: {operation_results.get('status', 'unknown')}\n"
                    
                    # Add additional details if present
                    for key, value in operation_results.items():
                        if key != 'status':
                            output += f"    {key}: {value}\n"
            
            if 'error' in api_results:
                output += f"Error: {api_results['error']}\n"
                
            output += "\n"
    else:
        # Format single API test results or multiple API results without overall status
        for api, api_results in results.items():
            if isinstance(api_results, dict) and 'status' in api_results:
                output += f"API: {api}\n"
                output += f"Status: {api_results.get('status', 'unknown')}\n"
                
                if verbose and 'details' in api_results:
                    output += "Details:\n"
                    for operation, operation_results in api_results['details'].items():
                        output += f"  - {operation}: {operation_results.get('status', 'unknown')}\n"
                        
                        # Add additional details if present
                        for key, value in operation_results.items():
                            if key != 'status':
                                output += f"    {key}: {value}\n"
                
                if 'error' in api_results:
                    output += f"Error: {api_results['error']}\n"
                    
                output += "\n"
    
    return output


def save_test_results(results: Dict[str, Any], filename: str) -> bool:
    """
    Saves API test results to a JSON file
    
    Args:
        results: Test results to save
        filename: Name of the file to save to
        
    Returns:
        True if save was successful, False otherwise
    """
    try:
        # Add timestamp to results
        results_with_timestamp = results.copy()
        results_with_timestamp['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Ensure output directory exists
        output_dir = os.path.dirname(filename)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Write to file
        with open(filename, 'w') as f:
            json.dump(results_with_timestamp, f, indent=2)
        
        logger.info(f"Test results saved to {filename}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving test results: {str(e)}")
        return False


class APITester:
    """
    Class for testing and validating API integrations
    """
    
    def __init__(self, auth_service: Optional[AuthenticationService] = None,
                use_mocks: bool = None):
        """
        Initialize the API tester with authentication service
        
        Args:
            auth_service: Optional authentication service to use
            use_mocks: Whether to use mock responses
        """
        # Create auth service if not provided
        self.auth_service = auth_service or AuthenticationService()
        
        # Initialize empty test results
        self.test_results = {}
        
        # Set mock usage from parameter or settings
        self.use_mocks = use_mocks if use_mocks is not None else API_TEST_SETTINGS['USE_MOCK_RESPONSES']
        
        logger.info("APITester initialized")
    
    def test_api(self, api_name: str) -> Dict[str, Any]:
        """
        Tests a specific API by name
        
        Args:
            api_name: Name of the API to test
            
        Returns:
            Test results for the specified API
        """
        # Validate API name
        valid_apis = ['capital_one', 'google_sheets', 'gemini', 'gmail']
        if api_name not in valid_apis:
            raise ValueError(f"Invalid API name: {api_name}. Must be one of {valid_apis}")
        
        # Call appropriate test function
        if api_name == 'capital_one':
            results = test_capital_one_api(self.auth_service)
        elif api_name == 'google_sheets':
            results = test_google_sheets_api(self.auth_service)
        elif api_name == 'gemini':
            results = test_gemini_api(self.auth_service)
        elif api_name == 'gmail':
            results = test_gmail_api(self.auth_service)
        
        # Store results
        self.test_results[api_name] = results
        
        return results
    
    def test_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Tests all supported APIs
        
        Returns:
            Test results for all APIs
        """
        # Test each API
        apis = ['capital_one', 'google_sheets', 'gemini', 'gmail']
        for api in apis:
            self.test_api(api)
        
        # Calculate overall status
        overall_status = 'success'
        for api, api_results in self.test_results.items():
            if api_results.get('status') == 'failed':
                overall_status = 'failed'
                break
        
        logger.info(f"All API tests completed with overall status: {overall_status}")
        return self.test_results
    
    def get_results(self) -> Dict[str, Any]:
        """
        Gets the current test results
        
        Returns:
            Current test results
        """
        return self.test_results
    
    def format_results(self, verbose: bool = False) -> str:
        """
        Formats the test results for display
        
        Args:
            verbose: Whether to include detailed results
            
        Returns:
            Formatted test results string
        """
        if self.test_results:
            return format_test_results(self.test_results, verbose)
        else:
            return "No test results available."
    
    def save_results(self, filename: str) -> bool:
        """
        Saves the test results to a file
        
        Args:
            filename: Name of the file to save to
            
        Returns:
            True if save was successful
        """
        if self.test_results:
            return save_test_results(self.test_results, filename)
        else:
            logger.warning("No test results to save")
            return False