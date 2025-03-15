#!/usr/bin/env python3
"""
Utility script to manually trigger the Budget Management Application's Cloud Run job.

This script provides a command-line interface to initiate the weekly budget management process
on-demand, bypassing the scheduled execution. It can trigger the job, wait for its completion,
and display the results.

Usage:
    python trigger_job.py [options]

Options:
    --project-id PROJECT_ID      Google Cloud project ID (default: from environment)
    --region REGION              Google Cloud region (default: us-east1)
    --job-name JOB_NAME          Cloud Run job name (default: budget-management-job)
    --correlation-id ID          Custom correlation ID for job execution
    --wait                       Wait for job completion
    --timeout SECONDS            Wait timeout in seconds (default: 300)
    --check-health               Run system health check only
    --debug                      Enable debug logging
    --verbose                    Enable verbose output

Returns:
    0 if job was triggered successfully (and completed successfully if --wait)
    1 if there was an error triggering the job
    2 if the job failed (when using --wait)
    3 if the job timed out (when using --wait)
"""

import os
import sys
import argparse
import time
import uuid
import subprocess
import json
import google.cloud.run_v2
import google.auth

# Import internal modules
from ...config.script_settings import SCRIPT_SETTINGS, MAX_RETRIES, TIMEOUT
from ...config.logging_setup import get_logger, LoggingContext

# Set up logger
logger = get_logger('trigger_job')

# Default values
DEFAULT_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT', None)
DEFAULT_REGION = os.environ.get('GOOGLE_CLOUD_REGION', 'us-east1')
DEFAULT_JOB_NAME = os.environ.get('CLOUD_RUN_JOB_NAME', 'budget-management-job')


