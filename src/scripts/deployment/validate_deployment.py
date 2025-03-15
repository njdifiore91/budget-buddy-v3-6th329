#!/usr/bin/env python3
"""
Validates the successful deployment of the Budget Management Application to Google Cloud Run.

This script performs comprehensive checks to ensure that the Cloud Run job is properly
configured with the correct container image, resource allocations, service account,
and other critical settings. It can be run independently or as part of the deployment
process to verify deployment integrity.
"""

import argparse
import os
import sys
import json
import subprocess
import time

from src.scripts.config.path_constants import ROOT_DIR
from src.scripts.config.script_settings import SCRIPT_SETTINGS
from src.scripts.config.logging_setup import get_logger

# Set up logger
logger = get_logger('validate_deployment')

# Default values from environment variables
DEFAULT_PROJECT_ID = os.environ.get('PROJECT_ID', None)
DEFAULT_REGION = os.environ.get('REGION', 'us-east1')
DEFAULT_APP_NAME = os.environ.get('APP_NAME', 'budget-management')
DEFAULT_SERVICE_ACCOUNT = os.environ.get('SERVICE_ACCOUNT', None)
DEFAULT_CPU = os.environ.get('CPU', '1')
DEFAULT_MEMORY = os.environ.get('MEMORY', '2Gi')
DEFAULT_TIMEOUT_SECONDS = os.environ.get('TIMEOUT_SECONDS', '600')


