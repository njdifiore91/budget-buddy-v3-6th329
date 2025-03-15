"""
Mock implementation of Google Cloud Scheduler for testing purposes.

This module provides classes and functions to simulate Cloud Scheduler behavior
in tests without making actual API calls. It supports testing scheduled job execution,
cron expression parsing, and error handling scenarios.
"""

import json
import os
import datetime
import uuid
import copy
from typing import List, Dict, Optional, Any, Tuple

from ...backend.utils.error_handlers import AuthenticationError, APIError

# Path to test fixtures
FIXTURE_PATH = os.path.join(os.path.dirname(__file__), '../fixtures/json')

# Default retry configuration
DEFAULT_RETRY_CONFIG = {
    "retry_count": 3,
    "min_backoff_duration": "1s",
    "max_backoff_duration": "60s",
    "max_retry_duration": "300s",
    "max_doublings": 3
}


def load_fixture(filename: str) -> dict:
    """
    Load a JSON fixture file from the test fixtures directory.
    
    Args:
        filename: Name of the fixture file to load
        
    Returns:
        Parsed JSON data from the fixture file
    """
    filepath = os.path.join(FIXTURE_PATH, filename)
    with open(filepath, 'r') as f:
        return json.load(f)


def parse_cron_expression(cron_expression: str) -> dict:
    """
    Parse a cron expression into its component parts.
    
    Args:
        cron_expression: A cron expression (e.g., "0 12 * * 0")
        
    Returns:
        Dictionary with parsed cron components (minute, hour, day_of_month, month, day_of_week)
    """
    # Split the cron expression by whitespace
    components = cron_expression.split()
    
    # Validate that we have 5 components (minute, hour, day_of_month, month, day_of_week)
    if len(components) != 5:
        raise ValueError(f"Invalid cron expression: {cron_expression}. Must have 5 components.")
    
    # Return the parsed components
    return {
        'minute': components[0],
        'hour': components[1],
        'day_of_month': components[2],
        'month': components[3],
        'day_of_week': components[4]
    }


def calculate_next_execution(cron_expression: str, timezone: str, from_time: Optional[datetime.datetime] = None) -> datetime.datetime:
    """
    Calculate the next execution time based on a cron expression and timezone.
    
    Args:
        cron_expression: A cron expression (e.g., "0 12 * * 0")
        timezone: The timezone for the execution
        from_time: Reference time to calculate from (defaults to current time)
        
    Returns:
        Next execution time based on the cron expression
    """
    # Parse the cron expression
    cron = parse_cron_expression(cron_expression)
    
    # Use provided time or current time as reference
    if from_time is None:
        from_time = datetime.datetime.now()
    
    # For simplicity in testing, we'll implement a basic algorithm
    # In a real implementation, this would need to handle all cron syntax properly
    
    # Start with the reference time + 1 minute to ensure we get a future time
    next_time = from_time + datetime.timedelta(minutes=1)
    
    # For testing purposes, we'll implement a simplified algorithm:
    # If cron specifies a specific minute and it's not "*", advance to that minute
    if cron['minute'] != '*':
        minutes = int(cron['minute'])
        next_time = next_time.replace(minute=minutes, second=0, microsecond=0)
        if next_time <= from_time:
            next_time = next_time + datetime.timedelta(hours=1)
    
    # If cron specifies a specific hour and it's not "*", advance to that hour
    if cron['hour'] != '*':
        hours = int(cron['hour'])
        next_time = next_time.replace(hour=hours, second=0, microsecond=0)
        if next_time <= from_time:
            next_time = next_time + datetime.timedelta(days=1)
    
    # This is a simplified implementation for testing
    # A real implementation would need to handle all cron syntax including ranges, lists, steps, etc.
    
    return next_time


