#!/usr/bin/env python3
"""
Script for verifying API access to all external services used by the Budget Management Application.
Provides functions to test connectivity, authentication, and basic operations with
Capital One, Google Sheets, Gemini AI, and Gmail APIs.
"""

import os
import sys
import argparse
import json
import time
from typing import Dict, List, Optional, Union, Any

# Internal imports
from ..config.logging_setup import get_logger, LoggingContext
from ..config.script_settings import SCRIPT_SETTINGS, API_TEST_SETTINGS
from ..utils.api_testing import (
    test_capital_one_api,
    test_google_sheets_api,
    test_gemini_api,
    test_gmail_api,
    format_test_results
)
from ...backend.services.authentication_service import AuthenticationService

# Set up logger
logger = get_logger('verify_api_access')


def parse_arguments():
    """
    Parse command-line arguments for the API verification script
    
    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Verify API access for the Budget Management Application"
    )
    
    parser.add_argument(
        "--service", "-s",
        choices=["capital_one", "google_sheets", "gemini", "gmail"],
        help="Verify only the specified service (default: all)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Display detailed test results"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Save test results to the specified file"
    )
    
    parser.add_argument(
        "--mock", "-m",
        action="store_true",
        help="Use mock responses instead of real API calls"
    )
    
    return parser.parse_args()


def verify_capital_one_access(verbose: bool = False, use_mocks: bool = False) -> Dict[str, Any]:
    """
    Verify access to Capital One API
    
    Args:
        verbose: Whether to display detailed output
        use_mocks: Whether to use mock responses
    
    Returns:
        Dict[str, Any]: Verification results with status and details
    """
    logger.info("Starting Capital One API verification")
    
    with LoggingContext(logger, "verify_capital_one_access"):
        # Override API_TEST_SETTINGS if specified
        old_mock_setting = API_TEST_SETTINGS['USE_MOCK_RESPONSES']
        if use_mocks:
            API_TEST_SETTINGS['USE_MOCK_RESPONSES'] = True
            
        try:
            # Create authentication service
            auth_service = AuthenticationService()
            
            # Call the test function from api_testing
            result = test_capital_one_api(auth_service)
            
            # Log the result
            if result['status'] == 'success':
                logger.info("Capital One API verification succeeded")
            else:
                logger.error("Capital One API verification failed", 
                            context={'error': result.get('error', 'Unknown error')})
            
            # Print detailed results if verbose mode is enabled
            if verbose:
                print("Capital One API Verification:")
                print(f"Status: {result['status']}")
                if 'details' in result:
                    print("Details:")
                    for operation, operation_result in result['details'].items():
                        print(f"  - {operation}: {operation_result.get('status', 'unknown')}")
                        
                        # Add additional details if present
                        for key, value in operation_result.items():
                            if key != 'status':
                                print(f"    {key}: {value}")
                if 'error' in result:
                    print(f"Error: {result['error']}")
                print()
            
            return result
        except Exception as e:
            logger.error(f"Error during Capital One API verification: {str(e)}")
            error_result = {
                'status': 'failed',
                'error': str(e)
            }
            return error_result
        finally:
            # Restore original mock setting
            API_TEST_SETTINGS['USE_MOCK_RESPONSES'] = old_mock_setting


def verify_google_sheets_access(verbose: bool = False, use_mocks: bool = False) -> Dict[str, Any]:
    """
    Verify access to Google Sheets API
    
    Args:
        verbose: Whether to display detailed output
        use_mocks: Whether to use mock responses
    
    Returns:
        Dict[str, Any]: Verification results with status and details
    """
    logger.info("Starting Google Sheets API verification")
    
    with LoggingContext(logger, "verify_google_sheets_access"):
        # Override API_TEST_SETTINGS if specified
        old_mock_setting = API_TEST_SETTINGS['USE_MOCK_RESPONSES']
        if use_mocks:
            API_TEST_SETTINGS['USE_MOCK_RESPONSES'] = True
            
        try:
            # Create authentication service
            auth_service = AuthenticationService()
            
            # Call the test function from api_testing
            result = test_google_sheets_api(auth_service)
            
            # Log the result
            if result['status'] == 'success':
                logger.info("Google Sheets API verification succeeded")
            else:
                logger.error("Google Sheets API verification failed", 
                            context={'error': result.get('error', 'Unknown error')})
            
            # Print detailed results if verbose mode is enabled
            if verbose:
                print("Google Sheets API Verification:")
                print(f"Status: {result['status']}")
                if 'details' in result:
                    print("Details:")
                    for operation, operation_result in result['details'].items():
                        print(f"  - {operation}: {operation_result.get('status', 'unknown')}")
                        
                        # Add additional details if present
                        for key, value in operation_result.items():
                            if key != 'status':
                                print(f"    {key}: {value}")
                if 'error' in result:
                    print(f"Error: {result['error']}")
                print()
            
            return result
        except Exception as e:
            logger.error(f"Error during Google Sheets API verification: {str(e)}")
            error_result = {
                'status': 'failed',
                'error': str(e)
            }
            return error_result
        finally:
            # Restore original mock setting
            API_TEST_SETTINGS['USE_MOCK_RESPONSES'] = old_mock_setting


def verify_gemini_access(verbose: bool = False, use_mocks: bool = False) -> Dict[str, Any]:
    """
    Verify access to Gemini AI API
    
    Args:
        verbose: Whether to display detailed output
        use_mocks: Whether to use mock responses
    
    Returns:
        Dict[str, Any]: Verification results with status and details
    """
    logger.info("Starting Gemini AI API verification")
    
    with LoggingContext(logger, "verify_gemini_access"):
        # Override API_TEST_SETTINGS if specified
        old_mock_setting = API_TEST_SETTINGS['USE_MOCK_RESPONSES']
        if use_mocks:
            API_TEST_SETTINGS['USE_MOCK_RESPONSES'] = True
            
        try:
            # Create authentication service
            auth_service = AuthenticationService()
            
            # Call the test function from api_testing
            result = test_gemini_api(auth_service)
            
            # Log the result
            if result['status'] == 'success':
                logger.info("Gemini AI API verification succeeded")
            else:
                logger.error("Gemini AI API verification failed", 
                            context={'error': result.get('error', 'Unknown error')})
            
            # Print detailed results if verbose mode is enabled
            if verbose:
                print("Gemini AI API Verification:")
                print(f"Status: {result['status']}")
                if 'details' in result:
                    print("Details:")
                    for operation, operation_result in result['details'].items():
                        print(f"  - {operation}: {operation_result.get('status', 'unknown')}")
                        
                        # Add additional details if present
                        for key, value in operation_result.items():
                            if key != 'status':
                                print(f"    {key}: {value}")
                if 'error' in result:
                    print(f"Error: {result['error']}")
                print()
            
            return result
        except Exception as e:
            logger.error(f"Error during Gemini AI API verification: {str(e)}")
            error_result = {
                'status': 'failed',
                'error': str(e)
            }
            return error_result
        finally:
            # Restore original mock setting
            API_TEST_SETTINGS['USE_MOCK_RESPONSES'] = old_mock_setting


def verify_gmail_access(verbose: bool = False, use_mocks: bool = False) -> Dict[str, Any]:
    """
    Verify access to Gmail API
    
    Args:
        verbose: Whether to display detailed output
        use_mocks: Whether to use mock responses
    
    Returns:
        Dict[str, Any]: Verification results with status and details
    """
    logger.info("Starting Gmail API verification")
    
    with LoggingContext(logger, "verify_gmail_access"):
        # Override API_TEST_SETTINGS if specified
        old_mock_setting = API_TEST_SETTINGS['USE_MOCK_RESPONSES']
        if use_mocks:
            API_TEST_SETTINGS['USE_MOCK_RESPONSES'] = True
            
        try:
            # Create authentication service
            auth_service = AuthenticationService()
            
            # Call the test function from api_testing
            result = test_gmail_api(auth_service)
            
            # Log the result
            if result['status'] == 'success':
                logger.info("Gmail API verification succeeded")
            else:
                logger.error("Gmail API verification failed", 
                            context={'error': result.get('error', 'Unknown error')})
            
            # Print detailed results if verbose mode is enabled
            if verbose:
                print("Gmail API Verification:")
                print(f"Status: {result['status']}")
                if 'details' in result:
                    print("Details:")
                    for operation, operation_result in result['details'].items():
                        print(f"  - {operation}: {operation_result.get('status', 'unknown')}")
                        
                        # Add additional details if present
                        for key, value in operation_result.items():
                            if key != 'status':
                                print(f"    {key}: {value}")
                if 'error' in result:
                    print(f"Error: {result['error']}")
                print()
            
            return result
        except Exception as e:
            logger.error(f"Error during Gmail API verification: {str(e)}")
            error_result = {
                'status': 'failed',
                'error': str(e)
            }
            return error_result
        finally:
            # Restore original mock setting
            API_TEST_SETTINGS['USE_MOCK_RESPONSES'] = old_mock_setting


def verify_all_api_access(verbose: bool = False, use_mocks: bool = False) -> Dict[str, Dict[str, Any]]:
    """
    Verify access to all required APIs
    
    Args:
        verbose: Whether to display detailed output
        use_mocks: Whether to use mock responses
    
    Returns:
        Dict[str, Dict[str, Any]]: Verification results for all APIs
    """
    logger.info("Starting verification of all APIs")
    
    # Create authentication service
    auth_service = AuthenticationService()
    
    # Check if credentials are valid
    logger.info("Validating API credentials")
    creds_valid = auth_service.validate_credentials()
    logger.info(f"Credentials validation: {'successful' if creds_valid else 'failed'}")
    
    # Initialize results
    results = {}
    
    # Test Capital One API
    results['capital_one'] = verify_capital_one_access(verbose, use_mocks)
    
    # Test Google Sheets API
    results['google_sheets'] = verify_google_sheets_access(verbose, use_mocks)
    
    # Test Gemini API
    results['gemini'] = verify_gemini_access(verbose, use_mocks)
    
    # Test Gmail API
    results['gmail'] = verify_gmail_access(verbose, use_mocks)
    
    # Calculate overall status
    overall_status = 'success'
    for api, api_results in results.items():
        if api_results['status'] == 'failed':
            overall_status = 'failed'
            break
    
    logger.info(f"All API verifications completed with overall status: {overall_status}")
    
    # Add overall status to results
    results['overall_status'] = overall_status
    
    return results


def save_verification_results(results: Dict[str, Any], output_file: str) -> bool:
    """
    Save API verification results to a file
    
    Args:
        results: Verification results to save
        output_file: File path to save results
    
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        # Add timestamp to results
        results_with_timestamp = results.copy()
        results_with_timestamp['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Write results to file
        with open(output_file, 'w') as f:
            json.dump(results_with_timestamp, f, indent=2)
        
        logger.info(f"Verification results saved to {output_file}")
        return True
    
    except Exception as e:
        logger.error(f"Error saving verification results: {str(e)}")
        return False


def main() -> int:
    """
    Main function to orchestrate API verification
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Parse command line arguments
    args = parse_arguments()
    
    # Determine whether to use mock responses
    use_mocks = args.mock or API_TEST_SETTINGS['USE_MOCK_RESPONSES']
    
    if use_mocks:
        logger.info("Using mock responses for API tests")
    
    # Initialize results
    results = {}
    
    try:
        # Verify the specified service or all services
        if args.service:
            logger.info(f"Verifying only {args.service} API")
            
            if args.service == 'capital_one':
                results = {'capital_one': verify_capital_one_access(args.verbose, use_mocks)}
            elif args.service == 'google_sheets':
                results = {'google_sheets': verify_google_sheets_access(args.verbose, use_mocks)}
            elif args.service == 'gemini':
                results = {'gemini': verify_gemini_access(args.verbose, use_mocks)}
            elif args.service == 'gmail':
                results = {'gmail': verify_gmail_access(args.verbose, use_mocks)}
            
            # Determine overall status
            overall_status = 'success'
            for api, api_results in results.items():
                if api_results['status'] == 'failed':
                    overall_status = 'failed'
                    break
                    
            results['overall_status'] = overall_status
        else:
            # Verify all APIs
            results = verify_all_api_access(args.verbose, use_mocks)
        
        # Save results to file if specified
        if args.output:
            save_verification_results(results, args.output)
        
        # Print formatted results
        print(format_test_results(results, args.verbose))
        
        # Return exit code based on overall status
        return 0 if results.get('overall_status') == 'success' else 1
    
    except Exception as e:
        logger.critical(f"Unexpected error during API verification: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())