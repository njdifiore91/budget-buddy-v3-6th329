#!/usr/bin/env python3
"""
Emergency Stop Script for Budget Management Application.

This script provides functionality to immediately halt all running components
of the Budget Management Application during disaster recovery scenarios or
critical failures. It stops Cloud Run jobs, pauses scheduled operations,
and terminates any active API client connections.

Usage:
    python emergency_stop.py --project_id=my-project [--region=us-east1] [--app_name=budget-management] [--force] [--verbose]

The script requires confirmation unless the --force flag is provided.
"""

import argparse
import sys
import os
import subprocess
import time
from google.cloud import run_v2
from google.cloud import scheduler_v1

from ...config.script_settings import SCRIPT_SETTINGS
from ...config.logging_setup import get_logger, LoggingContext

# Initialize logger
logger = get_logger('emergency_stop')

# Default timeout and retry settings
DEFAULT_TIMEOUT = SCRIPT_SETTINGS['TIMEOUT']
DEFAULT_MAX_RETRIES = SCRIPT_SETTINGS['MAX_RETRIES']

def parse_arguments():
    """
    Parse command line arguments for the emergency stop script.
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Emergency stop utility for Budget Management Application',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--project_id',
        required=True,
        help='Google Cloud project ID where the application is deployed'
    )
    
    parser.add_argument(
        '--region',
        default='us-east1',
        help='Google Cloud region where the application is deployed'
    )
    
    parser.add_argument(
        '--app_name',
        default='budget-management',
        help='Application name used for identifying resources'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation and force emergency stop'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()

def confirm_emergency_stop(force):
    """
    Confirm with the user before proceeding with emergency stop.
    
    Args:
        force (bool): Whether to skip confirmation
        
    Returns:
        bool: True if confirmed, False otherwise
    """
    if force:
        logger.warning("Forced emergency stop - skipping confirmation")
        return True
    
    print("\n" + "!"*80)
    print("!! WARNING: EMERGENCY STOP PROCEDURE")
    print("!!")
    print("!! This will immediately terminate all running components of the")
    print("!! Budget Management Application. This includes:")
    print("!!  - Stopping all running Cloud Run jobs")
    print("!!  - Pausing all Cloud Scheduler jobs")
    print("!!  - Terminating all active API client connections")
    print("!!")
    print("!! This action is intended for emergency scenarios only and may result")
    print("!! in data loss or inconsistent state if executed during critical operations.")
    print("!" * 80 + "\n")
    
    response = input("To proceed, type 'STOP' (all caps): ")
    
    if response.strip() == "STOP":
        logger.info("Emergency stop confirmed by user")
        return True
    else:
        logger.info("Emergency stop cancelled by user")
        return False

def stop_cloud_run_job(project_id, region, app_name):
    """
    Stop any running Cloud Run jobs for the application.
    
    Args:
        project_id (str): Google Cloud project ID
        region (str): Google Cloud region
        app_name (str): Application name
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Stopping Cloud Run jobs for {app_name} in {project_id}/{region}")
    
    try:
        # Create Cloud Run jobs client
        client = run_v2.JobsClient()
        
        # Format the parent resource name
        parent = f"projects/{project_id}/locations/{region}"
        
        # List jobs to find the ones matching our app name
        response = client.list_jobs(parent=parent)
        
        jobs_stopped = 0
        jobs_failed = 0
        
        for job in response:
            # Check if this job belongs to our app
            if app_name.lower() in job.name.lower():
                logger.info(f"Found matching job: {job.name}")
                
                # Get executions for this job
                executions_parent = f"{job.name}/executions"
                executions = client.list_executions(parent=executions_parent)
                
                for execution in executions:
                    # Check if the execution is in a running state
                    if execution.condition.state != run_v2.Condition.State.SUCCEEDED and \
                       execution.condition.state != run_v2.Condition.State.FAILED and \
                       execution.condition.state != run_v2.Condition.State.CANCELLED:
                        
                        logger.info(f"Cancelling execution: {execution.name}")
                        try:
                            # Cancel the execution
                            client.cancel_execution(name=execution.name)
                            jobs_stopped += 1
                            logger.info(f"Successfully cancelled execution: {execution.name}")
                        except Exception as e:
                            jobs_failed += 1
                            logger.error(f"Failed to cancel execution {execution.name}: {str(e)}")
        
        if jobs_stopped > 0:
            logger.info(f"Successfully stopped {jobs_stopped} Cloud Run job executions")
        else:
            logger.info("No running Cloud Run job executions found")
            
        return jobs_failed == 0
    
    except Exception as e:
        logger.error(f"Error stopping Cloud Run jobs: {str(e)}")
        return False