class MockCloudSchedulerJob:
    """
    Mock implementation of a Cloud Scheduler job for testing.
    """
    
    def __init__(self, name: str, schedule: str, time_zone: str, 
                 description: str = "", retry_config: dict = None, 
                 http_target: dict = None):
        """
        Initialize a mock Cloud Scheduler job with the specified parameters.
        
        Args:
            name: Job name/identifier
            schedule: Cron schedule expression
            time_zone: Timezone for job execution
            description: Optional job description
            retry_config: Configuration for job retries
            http_target: HTTP target configuration
        """
        self.name = name
        self.description = description
        self.schedule = schedule
        self.time_zone = time_zone
        self.state = "ENABLED"
        self.retry_config = retry_config or copy.deepcopy(DEFAULT_RETRY_CONFIG)
        self.http_target = http_target or {}
        self.job_id = str(uuid.uuid4())
        
        # Execution tracking
        self.last_execution_time = None
        self.next_execution_time = calculate_next_execution(schedule, time_zone)
        self.execution_count = 0
        self.execution_history = []
    
    def to_dict(self) -> dict:
        """
        Convert the job to a dictionary representation.
        
        Returns:
            Dictionary representation of the job
        """
        return {
            'name': self.name,
            'description': self.description,
            'schedule': self.schedule,
            'time_zone': self.time_zone,
            'state': self.state,
            'retry_config': self.retry_config,
            'http_target': self.http_target,
            'job_id': self.job_id,
            'last_execution_time': self.last_execution_time.isoformat() if self.last_execution_time else None,
            'next_execution_time': self.next_execution_time.isoformat() if self.next_execution_time else None,
            'execution_count': self.execution_count
        }
    
    def update(self, job_config: dict) -> dict:
        """
        Update job properties with new values.
        
        Args:
            job_config: Dictionary containing properties to update
            
        Returns:
            Updated job dictionary
        """
        # Update job properties
        for key, value in job_config.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Recalculate next execution time if schedule or timezone changed
        if 'schedule' in job_config or 'time_zone' in job_config:
            self.next_execution_time = calculate_next_execution(
                self.schedule, self.time_zone
            )
        
        return self.to_dict()
    
    def pause(self) -> dict:
        """
        Pause the job by setting state to PAUSED.
        
        Returns:
            Updated job dictionary
        """
        self.state = "PAUSED"
        return self.to_dict()
    
    def resume(self) -> dict:
        """
        Resume the job by setting state to ENABLED.
        
        Returns:
            Updated job dictionary
        """
        self.state = "ENABLED"
        self.next_execution_time = calculate_next_execution(
            self.schedule, self.time_zone
        )
        return self.to_dict()
    
    def run(self) -> dict:
        """
        Simulate running the job.
        
        Returns:
            Execution result
        """
        # Check if job is enabled
        if self.state != "ENABLED":
            raise APIError(
                message=f"Cannot run job in {self.state} state", 
                api_name="Cloud Scheduler", 
                operation="run_job"
            )
        
        # Record execution
        execution_time = datetime.datetime.now()
        execution_record = {
            'time': execution_time,
            'status': 'SUCCESS',
            'job_id': self.job_id
        }
        self.execution_history.append(execution_record)
        
        # Update execution tracking
        self.last_execution_time = execution_time
        self.execution_count += 1
        self.next_execution_time = calculate_next_execution(
            self.schedule, self.time_zone, execution_time
        )
        
        return {
            'name': self.name,
            'execution_time': execution_time.isoformat(),
            'status': 'SUCCESS'
        }
    
    def get_execution_history(self) -> list:
        """
        Get the execution history of the job.
        
        Returns:
            List of execution history entries
        """
        # Return a copy to prevent modification
        return copy.deepcopy(self.execution_history)


