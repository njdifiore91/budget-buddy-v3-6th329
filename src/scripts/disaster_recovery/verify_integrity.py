#!/usr/bin/env python3
"""
Script for verifying the integrity of the Budget Management Application system components,
credentials, API connectivity, and data. Used during disaster recovery operations to ensure
the system is properly configured and operational.

Usage:
    python verify_integrity.py [--verbose] [--report] [--email] [--fix]

Options:
    --verbose    Show detailed output
    --report     Generate a comprehensive integrity report
    --email      Send the integrity report via email
    --fix        Attempt to fix issues automatically

Returns:
    0 if all checks pass, non-zero otherwise
"""

import os
import sys
import json
import argparse
import datetime
import time
from typing import Dict, List, Optional, Any

# Internal imports
from ..config.path_constants import BACKUP_DIR, DATA_DIR, CREDENTIALS_DIR, ensure_dir_exists
from ..config.logging_setup import get_script_logger, log_script_start, log_script_end
from ..config.script_settings import SCRIPT_SETTINGS

# API clients for connectivity testing
from ...backend.api_clients.google_sheets_client import GoogleSheetsClient
from ...backend.api_clients.capital_one_client import CapitalOneClient
from ...backend.api_clients.gemini_client import GeminiClient
from ...backend.api_clients.gmail_client import GmailClient
from ...backend.services.authentication_service import AuthenticationService

# Set up logger
logger = get_script_logger('verify_integrity')

# Constants
REQUIRED_DIRECTORIES = [DATA_DIR, BACKUP_DIR, CREDENTIALS_DIR]
REQUIRED_CREDENTIALS = ['capital_one.json', 'google_sheets.json', 'gemini.json', 'gmail.json']
REQUIRED_API_ENDPOINTS = ['capital_one', 'google_sheets', 'gemini', 'gmail']

