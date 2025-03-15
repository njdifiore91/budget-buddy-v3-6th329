"""
Initialization module for the Budget Management Application's maintenance package.
This module exports functions from various maintenance scripts to provide a unified
interface for system maintenance operations including health checks, credential
rotation, backup procedures, and dependency updates.
"""

# Internal imports
from src.scripts.maintenance.health_check import generate_health_report  # Import health check report generation function
from src.scripts.maintenance.health_check import check_authentication  # Import authentication check function
from src.scripts.maintenance.health_check import check_capital_one_connectivity  # Import Capital One connectivity check function
from src.scripts.maintenance.health_check import check_google_sheets_connectivity  # Import Google Sheets connectivity check function
from src.scripts.maintenance.health_check import check_gemini_connectivity  # Import Gemini API connectivity check function
from src.scripts.maintenance.health_check import check_gmail_connectivity  # Import Gmail connectivity check function
from src.scripts.maintenance.health_check import reset_circuit_breakers  # Import circuit breaker reset function
from src.scripts.maintenance.backup_sheets import backup_master_budget  # Import Master Budget backup function
from src.scripts.maintenance.backup_sheets import backup_weekly_spending  # Import Weekly Spending backup function
from src.scripts.maintenance.backup_sheets import backup_sheet_to_json  # Import sheet to JSON backup function
from src.scripts.maintenance.backup_sheets import create_in_spreadsheet_backup  # Import in-spreadsheet backup function
from src.scripts.maintenance.rotate_credentials import rotate_credentials  # Import credential rotation function
from src.scripts.maintenance.rotate_credentials import rotate_capital_one_credentials  # Import Capital One credential rotation function
from src.scripts.maintenance.rotate_credentials import rotate_google_sheets_credentials  # Import Google Sheets credential rotation function
from src.scripts.maintenance.rotate_credentials import rotate_gemini_credentials  # Import Gemini credential rotation function
from src.scripts.maintenance.rotate_credentials import rotate_gmail_credentials  # Import Gmail credential rotation function
from src.scripts.config.logging_setup import get_logger  # Import logger configuration function

# Initialize logger
logger = get_logger('maintenance')

# Define module metadata
__version__ = "1.0.0"
__author__ = "Nick DiFiore"
__email__ = "njdifiore@gmail.com"


def run_health_check(reset_circuits: bool = False, send_email: bool = False) -> dict:
    """
    Convenience function to run a complete health check of the system

    Args:
        reset_circuits (bool): Whether to reset circuit breakers before running the health check
        send_email (bool): Whether to send an email with the health check report

    Returns:
        dict: Health check report with status of all components
    """
    logger.info("Starting health check")

    if reset_circuits:
        logger.info("Resetting circuit breakers")
        reset_circuit_breakers()

    health_report = generate_health_report()

    logger.info(f"Health check results: {health_report}")

    # If send_email is True, send email with health report
    # TODO: Implement email sending functionality
    if send_email:
        logger.info("Sending email with health report")
        # send_health_report_email(health_report)
        pass

    return health_report


def run_credential_rotation(service_name: str = None, force: bool = False, verify: bool = True) -> dict:
    """
    Convenience function to run credential rotation for all or specific services

    Args:
        service_name (str): Name of the service to rotate, or None for all services
        force (bool): Whether to force rotation regardless of interval
        verify (bool): Whether to verify credentials after rotation

    Returns:
        dict: Rotation results for all services
    """
    logger.info("Starting credential rotation")

    rotation_results = rotate_credentials(service_name, force, verify)

    logger.info(f"Credential rotation results: {rotation_results}")

    return rotation_results


def run_backup(json_backup: bool = True, sheet_backup: bool = False, backup_dir: str = None) -> dict:
    """
    Convenience function to run backup of Google Sheets data

    Args:
        json_backup (bool): Whether to create JSON backups
        sheet_backup (bool): Whether to create in-spreadsheet backups
        backup_dir (str): Directory to store JSON backups

    Returns:
        dict: Backup results for all sheets
    """
    logger.info("Starting backup process")

    # Get Google Sheets service
    # TODO: Implement Google Sheets service
    # service = get_google_sheets_service()
    # if not service:
    #     logger.error("Failed to get Google Sheets service")
    #     return {}
    service = None

    # Backup Master Budget using backup_master_budget function
    master_budget_result = backup_master_budget(service, json_backup, sheet_backup, backup_dir)

    # Backup Weekly Spending using backup_weekly_spending function
    weekly_spending_result = backup_weekly_spending(service, json_backup, sheet_backup, backup_dir)

    backup_results = {
        "master_budget": master_budget_result,
        "weekly_spending": weekly_spending_result
    }

    logger.info(f"Backup results: {backup_results}")

    return backup_results


__all__ = [
    "generate_health_report",
    "check_authentication",
    "check_capital_one_connectivity",
    "check_google_sheets_connectivity",
    "check_gemini_connectivity",
    "check_gmail_connectivity",
    "reset_circuit_breakers",
    "rotate_credentials",
    "rotate_capital_one_credentials",
    "rotate_google_sheets_credentials",
    "rotate_gemini_credentials",
    "rotate_gmail_credentials",
    "backup_master_budget",
    "backup_weekly_spending",
    "backup_sheet_to_json",
    "create_in_spreadsheet_backup",
    "run_health_check",
    "run_credential_rotation",
    "run_backup"
]