class MockCloudScheduler:
    """
    Mock implementation of Google Cloud Scheduler for testing.
    """
    
    def __init__(self, should_fail: bool = False):
        """
        Initialize the mock Cloud Scheduler with test data and behavior flags.
        
        Args:
            should_fail: Whether API calls should fail (for testing error handling)
        """
        self.jobs = {}  # Dictionary to store jobs (name -> job)
        self.should_fail = should_fail
        
        # Load error responses from fixture if available
        try:
            self.error_responses = load_fixture('cloud_scheduler_errors.json')
        except (FileNotFoundError, json.JSONDecodeError):
            self.error_responses = {}
        
        # Call tracking for assertions in tests
        self.call_count_create_job = 0
        self.call_count_delete_job = 0
        self.call_count_get_job = 0
        self.call_count_update_job = 0
        self.call_count_pause_job = 0
        self.call_count_resume_job = 0
        self.call_count_run_job = 0
        self.call_count_list_jobs = 0
    
    def reset(self) -> None:
        """
        Reset the mock client to its initial state.
        """
        self.jobs = {}
        self.should_fail = False
        self.call_count_create_job = 0
        self.call_count_delete_job = 0
        self.call_count_get_job = 0
        self.call_count_update_job = 0
        self.call_count_pause_job = 0
        self.call_count_resume_job = 0
        self.call_count_run_job = 0
        self.call_count_list_jobs = 0
    
    def set_failure_mode(self, should_fail: bool) -> None:
        """
        Configure the mock to simulate failures.
        
        Args:
            should_fail: Whether API calls should fail
        """
        self.should_fail = should_fail
    
    def create_job(self, job_config: dict) -> dict:
        """
        Create a new Cloud Scheduler job.
        
        Args:
            job_config: Job configuration parameters
            
        Returns:
            Created job as dictionary
        """
        self.call_count_create_job += 1
        
        # Simulate failure if should_fail is True
        if self.should_fail:
            raise APIError(
                message="Simulated failure in create_job",
                api_name="Cloud Scheduler",
                operation="create_job"
            )
        
        # Extract job parameters
        name = job_config.get('name')
        schedule = job_config.get('schedule')
        time_zone = job_config.get('time_zone')
        description = job_config.get('description', '')
        retry_config = job_config.get('retry_config')
        http_target = job_config.get('http_target')
        
        # Create the job
        job = MockCloudSchedulerJob(
            name=name,
            schedule=schedule,
            time_zone=time_zone,
            description=description,
            retry_config=retry_config,
            http_target=http_target
        )
        
        # Store the job
        self.jobs[name] = job
        
        return job.to_dict()
    
    def delete_job(self, name: str) -> dict:
        """
        Delete a Cloud Scheduler job.
        
        Args:
            name: Name of the job to delete
            
        Returns:
            Empty dictionary on success
        """
        self.call_count_delete_job += 1
        
        # Simulate failure if should_fail is True
        if self.should_fail:
            raise APIError(
                message="Simulated failure in delete_job",
                api_name="Cloud Scheduler",
                operation="delete_job"
            )
        
        # Check if job exists
        if name in self.jobs:
            del self.jobs[name]
            return {}
        else:
            raise APIError(
                message=f"Job not found: {name}",
                api_name="Cloud Scheduler",
                operation="delete_job"
            )
    
    def get_job(self, name: str) -> dict:
        """
        Get a Cloud Scheduler job by name.
        
        Args:
            name: Name of the job to retrieve
            
        Returns:
            Job as dictionary
        """
        self.call_count_get_job += 1
        
        # Simulate failure if should_fail is True
        if self.should_fail:
            raise APIError(
                message="Simulated failure in get_job",
                api_name="Cloud Scheduler",
                operation="get_job"
            )
        
        # Check if job exists
        if name in self.jobs:
            return self.jobs[name].to_dict()
        else:
            raise APIError(
                message=f"Job not found: {name}",
                api_name="Cloud Scheduler",
                operation="get_job"
            )
    
    def update_job(self, name: str, job_config: dict) -> dict:
        """
        Update an existing Cloud Scheduler job.
        
        Args:
            name: Name of the job to update
            job_config: New job configuration
            
        Returns:
            Updated job as dictionary
        """
        self.call_count_update_job += 1
        
        # Simulate failure if should_fail is True
        if self.should_fail:
            raise APIError(
                message="Simulated failure in update_job",
                api_name="Cloud Scheduler",
                operation="update_job"
            )
        
        # Check if job exists
        if name in self.jobs:
            return self.jobs[name].update(job_config)
        else:
            raise APIError(
                message=f"Job not found: {name}",
                api_name="Cloud Scheduler",
                operation="update_job"
            )
    
    def pause_job(self, name: str) -> dict:
        """
        Pause a Cloud Scheduler job.
        
        Args:
            name: Name of the job to pause
            
        Returns:
            Updated job as dictionary
        """
        self.call_count_pause_job += 1
        
        # Simulate failure if should_fail is True
        if self.should_fail:
            raise APIError(
                message="Simulated failure in pause_job",
                api_name="Cloud Scheduler",
                operation="pause_job"
            )
        
        # Check if job exists
        if name in self.jobs:
            return self.jobs[name].pause()
        else:
            raise APIError(
                message=f"Job not found: {name}",
                api_name="Cloud Scheduler",
                operation="pause_job"
            )
    
    def resume_job(self, name: str) -> dict:
        """
        Resume a paused Cloud Scheduler job.
        
        Args:
            name: Name of the job to resume
            
        Returns:
            Updated job as dictionary
        """
        self.call_count_resume_job += 1
        
        # Simulate failure if should_fail is True
        if self.should_fail:
            raise APIError(
                message="Simulated failure in resume_job",
                api_name="Cloud Scheduler",
                operation="resume_job"
            )
        
        # Check if job exists
        if name in self.jobs:
            return self.jobs[name].resume()
        else:
            raise APIError(
                message=f"Job not found: {name}",
                api_name="Cloud Scheduler",
                operation="resume_job"
            )
    
    def run_job(self, name: str) -> dict:
        """
        Manually trigger a Cloud Scheduler job.
        
        Args:
            name: Name of the job to run
            
        Returns:
            Execution result
        """
        self.call_count_run_job += 1
        
        # Simulate failure if should_fail is True
        if self.should_fail:
            raise APIError(
                message="Simulated failure in run_job",
                api_name="Cloud Scheduler",
                operation="run_job"
            )
        
        # Check if job exists
        if name in self.jobs:
            return self.jobs[name].run()
        else:
            raise APIError(
                message=f"Job not found: {name}",
                api_name="Cloud Scheduler",
                operation="run_job"
            )
    
    def list_jobs(self) -> list:
        """
        List all Cloud Scheduler jobs.
        
        Returns:
            List of jobs as dictionaries
        """
        self.call_count_list_jobs += 1
        
        # Simulate failure if should_fail is True
        if self.should_fail:
            raise APIError(
                message="Simulated failure in list_jobs",
                api_name="Cloud Scheduler",
                operation="list_jobs"
            )
        
        # Convert all jobs to dictionaries
        return [job.to_dict() for job in self.jobs.values()]
    
    def simulate_error(self, error_type: str) -> None:
        """
        Simulate a specific error response for testing error handling.
        
        Args:
            error_type: Type of error to simulate
        """
        if error_type in self.error_responses:
            error_info = self.error_responses[error_type]
            
            if error_info.get('type') == 'authentication':
                raise AuthenticationError(
                    message=error_info.get('message', 'Authentication error'),
                    service_name="Cloud Scheduler"
                )
            else:
                raise APIError(
                    message=error_info.get('message', 'API error'),
                    api_name="Cloud Scheduler",
                    operation=error_info.get('operation', 'unknown_operation'),
                    status_code=error_info.get('status_code')
                )
        else:
            raise ValueError(f"Unknown error type: {error_type}")
    
    def add_job(self, job: MockCloudSchedulerJob) -> dict:
        """
        Add a pre-configured job to the mock scheduler.
        
        Args:
            job: The job instance to add
            
        Returns:
            Added job as dictionary
        """
        self.jobs[job.name] = job
        return job.to_dict()