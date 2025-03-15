#!/usr/bin/env python3
"""
Scheduled script that verifies the validity and expiration status of API credentials
used by the Budget Management Application. Performs regular checks on Capital One,
Google Sheets, Gemini AI, and Gmail API credentials to ensure they are valid and not
approaching expiration, triggering alerts and optional credential rotation when
issues are detected.
"""

import os
import sys
import argparse
import datetime
import json
from typing import Dict, List, Optional, Union, Any, Tuple
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Internal imports
from ..config.logging_setup import get_logger, LoggingContext
from ..config.script_settings import MAINTENANCE_SETTINGS, SCRIPT_SETTINGS
from ...backend.services.authentication_service import AuthenticationService
from ..setup.verify_api_access import (
    verify_capital_one_access,
    verify_google_sheets_access,
    verify_gemini_access,
    verify_gmail_access
)
from ..maintenance.rotate_credentials import rotate_credentials, load_rotation_history

# Set up logger
logger = get_logger('credential_check')

# Global constants
CREDENTIAL_STATUS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'credential_status.json')
SERVICES = ['capital_one', 'google_sheets', 'gemini', 'gmail']

def parse_arguments():
    """
    Parse command-line arguments for the credential check script
    
    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Check status of API credentials for the Budget Management Application"
    )
    
    parser.add_argument(
        "--service", "-s",
        choices=SERVICES,
        help="Check only the specified service (default: all)"
    )
    
    parser.add_argument(
        "--rotate", "-r",
        action="store_true",
        help="Automatically rotate credentials if issues are found"
    )
    
    parser.add_argument(
        "--notify", "-n",
        action="store_true",
        help="Send email notifications about credential status"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Save check results to the specified file"
    )
    
    return parser.parse_args()

def load_credential_status():
    """
    Load previous credential check status from JSON file
    
    Returns:
        Dict[str, Any]: Credential status dictionary or empty dict if file not found
    """
    try:
        if os.path.exists(CREDENTIAL_STATUS_FILE):
            with open(CREDENTIAL_STATUS_FILE, 'r') as f:
                return json.load(f)
        else:
            # Create default status structure
            return {
                "last_check": None,
                "services": {
                    "capital_one": {"status": "unknown", "last_check": None},
                    "google_sheets": {"status": "unknown", "last_check": None},
                    "gemini": {"status": "unknown", "last_check": None},
                    "gmail": {"status": "unknown", "last_check": None}
                }
            }
    except Exception as e:
        logger.error(f"Error loading credential status: {e}")
        return {}

def save_credential_status(status: Dict[str, Any]) -> bool:
    """
    Save credential check status to JSON file
    
    Args:
        status: Credential status dictionary
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(CREDENTIAL_STATUS_FILE), exist_ok=True)
        
        # Write status to file
        with open(CREDENTIAL_STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2)
        
        logger.info(f"Credential status saved to {CREDENTIAL_STATUS_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error saving credential status: {e}")
        return False

def check_credential_expiration(service_name: str, rotation_history: Dict[str, Any]) -> Tuple[str, int]:
    """
    Check if credentials are approaching expiration based on rotation history
    
    Args:
        service_name: Name of the service
        rotation_history: Credential rotation history
        
    Returns:
        Tuple[str, int]: Status ('ok', 'warning', or 'expired') and days until expiration
    """
    try:
        # Get service rotation history
        service_rotation = rotation_history.get(service_name, {})
        last_rotation = service_rotation.get("last_rotation")
        
        # If no rotation history, consider as warning
        if not last_rotation:
            logger.warning(f"No rotation history found for {service_name}")
            return "warning", 0
        
        # Calculate days since last rotation and days until expiration
        last_rotation_date = datetime.datetime.fromisoformat(last_rotation)
        days_since_rotation = (datetime.datetime.now() - last_rotation_date).days
        
        # Get rotation interval from settings
        rotation_interval = MAINTENANCE_SETTINGS["CREDENTIAL_ROTATION_INTERVAL"]
        days_until_expiration = rotation_interval - days_since_rotation
        
        # Determine status based on days until expiration
        if days_until_expiration <= 0:
            status = "expired"
        elif days_until_expiration <= 14:  # Warning if expiring within 2 weeks
            status = "warning"
        else:
            status = "ok"
        
        logger.info(f"{service_name} credentials: {status}, {days_until_expiration} days until expiration")
        return status, days_until_expiration
    
    except Exception as e:
        logger.error(f"Error checking credential expiration for {service_name}: {e}")
        return "warning", 0

