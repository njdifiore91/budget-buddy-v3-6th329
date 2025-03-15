#!/usr/bin/env python3
"""
Script for configuring and managing API credentials for the Budget Management Application.

This script provides interactive setup for Capital One, Google Sheets, Gemini, and Gmail 
API credentials, with validation and secure storage options. It supports both interactive
and non-interactive modes, with options to verify credentials after configuration.
"""

import os
import sys
import json
import getpass
import argparse
import dotenv

# Internal imports
from ..config.logging_setup import get_script_logger, log_script_start, log_script_end
from ..config.path_constants import CREDENTIALS_DIR, ENV_FILE, ensure_dir_exists
from .verify_api_access import (
    verify_capital_one_access,
    verify_google_sheets_access,
    verify_gemini_access,
    verify_gmail_access
)

# Set up logger
logger = get_script_logger('configure_credentials')

# Constants for credential file locations
CAPITAL_ONE_CREDENTIALS_FILE = os.path.join(CREDENTIALS_DIR, 'capital_one_credentials.json')
GOOGLE_SHEETS_CREDENTIALS_FILE = os.path.join(CREDENTIALS_DIR, 'sheets_credentials.json')
GMAIL_CREDENTIALS_FILE = os.path.join(CREDENTIALS_DIR, 'gmail_credentials.json')

def parse_arguments():
    """
    Parse command-line arguments for the credential configuration script
    
    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Configure API credentials for the Budget Management Application"
    )
    
    parser.add_argument(
        "--service", "-s",
        choices=["capital_one", "google_sheets", "gemini", "gmail"],
        help="Configure only the specified service (default: all)"
    )
    
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify credentials after configuration"
    )
    
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force overwrite of existing credentials"
    )
    
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode using environment variables"
    )
    
    return parser.parse_args()

def validate_json_file(file_path):
    """
    Validate that a file exists and contains valid JSON
    
    Args:
        file_path (str): Path to the JSON file
        
    Returns:
        bool: True if file exists and contains valid JSON, False otherwise
    """
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return False
    
    try:
        with open(file_path, 'r') as f:
            json.load(f)
        
        logger.debug(f"JSON file validated: {file_path}")
        return True
    
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {file_path}: {e}")
        return False
    
    except Exception as e:
        logger.error(f"Error validating JSON file {file_path}: {e}")
        return False

def update_env_file(env_vars, env_file):
    """
    Update environment file with new key-value pairs
    
    Args:
        env_vars (dict): Dictionary of environment variables to update
        env_file (str): Path to the .env file
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        # Ensure the .env file exists
        if not os.path.exists(env_file):
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(env_file), exist_ok=True)
            # Create an empty .env file
            with open(env_file, 'w'):
                pass
        
        # Load existing variables
        dotenv.load_dotenv(env_file)
        existing_vars = {}
        
        # Read existing variables from file
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        existing_vars[key.strip()] = value.strip()
        
        # Update with new variables
        existing_vars.update(env_vars)
        
        # Write all variables back to file
        with open(env_file, 'w') as f:
            for key, value in existing_vars.items():
                f.write(f"{key}={value}\n")
        
        # Reload environment variables
        dotenv.load_dotenv(env_file)
        
        logger.info(f"Updated environment variables in {env_file}")
        return True
    
    except Exception as e:
        logger.error(f"Error updating environment file: {e}")
        return False

