#!/usr/bin/env python3
"""
Script for rotating API credentials used by the Budget Management Application.
Provides functionality to update and verify credentials for Capital One, Google Sheets,
Gemini AI, and Gmail APIs on a regular schedule to enhance security.
"""

import os
import sys
import argparse
import datetime
import json
from typing import Dict, List, Optional, Union, Any
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Internal imports
from ..config.logging_setup import get_logger, LoggingContext
from ..config.script_settings import MAINTENANCE_SETTINGS
from ..config.path_constants import CREDENTIALS_DIR, ENV_FILE
from ..setup.configure_credentials import (
    configure_capital_one,
    configure_google_sheets,
    configure_gemini,
    configure_gmail,
    update_env_file
)
from ..setup.verify_api_access import (
    verify_capital_one_access,
    verify_google_sheets_access,
    verify_gemini_access,
    verify_gmail_access
)

# Set up logger
logger = get_logger('rotate_credentials')

# Global constants
ROTATION_HISTORY_FILE = os.path.join(CREDENTIALS_DIR, 'rotation_history.json')
BACKUP_DIR = os.path.join(CREDENTIALS_DIR, 'backups')

def parse_arguments():
    """
    Parse command-line arguments for the credential rotation script
    
    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Rotate API credentials for the Budget Management Application"
    )
    
    parser.add_argument(
        "--service", "-s",
        choices=["capital_one", "google_sheets", "gemini", "gmail"],
        help="Rotate only the specified service (default: all services as needed)"
    )
    
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force rotation regardless of interval"
    )
    
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip verification after rotation"
    )
    
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip backup of current credentials"
    )
    
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="Skip email notification"
    )
    
    return parser.parse_args()

def load_rotation_history():
    """
    Load credential rotation history from JSON file
    
    Returns:
        Dict[str, Any]: Rotation history dictionary
    """
    try:
        if os.path.exists(ROTATION_HISTORY_FILE):
            with open(ROTATION_HISTORY_FILE, 'r') as f:
                return json.load(f)
        else:
            # Create default history structure
            return {
                "capital_one": {"last_rotation": None, "success": False},
                "google_sheets": {"last_rotation": None, "success": False},
                "gemini": {"last_rotation": None, "success": False},
                "gmail": {"last_rotation": None, "success": False},
                "last_updated": datetime.datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Error loading rotation history: {e}")
        return {
            "capital_one": {"last_rotation": None, "success": False},
            "google_sheets": {"last_rotation": None, "success": False},
            "gemini": {"last_rotation": None, "success": False},
            "gmail": {"last_rotation": None, "success": False},
            "last_updated": datetime.datetime.now().isoformat()
        }

def save_rotation_history(history: Dict[str, Any]):
    """
    Save credential rotation history to JSON file
    
    Args:
        history: Rotation history dictionary
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        # Ensure credentials directory exists
        os.makedirs(os.path.dirname(ROTATION_HISTORY_FILE), exist_ok=True)
        
        # Update last_updated timestamp
        history["last_updated"] = datetime.datetime.now().isoformat()
        
        # Write history to file
        with open(ROTATION_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
        
        logger.info(f"Rotation history saved to {ROTATION_HISTORY_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error saving rotation history: {e}")
        return False

def backup_credentials(service_name: str):
    """
    Backup current credentials before rotation
    
    Args:
        service_name: Name of the service to backup
        
    Returns:
        bool: True if backup was successful, False otherwise
    """
    try:
        # Create timestamp for backup filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Ensure backup directory exists
        os.makedirs(BACKUP_DIR, exist_ok=True)
        
        # Determine which files to backup based on service
        files_to_backup = []
        
        if service_name == "capital_one":
            capital_one_file = os.path.join(CREDENTIALS_DIR, 'capital_one_credentials.json')
            if os.path.exists(capital_one_file):
                files_to_backup.append(capital_one_file)
        
        elif service_name == "google_sheets":
            sheets_file = os.path.join(CREDENTIALS_DIR, 'sheets_credentials.json')
            if os.path.exists(sheets_file):
                files_to_backup.append(sheets_file)
        
        elif service_name == "gmail":
            gmail_file = os.path.join(CREDENTIALS_DIR, 'gmail_credentials.json')
            if os.path.exists(gmail_file):
                files_to_backup.append(gmail_file)
        
        elif service_name == "gemini":
            # Gemini API key is stored in .env file, backup the entire file
            if os.path.exists(ENV_FILE):
                files_to_backup.append(ENV_FILE)
        
        # No files to backup
        if not files_to_backup:
            logger.warning(f"No credential files found to backup for {service_name}")
            return True
        
        # Backup each file
        for file_path in files_to_backup:
            file_name = os.path.basename(file_path)
            backup_path = os.path.join(BACKUP_DIR, f"{file_name}.{service_name}.{timestamp}")
            
            with open(file_path, 'r') as src, open(backup_path, 'w') as dst:
                dst.write(src.read())
            
            logger.info(f"Backed up {file_path} to {backup_path}")
        
        return True
    except Exception as e:
        logger.error(f"Error backing up credentials for {service_name}: {e}")
        return False

def should_rotate_credentials(service_name: str, history: Dict[str, Any], force: bool):
    """
    Check if credentials should be rotated based on history and interval
    
    Args:
        service_name: Name of the service to check
        history: Rotation history dictionary
        force: Force rotation regardless of interval
        
    Returns:
        bool: True if credentials should be rotated, False otherwise
    """
    # Force rotation if requested
    if force:
        logger.info(f"Forcing rotation of {service_name} credentials")
        return True
    
    # Get last rotation timestamp
    service_history = history.get(service_name, {})
    last_rotation = service_history.get("last_rotation")
    
    # If never rotated, rotate now
    if last_rotation is None:
        logger.info(f"{service_name} credentials have never been rotated")
        return True
    
    # Calculate days since last rotation
    try:
        last_rotation_date = datetime.datetime.fromisoformat(last_rotation)
        days_since_rotation = (datetime.datetime.now() - last_rotation_date).days
        
        # Get rotation interval from settings
        rotation_interval = MAINTENANCE_SETTINGS["CREDENTIAL_ROTATION_INTERVAL"]
        
        # Check if interval has passed
        if days_since_rotation >= rotation_interval:
            logger.info(f"{service_name} credentials were last rotated {days_since_rotation} days ago, exceeding the {rotation_interval} day interval")
            return True
        else:
            logger.info(f"{service_name} credentials were rotated {days_since_rotation} days ago, which is within the {rotation_interval} day interval")
            return False
    except Exception as e:
        logger.error(f"Error checking rotation interval for {service_name}: {e}")
        # Default to requiring rotation on error
        return True

def rotate_capital_one_credentials(verify: bool):
    """
    Rotate Capital One API credentials
    
    Args:
        verify: Whether to verify credentials after rotation
        
    Returns:
        bool: True if rotation was successful, False otherwise
    """
    logger.info("Starting Capital One credential rotation")
    
    try:
        with LoggingContext(logger, "rotate_capital_one_credentials"):
            # Configure new credentials (force=True to overwrite existing)
            config_result = configure_capital_one(force=True, non_interactive=True)
            
            if not config_result:
                logger.error("Failed to configure Capital One credentials")
                return False
            
            # Verify credentials if requested
            if verify:
                verify_result = verify_capital_one_access(verbose=False, use_mocks=False)
                if verify_result.get('status') != 'success':
                    logger.error("Capital One credentials verification failed", context=verify_result)
                    return False
                else:
                    logger.info("Capital One credentials verified successfully")
            
            logger.info("Capital One credential rotation completed successfully")
            return True
    except Exception as e:
        logger.error(f"Error rotating Capital One credentials: {e}")
        return False

def rotate_google_sheets_credentials(verify: bool):
    """
    Rotate Google Sheets API credentials
    
    Args:
        verify: Whether to verify credentials after rotation
        
    Returns:
        bool: True if rotation was successful, False otherwise
    """
    logger.info("Starting Google Sheets credential rotation")
    
    try:
        with LoggingContext(logger, "rotate_google_sheets_credentials"):
            # Configure new credentials (force=True to overwrite existing)
            config_result = configure_google_sheets(force=True, non_interactive=True)
            
            if not config_result:
                logger.error("Failed to configure Google Sheets credentials")
                return False
            
            # Verify credentials if requested
            if verify:
                verify_result = verify_google_sheets_access(verbose=False, use_mocks=False)
                if verify_result.get('status') != 'success':
                    logger.error("Google Sheets credentials verification failed", context=verify_result)
                    return False
                else:
                    logger.info("Google Sheets credentials verified successfully")
            
            logger.info("Google Sheets credential rotation completed successfully")
            return True
    except Exception as e:
        logger.error(f"Error rotating Google Sheets credentials: {e}")
        return False

def rotate_gemini_credentials(verify: bool):
    """
    Rotate Gemini AI API credentials
    
    Args:
        verify: Whether to verify credentials after rotation
        
    Returns:
        bool: True if rotation was successful, False otherwise
    """
    logger.info("Starting Gemini AI credential rotation")
    
    try:
        with LoggingContext(logger, "rotate_gemini_credentials"):
            # Configure new credentials (force=True to overwrite existing)
            config_result = configure_gemini(force=True, non_interactive=True)
            
            if not config_result:
                logger.error("Failed to configure Gemini AI credentials")
                return False
            
            # Verify credentials if requested
            if verify:
                verify_result = verify_gemini_access(verbose=False, use_mocks=False)
                if verify_result.get('status') != 'success':
                    logger.error("Gemini AI credentials verification failed", context=verify_result)
                    return False
                else:
                    logger.info("Gemini AI credentials verified successfully")
            
            logger.info("Gemini AI credential rotation completed successfully")
            return True
    except Exception as e:
        logger.error(f"Error rotating Gemini AI credentials: {e}")
        return False

def rotate_gmail_credentials(verify: bool):
    """
    Rotate Gmail API credentials
    
    Args:
        verify: Whether to verify credentials after rotation
        
    Returns:
        bool: True if rotation was successful, False otherwise
    """
    logger.info("Starting Gmail credential rotation")
    
    try:
        with LoggingContext(logger, "rotate_gmail_credentials"):
            # Configure new credentials (force=True to overwrite existing)
            config_result = configure_gmail(force=True, non_interactive=True)
            
            if not config_result:
                logger.error("Failed to configure Gmail credentials")
                return False
            
            # Verify credentials if requested
            if verify:
                verify_result = verify_gmail_access(verbose=False, use_mocks=False)
                if verify_result.get('status') != 'success':
                    logger.error("Gmail credentials verification failed", context=verify_result)
                    return False
                else:
                    logger.info("Gmail credentials verified successfully")
            
            logger.info("Gmail credential rotation completed successfully")
            return True
    except Exception as e:
        logger.error(f"Error rotating Gmail credentials: {e}")
        return False

def update_rotation_history(service_name: str, history: Dict[str, Any], success: bool):
    """
    Update rotation history with successful rotation
    
    Args:
        service_name: Name of the service that was rotated
        history: Rotation history dictionary
        success: Whether the rotation was successful
        
    Returns:
        Dict[str, Any]: Updated rotation history
    """
    # Get current timestamp
    now = datetime.datetime.now().isoformat()
    
    # Ensure service exists in history
    if service_name not in history:
        history[service_name] = {"last_rotation": None, "success": False}
    
    # Update history
    history[service_name]["last_rotation"] = now
    history[service_name]["success"] = success
    
    # Save updated history
    save_rotation_history(history)
    
    return history

def send_rotation_notification(rotation_results: Dict[str, Any], recipient_email: str):
    """
    Send email notification about credential rotation results
    
    Args:
        rotation_results: Results of credential rotation
        recipient_email: Email address to send notification to
        
    Returns:
        bool: True if notification was sent successfully, False otherwise
    """
    try:
        # Create email subject with timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        subject = f"Credential Rotation Report - {timestamp}"
        
        # Format rotation results
        email_body = format_rotation_results(rotation_results)
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = os.getenv('EMAIL_SENDER', 'njdifiore@gmail.com')
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # Attach text part
        msg.attach(MIMEText(email_body, 'plain'))
        
        # Send email using Gmail API client from the application
        # This would typically use the Gmail client, but for simplicity we'll use smtplib here
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        
        # Gmail login
        server.login(os.getenv('EMAIL_SENDER'), os.getenv('EMAIL_PASSWORD'))
        
        # Send email
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Rotation notification sent to {recipient_email}")
        return True
    except Exception as e:
        logger.error(f"Error sending rotation notification: {e}")
        return False

def format_rotation_results(results: Dict[str, Any]):
    """
    Format credential rotation results for display or notification
    
    Args:
        results: Rotation results dictionary
        
    Returns:
        str: Formatted rotation results string
    """
    # Initialize output string
    output = "Credential Rotation Results\n"
    output += "==========================\n\n"
    
    # Add timestamp
    output += f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    # Format results for each service
    for service, service_results in results.items():
        if service == "timestamp" or service == "overall_success":
            continue
            
        output += f"Service: {service}\n"
        output += f"Status: {'Success' if service_results.get('success') else 'Failed'}\n"
        
        if 'rotated' in service_results:
            output += f"Rotated: {'Yes' if service_results.get('rotated') else 'No'}\n"
            
        if 'message' in service_results:
            output += f"Message: {service_results.get('message')}\n"
            
        output += "\n"
    
    # Add summary
    successful = sum(1 for service, results in results.items() 
                   if service not in ["timestamp", "overall_success"] and results.get('success'))
    total = sum(1 for service in results if service not in ["timestamp", "overall_success"])
    
    output += f"Summary: {successful}/{total} services rotated successfully\n"
    output += f"Overall Status: {'Success' if results.get('overall_success') else 'Failure'}\n"
    
    return output

def rotate_credentials(service_name: Optional[str] = None, force: bool = False, 
                      verify: bool = True, backup: bool = True):
    """
    Rotate credentials for a specific service or all services
    
    Args:
        service_name: Name of the service to rotate, or None for all services
        force: Force rotation regardless of interval
        verify: Whether to verify credentials after rotation
        backup: Whether to backup current credentials before rotation
        
    Returns:
        Dict[str, Any]: Rotation results for all services
    """
    # Load rotation history
    history = load_rotation_history()
    
    # Initialize results
    results = {
        "timestamp": datetime.datetime.now().isoformat(),
        "overall_success": True
    }
    
    # If specific service requested, only rotate that service
    if service_name:
        # Check if service needs rotation
        if should_rotate_credentials(service_name, history, force):
            # Backup credentials if requested
            if backup:
                backup_credentials(service_name)
            
            # Rotate credentials based on service type
            success = False
            rotated = True
            
            if service_name == "capital_one":
                success = rotate_capital_one_credentials(verify)
            elif service_name == "google_sheets":
                success = rotate_google_sheets_credentials(verify)
            elif service_name == "gemini":
                success = rotate_gemini_credentials(verify)
            elif service_name == "gmail":
                success = rotate_gmail_credentials(verify)
            
            # Update history on success
            if success:
                update_rotation_history(service_name, history, True)
            
            # Add to results
            results[service_name] = {
                "success": success,
                "rotated": rotated,
                "message": "Credentials rotated successfully" if success else "Credential rotation failed"
            }
            
            # Update overall success
            results["overall_success"] = results["overall_success"] and success
        else:
            # No rotation needed
            results[service_name] = {
                "success": True,
                "rotated": False,
                "message": "Rotation not needed at this time"
            }
    else:
        # Rotate all services as needed
        
        # Capital One
        if should_rotate_credentials("capital_one", history, force):
            if backup:
                backup_credentials("capital_one")
            
            success = rotate_capital_one_credentials(verify)
            
            if success:
                update_rotation_history("capital_one", history, True)
            
            results["capital_one"] = {
                "success": success,
                "rotated": True,
                "message": "Credentials rotated successfully" if success else "Credential rotation failed"
            }
            
            results["overall_success"] = results["overall_success"] and success
        else:
            results["capital_one"] = {
                "success": True,
                "rotated": False,
                "message": "Rotation not needed at this time"
            }
        
        # Google Sheets
        if should_rotate_credentials("google_sheets", history, force):
            if backup:
                backup_credentials("google_sheets")
            
            success = rotate_google_sheets_credentials(verify)
            
            if success:
                update_rotation_history("google_sheets", history, True)
            
            results["google_sheets"] = {
                "success": success,
                "rotated": True,
                "message": "Credentials rotated successfully" if success else "Credential rotation failed"
            }
            
            results["overall_success"] = results["overall_success"] and success
        else:
            results["google_sheets"] = {
                "success": True,
                "rotated": False,
                "message": "Rotation not needed at this time"
            }
        
        # Gemini
        if should_rotate_credentials("gemini", history, force):
            if backup:
                backup_credentials("gemini")
            
            success = rotate_gemini_credentials(verify)
            
            if success:
                update_rotation_history("gemini", history, True)
            
            results["gemini"] = {
                "success": success,
                "rotated": True,
                "message": "Credentials rotated successfully" if success else "Credential rotation failed"
            }
            
            results["overall_success"] = results["overall_success"] and success
        else:
            results["gemini"] = {
                "success": True,
                "rotated": False,
                "message": "Rotation not needed at this time"
            }
        
        # Gmail
        if should_rotate_credentials("gmail", history, force):
            if backup:
                backup_credentials("gmail")
            
            success = rotate_gmail_credentials(verify)
            
            if success:
                update_rotation_history("gmail", history, True)
            
            results["gmail"] = {
                "success": success,
                "rotated": True,
                "message": "Credentials rotated successfully" if success else "Credential rotation failed"
            }
            
            results["overall_success"] = results["overall_success"] and success
        else:
            results["gmail"] = {
                "success": True,
                "rotated": False,
                "message": "Rotation not needed at this time"
            }
    
    return results

def main():
    """
    Main function to orchestrate credential rotation
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Parse command-line arguments
    args = parse_arguments()
    
    # Log script start
    logger.info("Starting credential rotation script")
    
    # Rotate credentials
    rotation_results = rotate_credentials(
        service_name=args.service,
        force=args.force,
        verify=not args.no_verify,
        backup=not args.no_backup
    )
    
    # Format and display results
    formatted_results = format_rotation_results(rotation_results)
    print(formatted_results)
    
    # Send notification if enabled
    if not args.no_notify:
        recipient_email = MAINTENANCE_SETTINGS.get("ALERT_EMAIL", "njdifiore@gmail.com")
        send_rotation_notification(rotation_results, recipient_email)
    
    # Log script end
    logger.info("Credential rotation script completed")
    
    # Return exit code based on overall success
    return 0 if rotation_results.get("overall_success", False) else 1

if __name__ == "__main__":
    sys.exit(main())