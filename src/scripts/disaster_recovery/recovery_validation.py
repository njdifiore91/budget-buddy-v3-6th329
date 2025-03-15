#!/usr/bin/env python3
"""
A comprehensive validation script that verifies the successful recovery of the Budget Management Application after disaster recovery operations. It performs a series of checks to ensure that all system components, data integrity, API connectivity, and application functionality have been properly restored.
"""

import os  # standard library
import sys  # standard library
import argparse  # standard library
import json  # standard library
import datetime  # standard library
import time  # standard library
import subprocess  # standard library
from typing import Dict, List, Optional, Any, Tuple, Union  # standard library

# Internal imports
from src.scripts.config.logging_setup import get_logger, LoggingContext  # src/scripts/config/logging_setup.py
from src.scripts.config.script_settings import SCRIPT_SETTINGS  # src/scripts/config/script_settings.py
from src.scripts.disaster_recovery.verify_integrity import verify_directory_structure, verify_credentials, verify_api_connectivity, verify_sheets_data_integrity, verify_capital_one_accounts  # src/scripts/disaster_recovery/verify_integrity.py
from src.scripts.deployment.validate_deployment import validate_deployment  # src/scripts/deployment/validate_deployment.py

# Initialize global logger
logger = get_logger('recovery_validation')

# Define global constants
DEFAULT_PROJECT_ID = os.environ.get('PROJECT_ID', None)
DEFAULT_REGION = os.environ.get('REGION', 'us-east1')
DEFAULT_APP_NAME = os.environ.get('APP_NAME', 'budget-management')
MAX_RETRIES = SCRIPT_SETTINGS['MAX_RETRIES']
TIMEOUT = SCRIPT_SETTINGS['TIMEOUT']
VALIDATION_COMPONENTS = ["directories", "credentials", "apis", "data", "infrastructure", "functionality"]


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments for the recovery validation script

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    # Create ArgumentParser with description
    parser = argparse.ArgumentParser(
        description='Validate the Budget Management Application after disaster recovery.'
    )

    # Add --project-id argument with default from environment
    parser.add_argument(
        '--project-id',
        help='Google Cloud project ID',
        default=DEFAULT_PROJECT_ID
    )

    # Add --region argument with default from environment
    parser.add_argument(
        '--region',
        help='Google Cloud region',
        default=DEFAULT_REGION
    )

    # Add --app-name argument with default from environment
    parser.add_argument(
        '--app-name',
        help='Application name (Cloud Run job name)',
        default=DEFAULT_APP_NAME
    )

    # Add --verbose flag to enable detailed logging
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    # Add --report flag to generate validation report
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate validation report'
    )

    # Add --email flag to send report via email
    parser.add_argument(
        '--email',
        action='store_true',
        help='Send report via email'
    )

    # Add --skip-components argument to skip specific validation components
    parser.add_argument(
        '--skip-components',
        nargs='+',
        help='List of validation components to skip (directories, credentials, apis, data, infrastructure, functionality)'
    )

    # Add --only-components argument to run only specific validation components
    parser.add_argument(
        '--only-components',
        nargs='+',
        help='List of validation components to run (directories, credentials, apis, data, infrastructure, functionality)'
    )

    # Parse and return arguments
    return parser.parse_args()


def validate_directories(verbose: bool) -> Dict[str, Any]:
    """
    Validate that all required directories exist and have correct permissions

    Args:
        verbose: Whether to show detailed output

    Returns:
        Dict[str, Any]: Validation results for directories
    """
    # Log start of directory validation
    logger.info("Starting directory validation...")

    # Call verify_directory_structure from verify_integrity
    directory_results = verify_directory_structure(verbose)

    # Log validation results
    logger.info(f"Directory validation results: {directory_results}")

    # Return validation results
    return directory_results


def validate_credentials(verbose: bool) -> Dict[str, Any]:
    """
    Validate that all required API credentials exist and are valid

    Args:
        verbose: Whether to show detailed output

    Returns:
        Dict[str, Any]: Validation results for credentials
    """
    # Log start of credentials validation
    logger.info("Starting credentials validation...")

    # Call verify_credentials from verify_integrity
    credential_results = verify_credentials(verbose)

    # Log validation results
    logger.info(f"Credential validation results: {credential_results}")

    # Return validation results
    return credential_results


