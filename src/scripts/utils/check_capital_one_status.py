#!/usr/bin/env python3
"""
check_capital_one_status.py - Utility script to check the status and connectivity of the Capital One API.

This script verifies authentication, account access, and API availability to ensure
the Budget Management Application can successfully interact with Capital One services
for transaction retrieval and fund transfers.

Usage:
    python check_capital_one_status.py [options]

Options:
    -v, --verbose     Display detailed output
    -o, --output      Output results to specified file
"""

import argparse
import sys
import time
import requests  # requests 2.31.0+

from ...backend.api_clients.capital_one_client import CapitalOneClient
from ...backend.services.authentication_service import AuthenticationService
from ..config.logging_setup import get_logger
from ..config.script_settings import SCRIPT_SETTINGS, API_TEST_SETTINGS

# Set up logger
logger = get_logger('check_capital_one_status')


def check_authentication(client):
    """
    Checks if authentication with Capital One API is successful.
    
    Args:
        client (CapitalOneClient): Client for Capital One API
        
    Returns:
        bool: True if authentication is successful, False otherwise
    """
    logger.info("Checking Capital One API authentication")
    
    try:
        # Measure start time
        start_time = time.time()
        
        # Attempt to authenticate
        auth_result = client.authenticate()
        
        # Measure end time
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        if auth_result:
            logger.info(f"Authentication successful (took {duration_ms:.2f}ms)")
            return True
        else:
            logger.error(f"Authentication failed (took {duration_ms:.2f}ms)")
            return False
            
    except Exception as e:
        logger.error(f"Error during authentication check: {str(e)}")
        return False


def check_account_access(client):
    """
    Checks if the application can access account details from Capital One.
    
    Args:
        client (CapitalOneClient): Client for Capital One API
        
    Returns:
        bool: True if account access is successful, False otherwise
    """
    logger.info("Checking Capital One account access")
    
    try:
        # Measure start time
        start_time = time.time()
        
        # Get test account ID if specified, otherwise use the client's default
        test_account_id = API_TEST_SETTINGS.get('CAPITAL_ONE_TEST_ACCOUNT')
        
        # Attempt to retrieve account details
        if test_account_id:
            logger.info(f"Using test account ID for access check")
            account_details = client.get_account_details(test_account_id)
        else:
            account_details = client.get_checking_account_details()
        
        # Measure end time
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # Verify response contains expected account information
        if isinstance(account_details, dict) and 'accountId' in account_details:
            logger.info(f"Account access successful (took {duration_ms:.2f}ms)")
            return True
        else:
            logger.error(f"Account access failed - invalid response format (took {duration_ms:.2f}ms)")
            return False
            
    except Exception as e:
        logger.error(f"Error during account access check: {str(e)}")
        return False


def check_api_responsiveness(client):
    """
    Checks the responsiveness of the Capital One API.
    
    Args:
        client (CapitalOneClient): Client for Capital One API
        
    Returns:
        dict: Dictionary with response time and status
    """
    logger.info("Checking Capital One API responsiveness")
    
    try:
        # Measure start time
        start_time = time.time()
        
        # Test API connectivity
        timeout = SCRIPT_SETTINGS.get('TIMEOUT', 30)
        connectivity_result = client.test_connectivity()
        
        # Measure end time
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # Prepare response details
        response = {
            "time_ms": duration_ms,
            "status": "ok" if connectivity_result else "fail"
        }
        
        logger.info(f"API responsiveness check completed in {duration_ms:.2f}ms - Status: {response['status']}")
        return response
        
    except Exception as e:
        logger.error(f"Error during API responsiveness check: {str(e)}")
        return {
            "time_ms": 0,
            "status": "error",
            "error": str(e)
        }


def run_all_checks():
    """
    Runs all Capital One API status checks.
    
    Returns:
        dict: Dictionary with results of all checks
    """
    logger.info("Running all Capital One API checks")
    
    results = {
        "authentication": False,
        "account_access": False,
        "api_responsiveness": {"status": "fail", "time_ms": 0}
    }
    
    try:
        # Create services
        auth_service = AuthenticationService()
        client = CapitalOneClient(auth_service)
        
        # Check authentication
        results["authentication"] = check_authentication(client)
        
        # Only proceed with other checks if authentication succeeded
        if results["authentication"]:
            # Check account access
            results["account_access"] = check_account_access(client)
            
            # Check API responsiveness
            results["api_responsiveness"] = check_api_responsiveness(client)
            
        # Determine overall status
        results["overall_status"] = all([
            results["authentication"],
            results["account_access"],
            results["api_responsiveness"]["status"] == "ok"
        ])
        
        logger.info(f"All checks completed - Overall status: {'Pass' if results['overall_status'] else 'Fail'}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error running Capital One API checks: {str(e)}")
        results["overall_status"] = False
        results["error"] = str(e)
        return results


def format_results(results):
    """
    Formats check results for display.
    
    Args:
        results (dict): Results from run_all_checks
        
    Returns:
        str: Formatted results string
    """
    # Create header
    output = "===== Capital One API Status Check =====\n\n"
    
    # Format authentication result
    auth_status = "✓ PASS" if results.get("authentication", False) else "✗ FAIL"
    output += f"Authentication:      {auth_status}\n"
    
    # Format account access result
    access_status = "✓ PASS" if results.get("account_access", False) else "✗ FAIL"
    output += f"Account Access:      {access_status}\n"
    
    # Format API responsiveness result
    api_resp = results.get("api_responsiveness", {})
    resp_status = "✓ PASS" if api_resp.get("status") == "ok" else "✗ FAIL"
    resp_time = api_resp.get("time_ms", 0)
    output += f"API Responsiveness:  {resp_status} ({resp_time:.2f}ms)\n"
    
    # Add a separator
    output += "\n" + "-" * 40 + "\n\n"
    
    # Add overall status
    overall = results.get("overall_status", False)
    output += f"OVERALL STATUS:      {'✓ PASS' if overall else '✗ FAIL'}\n"
    
    # Add error if present
    if "error" in results:
        output += f"\nError: {results['error']}\n"
    
    return output


def main():
    """
    Main function to run the Capital One status check script.
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Check Capital One API status and connectivity")
    parser.add_argument("-v", "--verbose", action="store_true", help="Display detailed output")
    parser.add_argument("-o", "--output", help="Write results to specified file")
    args = parser.parse_args()
    
    try:
        # Run all checks
        results = run_all_checks()
        
        # Format the results
        formatted_results = format_results(results)
        
        # Display the results
        print(formatted_results)
        
        # Write to output file if specified
        if args.output:
            try:
                with open(args.output, "w") as f:
                    f.write(formatted_results)
                print(f"Results written to {args.output}")
            except Exception as e:
                logger.error(f"Error writing to output file: {str(e)}")
                print(f"Error writing to output file: {str(e)}")
        
        # Return appropriate exit code
        return 0 if results.get("overall_status", False) else 1
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())