"""
Initialization module for the disaster recovery package that provides a centralized entry point for all disaster recovery operations in the Budget Management Application. It exposes key functions from the various disaster recovery scripts to facilitate easy access to recovery operations.
"""

import logging  # standard library
from .emergency_stop import execute_emergency_stop  # src/scripts/disaster_recovery/emergency_stop.py
from .restore_from_backup import restore_from_latest, restore_from_specific_date  # src/scripts/disaster_recovery/restore_from_backup.py
from .verify_integrity import verify_directory_structure, verify_credentials, verify_api_connectivity, verify_sheets_data_integrity, verify_capital_one_accounts  # src/scripts/disaster_recovery/verify_integrity.py
from .recovery_validation import validate_directories, validate_credentials, validate_apis, validate_data, validate_infrastructure, validate_functionality, generate_validation_report  # src/scripts/disaster_recovery/recovery_validation.py

__version__ = "1.0.0"
__author__ = "Budget Management Application Team"
__all__ = [
    "execute_emergency_stop", "restore_from_latest", "restore_from_specific_date",
    "verify_directory_structure", "verify_credentials", "verify_api_connectivity",
    "verify_sheets_data_integrity", "verify_capital_one_accounts",
    "validate_directories", "validate_credentials", "validate_apis", "validate_data",
    "validate_infrastructure", "validate_functionality", "generate_validation_report"
]

logger = logging.getLogger(__name__)


def emergency_stop(project_id: str, region: str, app_name: str, force: bool) -> bool:
    """
    Convenience function to execute emergency stop procedure

    Args:
        project_id (str): Google Cloud project ID
        region (str): Google Cloud region
        app_name (str): Application name
        force (bool): Whether to skip confirmation

    Returns:
        bool: True if emergency stop was successful, False otherwise
    """
    logger.info("Attempting emergency stop")
    result = execute_emergency_stop(project_id, region, app_name, force)
    logger.info(f"Emergency stop result: {result}")
    return result


def restore_data(backup_date: str, use_json_backup: bool, backup_dir: str) -> bool:
    """
    Convenience function to restore data from backup

    Args:
        backup_date (str): Date of the backup to restore from
        use_json_backup (bool): Whether to use JSON backup files
        backup_dir (str): Directory containing backup files

    Returns:
        bool: True if restoration was successful, False otherwise
    """
    logger.info("Attempting data restoration")
    if backup_date is None or backup_date == 'latest':
        result = restore_from_latest(use_json_backup, backup_dir)
    else:
        try:
            # Attempt to parse the date string
            datetime.datetime.strptime(backup_date, "%Y-%m-%d")
            result = restore_from_specific_date(backup_date, use_json_backup, backup_dir)
        except ValueError:
            logger.error("Invalid date format. Please use YYYY-MM-DD.")
            return False
    logger.info(f"Data restoration result: {result}")
    return result


def verify_system_integrity(verbose: bool) -> Dict:
    """
    Convenience function to verify system integrity

    Args:
        verbose (bool): Whether to show detailed output

    Returns:
        dict: Dictionary with verification results for all components
    """
    logger.info("Attempting system integrity verification")
    directory_results = verify_directory_structure(verbose)
    credential_results = verify_credentials(verbose)
    api_results = verify_api_connectivity(verbose)

    if api_results.get('google_sheets', {}).get('connectivity', False) and api_results.get('capital_one', {}).get('connectivity', False):
        data_results = verify_sheets_data_integrity(api_results['google_sheets']['client'])
        accounts_results = verify_capital_one_accounts(api_results['capital_one']['client'])
    else:
        data_results = {'status': 'API_unavailable'}
        accounts_results = {'status': 'API_unavailable'}

    combined_results = {
        'directories': directory_results,
        'credentials': credential_results,
        'apis': api_results,
        'sheets': data_results,
        'accounts': accounts_results
    }

    logger.info(f"System integrity verification result: {combined_results}")
    return combined_results


def validate_recovery(project_id: str, region: str, app_name: str, verbose: bool, generate_report: bool) -> Dict:
    """
    Convenience function to validate recovery after disaster recovery operations

    Args:
        project_id (str): Google Cloud project ID
        region (str): Google Cloud region
        app_name (str): Application name
        verbose (bool): Whether to show detailed output
        generate_report (bool): Whether to generate a validation report

    Returns:
        dict: Dictionary with validation results for all components
    """
    logger.info("Attempting recovery validation")
    directory_results = validate_directories(verbose)
    credential_results = validate_credentials(verbose)
    api_results = validate_apis(verbose)

    if api_results.get('google_sheets', {}).get('connectivity', False) and api_results.get('capital_one', {}).get('connectivity', False):
        data_results = validate_data(verbose, api_results)
    else:
        data_results = {'status': 'API_unavailable'}

    infrastructure_results = validate_infrastructure(project_id, region, app_name, verbose)
    functionality_results = validate_functionality(project_id, region, app_name, verbose, api_results)

    combined_results = {
        'directories': directory_results,
        'credentials': credential_results,
        'apis': api_results,
        'data': data_results,
        'infrastructure': infrastructure_results,
        'functionality': functionality_results
    }

    if generate_report:
        report = generate_validation_report(combined_results)
        logger.info(f"Validation report generated: {report}")

    logger.info(f"Recovery validation result: {combined_results}")
    return combined_results