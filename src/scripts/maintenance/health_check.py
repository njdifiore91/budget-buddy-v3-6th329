"""
Script that performs comprehensive health checks on the Budget Management Application's components and integrations.
Verifies connectivity to external APIs, validates authentication, checks data access, and reports system status.
Used for proactive monitoring and troubleshooting.
"""

import os  # standard library
import sys  # standard library
import argparse  # standard library
import datetime  # standard library
import json  # standard library
import requests  # requests 2.31.0+

# Internal imports
from src.scripts.config.script_settings import MAINTENANCE_SETTINGS  # Access maintenance script configuration settings
from src.scripts.config.logging_setup import get_logger  # Get configured logger for health check script
from src.backend.services.authentication_service import AuthenticationService  # Validate authentication with external APIs
from src.backend.api_clients.capital_one_client import CapitalOneClient  # Test connectivity to Capital One API
from src.backend.api_clients.google_sheets_client import GoogleSheetsClient  # Test connectivity to Google Sheets API
from src.backend.api_clients.gemini_client import GeminiClient  # Test connectivity to Gemini API
from src.backend.api_clients.gmail_client import GmailClient  # Test connectivity to Gmail API
from src.backend.services.error_handling_service import with_error_handling  # Add error handling to health check functions
from src.backend.services.error_handling_service import reset_circuit  # Reset circuit breakers for services
from src.backend.services.error_handling_service import get_circuit_state  # Get circuit breaker state for services

# Initialize logger
logger = get_logger('health_check')

# Define the path for the health check report file
HEALTH_CHECK_REPORT_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'health_check_report.json')


@with_error_handling('health_check', 'check_authentication', {})
def check_authentication() -> dict:
    """
    Checks authentication with all external APIs.

    Returns:
        dict: Authentication status for each service
    """
    # Create AuthenticationService instance
    auth_service = AuthenticationService()

    # Call validate_credentials() to check all API credentials
    auth_status = auth_service.validate_credentials()

    # Log authentication check results
    logger.info(f"Authentication check: {'Passed' if auth_status else 'Failed'}")

    # Return dictionary with authentication status for each service
    return {"authentication_status": auth_status}


@with_error_handling('health_check', 'check_capital_one_connectivity', {})
def check_capital_one_connectivity() -> dict:
    """
    Checks connectivity to Capital One API.

    Returns:
        dict: Connectivity status and details
    """
    # Create AuthenticationService instance
    auth_service = AuthenticationService()

    # Create CapitalOneClient with the authentication service
    capital_one_client = CapitalOneClient(auth_service)

    # Call test_connectivity() to verify API connection
    connectivity_status = capital_one_client.test_connectivity()

    # Log connectivity check results
    logger.info(f"Capital One connectivity check: {'Passed' if connectivity_status else 'Failed'}")

    # Return dictionary with connectivity status and details
    return {"capital_one_connectivity": connectivity_status}


@with_error_handling('health_check', 'check_google_sheets_connectivity', {})
def check_google_sheets_connectivity() -> dict:
    """
    Checks connectivity to Google Sheets API.

    Returns:
        dict: Connectivity status and details
    """
    # Create AuthenticationService instance
    auth_service = AuthenticationService()

    # Create GoogleSheetsClient with the authentication service
    sheets_client = GoogleSheetsClient(auth_service)

    # Call authenticate() to verify API authentication
    auth_status = sheets_client.authenticate()

    # Attempt to read a small range from Master Budget sheet
    try:
        sheets_client.read_sheet(sheets_client.master_budget_id, 'A1:A2')
        read_status = True
    except Exception:
        read_status = False

    # Log connectivity check results
    logger.info(f"Google Sheets connectivity check: {'Passed' if auth_status and read_status else 'Failed'}")

    # Return dictionary with connectivity status and details
    return {"google_sheets_connectivity": auth_status and read_status}