def parse_arguments():
    """
    Parses command line arguments for the script.
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Manually trigger the Budget Management Application Cloud Run job'
    )
    
    parser.add_argument(
        '--project-id',
        help=f'Google Cloud project ID (default: {DEFAULT_PROJECT_ID or "from environment"})',
        default=DEFAULT_PROJECT_ID
    )
    
    parser.add_argument(
        '--region',
        help=f'Google Cloud region (default: {DEFAULT_REGION})',
        default=DEFAULT_REGION
    )
    
    parser.add_argument(
        '--job-name',
        help=f'Cloud Run job name (default: {DEFAULT_JOB_NAME})',
        default=DEFAULT_JOB_NAME
    )
    
    parser.add_argument(
        '--correlation-id',
        help='Custom correlation ID for job execution',
        default=None
    )
    
    parser.add_argument(
        '--wait',
        help='Wait for job completion',
        action='store_true'
    )
    
    parser.add_argument(
        '--timeout',
        help=f'Wait timeout in seconds (default: {TIMEOUT})',
        type=int,
        default=TIMEOUT
    )
    
    parser.add_argument(
        '--check-health',
        help='Run system health check only',
        action='store_true'
    )
    
    parser.add_argument(
        '--debug',
        help='Enable debug logging',
        action='store_true'
    )
    
    parser.add_argument(
        '--verbose',
        help='Enable verbose output',
        action='store_true'
    )
    
    return parser.parse_args()


def check_gcloud_installed():
    """
    Checks if gcloud CLI is installed and configured.
    
    Returns:
        bool: True if gcloud is installed and configured, False otherwise
    """
    try:
        result = subprocess.run(
            ['gcloud', '--version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        
        if result.returncode == 0:
            logger.debug("gcloud CLI is installed and available")
            return True
        else:
            logger.error("gcloud CLI check failed: %s", result.stderr.decode().strip())
            return False
    except Exception as e:
        logger.error("Error checking gcloud CLI: %s", str(e))
        return False


def check_job_exists(project_id, region, job_name):
    """
    Checks if the specified Cloud Run job exists.
    
    Args:
        project_id (str): Google Cloud project ID
        region (str): Google Cloud region
        job_name (str): Cloud Run job name
        
    Returns:
        bool: True if job exists, False otherwise
    """
    try:
        cmd = [
            'gcloud', 'run', 'jobs', 'describe', job_name,
            '--project', project_id,
            '--region', region,
            '--format', 'json'
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        
        if result.returncode == 0:
            logger.debug("Cloud Run job '%s' exists", job_name)
            return True
        else:
            error_msg = result.stderr.decode().strip()
            if "NOT_FOUND" in error_msg:
                logger.error("Cloud Run job '%s' not found", job_name)
                return False
            else:
                logger.error("Error checking job existence: %s", error_msg)
                return False
    except Exception as e:
        logger.error("Error checking job existence: %s", str(e))
        return False


def trigger_job_gcloud(project_id, region, job_name, correlation_id):
    """
    Triggers a Cloud Run job using gcloud CLI.
    
    Args:
        project_id (str): Google Cloud project ID
        region (str): Google Cloud region
        job_name (str): Cloud Run job name
        correlation_id (str): Correlation ID for the job execution
        
    Returns:
        dict: Job execution details including execution ID
    """
    try:
        cmd = [
            'gcloud', 'run', 'jobs', 'execute', job_name,
            '--project', project_id,
            '--region', region,
            '--update-env-vars', f'CORRELATION_ID={correlation_id}',
            '--format', 'json'
        ]
        
        logger.debug("Executing command: %s", ' '.join(cmd))
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        
        if result.returncode == 0:
            response = json.loads(result.stdout.decode())
            execution_id = response.get('metadata', {}).get('name', '').split('/')[-1]
            
            return {
                'status': 'triggered',
                'execution_id': execution_id,
                'details': response
            }
        else:
            error_msg = result.stderr.decode().strip()
            logger.error("Error triggering job with gcloud: %s", error_msg)
            
            return {
                'status': 'error',
                'error': error_msg
            }
    except Exception as e:
        logger.error("Error triggering job with gcloud: %s", str(e))
        
        return {
            'status': 'error',
            'error': str(e)
        }


def trigger_job_api(project_id, region, job_name, correlation_id):
    """
    Triggers a Cloud Run job using Google Cloud Run API.
    
    Args:
        project_id (str): Google Cloud project ID
        region (str): Google Cloud region
        job_name (str): Cloud Run job name
        correlation_id (str): Correlation ID for the job execution
        
    Returns:
        dict: Job execution details including execution ID
    """
    try:
        from google.cloud.run_v2 import JobsClient
        from google.cloud.run_v2 import RunJobRequest
        
        logger.debug("Using Google Cloud Run API to trigger job")
        
        # Authenticate with Google Cloud
        credentials, project = google.auth.default()
        
        # If no project_id was provided, use the default one
        if not project_id:
            project_id = project
            
        if not project_id:
            raise ValueError("No Google Cloud project ID specified")
        
        # Create the client
        client = JobsClient(credentials=credentials)
        
        # Prepare the job name in the required format
        job_name_full = f"projects/{project_id}/locations/{region}/jobs/{job_name}"
        
        # Create the execution request
        request = RunJobRequest(
            name=job_name_full,
            overrides={
                "container_overrides": [
                    {
                        "env": [
                            {"name": "CORRELATION_ID", "value": correlation_id}
                        ]
                    }
                ]
            }
        )
        
        # Execute the job
        response = client.run_job(request=request)
        
        # Extract execution ID from response
        execution_id = response.name.split('/')[-1]
        
        return {
            'status': 'triggered',
            'execution_id': execution_id,
            'details': {
                'name': response.name,
                'uid': response.uid,
                'generation': response.generation,
                'createTime': response.create_time.isoformat() if hasattr(response, 'create_time') else None,
            }
        }
    except ImportError:
        logger.warning("Google Cloud Run API not available, falling back to gcloud CLI")
        return {
            'status': 'fallback',
            'error': 'Google Cloud Run API not available'
        }
    except Exception as e:
        logger.error("Error triggering job with API: %s", str(e))
        
        return {
            'status': 'error',
            'error': str(e)
        }


def wait_for_job_completion(project_id, region, job_name, execution_id, timeout):
    """
    Waits for a Cloud Run job execution to complete.
    
    Args:
        project_id (str): Google Cloud project ID
        region (str): Google Cloud region
        job_name (str): Cloud Run job name
        execution_id (str): Execution ID to wait for
        timeout (int): Maximum time to wait in seconds
        
    Returns:
        dict: Final job execution status
    """
    try:
        start_time = time.time()
        elapsed = 0
        
        logger.info("Waiting for job execution to complete (timeout: %d seconds)", timeout)
        
        while elapsed < timeout:
            # Check execution status using gcloud
            cmd = [
                'gcloud', 'run', 'jobs', 'executions', 'describe', execution_id,
                '--job', job_name,
                '--project', project_id,
                '--region', region,
                '--format', 'json'
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            
            if result.returncode == 0:
                execution_data = json.loads(result.stdout.decode())
                status = execution_data.get('status', {}).get('condition', {}).get('state', '')
                
                if status in ('SUCCEEDED', 'FAILED', 'CANCELLED'):
                    logger.info("Job execution completed with status: %s", status)
                    
                    return {
                        'status': status.lower(),
                        'execution_id': execution_id,
                        'details': execution_data
                    }
                
                # If the job is still running, wait and check again
                if elapsed % 15 == 0:  # Log progress every 15 seconds
                    logger.info("Job execution still running (elapsed: %d seconds)", elapsed)
            else:
                logger.warning("Error checking job status: %s", result.stderr.decode().strip())
            
            # Sleep for a bit before checking again
            time.sleep(5)
            elapsed = int(time.time() - start_time)
        
        # If we get here, the job timed out
        logger.warning("Timeout waiting for job execution to complete")
        
        return {
            'status': 'timeout',
            'execution_id': execution_id,
            'error': f"Timeout after {timeout} seconds"
        }
    except Exception as e:
        logger.error("Error waiting for job completion: %s", str(e))
        
        return {
            'status': 'error',
            'execution_id': execution_id,
            'error': str(e)
        }


def get_job_logs(project_id, job_name, execution_id):
    """
    Retrieves logs for a Cloud Run job execution.
    
    Args:
        project_id (str): Google Cloud project ID
        job_name (str): Cloud Run job name
        execution_id (str): Execution ID to get logs for
        
    Returns:
        list: List of log entries
    """
    try:
        filter_str = (
            f'resource.type="cloud_run_job" AND '
            f'resource.labels.job_name="{job_name}" AND '
            f'resource.labels.execution_name="{execution_id}"'
        )
        
        cmd = [
            'gcloud', 'logging', 'read',
            filter_str,
            f'--project={project_id}',
            '--format=json',
            '--limit=50'
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        
        if result.returncode == 0:
            log_entries = json.loads(result.stdout.decode())
            return log_entries
        else:
            logger.warning("Error retrieving job logs: %s", result.stderr.decode().strip())
            return []
    except Exception as e:
        logger.error("Error retrieving job logs: %s", str(e))
        return []


def display_job_status(execution_status, verbose=False):
    """
    Displays the status of a Cloud Run job execution.
    
    Args:
        execution_status (dict): Job execution status dictionary
        verbose (bool): Whether to show verbose details
        
    Returns:
        None
    """
    status = execution_status.get('status', 'unknown')
    execution_id = execution_status.get('execution_id', 'unknown')
    
    if status == 'error':
        logger.error("Job execution failed: %s", execution_status.get('error', 'Unknown error'))
        return
    
    if status == 'timeout':
        logger.warning("Job execution timed out: %s", execution_id)
        return
    
    details = execution_status.get('details', {})
    
    logger.info("Job execution ID: %s", execution_id)
    logger.info("Job status: %s", status)
    
    if 'status' in details:
        condition = details.get('status', {}).get('condition', {})
        
        if 'executionStartTime' in condition:
            logger.info("Start time: %s", condition['executionStartTime'])
            
        if 'executionCompletionTime' in condition:
            logger.info("Completion time: %s", condition['executionCompletionTime'])
    
    if verbose:
        if status == 'succeeded':
            logger.info("Job completed successfully")
        elif status == 'failed':
            logger.error("Job execution failed")
            
            # Show error details if available
            if 'status' in details and 'condition' in details['status']:
                condition = details['status']['condition']
                if 'message' in condition:
                    logger.error("Error details: %s", condition['message'])


def main():
    """
    Main function that orchestrates the job triggering process.
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Parse command line arguments
    args = parse_arguments()
    
    # Generate a correlation ID if not provided
    correlation_id = args.correlation_id or str(uuid.uuid4())
    
    # Set up logging context for this operation
    with LoggingContext(logger, "manual_job_trigger", context={
        "project_id": args.project_id,
        "region": args.region,
        "job_name": args.job_name,
        "wait": args.wait,
        "timeout": args.timeout
    }, correlation_id=correlation_id):
        
        # Enable debug logging if requested
        if args.debug:
            logger.setLevel('DEBUG')
            logger.debug("Debug logging enabled")
        
        # Check if gcloud is installed
        if not check_gcloud_installed():
            logger.error("gcloud CLI is not installed or not properly configured")
            return 1
        
        # Verify Google Cloud project ID
        if not args.project_id:
            logger.error("No Google Cloud project ID specified. Use --project-id or set GOOGLE_CLOUD_PROJECT environment variable")
            return 1
        
        # Check if the job exists
        if not check_job_exists(args.project_id, args.region, args.job_name):
            logger.error("The specified Cloud Run job does not exist")
            return 1
        
        # If only doing a health check, exit now
        if args.check_health:
            logger.info("Health check completed successfully. The job exists and is ready to run.")
            return 0
        
        # Trigger the job
        logger.info("Triggering Cloud Run job: %s (correlation ID: %s)", args.job_name, correlation_id)
        
        # Try to use the API first, fall back to gcloud CLI if needed
        execution_result = trigger_job_api(args.project_id, args.region, args.job_name, correlation_id)
        
        if execution_result.get('status') in ('error', 'fallback'):
            logger.warning("Falling back to gcloud CLI for job triggering")
            execution_result = trigger_job_gcloud(args.project_id, args.region, args.job_name, correlation_id)
        
        # Check if job was triggered successfully
        if execution_result.get('status') != 'triggered':
            logger.error("Failed to trigger job: %s", execution_result.get('error', 'Unknown error'))
            return 1
        
        # Job was triggered successfully
        execution_id = execution_result.get('execution_id')
        logger.info("Job execution started with ID: %s", execution_id)
        
        # If wait flag is set, wait for job completion
        if args.wait:
            completion_result = wait_for_job_completion(
                args.project_id, 
                args.region, 
                args.job_name, 
                execution_id, 
                args.timeout
            )
            
            # Display the final job status
            display_job_status(completion_result, args.verbose)
            
            # Return appropriate exit code based on job status
            status = completion_result.get('status')
            
            if status == 'succeeded':
                return 0
            elif status == 'failed':
                return 2
            elif status == 'timeout':
                return 3
            else:
                return 1
        
        # If not waiting, just return success for triggering
        return 0


if __name__ == "__main__":
    sys.exit(main())