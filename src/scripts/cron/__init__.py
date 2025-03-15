#!/usr/bin/env python3
"""
Initialization module for the cron package that provides scheduled task
functionality for the Budget Management Application. This module exposes
key functions from the cron submodules to enable scheduled credential
checking, health monitoring, backup operations, and report generation.
"""

# Internal imports
from .credential_check import check_credential_validity  # Import function to check API credential validity
from .credential_check import check_all_credentials  # Import function to check all API credentials
from .credential_check import handle_credential_issues  # Import function to handle credential issues
from .weekly_healthcheck import HealthChecker  # Import class for performing health checks
from .backup_schedule import is_backup_due  # Import function to check if backup is due
from .backup_schedule import perform_backup  # Import function to perform backup operations
from .backup_schedule import get_next_backup_time  # Import function to get next scheduled backup time
from ..config.logging_setup import get_logger  # Import function to get configured logger

# Initialize logger
logger = get_logger('cron')

# Define global variables
__all__ = [
    "check_credential_validity",
    "check_all_credentials",
    "handle_credential_issues",
    "HealthChecker",
    "is_backup_due",
    "perform_backup",
    "get_next_backup_time"
]

# Export functions and classes
__all__ = [
    "check_credential_validity",
    "check_all_credentials",
    "handle_credential_issues",
    "HealthChecker",
    "is_backup_due",
    "perform_backup",
    "get_next_backup_time"
]

# Log initialization of the cron package
logger.info("Cron package initialized")