def check_credential_validity(service_name: str) -> Dict[str, Any]:
    """
    Check if credentials are valid by testing API access
    
    Args:
        service_name: Name of the service to check
        
    Returns:
        Dict[str, Any]: Validation results with status and details
    """
    logger.info(f"Checking credential validity for {service_name}")
    
    with LoggingContext(logger, "check_credential_validity", context={"service": service_name}):
        try:
            # Call appropriate verification function based on service
            if service_name == "capital_one":
                result = verify_capital_one_access(verbose=False, use_mocks=False)
            elif service_name == "google_sheets":
                result = verify_google_sheets_access(verbose=False, use_mocks=False)
            elif service_name == "gemini":
                result = verify_gemini_access(verbose=False, use_mocks=False)
            elif service_name == "gmail":
                result = verify_gmail_access(verbose=False, use_mocks=False)
            else:
                logger.error(f"Unknown service: {service_name}")
                return {"status": "error", "error": f"Unknown service: {service_name}"}
            
            # Log and return results
            if result.get("status") == "success":
                logger.info(f"{service_name} credential validation succeeded")
            else:
                logger.error(f"{service_name} credential validation failed: {result.get('error', 'Unknown error')}")
            
            return result
        except Exception as e:
            logger.error(f"Error validating credentials for {service_name}: {e}")
            return {"status": "error", "error": str(e)}

def check_all_credentials() -> Dict[str, Dict[str, Any]]:
    """
    Check validity and expiration of all service credentials
    
    Returns:
        Dict[str, Dict[str, Any]]: Check results for all services
    """
    logger.info("Starting credential check for all services")
    
    # Load rotation history
    rotation_history = load_rotation_history()
    
    # Initialize results
    results = {}
    
    # Check each service
    for service in SERVICES:
        # Check validity
        validity_result = check_credential_validity(service)
        
        # Check expiration
        expiration_status, days_until_expiration = check_credential_expiration(service, rotation_history)
        
        # Combine results
        service_result = {
            "validity": {
                "status": validity_result.get("status", "error"),
                "details": validity_result.get("details", {})
            },
            "expiration": {
                "status": expiration_status,
                "days_until_expiration": days_until_expiration
            }
        }
        
        # Add error information if present
        if "error" in validity_result:
            service_result["validity"]["error"] = validity_result["error"]
        
        # Determine overall service status (worst of validity and expiration)
        if validity_result.get("status") != "success" or expiration_status == "expired":
            service_result["status"] = "error"
        elif expiration_status == "warning":
            service_result["status"] = "warning"
        else:
            service_result["status"] = "ok"
        
        # Add to results
        results[service] = service_result
    
    # Calculate overall status
    overall_status = "ok"
    for service, service_result in results.items():
        if service_result["status"] == "error":
            overall_status = "error"
            break
        elif service_result["status"] == "warning" and overall_status != "error":
            overall_status = "warning"
    
    results["overall_status"] = overall_status
    logger.info(f"Credential check completed with overall status: {overall_status}")
    
    return results

def format_check_results(results: Dict[str, Any]) -> str:
    """
    Format credential check results for display or notification
    
    Args:
        results: Check results dictionary
        
    Returns:
        str: Formatted check results string
    """
    # Initialize output
    output = "Credential Check Results\n"
    output += "=======================\n\n"
    
    # Add timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output += f"Timestamp: {timestamp}\n\n"
    
    # Add overall status
    overall_status = results.get("overall_status", "unknown")
    output += f"Overall Status: {overall_status.upper()}\n\n"
    
    # Add results for each service
    for service, service_results in results.items():
        if service == "overall_status":
            continue
            
        output += f"Service: {service}\n"
        output += f"Status: {service_results.get('status', 'unknown').upper()}\n"
        
        # Add validity details
        validity = service_results.get("validity", {})
        output += f"Validity: {validity.get('status', 'unknown').upper()}\n"
        
        if "error" in validity:
            output += f"Error: {validity['error']}\n"
        
        # Add expiration details
        expiration = service_results.get("expiration", {})
        output += f"Expiration: {expiration.get('status', 'unknown').upper()}\n"
        
        if "days_until_expiration" in expiration:
            days = expiration["days_until_expiration"]
            if days > 0:
                output += f"Days until expiration: {days}\n"
            else:
                output += f"Expired {abs(days)} days ago\n"
        
        # Add any handling actions
        if "handling" in service_results:
            handling = service_results["handling"]
            if "action" in handling:
                output += f"Action taken: {handling['action']}\n"
            if "result" in handling:
                output += f"Result: {handling['result']}\n"
        
        output += "\n"
    
    # Add summary
    valid_count = sum(1 for s, r in results.items() 
                     if s != "overall_status" and r.get("validity", {}).get("status") == "success")
    total_count = len(results) - 1  # Exclude overall_status
    
    output += f"Valid credentials: {valid_count}/{total_count}\n"
    
    expiring_count = sum(1 for s, r in results.items() 
                        if s != "overall_status" and r.get("expiration", {}).get("status") in ["warning", "expired"])
    
    if expiring_count > 0:
        output += f"Expiring/expired credentials: {expiring_count}/{total_count}\n"
    
    return output