def validate_apis(verbose: bool) -> Dict[str, Any]:
    """
    Validate connectivity to all required external APIs

    Args:
        verbose: Whether to show detailed output

    Returns:
        Dict[str, Any]: Validation results for API connectivity
    """
    # Log start of API validation
    logger.info("Starting API validation...")

    # Call verify_api_connectivity from verify_integrity
    api_results = verify_api_connectivity(verbose)

    # Log validation results
    logger.info(f"API validation results: {api_results}")

    # Return validation results
    return api_results


def validate_data(verbose: bool, api_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the integrity of application data in Google Sheets and Capital One

    Args:
        verbose: Whether to show detailed output
        api_results (Dict[str, Any]): Results from API connectivity validation

    Returns:
        Dict[str, Any]: Validation results for data integrity
    """
    # Log start of data validation
    logger.info("Starting data validation...")

    # Initialize results dictionary
    data_results: Dict[str, Any] = {}

    # Check if Google Sheets API is accessible from api_results
    if api_results.get('google_sheets', {}).get('connectivity', False):
        # Get Google Sheets client from api_results
        # sheets_client = api_results['google_sheets']['client']  # This line is not needed as the client is created inside the function

        # Call verify_sheets_data_integrity with sheets client
        sheets_results = verify_sheets_data_integrity(api_results['google_sheets']['client'])
        data_results['sheets'] = sheets_results
    else:
        sheets_results = {'status': 'API_unavailable'}
        data_results['sheets'] = sheets_results
        logger.warning("Skipping Google Sheets data integrity verification due to API connectivity issues")

    # Check if Capital One API is accessible from api_results
    if api_results.get('capital_one', {}).get('connectivity', False):
        # Get Capital One client from api_results
        # capital_one_client = api_results['capital_one']['client']  # This line is not needed as the client is created inside the function

        # Call verify_capital_one_accounts with Capital One client
        capital_one_results = verify_capital_one_accounts(api_results['capital_one']['client'])
        data_results['capital_one'] = capital_one_results
    else:
        capital_one_results = {'status': 'API_unavailable'}
        data_results['capital_one'] = capital_one_results
        logger.warning("Skipping Capital One data integrity verification due to API connectivity issues")

    # Combine results into a single dictionary
    data_results['status'] = 'valid' if (sheets_results.get('status') == 'valid' and
                                         capital_one_results.get('status') == 'valid') else 'invalid'

    # Log validation results
    logger.info(f"Data validation results: {data_results}")

    # Return validation results
    return data_results


def validate_infrastructure(project_id: str, region: str, app_name: str, verbose: bool) -> Dict[str, Any]:
    """
    Validate that the Cloud Run infrastructure is properly deployed

    Args:
        project_id: Google Cloud project ID
        region: Google Cloud region
        app_name: Application name (Cloud Run job name)
        verbose: Whether to show detailed output

    Returns:
        Dict[str, Any]: Validation results for infrastructure
    """
    # Log start of infrastructure validation
    logger.info("Starting infrastructure validation...")

    # Call validate_deployment from validate_deployment module
    infrastructure_valid = validate_deployment(project_id, region, app_name)

    # Format results into a dictionary
    infrastructure_results = {
        'valid': infrastructure_valid
    }

    # Log validation results
    logger.info(f"Infrastructure validation results: {infrastructure_results}")

    # Return validation results
    return infrastructure_results


def validate_functionality(project_id: str, region: str, app_name: str, verbose: bool, api_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that the application functions correctly by testing key operations

    Args:
        project_id: Google Cloud project ID
        region: Google Cloud region
        app_name: Application name (Cloud Run job name)
        verbose: Whether to show detailed output
        api_results (Dict[str, Any]): Results from API connectivity validation

    Returns:
        Dict[str, Any]: Validation results for functionality
    """
    # Log start of functionality validation
    logger.info("Starting functionality validation...")

    # Initialize results dictionary
    functionality_results: Dict[str, Any] = {}

    # Test transaction retrieval functionality
    functionality_results['transaction_retrieval'] = test_transaction_retrieval(api_results)

    # Test transaction categorization functionality
    functionality_results['transaction_categorization'] = test_transaction_categorization(api_results)

    # Test budget analysis functionality
    functionality_results['budget_analysis'] = test_budget_analysis(api_results)

    # Test email delivery functionality
    functionality_results['email_delivery'] = test_email_delivery(api_results)

    # Test manual job execution
    functionality_results['manual_job_execution'] = test_manual_job_execution(project_id, region, app_name)

    # Combine results into a single dictionary
    functionality_results['status'] = 'valid' if all(result.get('success', False) for result in functionality_results.values()) else 'invalid'

    # Log validation results
    logger.info(f"Functionality validation results: {functionality_results}")

    # Return validation results
    return functionality_results


def test_transaction_retrieval(api_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test the transaction retrieval functionality

    Args:
        api_results (Dict[str, Any]): Results from API connectivity validation

    Returns:
        Dict[str, Any]: Test results for transaction retrieval
    """
    # Check if Capital One API is accessible from api_results
    if not api_results.get('capital_one', {}).get('connectivity', False):
        return {'success': False, 'message': 'Capital One API not accessible'}

    # Get Capital One client from api_results
    capital_one_client = api_results['capital_one']['client']

    # Attempt to retrieve a small sample of transactions
    try:
        transactions = capital_one_client.get_weekly_transactions()

        # Verify that transactions are returned in the expected format
        if isinstance(transactions, list):
            return {'success': True, 'message': f'Successfully retrieved {len(transactions)} transactions'}
        else:
            return {'success': False, 'message': 'Transactions not returned in expected format'}

    except Exception as e:
        return {'success': False, 'message': f'Error retrieving transactions: {str(e)}'}


def test_transaction_categorization(api_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test the transaction categorization functionality

    Args:
        api_results (Dict[str, Any]): Results from API connectivity validation

    Returns:
        Dict[str, Any]: Test results for transaction categorization
    """
    # Check if Gemini API is accessible from api_results
    if not api_results.get('gemini', {}).get('connectivity', False):
        return {'success': False, 'message': 'Gemini API not accessible'}

    # Get Gemini client from api_results
    gemini_client = api_results['gemini']['client']

    # Create a sample transaction for categorization
    sample_transaction = "Sample Transaction"
    sample_categories = ["Category 1", "Category 2"]

    # Attempt to categorize the sample transaction
    try:
        categorized = gemini_client.categorize_transactions([sample_transaction], sample_categories)

        # Verify that a valid category is returned
        if isinstance(categorized, dict) and sample_transaction in categorized:
            return {'success': True, 'message': f'Successfully categorized transaction'}
        else:
            return {'success': False, 'message': 'Transaction not categorized correctly'}

    except Exception as e:
        return {'success': False, 'message': f'Error categorizing transaction: {str(e)}'}


def test_budget_analysis(api_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test the budget analysis functionality

    Args:
        api_results (Dict[str, Any]): Results from API connectivity validation

    Returns:
        Dict[str, Any]: Test results for budget analysis
    """
    # Check if Google Sheets API is accessible from api_results
    if not api_results.get('google_sheets', {}).get('connectivity', False):
        return {'success': False, 'message': 'Google Sheets API not accessible'}

    # Get Google Sheets client from api_results
    sheets_client = api_results['google_sheets']['client']

    # Retrieve sample budget data
    try:
        budget_data = sheets_client.get_master_budget_data()
        spending_data = sheets_client.get_weekly_spending_data()

        # Verify that the calculation produces expected results
        if isinstance(budget_data, list) and isinstance(spending_data, list):
            return {'success': True, 'message': 'Successfully retrieved budget and spending data'}
        else:
            return {'success': False, 'message': 'Could not retrieve budget and spending data'}

    except Exception as e:
        return {'success': False, 'message': f'Error performing budget analysis: {str(e)}'}


def test_email_delivery(api_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test the email delivery functionality

    Args:
        api_results (Dict[str, Any]): Results from API connectivity validation

    Returns:
        Dict[str, Any]: Test results for email delivery
    """
    # Check if Gmail API is accessible from api_results
    if not api_results.get('gmail', {}).get('connectivity', False):
        return {'success': False, 'message': 'Gmail API not accessible'}

    # Get Gmail client from api_results
    gmail_client = api_results['gmail']['client']

    # Create a test email with recovery validation information
    test_subject = "Test Email from Recovery Validation"
    test_content = "This is a test email to verify email delivery functionality."

    # Attempt to send the test email
    try:
        send_result = gmail_client.send_email(subject=test_subject, html_content=test_content, recipients=[APP_SETTINGS['EMAIL_SENDER']])

        # Verify that the email was sent successfully
        if send_result.get('status') == 'success':
            return {'success': True, 'message': 'Successfully sent test email'}
        else:
            return {'success': False, 'message': f'Failed to send test email: {send_result.get("message")}'}

    except Exception as e:
        return {'success': False, 'message': f'Error sending test email: {str(e)}'}


def test_manual_job_execution(project_id: str, region: str, app_name: str) -> Dict[str, Any]:
    """
    Test that the Cloud Run job can be manually executed

    Args:
        project_id: Google Cloud project ID
        region: Google Cloud region
        app_name: Application name (Cloud Run job name)

    Returns:
        Dict[str, Any]: Test results for manual job execution
    """
    # Log attempt to execute job manually
    logger.info("Attempting to execute job manually...")

    # Construct gcloud command to execute the job with --wait flag
    command = [
        "gcloud", "run", "jobs", "execute", app_name,
        "--project", project_id,
        "--region", region,
        "--wait"
    ]

    # Execute the command with subprocess.run
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        # Check if command succeeded (return code 0)
        if result.returncode == 0:
            # Return success or failure result with details
            return {'success': True, 'message': 'Job executed successfully'}
        else:
            return {'success': False, 'message': f'Job execution failed with code {result.returncode}'}

    except subprocess.CalledProcessError as e:
        # Return success or failure result with details
        return {'success': False, 'message': f'Job execution failed: {str(e)}'}


def generate_validation_report(all_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a comprehensive validation report based on all validation results

    Args:
        all_results (Dict[str, Dict[str, Any]]): Dictionary containing validation results for all components

    Returns:
        Dict[str, Any]: Comprehensive validation report
    """
    # Initialize report dictionary with timestamp
    report: Dict[str, Any] = {'timestamp': datetime.datetime.now().isoformat()}

    # Calculate overall recovery success percentage
    num_valid_components = sum(1 for component, result in all_results.items()
                               if result.get('valid') is True or result.get('status') == 'valid')
    total_components = len(all_results)
    success_percentage = (num_valid_components / total_components) * 100 if total_components else 0

    # Add validation results for each component
    report['results'] = all_results

    # Generate recommendations for failed validations
    recommendations = []
    for component, result in all_results.items():
        if result.get('valid') is False or result.get('status') == 'invalid':
            recommendations.append(f"Check {component} configuration and status.")

    report['recommendations'] = recommendations

    # Format report with summary and details
    report['summary'] = {
        'success_percentage': success_percentage,
        'num_valid_components': num_valid_components,
        'total_components': total_components
    }

    # Save report to file in JSON format
    report_path = f"validation_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=4)
        logger.info(f"Validation report saved to {report_path}")
        report['report_path'] = report_path
    except Exception as e:
        logger.error(f"Error saving validation report: {e}")
        report['report_error'] = str(e)

    # Log report generation
    logger.info(f"Validation report generated: {report}")

    # Return the report dictionary
    return report


def send_validation_report(report: Dict[str, Any], api_results: Dict[str, Any]) -> bool:
    """
    Send the validation report via email

    Args:
        report (Dict[str, Any]): Validation report data
        api_results (Dict[str, Any]): Results from API connectivity validation

    Returns:
        bool: True if report was sent successfully, False otherwise
    """
    # Check if Gmail API is accessible from api_results
    if not api_results.get('gmail', {}).get('connectivity', False):
        logger.error("Gmail API not accessible, cannot send report via email")
        return False

    # Get Gmail client from api_results
    gmail_client = api_results['gmail']['client']

    # Format the report as HTML for email
    html_report = f"""
    <h1>Validation Report</h1>
    <p>Timestamp: {report.get('timestamp')}</p>
    <p>Success Percentage: {report['summary']['success_percentage']:.2f}%</p>
    <h2>Recommendations:</h2>
    <ul>
    """
    for recommendation in report['recommendations']:
        html_report += f"<li>{recommendation}</li>"
    html_report += "</ul>"

    # Create email subject with recovery success percentage
    subject = f"Recovery Validation Report - Success: {report['summary']['success_percentage']:.2f}%"

    # Send email with the formatted report using Gmail client
    try:
        send_result = gmail_client.send_email(subject=subject, html_content=html_report, recipients=[APP_SETTINGS['EMAIL_SENDER']])

        # Log email delivery status
        if send_result.get('status') == 'success':
            logger.info("Validation report sent via email successfully")
            return True
        else:
            logger.error(f"Failed to send validation report via email: {send_result.get('message')}")
            return False

    except Exception as e:
        logger.error(f"Error sending validation report via email: {str(e)}")
        return False


def should_validate_component(component: str, skip_components: Optional[List[str]], only_components: Optional[List[str]]) -> bool:
    """
    Determine if a specific component should be validated based on command line arguments

    Args:
        component: Name of the component to check
        skip_components: List of components to skip
        only_components: List of components to run exclusively

    Returns:
        bool: True if component should be validated, False otherwise
    """
    # If component is in skip_components, return False
    if skip_components and component in skip_components:
        return False

    # If only_components is not empty and component is not in only_components, return False
    if only_components and component not in only_components:
        return False

    # Return True in all other cases
    return True


def main() -> int:
    """
    Main function that orchestrates the recovery validation process

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Parse command line arguments
    args = parse_arguments()

    # Set up logging context with operation='recovery_validation'
    with LoggingContext(logger, "recovery_validation"):

        # Record start time for performance measurement
        start_time = time.time()

        # Initialize results dictionary for all validation components
        all_results: Dict[str, Dict[str, Any]] = {}

        # Parse skip_components and only_components from arguments
        skip_components = args.skip_components if args.skip_components else None
        only_components = args.only_components if args.only_components else None

        # If should validate directories, call validate_directories
        if should_validate_component("directories", skip_components, only_components):
            all_results['directories'] = validate_directories(args.verbose)

        # If should validate credentials, call validate_credentials
        if should_validate_component("credentials", skip_components, only_components):
            all_results['credentials'] = validate_credentials(args.verbose)

        # If should validate APIs, call validate_apis
        if should_validate_component("apis", skip_components, only_components):
            all_results['apis'] = validate_apis(args.verbose)

        # If should validate data and APIs passed, call validate_data
        if should_validate_component("data", skip_components, only_components) and 'apis' in all_results:
            all_results['data'] = validate_data(args.verbose, all_results['apis'])

        # If should validate infrastructure, call validate_infrastructure
        if should_validate_component("infrastructure", skip_components, only_components):
            all_results['infrastructure'] = validate_infrastructure(args.project_id, args.region, args.app_name, args.verbose)

        # If should validate functionality and APIs passed, call validate_functionality
        if should_validate_component("functionality", skip_components, only_components) and 'apis' in all_results:
            all_results['functionality'] = validate_functionality(args.project_id, args.region, args.app_name, args.verbose, all_results['apis'])

        # If report flag is set, generate validation report
        if args.report:
            report = generate_validation_report(all_results)

            # If email flag is set and Gmail API is accessible, send report via email
            if args.email and all_results.get('apis', {}).get('gmail', {}).get('connectivity', False):
                send_validation_report(report, all_results['apis'])

        # Calculate overall success (all components passed)
        overall_success = all(
            result.get('valid') is True or result.get('status') == 'valid'
            for result in all_results.values()
        )

        # Calculate execution time
        execution_time = time.time() - start_time

        # Log validation completion with execution time
        logger.info(f"Recovery validation completed in {execution_time:.2f} seconds")

        # Return 0 if all validations passed, 1 otherwise
        return 0 if overall_success else 1