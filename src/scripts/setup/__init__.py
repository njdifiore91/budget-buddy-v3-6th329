#!/usr/bin/env python3
"""
Initialization module for the setup package that provides centralized access to all setup-related functions for the Budget Management Application. 

This module exports functions for configuring API credentials, initializing Google Sheets, and verifying API access to ensure the application is properly configured for execution.
"""

import os  # standard library
import sys  # standard library
from typing import Dict, List, Optional, Union, Any  # standard library

# Internal imports
from .configure_credentials import configure_capital_one  # src/scripts/setup/configure_credentials.py
from .configure_credentials import configure_google_sheets  # src/scripts/setup/configure_credentials.py
from .configure_credentials import configure_gemini  # src/scripts/setup/configure_credentials.py
from .configure_credentials import configure_gmail  # src/scripts/setup/configure_credentials.py
from .configure_credentials import update_env_file  # src/scripts/setup/configure_credentials.py
from .configure_credentials import validate_json_file  # src/scripts/setup/configure_credentials.py
from .initialize_sheets import initialize_master_budget  # src/scripts/setup/initialize_sheets.py
from .initialize_sheets import initialize_weekly_spending  # src/scripts/setup/initialize_sheets.py
from .initialize_sheets import validate_sheets  # src/scripts/setup/initialize_sheets.py
from .verify_api_access import verify_capital_one_access  # src/scripts/setup/verify_api_access.py
from .verify_api_access import verify_google_sheets_access  # src/scripts/setup/verify_api_access.py
from .verify_api_access import verify_gemini_access  # src/scripts/setup/verify_api_access.py
from .verify_api_access import verify_gmail_access  # src/scripts/setup/verify_api_access.py
from .verify_api_access import verify_all_api_access  # src/scripts/setup/verify_api_access.py
from ..config.logging_setup import get_script_logger  # src/scripts/config/logging_setup.py

__version__ = "1.0.0"
"""Current version of the setup package"""

__author__ = "Budget Management Application Team"
"""Author information for the setup package"""

logger = get_script_logger('setup')
"""Logger for the setup package"""


def setup_environment(force: bool, non_interactive: bool, verify: bool) -> bool:
    """
    Comprehensive setup function that configures all aspects of the application environment

    Args:
        force (bool): Whether to force overwrite of existing configurations
        non_interactive (bool): Whether to run in non-interactive mode
        verify (bool): Whether to verify API access after configuration

    Returns:
        bool: True if setup was successful, False otherwise
    """
    logger.info("Starting environment setup")

    # Configure API credentials for all services
    credentials_success = configure_all_credentials(force, non_interactive)

    # Initialize Google Sheets for budget and transaction data
    sheets_success = initialize_all_sheets(force)

    # Verify API access if verify flag is set
    if verify:
        api_success = verify_all_apis()
    else:
        api_success = True

    logger.info("Completed environment setup")

    # Return True if all steps were successful, False otherwise
    return credentials_success and sheets_success and api_success


def configure_all_credentials(force: bool, non_interactive: bool) -> bool:
    """
    Configure credentials for all required external APIs

    Args:
        force (bool): Whether to force overwrite of existing credentials
        non_interactive (bool): Whether to run in non-interactive mode

    Returns:
        bool: True if all credential configurations were successful, False otherwise
    """
    logger.info("Starting credential configuration")

    # Configure Capital One API credentials
    capital_one_success = configure_capital_one(force, non_interactive)

    # Configure Google Sheets API credentials
    google_sheets_success = configure_google_sheets(force, non_interactive)

    # Configure Gemini AI API credentials
    gemini_success = configure_gemini(force, non_interactive)

    # Configure Gmail API credentials
    gmail_success = configure_gmail(force, non_interactive)

    logger.info("Completed credential configuration")

    # Return True if all configurations were successful, False otherwise
    return (
        capital_one_success and
        google_sheets_success and
        gemini_success and
        gmail_success
    )


def initialize_all_sheets(force: bool, spreadsheet_id: str = None) -> bool:
    """
    Initialize all required Google Sheets for the application

    Args:
        force (bool): Whether to force overwrite of existing sheets
        spreadsheet_id (str): The ID of the spreadsheet to initialize

    Returns:
        bool: True if all sheet initializations were successful, False otherwise
    """
    logger.info("Starting sheet initialization")

    # Initialize Master Budget sheet with default categories and amounts
    master_success = initialize_master_budget(force=force, spreadsheet_id=spreadsheet_id)

    # Initialize Weekly Spending sheet with appropriate headers
    weekly_success = initialize_weekly_spending(force=force, spreadsheet_id=spreadsheet_id)

    # Validate that both sheets have the expected structure
    validation_success = validate_sheets()

    logger.info("Completed sheet initialization")

    # Return True if all initializations were successful, False otherwise
    return master_success and weekly_success and validation_success


def verify_all_apis(verbose: bool = False) -> bool:
    """
    Verify access to all required external APIs

    Args:
        verbose (bool): Whether to display verbose output

    Returns:
        bool: True if all API verifications were successful, False otherwise
    """
    logger.info("Starting API verification")

    # Call verify_all_api_access function from verify_api_access module
    verification_results = verify_all_api_access(verbose=verbose)

    # Log verification results
    if verification_results['overall_status'] == 'success':
        logger.info("All API verifications succeeded")
        success = True
    else:
        logger.warning("Some API verifications failed")
        success = False

    logger.info("Completed API verification")

    # Return True if all verifications were successful, False otherwise
    return success