def send_alert_notification(results: Dict[str, Any], recipient_email: str) -> bool:
    """
    Send email notification about credential check results
    
    Args:
        results: Check results dictionary
        recipient_email: Email address to send notification to
        
    Returns:
        bool: True if notification was sent successfully, False otherwise
    """
    try:
        # Determine if notification should be sent based on status and settings
        overall_status = results.get("overall_status", "error")
        
        if overall_status == "ok":
            # Don't send notification for "ok" status unless requested
            return True
            
        if overall_status == "warning" and not MAINTENANCE_SETTINGS["ALERT_ON_WARNING"]:
            logger.info("Skipping notification for warning status (ALERT_ON_WARNING is disabled)")
            return True
            
        if overall_status == "error" and not MAINTENANCE_SETTINGS["ALERT_ON_ERROR"]:
            logger.info("Skipping notification for error status (ALERT_ON_ERROR is disabled)")
            return True
        
        # Create email subject
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        subject = f"Credential Check Alert - {overall_status.upper()} - {timestamp}"
        
        # Format results
        email_body = format_check_results(results)
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = MAINTENANCE_SETTINGS.get("ALERT_EMAIL", "njdifiore@gmail.com")
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # Add body
        msg.attach(MIMEText(email_body, 'plain'))
        
        # Send email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        
        # Use email credentials from environment or configuration
        email_sender = os.environ.get("EMAIL_SENDER", MAINTENANCE_SETTINGS.get("ALERT_EMAIL", "njdifiore@gmail.com"))
        email_password = os.environ.get("EMAIL_PASSWORD", "")
        
        server.login(email_sender, email_password)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Alert notification sent to {recipient_email}")
        return True
    except Exception as e:
        logger.error(f"Error sending alert notification: {e}")
        return False

def handle_credential_issues(results: Dict[str, Any], auto_rotate: bool) -> Dict[str, Any]:
    """
    Handle detected credential issues by rotating or alerting
    
    Args:
        results: Check results dictionary
        auto_rotate: Whether to automatically rotate credentials
        
    Returns:
        Dict[str, Any]: Handling results with actions taken
    """
    handling_results = {}
    
    for service, service_results in results.items():
        if service == "overall_status":
            continue
            
        # Check if service has issues
        has_validity_issue = service_results.get("validity", {}).get("status") != "success"
        has_expiration_issue = service_results.get("expiration", {}).get("status") in ["warning", "expired"]
        
        if has_validity_issue or has_expiration_issue:
            logger.info(f"Detected credential issues for {service}")
            handling_results[service] = {"issues_detected": True}
            
            # Handle issues based on auto_rotate setting
            if auto_rotate:
                logger.info(f"Attempting to rotate credentials for {service}")
                handling_results[service]["action"] = "rotate"
                
                try:
                    # Call rotation function
                    rotation_result = rotate_credentials(service_name=service, force=True)
                    rotation_success = rotation_result.get(service, {}).get("success", False)
                    
                    handling_results[service]["result"] = "success" if rotation_success else "failed"
                    
                    # If rotation succeeded, verify credentials again
                    if rotation_success:
                        logger.info(f"Credential rotation successful for {service}, verifying new credentials")
                        new_validity = check_credential_validity(service)
                        
                        if new_validity.get("status") == "success":
                            handling_results[service]["verification"] = "success"
                        else:
                            handling_results[service]["verification"] = "failed"
                            handling_results[service]["verification_error"] = new_validity.get("error", "Unknown error")
                    
                except Exception as e:
                    logger.error(f"Error rotating credentials for {service}: {e}")
                    handling_results[service]["result"] = "failed"
                    handling_results[service]["error"] = str(e)
            else:
                logger.info(f"Not rotating credentials for {service} (auto-rotate disabled)")
                handling_results[service]["action"] = "notify"
    
    return handling_results