def parse_arguments():
    """
    Parse command-line arguments for the script
    
    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description='Verify integrity of Budget Management Application system components'
    )
    parser.add_argument('--verbose', action='store_true', help='Show detailed output')
    parser.add_argument('--report', action='store_true', help='Generate integrity report')
    parser.add_argument('--email', action='store_true', help='Send integrity report via email')
    parser.add_argument('--fix', action='store_true', help='Attempt to fix issues automatically')
    return parser.parse_args()

def verify_directory_structure(verbose: bool) -> Dict:
    """
    Verify that all required directories exist and have correct permissions
    
    Args:
        verbose: Whether to show detailed output
        
    Returns:
        Dictionary with verification results for each directory
    """
    results = {}
    
    logger.info("Verifying directory structure...")
    
    for directory in REQUIRED_DIRECTORIES:
        dir_result = {
            'exists': os.path.exists(directory),
            'is_dir': os.path.isdir(directory) if os.path.exists(directory) else False,
            'permissions': oct(os.stat(directory).st_mode & 0o777) if os.path.exists(directory) else None
        }
        
        # Determine if directory is valid (exists and is a directory)
        dir_result['valid'] = dir_result['exists'] and dir_result['is_dir']
        
        # Add to results
        results[directory] = dir_result
        
        if verbose:
            status = "✓" if dir_result['valid'] else "✗"
            logger.info(f"{status} {directory} - Exists: {dir_result['exists']}, Permissions: {dir_result['permissions']}")
    
    # Log summary
    valid_dirs = sum(1 for result in results.values() if result['valid'])
    logger.info(f"Directory verification complete: {valid_dirs}/{len(REQUIRED_DIRECTORIES)} valid")
    
    return results

def verify_credentials(verbose: bool) -> Dict:
    """
    Verify that all required API credentials exist and are valid
    
    Args:
        verbose: Whether to show detailed output
        
    Returns:
        Dictionary with verification results for each credential file
    """
    results = {}
    
    logger.info("Verifying API credentials...")
    
    for cred_file in REQUIRED_CREDENTIALS:
        cred_path = os.path.join(CREDENTIALS_DIR, cred_file)
        cred_result = {
            'exists': os.path.exists(cred_path),
            'is_file': os.path.isfile(cred_path) if os.path.exists(cred_path) else False,
        }
        
        # Check if it's valid JSON and has required fields
        cred_result['valid_json'] = False
        cred_result['has_required_fields'] = False
        
        if cred_result['exists'] and cred_result['is_file']:
            try:
                with open(cred_path, 'r') as f:
                    cred_data = json.load(f)
                cred_result['valid_json'] = True
                
                # Different credential files have different required fields
                if cred_file == 'capital_one.json':
                    required_fields = ['client_id', 'client_secret']
                elif cred_file == 'google_sheets.json' or cred_file == 'gmail.json':
                    required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
                elif cred_file == 'gemini.json':
                    required_fields = ['api_key']
                else:
                    required_fields = []
                
                # Check for required fields
                cred_result['has_required_fields'] = all(field in cred_data for field in required_fields)
                cred_result['missing_fields'] = [field for field in required_fields if field not in cred_data]
                
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Error validating {cred_file}: {str(e)}")
                cred_result['error'] = str(e)
        
        # Determine if credential is valid (exists, is a file, valid JSON, has required fields)
        cred_result['valid'] = (cred_result['exists'] and cred_result['is_file'] and 
                               cred_result['valid_json'] and cred_result['has_required_fields'])
        
        # Add to results
        results[cred_file] = cred_result
        
        if verbose:
            status = "✓" if cred_result['valid'] else "✗"
            logger.info(f"{status} {cred_file} - Exists: {cred_result['exists']}, Valid JSON: {cred_result.get('valid_json', False)}")
    
    # Log summary
    valid_creds = sum(1 for result in results.values() if result['valid'])
    logger.info(f"Credentials verification complete: {valid_creds}/{len(REQUIRED_CREDENTIALS)} valid")
    
    return results

def verify_api_connectivity(verbose: bool) -> Dict:
    """
    Verify connectivity to all required external APIs
    
    Args:
        verbose: Whether to show detailed output
        
    Returns:
        Dictionary with verification results for each API
    """
    results = {}
    
    logger.info("Verifying API connectivity...")
    
    # Initialize API clients
    auth_service = AuthenticationService()
    timeout = SCRIPT_SETTINGS.get('TIMEOUT', 30)
    max_retries = SCRIPT_SETTINGS.get('MAX_RETRIES', 3)
    
    for api in REQUIRED_API_ENDPOINTS:
        api_result = {
            'connectivity': False,
            'authentication': False,
            'error': None
        }
        
        try:
            if api == 'capital_one':
                client = CapitalOneClient(auth_service)
                api_result['authentication'] = client.authenticate()
                if api_result['authentication']:
                    api_result['connectivity'] = client.test_connectivity()
                    if verbose:
                        # Test account access if verbose
                        checking = client.get_checking_account_details()
                        savings = client.get_savings_account_details()
                        api_result['checking_account'] = 'accountId' in checking
                        api_result['savings_account'] = 'accountId' in savings
                
            elif api == 'google_sheets':
                client = GoogleSheetsClient(auth_service)
                api_result['authentication'] = client.authenticate()
                if api_result['authentication']:
                    # Try to access sheet data to verify connectivity
                    try:
                        budget_data = client.get_master_budget_data()
                        api_result['connectivity'] = True
                        if verbose:
                            api_result['data_rows'] = len(budget_data)
                    except Exception as e:
                        api_result['error'] = f"Error accessing sheet data: {str(e)}"
                
            elif api == 'gemini':
                client = GeminiClient(auth_service)
                api_result['authentication'] = client.authenticate()
                if api_result['authentication']:
                    # Test with a simple prompt
                    try:
                        response = client.generate_completion("Generate a test response of one word.")
                        api_result['connectivity'] = response is not None and len(response) > 0
                    except Exception as e:
                        api_result['error'] = f"Error testing Gemini API: {str(e)}"
                
            elif api == 'gmail':
                client = GmailClient(auth_service)
                api_result['authentication'] = client.authenticate()
                if api_result['authentication']:
                    api_result['connectivity'] = True  # If authentication succeeds, connectivity is good
            
        except Exception as e:
            logger.warning(f"Error verifying {api} API: {str(e)}")
            api_result['error'] = str(e)
        
        # Determine overall status
        api_result['status'] = 'operational' if api_result['connectivity'] else 'failed'
        
        # Add to results
        results[api] = api_result
        
        if verbose:
            status = "✓" if api_result['connectivity'] else "✗"
            logger.info(f"{status} {api} API - Authentication: {api_result['authentication']}, Connectivity: {api_result['connectivity']}")
    
    # Log summary
    operational_apis = sum(1 for result in results.values() if result['status'] == 'operational')
    logger.info(f"API connectivity verification complete: {operational_apis}/{len(REQUIRED_API_ENDPOINTS)} operational")
    
    return results

def verify_sheets_data_integrity(sheets_client: GoogleSheetsClient) -> Dict:
    """
    Verify the integrity of Google Sheets data
    
    Args:
        sheets_client: Authenticated GoogleSheetsClient instance
        
    Returns:
        Dictionary with verification results for Google Sheets data
    """
    results = {
        'master_budget': {
            'exists': False,
            'has_data': False,
            'has_required_columns': False,
            'row_count': 0
        },
        'weekly_spending': {
            'exists': False,
            'has_data': False,
            'has_required_columns': False,
            'row_count': 0
        },
        'data_consistency': False
    }
    
    logger.info("Verifying Google Sheets data integrity...")
    
    try:
        # Verify Master Budget sheet
        try:
            budget_data = sheets_client.get_master_budget_data()
            results['master_budget']['exists'] = True
            results['master_budget']['row_count'] = len(budget_data)
            results['master_budget']['has_data'] = len(budget_data) > 0
            
            # Check for required columns (in the sheet, we can't directly check column names)
            # So we check if rows have at least 2 entries (category name and amount)
            if results['master_budget']['has_data']:
                has_required_columns = all(len(row) >= 2 for row in budget_data)
                results['master_budget']['has_required_columns'] = has_required_columns
            
            logger.info(f"Master Budget sheet verification: {len(budget_data)} rows found")
            
        except Exception as e:
            logger.warning(f"Error verifying Master Budget sheet: {str(e)}")
            results['master_budget']['error'] = str(e)
        
        # Verify Weekly Spending sheet
        try:
            spending_data = sheets_client.get_weekly_spending_data()
            results['weekly_spending']['exists'] = True
            results['weekly_spending']['row_count'] = len(spending_data)
            results['weekly_spending']['has_data'] = len(spending_data) > 0
            
            # Check for required columns (location, amount, timestamp, category)
            if results['weekly_spending']['has_data']:
                has_required_columns = all(len(row) >= 3 for row in spending_data)  # At least 3 columns
                results['weekly_spending']['has_required_columns'] = has_required_columns
            
            logger.info(f"Weekly Spending sheet verification: {len(spending_data)} rows found")
            
        except Exception as e:
            logger.warning(f"Error verifying Weekly Spending sheet: {str(e)}")
            results['weekly_spending']['error'] = str(e)
        
        # Check data consistency between sheets
        if (results['master_budget']['exists'] and results['weekly_spending']['exists'] and
                results['master_budget']['has_data'] and results['weekly_spending']['has_data']):
            
            # Extract categories from Master Budget
            budget_categories = [row[0] for row in budget_data if len(row) >= 1]
            
            # Check if transactions have categories that match budget categories
            if spending_data and len(spending_data) > 0:
                categories_in_transactions = [row[3] for row in spending_data if len(row) >= 4 and row[3]]
                
                # Check if all transaction categories are in the budget
                invalid_categories = [cat for cat in categories_in_transactions 
                                    if cat and cat not in budget_categories]
                
                results['data_consistency'] = len(invalid_categories) == 0
                results['invalid_categories'] = invalid_categories
                
                logger.info(f"Data consistency check: {len(invalid_categories)} invalid categories found")
            else:
                results['data_consistency'] = True  # No transactions to check
                
    except Exception as e:
        logger.warning(f"Error during sheets data integrity verification: {str(e)}")
        results['error'] = str(e)
    
    # Determine overall status
    master_budget_valid = (results['master_budget']['exists'] and 
                          results['master_budget']['has_data'] and 
                          results['master_budget']['has_required_columns'])
    
    weekly_spending_valid = (results['weekly_spending']['exists'] and
                            results['weekly_spending']['has_required_columns'])
    
    results['status'] = 'valid' if (master_budget_valid and weekly_spending_valid and 
                                  results['data_consistency']) else 'invalid'
    
    logger.info(f"Sheets data integrity verification complete: {results['status']}")
    
    return results

def verify_capital_one_accounts(capital_one_client: CapitalOneClient) -> Dict:
    """
    Verify Capital One accounts are accessible and have correct status
    
    Args:
        capital_one_client: Authenticated CapitalOneClient instance
        
    Returns:
        Dictionary with verification results for Capital One accounts
    """
    results = {
        'checking_account': {
            'exists': False,
            'active': False,
            'balance_accessible': False
        },
        'savings_account': {
            'exists': False,
            'active': False,
            'balance_accessible': False
        }
    }
    
    logger.info("Verifying Capital One accounts...")
    
    try:
        # Verify checking account
        checking = capital_one_client.get_checking_account_details()
        results['checking_account']['exists'] = 'accountId' in checking
        
        if results['checking_account']['exists']:
            results['checking_account']['active'] = checking.get('status') == 'active'
            results['checking_account']['balance_accessible'] = 'balance' in checking
            
            if results['checking_account']['balance_accessible']:
                results['checking_account']['balance'] = checking.get('balance')
        
        # Verify savings account
        savings = capital_one_client.get_savings_account_details()
        results['savings_account']['exists'] = 'accountId' in savings
        
        if results['savings_account']['exists']:
            results['savings_account']['active'] = savings.get('status') == 'active'
            results['savings_account']['balance_accessible'] = 'balance' in savings
            
            if results['savings_account']['balance_accessible']:
                results['savings_account']['balance'] = savings.get('balance')
        
    except Exception as e:
        logger.warning(f"Error verifying Capital One accounts: {str(e)}")
        results['error'] = str(e)
    
    # Determine overall status
    checking_valid = (results['checking_account']['exists'] and 
                     results['checking_account']['active'] and 
                     results['checking_account']['balance_accessible'])
    
    savings_valid = (results['savings_account']['exists'] and 
                    results['savings_account']['active'] and 
                    results['savings_account']['balance_accessible'])
    
    results['status'] = 'valid' if checking_valid and savings_valid else 'invalid'
    
    logger.info(f"Capital One accounts verification complete: {results['status']}")
    
    return results

def fix_directory_structure(directory_results: Dict) -> Dict:
    """
    Attempt to fix directory structure issues
    
    Args:
        directory_results: Results from verify_directory_structure()
        
    Returns:
        Dictionary with fix results for each directory
    """
    fix_results = {}
    
    logger.info("Attempting to fix directory structure issues...")
    
    for directory, result in directory_results.items():
        if not result['valid']:
            try:
                # Create directory if it doesn't exist
                if not result['exists'] or not result['is_dir']:
                    logger.info(f"Creating directory: {directory}")
                    ensure_dir_exists(directory)
                    
                    # Check if fix was successful
                    fixed = os.path.exists(directory) and os.path.isdir(directory)
                    fix_results[directory] = {
                        'fixed': fixed,
                        'action': 'created'
                    }
                    
                    if fixed:
                        logger.info(f"✓ Successfully created directory: {directory}")
                    else:
                        logger.warning(f"✗ Failed to create directory: {directory}")
                
                # Fix permissions if needed (for credentials directory)
                if directory == CREDENTIALS_DIR and result['exists'] and result.get('permissions') != '0o700':
                    logger.info(f"Fixing permissions for credentials directory")
                    os.chmod(CREDENTIALS_DIR, 0o700)
                    
                    # Check if permissions were fixed
                    new_permissions = oct(os.stat(CREDENTIALS_DIR).st_mode & 0o777)
                    fixed_permissions = new_permissions == '0o700'
                    
                    if 'fixed' in fix_results.get(directory, {}):
                        fix_results[directory]['permissions_fixed'] = fixed_permissions
                    else:
                        fix_results[directory] = {
                            'fixed': fixed_permissions,
                            'action': 'permissions'
                        }
                    
                    if fixed_permissions:
                        logger.info(f"✓ Successfully fixed permissions for: {directory}")
                    else:
                        logger.warning(f"✗ Failed to fix permissions for: {directory}")
                
            except Exception as e:
                logger.error(f"Error fixing directory {directory}: {str(e)}")
                fix_results[directory] = {
                    'fixed': False,
                    'error': str(e)
                }
    
    # Log summary
    fixed_dirs = sum(1 for result in fix_results.values() if result.get('fixed', False))
    logger.info(f"Directory structure fix attempts complete: {fixed_dirs}/{len(fix_results)} fixed")
    
    return fix_results

def generate_integrity_report(directory_results: Dict, credential_results: Dict, 
                             api_results: Dict, data_results: Dict) -> Dict:
    """
    Generate a comprehensive integrity report based on verification results
    
    Args:
        directory_results: Results from verify_directory_structure()
        credential_results: Results from verify_credentials()
        api_results: Results from verify_api_connectivity()
        data_results: Results from data verification functions
        
    Returns:
        Comprehensive integrity report
    """
    # Calculate timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create report structure
    report = {
        'timestamp': timestamp,
        'summary': {
            'directories': sum(1 for r in directory_results.values() if r.get('valid', False)),
            'total_directories': len(directory_results),
            'credentials': sum(1 for r in credential_results.values() if r.get('valid', False)),
            'total_credentials': len(credential_results),
            'apis': sum(1 for r in api_results.values() if r.get('status') == 'operational'),
            'total_apis': len(api_results)
        },
        'details': {
            'directories': directory_results,
            'credentials': credential_results,
            'apis': api_results,
            'data': data_results
        },
        'recommendations': []
    }
    
    # Calculate overall health
    dir_health = report['summary']['directories'] / report['summary']['total_directories'] if report['summary']['total_directories'] > 0 else 0
    cred_health = report['summary']['credentials'] / report['summary']['total_credentials'] if report['summary']['total_credentials'] > 0 else 0
    api_health = report['summary']['apis'] / report['summary']['total_apis'] if report['summary']['total_apis'] > 0 else 0
    
    # Weight the health factors (directories and credentials more important than API connectivity)
    health_score = (dir_health * 0.3) + (cred_health * 0.3) + (api_health * 0.4)
    report['health_percentage'] = round(health_score * 100, 1)
    
    # Determine health status
    if report['health_percentage'] >= 90:
        report['health_status'] = 'Healthy'
    elif report['health_percentage'] >= 70:
        report['health_status'] = 'Warning'
    else:
        report['health_status'] = 'Critical'
    
    # Generate recommendations based on issues found
    if report['summary']['directories'] < report['summary']['total_directories']:
        report['recommendations'].append("Create missing directories to ensure system can store data properly.")
    
    if report['summary']['credentials'] < report['summary']['total_credentials']:
        report['recommendations'].append("Fix or restore missing credentials files to enable API authentication.")
    
    if report['summary']['apis'] < report['summary']['total_apis']:
        report['recommendations'].append("Check API connectivity and authentication settings for failed services.")
    
    # Add data-specific recommendations
    sheets_status = data_results.get('sheets', {}).get('status', 'unknown')
    if sheets_status != 'valid':
        report['recommendations'].append("Verify Google Sheets structure and data are properly configured.")
    
    accounts_status = data_results.get('capital_one', {}).get('status', 'unknown')
    if accounts_status != 'valid':
        report['recommendations'].append("Verify Capital One account access and status.")
    
    # Save report to file
    report_path = os.path.join(DATA_DIR, f"integrity_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    try:
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Integrity report saved to: {report_path}")
        report['report_path'] = report_path
    except Exception as e:
        logger.error(f"Error saving integrity report: {str(e)}")
        report['error'] = str(e)
    
    logger.info(f"Integrity report generated. System health: {report['health_status']} ({report['health_percentage']}%)")
    return report

def send_integrity_report(report: Dict, gmail_client: GmailClient) -> bool:
    """
    Send the integrity report via email
    
    Args:
        report: Integrity report data
        gmail_client: Authenticated GmailClient instance
        
    Returns:
        True if report was sent successfully, False otherwise
    """
    logger.info("Preparing to send integrity report via email...")
    
    try:
        # Format report as HTML for email
        health_color = "green" if report['health_status'] == 'Healthy' else ("orange" if report['health_status'] == 'Warning' else "red")
        
        html_content = f"""
        <html>
        <body>
            <h1>Budget Management Application Integrity Report</h1>
            <p><strong>Generated:</strong> {report['timestamp']}</p>
            <h2>System Health: <span style="color: {health_color};">{report['health_status']} ({report['health_percentage']}%)</span></h2>
            
            <h3>Summary</h3>
            <ul>
                <li>Directories: {report['summary']['directories']}/{report['summary']['total_directories']} valid</li>
                <li>Credentials: {report['summary']['credentials']}/{report['summary']['total_credentials']} valid</li>
                <li>APIs: {report['summary']['apis']}/{report['summary']['total_apis']} operational</li>
            </ul>
            
            <h3>Recommendations</h3>
            <ul>
        """
        
        for recommendation in report['recommendations']:
            html_content += f"<li>{recommendation}</li>\n"
        
        html_content += """
            </ul>
            
            <h3>Details</h3>
            <p>Please see the attached JSON report for detailed information.</p>
        </body>
        </html>
        """
        
        # Create email subject
        subject = f"Budget Management System Integrity Report - {report['health_status']} ({report['health_percentage']}%)"
        
        # Send email
        recipients = ['njdifiore@gmail.com']  # Default recipient from technical specification
        
        result = gmail_client.send_email(
            subject=subject,
            html_content=html_content,
            recipients=recipients,
            attachment_paths=[report.get('report_path')] if 'report_path' in report else []
        )
        
        logger.info(f"Integrity report email sent to {', '.join(recipients)}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send integrity report email: {str(e)}")
        return False

def main():
    """
    Main function that orchestrates the integrity verification process
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Parse command-line arguments
    args = parse_arguments()
    
    # Start logging
    log_script_start("verify_integrity")
    
    # Record start time for performance measurement
    start_time = time.time()
    
    # Initialize variables for verification results
    directory_results = {}
    credential_results = {}
    api_results = {}
    data_results = {}
    
    try:
        # Verify directory structure
        logger.info("Starting directory structure verification...")
        directory_results = verify_directory_structure(args.verbose)
        
        # Verify credentials
        logger.info("Starting credentials verification...")
        credential_results = verify_credentials(args.verbose)
        
        # Try to fix directory structure if requested
        if args.fix:
            logger.info("Attempting to fix directory structure issues...")
            fix_results = fix_directory_structure(directory_results)
            
            # Re-verify directories after fix attempt
            if any(result.get('fixed', False) for result in fix_results.values()):
                logger.info("Re-verifying directory structure after fixes...")
                directory_results = verify_directory_structure(args.verbose)
        
        # Verify API connectivity
        logger.info("Starting API connectivity verification...")
        api_results = verify_api_connectivity(args.verbose)
        
        # Verify data integrity if APIs are accessible
        sheets_operational = api_results.get('google_sheets', {}).get('connectivity', False)
        capital_one_operational = api_results.get('capital_one', {}).get('connectivity', False)
        
        if sheets_operational and capital_one_operational:
            logger.info("Starting data integrity verification...")
            
            try:
                # Initialize authentication service
                auth_service = AuthenticationService()
                
                # Verify Google Sheets data integrity
                sheets_client = GoogleSheetsClient(auth_service)
                if sheets_client.authenticate():
                    sheets_results = verify_sheets_data_integrity(sheets_client)
                else:
                    logger.warning("Could not authenticate with Google Sheets")
                    sheets_results = {'status': 'authentication_failed'}
                
                # Verify Capital One accounts
                capital_one_client = CapitalOneClient(auth_service)
                if capital_one_client.authenticate():
                    accounts_results = verify_capital_one_accounts(capital_one_client)
                else:
                    logger.warning("Could not authenticate with Capital One")
                    accounts_results = {'status': 'authentication_failed'}
                
                # Combine data verification results
                data_results = {
                    'sheets': sheets_results,
                    'capital_one': accounts_results,
                    'status': 'valid' if (sheets_results.get('status') == 'valid' and 
                                         accounts_results.get('status') == 'valid') else 'invalid'
                }
                
                logger.info(f"Data integrity verification complete: {data_results['status']}")
                
            except Exception as e:
                logger.error(f"Error during data integrity verification: {str(e)}")
                data_results = {'status': 'error', 'error': str(e)}
        else:
            logger.warning("Skipping data integrity verification due to API connectivity issues")
        
        # Generate integrity report if requested
        if args.report:
            logger.info("Generating integrity report...")
            report = generate_integrity_report(directory_results, credential_results, api_results, data_results)
            
            # Send report via email if requested
            if args.email and api_results.get('gmail', {}).get('connectivity', False):
                logger.info("Sending integrity report via email...")
                try:
                    auth_service = AuthenticationService()
                    gmail_client = GmailClient(auth_service)
                    if gmail_client.authenticate():
                        send_status = send_integrity_report(report, gmail_client)
                        if not send_status:
                            logger.warning("Failed to send integrity report via email")
                    else:
                        logger.warning("Could not authenticate with Gmail for sending report")
                except Exception as e:
                    logger.error(f"Error sending integrity report via email: {str(e)}")
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Determine exit code based on verification results
        dir_health = sum(1 for r in directory_results.values() if r.get('valid', False)) / len(directory_results) if directory_results else 0
        cred_health = sum(1 for r in credential_results.values() if r.get('valid', False)) / len(credential_results) if credential_results else 0
        api_health = sum(1 for r in api_results.values() if r.get('connectivity', False)) / len(api_results) if api_results else 0
        data_health = 1 if data_results.get('status') == 'valid' else 0
        
        overall_health = (dir_health * 0.3) + (cred_health * 0.3) + (api_health * 0.3) + (data_health * 0.1)
        
        # Log script end with execution time
        log_script_end("verify_integrity", execution_time)
        
        if overall_health >= 0.9:
            logger.info("System integrity verification successful")
            return 0
        elif overall_health >= 0.7:
            logger.warning("System integrity verification completed with warnings")
            return 1
        else:
            logger.error("System integrity verification failed with critical issues")
            return 2
            
    except Exception as e:
        # Log any unhandled exceptions
        logger.error(f"Error during integrity verification: {str(e)}")
        
        # Calculate execution time even on error
        execution_time = time.time() - start_time
        log_script_end("verify_integrity", execution_time)
        
        return 3  # Critical error exit code


if __name__ == "__main__":
    sys.exit(main())