@with_error_handling('health_check', 'check_gemini_connectivity', {})
def check_gemini_connectivity() -> dict:
    """
    Checks connectivity to Gemini AI API.

    Returns:
        dict: Connectivity status and details
    """
    # Create AuthenticationService instance
    auth_service = AuthenticationService()

    # Create GeminiClient with the authentication service
    gemini_client = GeminiClient(auth_service)

    # Call authenticate() to verify API authentication
    auth_status = gemini_client.authenticate()

    # Attempt a simple test completion with the API
    try:
        gemini_client.generate_completion("This is a test prompt.")
        completion_status = True
    except Exception:
        completion_status = False

    # Log connectivity check results
    logger.info(f"Gemini AI connectivity check: {'Passed' if auth_status and completion_status else 'Failed'}")

    # Return dictionary with connectivity status and details
    return {"gemini_connectivity": auth_status and completion_status}


@with_error_handling('health_check', 'check_gmail_connectivity', {})
def check_gmail_connectivity() -> dict:
    """
    Checks connectivity to Gmail API.

    Returns:
        dict: Connectivity status and details
    """
    # Create AuthenticationService instance
    auth_service = AuthenticationService()

    # Create GmailClient with the authentication service
    gmail_client = GmailClient(auth_service)

    # Call is_authenticated() to verify API authentication
    auth_status = gmail_client.is_authenticated()

    # Log connectivity check results
    logger.info(f"Gmail API connectivity check: {'Passed' if auth_status else 'Failed'}")

    # Return dictionary with connectivity status and details
    return {"gmail_connectivity": auth_status}


@with_error_handling('health_check', 'check_circuit_breakers', {})
def check_circuit_breakers() -> dict:
    """
    Checks the status of all circuit breakers.

    Returns:
        dict: Circuit breaker status for each service
    """
    # Get circuit state for Capital One service
    capital_one_circuit = get_circuit_state('CAPITAL_ONE')

    # Get circuit state for Google Sheets service
    google_sheets_circuit = get_circuit_state('GOOGLE_SHEETS')

    # Get circuit state for Gemini service
    gemini_circuit = get_circuit_state('GEMINI')

    # Get circuit state for Gmail service
    gmail_circuit = get_circuit_state('GMAIL')

    # Log circuit breaker status
    logger.info("Circuit breaker status checked")

    # Return dictionary with circuit breaker status for each service
    return {
        "capital_one_circuit": capital_one_circuit['state'],
        "google_sheets_circuit": google_sheets_circuit['state'],
        "gemini_circuit": gemini_circuit['state'],
        "gmail_circuit": gmail_circuit['state']
    }


@with_error_handling('health_check', 'reset_circuit_breakers', {})
def reset_circuit_breakers() -> dict:
    """
    Resets all circuit breakers to closed state.

    Returns:
        dict: Reset status for each service
    """
    # Reset circuit for Capital One service
    capital_one_reset = reset_circuit('CAPITAL_ONE')

    # Reset circuit for Google Sheets service
    google_sheets_reset = reset_circuit('GOOGLE_SHEETS')

    # Reset circuit for Gemini service
    gemini_reset = reset_circuit('GEMINI')

    # Reset circuit for Gmail service
    gmail_reset = reset_circuit('GMAIL')

    # Log circuit breaker reset results
    logger.info("Circuit breakers reset")

    # Return dictionary with reset status for each service
    return {
        "capital_one_reset": capital_one_reset,
        "google_sheets_reset": google_sheets_reset,
        "gemini_reset": gemini_reset,
        "gmail_reset": gmail_reset
    }


def generate_health_report() -> dict:
    """
    Generates a comprehensive health check report.

    Returns:
        dict: Complete health check report
    """
    # Create report dictionary with timestamp
    report = {"timestamp": datetime.datetime.now().isoformat()}

    # Add authentication status from check_authentication()
    report.update(check_authentication())

    # Add Capital One connectivity status from check_capital_one_connectivity()
    report.update(check_capital_one_connectivity())

    # Add Google Sheets connectivity status from check_google_sheets_connectivity()
    report.update(check_google_sheets_connectivity())

    # Add Gemini connectivity status from check_gemini_connectivity()
    report.update(check_gemini_connectivity())

    # Add Gmail connectivity status from check_gmail_connectivity()
    report.update(check_gmail_connectivity())

    # Add circuit breaker status from check_circuit_breakers()
    report.update(check_circuit_breakers())

    # Calculate overall system health status
    overall_health = (
        report["authentication_status"]
        and report["capital_one_connectivity"]
        and report["google_sheets_connectivity"]
        and report["gemini_connectivity"]
        and report["gmail_connectivity"]
    )
    report["overall_health"] = overall_health

    # Log health report generation
    logger.info("Health report generated")

    # Return the complete health report
    return report