def pause_cloud_scheduler(project_id, region, app_name):
    """
    Pause any Cloud Scheduler jobs related to the application.
    
    Args:
        project_id (str): Google Cloud project ID
        region (str): Google Cloud region
        app_name (str): Application name
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Pausing Cloud Scheduler jobs for {app_name} in {project_id}/{region}")
    
    try:
        # Create Cloud Scheduler client
        client = scheduler_v1.CloudSchedulerClient()
        
        # Format the parent resource name
        parent = f"projects/{project_id}/locations/{region}"
        
        # List jobs to find the ones matching our app name
        response = client.list_jobs(parent=parent)
        
        jobs_paused = 0
        jobs_failed = 0
        
        for job in response:
            # Check if this job belongs to our app
            if app_name.lower() in job.name.lower():
                logger.info(f"Found matching scheduler job: {job.name}")
                
                try:
                    # Pause the job
                    client.pause_job(name=job.name)
                    jobs_paused += 1
                    logger.info(f"Successfully paused scheduler job: {job.name}")
                except Exception as e:
                    jobs_failed += 1
                    logger.error(f"Failed to pause scheduler job {job.name}: {str(e)}")
        
        if jobs_paused > 0:
            logger.info(f"Successfully paused {jobs_paused} Cloud Scheduler jobs")
        else:
            logger.info("No matching Cloud Scheduler jobs found")
            
        return jobs_failed == 0
    
    except Exception as e:
        logger.error(f"Error pausing Cloud Scheduler jobs: {str(e)}")
        return False

def stop_api_clients():
    """
    Terminate any active API client connections.
    
    In a serverless environment, API clients are stateless and don't require
    explicit termination. This function is provided for interface completeness.
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Terminating API client connections")
    
    # In a serverless architecture, client connections are stateless
    # and don't need active termination. If future implementations use
    # persistent connections, termination logic would go here.
    logger.info("No persistent API clients to terminate in serverless architecture")
    
    return True

def execute_emergency_stop(project_id, region, app_name, force=False):
    """
    Execute the emergency stop procedure for all components.
    
    Args:
        project_id (str): Google Cloud project ID
        region (str): Google Cloud region
        app_name (str): Application name
        force (bool): Whether to skip confirmation
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.warning(f"Starting emergency stop procedure for {app_name} in {project_id}/{region}")
    
    # Confirm with user unless force is True
    if not confirm_emergency_stop(force):
        logger.info("Emergency stop cancelled")
        return False
    
    # Track success of each operation
    success_tracker = []
    
    # Stop Cloud Run jobs
    cloud_run_success = stop_cloud_run_job(project_id, region, app_name)
    success_tracker.append(cloud_run_success)
    
    # Pause Cloud Scheduler jobs
    scheduler_success = pause_cloud_scheduler(project_id, region, app_name)
    success_tracker.append(scheduler_success)
    
    # Stop API clients
    api_clients_success = stop_api_clients()
    success_tracker.append(api_clients_success)
    
    # Check if all operations were successful
    all_success = all(success_tracker)
    
    if all_success:
        logger.info("Emergency stop completed successfully")
    else:
        logger.error("Emergency stop completed with errors")
    
    return all_success

def main():
    """
    Main function to run the emergency stop script.
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    args = parse_arguments()
    
    # Set up logging for verbose mode if requested
    if args.verbose:
        SCRIPT_SETTINGS['LOG_LEVEL'] = 'DEBUG'
    
    # Run with logging context
    with LoggingContext(logger, operation='emergency_stop'):
        success = execute_emergency_stop(
            project_id=args.project_id,
            region=args.region,
            app_name=args.app_name,
            force=args.force
        )
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())