def parse_arguments():
    """
    Parses command line arguments for the validation script.
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Validate the Budget Management Application deployment to Google Cloud Run."
    )
    
    parser.add_argument(
        "--project-id",
        help="Google Cloud project ID",
        default=DEFAULT_PROJECT_ID,
        required=DEFAULT_PROJECT_ID is None
    )
    
    parser.add_argument(
        "--region",
        help="Google Cloud region",
        default=DEFAULT_REGION
    )
    
    parser.add_argument(
        "--app-name",
        help="Application name (Cloud Run job name)",
        default=DEFAULT_APP_NAME
    )
    
    parser.add_argument(
        "--service-account",
        help="Service account email for the Cloud Run job",
        default=DEFAULT_SERVICE_ACCOUNT
    )
    
    parser.add_argument(
        "--cpu",
        help="Expected CPU allocation for the Cloud Run job",
        default=DEFAULT_CPU
    )
    
    parser.add_argument(
        "--memory",
        help="Expected memory allocation for the Cloud Run job",
        default=DEFAULT_MEMORY
    )
    
    parser.add_argument(
        "--timeout",
        help="Expected timeout in seconds for the Cloud Run job",
        default=DEFAULT_TIMEOUT_SECONDS
    )
    
    parser.add_argument(
        "--verbose",
        help="Enable verbose output",
        action="store_true"
    )
    
    parser.add_argument(
        "--check-execution",
        help="Check if the job can be executed",
        action="store_true"
    )
    
    return parser.parse_args()


def run_gcloud_command(command, capture_output=True, check=True):
    """
    Executes a Google Cloud CLI command and returns the result.
    
    Args:
        command: List containing the command and its arguments
        capture_output: Whether to capture the command output
        check: Whether to raise an exception on non-zero return code
        
    Returns:
        dict or subprocess.CompletedProcess: Command output as parsed JSON or CompletedProcess object
    """
    logger.info(f"Executing command: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None,
            text=True if capture_output else False,
            check=check
        )
        
        if capture_output and result.stdout:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                logger.warning("Failed to parse command output as JSON")
                return result
        
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with return code {e.returncode}: {e}")
        if capture_output and e.stderr:
            logger.error(f"Error output: {e.stderr}")
        if check:
            raise
        return e


def check_gcloud_installed():
    """
    Checks if Google Cloud CLI is installed and configured.
    
    Returns:
        bool: True if gcloud is installed and configured, False otherwise
    """
    try:
        run_gcloud_command(["gcloud", "--version"], capture_output=True, check=True)
        logger.info("Google Cloud CLI is installed and available")
        return True
    except Exception as e:
        logger.error(f"Google Cloud CLI is not available: {e}")
        return False


def get_cloud_run_job(project_id, region, app_name):
    """
    Retrieves the Cloud Run job configuration.
    
    Args:
        project_id: Google Cloud project ID
        region: Google Cloud region
        app_name: Application name (Cloud Run job name)
        
    Returns:
        dict or None: Job configuration as dictionary or None if not found
    """
    command = [
        "gcloud", "run", "jobs", "describe", app_name,
        "--project", project_id,
        "--region", region,
        "--format", "json"
    ]
    
    max_retries = SCRIPT_SETTINGS.get('MAX_RETRIES', 3)
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            return run_gcloud_command(command, capture_output=True, check=True)
        except Exception as e:
            logger.warning(f"Failed to retrieve job configuration (attempt {retry_count + 1}): {e}")
            retry_count += 1
            if retry_count < max_retries:
                timeout = 2 ** retry_count  # Exponential backoff
                logger.info(f"Retrying in {timeout} seconds...")
                time.sleep(timeout)
            else:
                logger.error("Failed to retrieve job configuration after max retries")
                return None


def validate_job_exists(job_config):
    """
    Validates that the Cloud Run job exists.
    
    Args:
        job_config: Job configuration as dictionary
        
    Returns:
        bool: True if job exists, False otherwise
    """
    if job_config is not None:
        logger.info("Cloud Run job exists")
        return True
    else:
        logger.error("Cloud Run job does not exist")
        return False


def validate_container_image(job_config, expected_image=None):
    """
    Validates that the Cloud Run job uses the correct container image.
    
    Args:
        job_config: Job configuration as dictionary
        expected_image: Expected container image (if None, skip validation)
        
    Returns:
        bool: True if container image is correct, False otherwise
    """
    if expected_image is None:
        logger.warning("No expected container image provided, skipping image validation")
        return True
    
    try:
        actual_image = job_config.get("template", {}).get("template", {}).get("containers", [{}])[0].get("image")
        
        if actual_image == expected_image:
            logger.info(f"Container image is correct: {actual_image}")
            return True
        else:
            logger.error(f"Container image mismatch: expected {expected_image}, got {actual_image}")
            return False
    except (IndexError, KeyError, TypeError) as e:
        logger.error(f"Failed to extract container image from job configuration: {e}")
        return False


def validate_resource_allocation(job_config, expected_cpu, expected_memory):
    """
    Validates that the Cloud Run job has the correct resource allocation.
    
    Args:
        job_config: Job configuration as dictionary
        expected_cpu: Expected CPU allocation
        expected_memory: Expected memory allocation
        
    Returns:
        bool: True if resource allocation is correct, False otherwise
    """
    try:
        container = job_config.get("template", {}).get("template", {}).get("containers", [{}])[0]
        actual_cpu = container.get("resources", {}).get("limits", {}).get("cpu")
        actual_memory = container.get("resources", {}).get("limits", {}).get("memory")
        
        cpu_match = actual_cpu == expected_cpu
        memory_match = actual_memory == expected_memory
        
        if cpu_match and memory_match:
            logger.info(f"Resource allocation is correct: CPU={actual_cpu}, Memory={actual_memory}")
            return True
        else:
            if not cpu_match:
                logger.error(f"CPU allocation mismatch: expected {expected_cpu}, got {actual_cpu}")
            if not memory_match:
                logger.error(f"Memory allocation mismatch: expected {expected_memory}, got {actual_memory}")
            return False
    except (IndexError, KeyError, TypeError) as e:
        logger.error(f"Failed to extract resource allocation from job configuration: {e}")
        return False


def validate_timeout(job_config, expected_timeout):
    """
    Validates that the Cloud Run job has the correct timeout setting.
    
    Args:
        job_config: Job configuration as dictionary
        expected_timeout: Expected timeout in seconds
        
    Returns:
        bool: True if timeout is correct, False otherwise
    """
    try:
        # Convert expected_timeout to string if it's not already
        expected_timeout = str(expected_timeout)
        actual_timeout = str(job_config.get("template", {}).get("template", {}).get("timeoutSeconds", ""))
        
        if actual_timeout == expected_timeout:
            logger.info(f"Timeout setting is correct: {actual_timeout}s")
            return True
        else:
            logger.error(f"Timeout setting mismatch: expected {expected_timeout}s, got {actual_timeout}s")
            return False
    except (KeyError, TypeError) as e:
        logger.error(f"Failed to extract timeout from job configuration: {e}")
        return False


def validate_service_account(job_config, expected_service_account=None):
    """
    Validates that the Cloud Run job uses the correct service account.
    
    Args:
        job_config: Job configuration as dictionary
        expected_service_account: Expected service account email (if None, skip validation)
        
    Returns:
        bool: True if service account is correct, False otherwise
    """
    if expected_service_account is None:
        logger.warning("No expected service account provided, skipping service account validation")
        return True
    
    try:
        actual_service_account = job_config.get("template", {}).get("template", {}).get("serviceAccount")
        
        if actual_service_account == expected_service_account:
            logger.info(f"Service account is correct: {actual_service_account}")
            return True
        else:
            logger.error(f"Service account mismatch: expected {expected_service_account}, got {actual_service_account}")
            return False
    except (KeyError, TypeError) as e:
        logger.error(f"Failed to extract service account from job configuration: {e}")
        return False


def validate_job_can_execute(project_id, region, app_name):
    """
    Validates that the Cloud Run job can be executed manually.
    
    Args:
        project_id: Google Cloud project ID
        region: Google Cloud region
        app_name: Application name (Cloud Run job name)
        
    Returns:
        bool: True if job can be executed, False otherwise
    """
    logger.info("Checking if job can be executed manually")
    
    command = [
        "gcloud", "run", "jobs", "execute", app_name,
        "--project", project_id,
        "--region", region,
        "--wait"
    ]
    
    try:
        result = run_gcloud_command(command, capture_output=True, check=False)
        if hasattr(result, 'returncode') and result.returncode == 0:
            logger.info("Job executed successfully")
            return True
        else:
            logger.warning("Job execution failed, but continuing validation")
            if hasattr(result, 'stderr') and result.stderr:
                logger.warning(f"Execution error: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Failed to execute job: {e}")
        return False


def validate_deployment(project_id, region, app_name, service_account=None, 
                       cpu=None, memory=None, timeout=None, check_execution=False):
    """
    Main function to validate the Cloud Run job deployment.
    
    Args:
        project_id: Google Cloud project ID
        region: Google Cloud region
        app_name: Application name (Cloud Run job name)
        service_account: Expected service account email
        cpu: Expected CPU allocation
        memory: Expected memory allocation
        timeout: Expected timeout in seconds
        check_execution: Whether to check if the job can be executed
        
    Returns:
        bool: True if all validations pass, False otherwise
    """
    logger.info(f"Starting deployment validation for {app_name} in {project_id}/{region}")
    
    # Check if gcloud is installed
    if not check_gcloud_installed():
        return False
    
    # Get Cloud Run job configuration
    job_config = get_cloud_run_job(project_id, region, app_name)
    
    # Validate job exists
    if not validate_job_exists(job_config):
        return False
    
    # Perform all validations
    validations = []
    
    # Validate resource allocation
    validations.append(validate_resource_allocation(job_config, cpu, memory))
    
    # Validate timeout
    validations.append(validate_timeout(job_config, timeout))
    
    # Validate service account (if provided)
    validations.append(validate_service_account(job_config, service_account))
    
    # Validate job can execute (if requested)
    if check_execution:
        validations.append(validate_job_can_execute(project_id, region, app_name))
    
    # Overall validation result
    validation_result = all(validations)
    
    if validation_result:
        logger.info(f"Deployment validation successful for {app_name}")
    else:
        logger.error(f"Deployment validation failed for {app_name}")
    
    return validation_result


def main():
    """
    Main entry point for the script.
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    args = parse_arguments()
    
    # Validate deployment
    result = validate_deployment(
        project_id=args.project_id,
        region=args.region,
        app_name=args.app_name,
        service_account=args.service_account,
        cpu=args.cpu,
        memory=args.memory,
        timeout=args.timeout,
        check_execution=args.check_execution
    )
    
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())