def configure_capital_one(force=False, non_interactive=False):
    """
    Configure Capital One API credentials
    
    Args:
        force (bool): Whether to force overwrite of existing credentials
        non_interactive (bool): Whether to run in non-interactive mode
        
    Returns:
        bool: True if configuration was successful, False otherwise
    """
    logger.info("Configuring Capital One API credentials")
    
    # Check if credentials already exist
    if os.path.exists(CAPITAL_ONE_CREDENTIALS_FILE) and not force:
        if non_interactive:
            logger.info("Capital One credentials already exist and force is not enabled. Skipping.")
            return True
        
        response = input("Capital One credentials already exist. Overwrite? (y/n): ")
        if response.lower() != 'y':
            logger.info("Skipping Capital One credential configuration")
            return True
    
    try:
        # Get credentials
        if non_interactive:
            # Use environment variables
            client_id = os.getenv('CAPITAL_ONE_CLIENT_ID')
            client_secret = os.getenv('CAPITAL_ONE_CLIENT_SECRET')
            
            if not client_id or not client_secret:
                logger.error("CAPITAL_ONE_CLIENT_ID or CAPITAL_ONE_CLIENT_SECRET not set in environment")
                return False
        else:
            # Prompt for credentials
            print("\nEnter Capital One API credentials:")
            client_id = input("Client ID: ")
            client_secret = getpass.getpass("Client Secret: ")
            
            if not client_id or not client_secret:
                logger.error("Client ID and Client Secret are required")
                return False
        
        # Create credentials dictionary
        credentials = {
            "client_id": client_id,
            "client_secret": client_secret
        }
        
        # Ensure credentials directory exists
        ensure_dir_exists(CREDENTIALS_DIR)
        
        # Write credentials to file
        with open(CAPITAL_ONE_CREDENTIALS_FILE, 'w') as f:
            json.dump(credentials, f, indent=2)
        
        # Secure the file
        os.chmod(CAPITAL_ONE_CREDENTIALS_FILE, 0o600)
        
        logger.info("Capital One API credentials configured successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error configuring Capital One API credentials: {e}")
        return False

def configure_google_sheets(force=False, non_interactive=False):
    """
    Configure Google Sheets API credentials
    
    Args:
        force (bool): Whether to force overwrite of existing credentials
        non_interactive (bool): Whether to run in non-interactive mode
        
    Returns:
        bool: True if configuration was successful, False otherwise
    """
    logger.info("Configuring Google Sheets API credentials")
    
    # Check if credentials already exist
    if os.path.exists(GOOGLE_SHEETS_CREDENTIALS_FILE) and not force:
        if non_interactive:
            logger.info("Google Sheets credentials already exist and force is not enabled. Skipping.")
            return True
        
        response = input("Google Sheets credentials already exist. Overwrite? (y/n): ")
        if response.lower() != 'y':
            logger.info("Skipping Google Sheets credential configuration")
            return True
    
    try:
        # Get service account credentials file
        if non_interactive:
            # Use environment variables
            creds_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH')
            
            if not creds_path:
                logger.error("GOOGLE_SHEETS_CREDENTIALS_PATH not set in environment")
                return False
        else:
            # Prompt for credentials file
            print("\nEnter Google Sheets API credentials:")
            creds_path = input("Path to service account JSON file: ")
            
            if not creds_path:
                logger.error("Service account JSON file path is required")
                return False
        
        # Validate the JSON file
        if not validate_json_file(creds_path):
            logger.error(f"Invalid service account JSON file: {creds_path}")
            return False
        
        # Ensure credentials directory exists
        ensure_dir_exists(CREDENTIALS_DIR)
        
        # Copy the file to credentials directory
        with open(creds_path, 'r') as src, open(GOOGLE_SHEETS_CREDENTIALS_FILE, 'w') as dst:
            dst.write(src.read())
        
        # Secure the file
        os.chmod(GOOGLE_SHEETS_CREDENTIALS_FILE, 0o600)
        
        # Configure spreadsheet IDs
        if non_interactive:
            weekly_sheet_id = os.getenv('WEEKLY_SPENDING_SHEET_ID')
            master_sheet_id = os.getenv('MASTER_BUDGET_SHEET_ID')
        else:
            weekly_sheet_id = input("Weekly Spending Sheet ID: ")
            master_sheet_id = input("Master Budget Sheet ID: ")
        
        # Update environment variables
        env_vars = {}
        if weekly_sheet_id:
            env_vars['WEEKLY_SPENDING_SHEET_ID'] = weekly_sheet_id
        if master_sheet_id:
            env_vars['MASTER_BUDGET_SHEET_ID'] = master_sheet_id
        
        if env_vars:
            update_env_file(env_vars, ENV_FILE)
        
        logger.info("Google Sheets API credentials configured successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error configuring Google Sheets API credentials: {e}")
        return False