def update_credential_status(check_results: Dict[str, Any], handling_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update the stored credential status with check results
    
    Args:
        check_results: Credential check results
        handling_results: Results of handling any issues
        
    Returns:
        Dict[str, Any]: Updated credential status
    """
    # Load current status
    current_status = load_credential_status()
    
    # Get current timestamp
    timestamp = datetime.datetime.now().isoformat()
    
    # Update last check timestamp
    current_status["last_check"] = timestamp
    
    # Update each service status
    for service, service_results in check_results.items():
        if service == "overall_status":
            continue
            
        # Ensure service exists in status
        if service not in current_status["services"]:
            current_status["services"][service] = {"status": "unknown", "last_check": None}
        
        # Update service status
        current_status["services"][service]["status"] = service_results.get("status", "unknown")
        current_status["services"][service]["last_check"] = timestamp
        current_status["services"][service]["validity"] = service_results.get("validity", {}).get("status", "unknown")
        current_status["services"][service]["expiration"] = service_results.get("expiration", {}).get("status", "unknown")
        
        if "days_until_expiration" in service_results.get("expiration", {}):
            current_status["services"][service]["days_until_expiration"] = service_results["expiration"]["days_until_expiration"]
        
        # Add handling information if present
        if service in handling_results:
            current_status["services"][service]["handling"] = handling_results[service]
    
    # Save updated status
    save_credential_status(current_status)
    
    return current_status

def save_check_results(results: Dict[str, Any], output_file: str) -> bool:
    """
    Save credential check results to a file
    
    Args:
        results: Check results dictionary
        output_file: Output file path
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        # Add timestamp to results
        results_with_timestamp = results.copy()
        results_with_timestamp["timestamp"] = datetime.datetime.now().isoformat()
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Write results to file
        with open(output_file, 'w') as f:
            json.dump(results_with_timestamp, f, indent=2)
        
        logger.info(f"Check results saved to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving check results: {e}")
        return False

def main():
    """
    Main function to orchestrate credential checking
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Parse command-line arguments
    args = parse_arguments()
    
    logger.info("Starting credential check script")
    
    try:
        # Check service credentials
        if args.service:
            logger.info(f"Checking credentials for {args.service}")
            
            # Check specific service
            validity_result = check_credential_validity(args.service)
            
            # Load rotation history and check expiration
            rotation_history = load_rotation_history()
            expiration_status, days_until_expiration = check_credential_expiration(args.service, rotation_history)
            
            # Combine results
            results = {
                args.service: {
                    "validity": {
                        "status": validity_result.get("status", "error"),
                        "details": validity_result.get("details", {})
                    },
                    "expiration": {
                        "status": expiration_status,
                        "days_until_expiration": days_until_expiration
                    }
                }
            }
            
            # Add error information if present
            if "error" in validity_result:
                results[args.service]["validity"]["error"] = validity_result["error"]
            
            # Determine overall service status
            if validity_result.get("status") != "success" or expiration_status == "expired":
                results[args.service]["status"] = "error"
                results["overall_status"] = "error"
            elif expiration_status == "warning":
                results[args.service]["status"] = "warning"
                results["overall_status"] = "warning"
            else:
                results[args.service]["status"] = "ok"
                results["overall_status"] = "ok"
        else:
            # Check all services
            results = check_all_credentials()
        
        # Handle any credential issues
        handling_results = handle_credential_issues(results, args.rotate)
        
        # Update stored credential status
        updated_status = update_credential_status(results, handling_results)
        
        # Save results to file if specified
        if args.output:
            save_check_results(results, args.output)
        
        # Send notification if requested
        if args.notify:
            recipient_email = MAINTENANCE_SETTINGS.get("ALERT_EMAIL", "njdifiore@gmail.com")
            send_alert_notification(results, recipient_email)
        
        # Print formatted results
        print(format_check_results(results))
        
        logger.info("Credential check script completed")
        
        # Return exit code based on overall status
        return 0 if results.get("overall_status") == "ok" else 1
    
    except Exception as e:
        logger.error(f"Error in credential check script: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())