@with_error_handling('health_check', 'save_health_report', {})
def save_health_report(report: dict) -> bool:
    """
    Saves the health check report to a JSON file.

    Args:
        report (dict): report

    Returns:
        bool: True if save was successful, False otherwise
    """
    # Ensure the logs directory exists
    os.makedirs(os.path.dirname(HEALTH_CHECK_REPORT_FILE), exist_ok=True)

    # Convert report dictionary to JSON format
    try:
        with open(HEALTH_CHECK_REPORT_FILE, 'w') as f:
            json.dump(report, f, indent=4)
        logger.info(f"Health report saved to {HEALTH_CHECK_REPORT_FILE}")
        return True
    except Exception as e:
        logger.error(f"Failed to save health report: {str(e)}")
        return False


@with_error_handling('health_check', 'send_alert_email', {})
def send_alert_email(report: dict) -> bool:
    """
    Sends an alert email if health check detects issues.

    Args:
        report (dict): report

    Returns:
        bool: True if email was sent, False otherwise
    """
    # Check if alert should be sent based on report status and ALERT settings
    alert_on_warning = MAINTENANCE_SETTINGS.get('ALERT_ON_WARNING', True)
    alert_on_error = MAINTENANCE_SETTINGS.get('ALERT_ON_ERROR', True)
    alert_email = MAINTENANCE_SETTINGS.get('ALERT_EMAIL', 'njdifiore@gmail.com')

    # Determine if an alert is needed
    send_alert = False
    if not report["overall_health"] and alert_on_error:
        send_alert = True
    elif (
        report["capital_one_circuit"] == "OPEN"
        or report["google_sheets_circuit"] == "OPEN"
        or report["gemini_circuit"] == "OPEN"
        or report["gmail_circuit"] == "OPEN"
    ) and alert_on_warning:
        send_alert = True

    # If alert needed, create GmailClient
    if send_alert:
        try:
            auth_service = AuthenticationService()
            gmail_client = GmailClient(auth_service)

            # Format email subject with health status
            subject = f"Budget Management Health Check: {'FAILED' if not report['overall_health'] else 'Warning'}"

            # Format email body with health report details
            body = f"Health Check Report:\n\n{json.dumps(report, indent=4)}"

            # Send email to ALERT_EMAIL address
            gmail_client.send_email(subject, body, [alert_email])

            # Log alert email sending
            logger.info(f"Alert email sent to {alert_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send alert email: {str(e)}")
            return False
    else:
        logger.info("No alert email needed")
        return False


def parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments for the health check script.

    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    # Create ArgumentParser with description
    parser = argparse.ArgumentParser(description="Run health checks for the Budget Management Application.")

    # Add --reset-circuits flag to reset circuit breakers
    parser.add_argument(
        "--reset-circuits", action="store_true", help="Reset all circuit breakers to closed state."
    )

    # Add --email flag to force sending email report
    parser.add_argument(
        "--email", action="store_true", help="Force sending email report even if no issues are detected."
    )

    # Add --verbose flag for detailed output
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output for debugging."
    )

    # Parse and return command-line arguments
    return parser.parse_args()


def main() -> int:
    """
    Main function that runs the health check process.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Parse command-line arguments
    args = parse_arguments()

    # Log start of health check process
    logger.info("Starting health check process")

    # If --reset-circuits flag is set, reset all circuit breakers
    if args.reset_circuits:
        logger.info("Resetting circuit breakers")
        reset_circuit_breakers()

    # Generate health report by calling generate_health_report()
    report = generate_health_report()

    # Save health report to file
    save_health_report(report)

    # If --email flag is set or issues detected, send alert email
    if args.email or not report["overall_health"]:
        logger.info("Sending alert email")
        send_alert_email(report)

    # Log completion of health check process
    logger.info("Health check process completed")

    # Return 0 if all checks passed, 1 if any issues detected
    return 0 if report["overall_health"] else 1


if __name__ == "__main__":
    sys.exit(main())