def configure_gemini(force=False, non_interactive=False):
    """
    Configure Gemini AI API credentials
    
    Args:
        force (bool): Whether to force overwrite of existing credentials
        non_interactive (bool): Whether to run in non-interactive mode
        
    Returns:
        bool: True if configuration was successful, False otherwise
    """
    logger.info("Configuring Gemini AI API credentials")
    
    # Check if API key already exists in .env
    dotenv.load_dotenv(ENV_FILE)
    existing_key = os.getenv('GEMINI_API_KEY')
    
    if existing_key and not force:
        if non_interactive:
            logger.info("Gemini API key already exists and force is not enabled. Skipping.")
            return True
        
        response = input("Gemini API key already exists. Overwrite? (y/n): ")
        if response.lower() != 'y':
            logger.info("Skipping Gemini API key configuration")
            return True
    
    try:
        # Get API key
        if non_interactive:
            # Use environment variables
            api_key = os.getenv('GEMINI_API_KEY_INPUT')
            
            if not api_key:
                logger.error("GEMINI_API_KEY_INPUT not set in environment")
                return False
        else:
            # Prompt for API key
            print("\nEnter Gemini AI API credentials:")
            api_key = getpass.getpass("API Key: ")
            
            if not api_key:
                logger.error("API Key is required")
                return False
        
        # Update environment variables
        update_env_file({'GEMINI_API_KEY': api_key}, ENV_FILE)
        
        logger.info("Gemini AI API credentials configured successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error configuring Gemini AI API credentials: {e}")
        return False

def configure_gmail(force=False, non_interactive=False):
    """
    Configure Gmail API credentials
    
    Args:
        force (bool): Whether to force overwrite of existing credentials
        non_interactive (bool): Whether to run in non-interactive mode
        
    Returns:
        bool: True if configuration was successful, False otherwise
    """
    logger.info("Configuring Gmail API credentials")
    
    # Check if credentials already exist
    if os.path.exists(GMAIL_CREDENTIALS_FILE) and not force:
        if non_interactive:
            logger.info("Gmail credentials already exist and force is not enabled. Skipping.")
            return True
        
        response = input("Gmail credentials already exist. Overwrite? (y/n): ")
        if response.lower() != 'y':
            logger.info("Skipping Gmail credential configuration")
            return True
    
    try:
        # Get service account credentials file
        if non_interactive:
            # Use environment variables
            creds_path = os.getenv('GMAIL_CREDENTIALS_PATH')
            
            if not creds_path:
                logger.error("GMAIL_CREDENTIALS_PATH not set in environment")
                return False
        else:
            # Prompt for credentials file
            print("\nEnter Gmail API credentials:")
            creds_path = input("Path to service account JSON file: ")
            
            if not creds_path:
                logger.error("Service account JSON file path is required")
                return False
        
        # Validate the JSON file
        if not validate_json_file(creds_path):
            logger.error(f"Invalid service account JSON file: {creds_path}")
            return False
        
        # Ensure credentials directory exists
        ensure_dir_exists(CREDENTIALS_DIR)
        
        # Copy the file to credentials directory
        with open(creds_path, 'r') as src, open(GMAIL_CREDENTIALS_FILE, 'w') as dst:
            dst.write(src.read())
        
        # Secure the file
        os.chmod(GMAIL_CREDENTIALS_FILE, 0o600)
        
        # Configure email addresses
        if non_interactive:
            email_sender = os.getenv('EMAIL_SENDER')
            email_recipients = os.getenv('EMAIL_RECIPIENTS')
        else:
            email_sender = input("Email sender address (usually a Gmail address): ")
            email_recipients = input("Email recipients (comma-separated list): ")
        
        # Update environment variables
        env_vars = {}
        if email_sender:
            env_vars['EMAIL_SENDER'] = email_sender
        if email_recipients:
            env_vars['EMAIL_RECIPIENTS'] = email_recipients
        
        if env_vars:
            update_env_file(env_vars, ENV_FILE)
        
        logger.info("Gmail API credentials configured successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error configuring Gmail API credentials: {e}")
        return False

def configure_all_credentials(force=False, non_interactive=False):
    """
    Configure credentials for all required APIs
    
    Args:
        force (bool): Whether to force overwrite of existing credentials
        non_interactive (bool): Whether to run in non-interactive mode
        
    Returns:
        bool: True if all configurations were successful, False otherwise
    """
    logger.info("Configuring all API credentials")
    
    # Configure each API's credentials
    capital_one_success = configure_capital_one(force, non_interactive)
    google_sheets_success = configure_google_sheets(force, non_interactive)
    gemini_success = configure_gemini(force, non_interactive)
    gmail_success = configure_gmail(force, non_interactive)
    
    # Return overall success
    all_success = (
        capital_one_success and 
        google_sheets_success and 
        gemini_success and 
        gmail_success
    )
    
    if all_success:
        logger.info("All API credentials configured successfully")
    else:
        logger.warning("Some API credentials were not configured successfully")
    
    return all_success

def verify_credentials():
    """
    Verify that configured credentials work correctly
    
    Returns:
        bool: True if all credentials are valid, False otherwise
    """
    logger.info("Verifying API credentials")
    
    try:
        # Verify each API's credentials
        capital_one_result = verify_capital_one_access(verbose=False, use_mocks=False)
        google_sheets_result = verify_google_sheets_access(verbose=False, use_mocks=False)
        gemini_result = verify_gemini_access(verbose=False, use_mocks=False)
        gmail_result = verify_gmail_access(verbose=False, use_mocks=False)
        
        # Check status of each verification
        capital_one_valid = capital_one_result.get('status') == 'success'
        google_sheets_valid = google_sheets_result.get('status') == 'success'
        gemini_valid = gemini_result.get('status') == 'success'
        gmail_valid = gmail_result.get('status') == 'success'
        
        # Report results
        logger.info(f"Capital One API credentials: {'VALID' if capital_one_valid else 'INVALID'}")
        logger.info(f"Google Sheets API credentials: {'VALID' if google_sheets_valid else 'INVALID'}")
        logger.info(f"Gemini AI API credentials: {'VALID' if gemini_valid else 'INVALID'}")
        logger.info(f"Gmail API credentials: {'VALID' if gmail_valid else 'INVALID'}")
        
        # Return overall validity
        all_valid = capital_one_valid and google_sheets_valid and gemini_valid and gmail_valid
        
        if all_valid:
            logger.info("All API credentials are valid")
        else:
            logger.warning("Some API credentials are invalid")
        
        return all_valid
        
    except Exception as e:
        logger.error(f"Error verifying credentials: {e}")
        return False

def main():
    """
    Main function to orchestrate credential configuration
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Parse command-line arguments
    args = parse_arguments()
    
    # Log script start
    log_script_start()
    
    # Ensure credentials directory exists
    ensure_dir_exists(CREDENTIALS_DIR)
    
    # Configure credentials based on arguments
    success = False
    
    if args.service:
        # Configure only the specified service
        if args.service == 'capital_one':
            success = configure_capital_one(args.force, args.non_interactive)
        elif args.service == 'google_sheets':
            success = configure_google_sheets(args.force, args.non_interactive)
        elif args.service == 'gemini':
            success = configure_gemini(args.force, args.non_interactive)
        elif args.service == 'gmail':
            success = configure_gmail(args.force, args.non_interactive)
    else:
        # Configure all services
        success = configure_all_credentials(args.force, args.non_interactive)
    
    # Verify credentials if requested
    if args.verify and success:
        verification_success = verify_credentials()
        success = success and verification_success
    
    # Log script end
    log_script_end()
    
    # Return exit code
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())