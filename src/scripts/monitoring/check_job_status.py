#!/usr/bin/env python3
"""
Job Status Checker for Budget Management Application

This script checks the status of the Cloud Run job for the Budget Management Application,
retrieves execution history, analyzes metrics, and reports on failures or performance issues.

Usage:
    python check_job_status.py --project-id=your-project-id --job-name=budget-management-job
"""

import argparse
import os
import sys
import json
import datetime
import subprocess
from typing import Dict, List, Optional, Union, Any

from google.cloud import run_v2
import google.auth

# Internal imports
from ..config.logging_setup import get_logger, LoggingContext
from ..config.script_settings import SCRIPT_SETTINGS, MAINTENANCE_SETTINGS
from ../../backend.api_clients.gmail_client import GmailClient
from .analyze_logs import LogAnalyzer

# Initialize logger
logger = get_logger('check_job_status')

# Default values
DEFAULT_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT', None)
DEFAULT_JOB_NAME = 'budget-management-job'
DEFAULT_REGION = 'us-east1'
DEFAULT_DAYS = 7
DEFAULT_OUTPUT_FORMAT = 'json'
DEFAULT_OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'job_status_report.json')


class JobStatusChecker:
    """Class that handles Cloud Run job status checking operations"""
    
    def __init__(self, project_id: str, job_name: str, region: str):
        """
        Initialize the job status checker with project and job details
        
        Args:
            project_id: Google Cloud project ID
            job_name: Name of the Cloud Run job
            region: Region where the job is deployed
        """
        self.project_id = project_id
        self.job_name = job_name
        self.region = region
        
        # Initialize Cloud Run Jobs client
        try:
            self.client = run_v2.JobsClient()
            logger.info(f"Initialized JobStatusChecker for {job_name} in {project_id}")
            
            # Validate that job exists
            parent = f"projects/{self.project_id}/locations/{self.region}/jobs/{self.job_name}"
            try:
                self.client.get_job(name=parent)
                logger.info(f"Confirmed job {self.job_name} exists")
            except Exception as e:
                logger.warning(f"Could not confirm job exists: {e}")
                
        except Exception as e:
            logger.error(f"Error initializing Cloud Run Jobs client: {e}")
            self.client = None
    
    def get_executions(self, days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get job execution history
        
        Args:
            days: Number of days of history to retrieve
            limit: Maximum number of executions to retrieve
            
        Returns:
            List of job execution details
        """
        if not self.client:
            logger.error("Cloud Run Jobs client not initialized")
            return []
        
        try:
            # Calculate start date based on days parameter
            start_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
            
            # Construct parent resource name
            parent = f"projects/{self.project_id}/locations/{self.region}/jobs/{self.job_name}"
            
            # Call list_executions API
            request = run_v2.ListExecutionsRequest(
                parent=parent,
                limit=limit
            )
            
            executions = self.client.list_executions(request=request)
            
            # Process response into standardized execution details
            execution_details = []
            for execution in executions:
                # Convert the execution to a Python dictionary
                execution_dict = {
                    'execution_id': execution.name.split('/')[-1],
                    'status': execution.status.state.name,
                    'start_time': execution.creation_timestamp.isoformat() if execution.creation_timestamp else None,
                    'end_time': execution.completion_timestamp.isoformat() if execution.completion_timestamp else None,
                    'duration': None,
                    'logs_url': execution.logging_uri if hasattr(execution, 'logging_uri') else None,
                    'error': None
                }
                
                # Calculate duration if both timestamps are available
                if execution.creation_timestamp and execution.completion_timestamp:
                    duration = (execution.completion_timestamp - execution.creation_timestamp).total_seconds()
                    execution_dict['duration'] = duration
                
                # Extract error details if present
                if execution.status.state.name == 'FAILED' and hasattr(execution, 'status') and hasattr(execution.status, 'error'):
                    execution_dict['error'] = {
                        'code': execution.status.error.code if hasattr(execution.status.error, 'code') else None,
                        'message': execution.status.error.message if hasattr(execution.status.error, 'message') else None
                    }
                
                # Filter by time - only include executions within the requested time period
                if execution.creation_timestamp and execution.creation_timestamp >= start_time:
                    execution_details.append(execution_dict)
            
            logger.info(f"Retrieved {len(execution_details)} job executions")
            return execution_details
            
        except Exception as e:
            logger.error(f"Error retrieving job executions: {e}")
            return []
    
    def get_execution_details(self, execution_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific execution
        
        Args:
            execution_id: ID of the execution to retrieve
            
        Returns:
            Detailed execution information
        """
        if not self.client:
            logger.error("Cloud Run Jobs client not initialized")
            return {}
        
        try:
            # Construct execution name
            execution_name = f"projects/{self.project_id}/locations/{self.region}/jobs/{self.job_name}/executions/{execution_id}"
            
            # Call get_execution API
            execution = self.client.get_execution(name=execution_name)
            
            # Process response into detailed execution information
            execution_details = {
                'execution_id': execution_id,
                'status': execution.status.state.name,
                'start_time': execution.creation_timestamp.isoformat() if execution.creation_timestamp else None,
                'end_time': execution.completion_timestamp.isoformat() if execution.completion_timestamp else None,
                'duration': None,
                'logs_url': execution.logging_uri if hasattr(execution, 'logging_uri') else None,
                'error': None,
                'task_count': len(execution.tasks) if hasattr(execution, 'tasks') else 0,
                'tasks': []
            }
            
            # Calculate duration if both timestamps are available
            if execution.creation_timestamp and execution.completion_timestamp:
                duration = (execution.completion_timestamp - execution.creation_timestamp).total_seconds()
                execution_details['duration'] = duration
            
            # Extract error details if present
            if execution.status.state.name == 'FAILED' and hasattr(execution, 'status') and hasattr(execution.status, 'error'):
                execution_details['error'] = {
                    'code': execution.status.error.code if hasattr(execution.status.error, 'code') else None,
                    'message': execution.status.error.message if hasattr(execution.status.error, 'message') else None
                }
            
            # Extract task details if available
            if hasattr(execution, 'tasks'):
                for task in execution.tasks:
                    task_details = {
                        'index': task.index if hasattr(task, 'index') else None,
                        'status': task.status.state.name if hasattr(task, 'status') else None,
                        'start_time': task.creation_timestamp.isoformat() if hasattr(task, 'creation_timestamp') else None,
                        'end_time': task.completion_timestamp.isoformat() if hasattr(task, 'completion_timestamp') else None,
                        'error': None
                    }
                    
                    # Extract task error details if present
                    if hasattr(task, 'status') and task.status.state.name == 'FAILED' and hasattr(task.status, 'error'):
                        task_details['error'] = {
                            'code': task.status.error.code if hasattr(task.status.error, 'code') else None,
                            'message': task.status.error.message if hasattr(task.status.error, 'message') else None
                        }
                    
                    execution_details['tasks'].append(task_details)
            
            logger.info(f"Retrieved details for execution {execution_id}")
            return execution_details
            
        except Exception as e:
            logger.error(f"Error retrieving execution details: {e}")
            return {'execution_id': execution_id, 'error': str(e)}
    
    def analyze_executions(self, executions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze job execution history
        
        Args:
            executions: List of execution dictionaries
            
        Returns:
            Analysis results
        """
        return analyze_job_executions(executions)
    
    def check_latest(self, executions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Check status of latest execution
        
        Args:
            executions: List of execution dictionaries
            
        Returns:
            Latest execution status
        """
        return check_latest_execution(executions)
    
    def generate_report(self, executions: List[Dict[str, Any]], analysis: Dict[str, Any], 
                       latest_status: Dict[str, Any], log_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate comprehensive status report
        
        Args:
            executions: List of execution dictionaries
            analysis: Execution analysis results
            latest_status: Latest execution status
            log_analysis: Optional log analysis results
            
        Returns:
            Complete status report
        """
        return generate_status_report(executions, analysis, latest_status, log_analysis)


def parse_arguments():
    """
    Parse command line arguments for the script
    
    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Check the status of the Budget Management Application Cloud Run job'
    )
    
    parser.add_argument(
        '--project-id',
        default=DEFAULT_PROJECT_ID,
        help='Google Cloud project ID (defaults to GOOGLE_CLOUD_PROJECT env var)'
    )
    
    parser.add_argument(
        '--job-name',
        default=DEFAULT_JOB_NAME,
        help=f'Name of the Cloud Run job (default: {DEFAULT_JOB_NAME})'
    )
    
    parser.add_argument(
        '--region',
        default=DEFAULT_REGION,
        help=f'Region where the job is deployed (default: {DEFAULT_REGION})'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=DEFAULT_DAYS,
        help=f'Number of days of execution history to analyze (default: {DEFAULT_DAYS})'
    )
    
    parser.add_argument(
        '--format',
        choices=['json', 'text', 'markdown'],
        default=DEFAULT_OUTPUT_FORMAT,
        help=f'Output format (default: {DEFAULT_OUTPUT_FORMAT})'
    )
    
    parser.add_argument(
        '--output',
        default=DEFAULT_OUTPUT_FILE,
        help=f'Output file path (default: {DEFAULT_OUTPUT_FILE})'
    )
    
    parser.add_argument(
        '--email',
        action='store_true',
        help='Send email notification if issues are detected'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser.parse_args()


def get_job_executions(project_id: str, job_name: str, region: str, days: int) -> List[Dict[str, Any]]:
    """
    Retrieve job execution history from Google Cloud Run
    
    Args:
        project_id: Google Cloud project ID
        job_name: Name of the Cloud Run job
        region: Region where the job is deployed
        days: Number of days of history to retrieve
        
    Returns:
        List of job execution details
    """
    try:
        # Initialize Cloud Run Jobs client
        client = run_v2.JobsClient()
        
        # Calculate start date based on days parameter
        start_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        
        # Construct parent resource name
        parent = f"projects/{project_id}/locations/{region}/jobs/{job_name}"
        
        # Call list_executions API
        request = run_v2.ListExecutionsRequest(
            parent=parent,
            # No filtering by time in API, will filter results after
            limit=100  # Retrieve up to 100 executions
        )
        
        executions = client.list_executions(request=request)
        
        # Process response into standardized execution details
        execution_details = []
        for execution in executions:
            # Convert the execution to a Python dictionary
            creation_time = execution.creation_timestamp
            completion_time = execution.completion_timestamp
            
            # Skip executions older than the specified days
            if creation_time and creation_time < start_time:
                continue
            
            execution_dict = {
                'execution_id': execution.name.split('/')[-1],
                'status': execution.status.state.name,
                'start_time': creation_time.isoformat() if creation_time else None,
                'end_time': completion_time.isoformat() if completion_time else None,
                'duration': None,
                'logs_url': execution.logging_uri if hasattr(execution, 'logging_uri') else None,
                'error': None
            }
            
            # Calculate duration if both timestamps are available
            if creation_time and completion_time:
                duration = (completion_time - creation_time).total_seconds()
                execution_dict['duration'] = duration
            
            # Extract error details if present
            if execution.status.state.name == 'FAILED' and hasattr(execution.status, 'error'):
                execution_dict['error'] = {
                    'code': execution.status.error.code if hasattr(execution.status.error, 'code') else None,
                    'message': execution.status.error.message if hasattr(execution.status.error, 'message') else None
                }
            
            execution_details.append(execution_dict)
        
        logger.info(f"Retrieved {len(execution_details)} job executions via API")
        return execution_details
        
    except Exception as e:
        logger.error(f"Error retrieving job executions via API: {e}")
        logger.info("Falling back to gcloud CLI method")
        return get_job_executions_cli(project_id, job_name, region, days)


def get_job_executions_cli(project_id: str, job_name: str, region: str, days: int) -> List[Dict[str, Any]]:
    """
    Fallback method to retrieve job execution history using gcloud CLI
    
    Args:
        project_id: Google Cloud project ID
        job_name: Name of the Cloud Run job
        region: Region where the job is deployed
        days: Number of days of history to retrieve
        
    Returns:
        List of job execution details
    """
    try:
        # Construct gcloud command
        command = [
            'gcloud', 'run', 'jobs', 'executions', 'list',
            f'--project={project_id}',
            f'--region={region}',
            f'--job={job_name}',
            '--format=json',
            '--limit=100'
        ]
        
        # Execute command
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        # Parse JSON output
        executions = json.loads(result.stdout)
        
        # Calculate start date based on days parameter
        start_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        start_time_str = start_time.isoformat()
        
        # Process response into standardized execution details
        execution_details = []
        for execution in executions:
            # Filter by creation time
            creation_time = execution.get('metadata', {}).get('creationTimestamp')
            if creation_time and creation_time < start_time_str:
                continue
            
            # Extract data from CLI output
            execution_id = execution.get('name', '').split('/')[-1]
            status = execution.get('status', {}).get('conditions', [{}])[0].get('type', 'UNKNOWN')
            
            completion_time = execution.get('status', {}).get('completionTime')
            
            execution_dict = {
                'execution_id': execution_id,
                'status': status,
                'start_time': creation_time,
                'end_time': completion_time,
                'duration': None,
                'logs_url': execution.get('status', {}).get('logUri'),
                'error': None
            }
            
            # Calculate duration if both timestamps are available
            if creation_time and completion_time:
                try:
                    start_dt = datetime.datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
                    end_dt = datetime.datetime.fromisoformat(completion_time.replace('Z', '+00:00'))
                    duration = (end_dt - start_dt).total_seconds()
                    execution_dict['duration'] = duration
                except (ValueError, TypeError):
                    pass
            
            # Extract error details if present
            if status == 'FAILED':
                error_message = execution.get('status', {}).get('conditions', [{}])[0].get('message')
                if error_message:
                    execution_dict['error'] = {
                        'message': error_message
                    }
            
            execution_details.append(execution_dict)
        
        logger.info(f"Retrieved {len(execution_details)} job executions via CLI")
        return execution_details
        
    except Exception as e:
        logger.error(f"Error retrieving job executions via CLI: {e}")
        return []


def analyze_job_executions(executions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze job execution history to identify patterns and issues
    
    Args:
        executions: List of execution dictionaries
        
    Returns:
        Analysis results including success rate, duration stats, and issues
    """
    if not executions:
        return {'error': 'No execution data available'}
    
    # Count executions by status
    total_executions = len(executions)
    successful_executions = sum(1 for ex in executions if ex['status'] == 'SUCCEEDED')
    failed_executions = sum(1 for ex in executions if ex['status'] == 'FAILED')
    other_executions = total_executions - successful_executions - failed_executions
    
    # Calculate success rate
    success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0
    
    # Extract durations for successful executions
    durations = [ex['duration'] for ex in executions if ex['status'] == 'SUCCEEDED' and ex['duration'] is not None]
    
    # Calculate duration statistics
    duration_stats = {}
    if durations:
        durations.sort()
        duration_stats = {
            'min': min(durations),
            'max': max(durations),
            'avg': sum(durations) / len(durations),
            'median': durations[len(durations) // 2],
            'p95': durations[int(len(durations) * 0.95)] if len(durations) >= 20 else None,
            'count': len(durations)
        }
    
    # Check for execution time trends
    time_trend = None
    if len(durations) >= 3:
        # Simple trend detection by comparing first third to last third
        third = len(durations) // 3
        first_third_avg = sum(durations[:third]) / third
        last_third_avg = sum(durations[-third:]) / third
        
        if last_third_avg > first_third_avg * 1.2:  # 20% increase
            time_trend = 'increasing'
        elif first_third_avg > last_third_avg * 1.2:  # 20% decrease
            time_trend = 'decreasing'
        else:
            time_trend = 'stable'
    
    # Extract common error patterns
    error_patterns = {}
    for ex in executions:
        if ex['status'] == 'FAILED' and ex['error'] and 'message' in ex['error']:
            error_message = ex['error']['message']
            # Extract key part of error message (first line or first 100 chars)
            key_error = error_message.split('\n')[0][:100]
            
            if key_error in error_patterns:
                error_patterns[key_error]['count'] += 1
                error_patterns[key_error]['executions'].append(ex['execution_id'])
            else:
                error_patterns[key_error] = {
                    'count': 1,
                    'message': error_message,
                    'executions': [ex['execution_id']]
                }
    
    # Format error patterns as a list sorted by count
    error_list = [
        {'pattern': k, 'count': v['count'], 'message': v['message'], 'executions': v['executions']}
        for k, v in error_patterns.items()
    ]
    error_list.sort(key=lambda x: x['count'], reverse=True)
    
    # Compile analysis results
    analysis = {
        'total_executions': total_executions,
        'successful_executions': successful_executions,
        'failed_executions': failed_executions,
        'other_executions': other_executions,
        'success_rate': success_rate,
        'duration_stats': duration_stats,
        'time_trend': time_trend,
        'error_patterns': error_list,
        'analysis_timestamp': datetime.datetime.now().isoformat()
    }
    
    return analysis


def check_latest_execution(executions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Check the status of the most recent job execution
    
    Args:
        executions: List of execution dictionaries
        
    Returns:
        Status details of the latest execution
    """
    if not executions:
        return {'error': 'No execution data available'}
    
    # Sort executions by start time (latest first)
    sorted_executions = sorted(
        [ex for ex in executions if ex['start_time']],
        key=lambda x: x['start_time'],
        reverse=True
    )
    
    if not sorted_executions:
        return {'error': 'No executions with valid timestamps'}
    
    # Get the latest execution
    latest = sorted_executions[0]
    
    # Calculate time since execution
    try:
        start_time = datetime.datetime.fromisoformat(latest['start_time'].replace('Z', '+00:00'))
        time_since = (datetime.datetime.now(datetime.timezone.utc) - start_time).total_seconds()
        time_since_hours = time_since / 3600
    except (ValueError, TypeError):
        time_since = None
        time_since_hours = None
    
    # Create status response
    status = {
        'execution_id': latest['execution_id'],
        'status': latest['status'],
        'start_time': latest['start_time'],
        'end_time': latest['end_time'],
        'duration': latest['duration'],
        'logs_url': latest['logs_url'],
        'is_successful': latest['status'] == 'SUCCEEDED',
        'error': latest.get('error'),
        'time_since_seconds': time_since,
        'time_since_hours': time_since_hours
    }
    
    return status


def generate_status_report(executions: List[Dict[str, Any]], analysis: Dict[str, Any], 
                         latest_status: Dict[str, Any], log_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generate a comprehensive job status report
    
    Args:
        executions: List of execution dictionaries
        analysis: Execution analysis results
        latest_status: Latest execution status
        log_analysis: Optional log analysis results
        
    Returns:
        Complete job status report
    """
    # Create base report structure
    report = {
        'timestamp': datetime.datetime.now().isoformat(),
        'job_info': {
            'name': os.environ.get('JOB_NAME', 'budget-management-job'),
            'project': os.environ.get('GOOGLE_CLOUD_PROJECT', 'unknown'),
            'region': os.environ.get('JOB_REGION', 'us-east1')
        },
        'latest_execution': latest_status,
        'execution_analysis': analysis
    }
    
    # Add log analysis if available
    if log_analysis:
        report['log_analysis'] = log_analysis
    
    # Add recommendations based on findings
    recommendations = []
    
    # Check success rate
    if analysis.get('success_rate', 100) < 90:
        recommendations.append({
            'type': 'warning',
            'message': f"Low success rate ({analysis['success_rate']:.1f}%) detected. Review error patterns and logs."
        })
    
    # Check for increasing execution time
    if analysis.get('time_trend') == 'increasing':
        recommendations.append({
            'type': 'warning',
            'message': "Execution time is trending upward. Consider performance optimization."
        })
    
    # Check latest execution
    if not latest_status.get('is_successful'):
        recommendations.append({
            'type': 'critical',
            'message': f"Latest execution failed: {latest_status.get('error', {}).get('message', 'Unknown error')}"
        })
    
    # Check time since last execution
    if latest_status.get('time_since_hours', 0) > 168:  # > 7 days
        recommendations.append({
            'type': 'critical',
            'message': f"No successful execution in over 7 days. Check scheduling and job health."
        })
    elif latest_status.get('time_since_hours', 0) > 48:  # > 2 days
        recommendations.append({
            'type': 'warning',
            'message': f"No execution in over 2 days. Verify job scheduling is working correctly."
        })
    
    # Add recommendations to report
    report['recommendations'] = recommendations
    
    return report


def save_report(report: Dict[str, Any], output_format: str, output_file: str) -> str:
    """
    Save the job status report to a file
    
    Args:
        report: Status report dictionary
        output_format: Format (json, text, markdown)
        output_file: Path to output file
        
    Returns:
        Path to the saved report file
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    if output_format == 'json':
        # JSON format
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
    
    elif output_format == 'text':
        # Plain text format
        with open(output_file, 'w') as f:
            f.write(f"JOB STATUS REPORT - {report['timestamp']}\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"JOB: {report['job_info']['name']} (Project: {report['job_info']['project']}, Region: {report['job_info']['region']})\n\n")
            
            # Latest execution
            latest = report['latest_execution']
            f.write("LATEST EXECUTION:\n")
            f.write(f"Status: {latest['status']}\n")
            f.write(f"Execution ID: {latest['execution_id']}\n")
            f.write(f"Start time: {latest['start_time']}\n")
            f.write(f"End time: {latest['end_time'] or 'N/A'}\n")
            f.write(f"Duration: {latest['duration']:.1f} seconds\n" if latest['duration'] else "Duration: N/A\n")
            f.write(f"Logs: {latest['logs_url'] or 'N/A'}\n")
            
            if not latest['is_successful'] and latest.get('error'):
                f.write("\nERROR DETAILS:\n")
                f.write(f"{latest['error'].get('message', 'Unknown error')}\n")
            
            # Execution analysis
            analysis = report['execution_analysis']
            f.write("\nEXECUTION ANALYSIS:\n")
            f.write(f"Total executions: {analysis['total_executions']}\n")
            f.write(f"Success rate: {analysis['success_rate']:.1f}%\n")
            f.write(f"Successful: {analysis['successful_executions']}, Failed: {analysis['failed_executions']}, Other: {analysis['other_executions']}\n")
            
            if analysis.get('duration_stats'):
                stats = analysis['duration_stats']
                f.write("\nDURATION STATISTICS (seconds):\n")
                f.write(f"Min: {stats['min']:.1f}, Max: {stats['max']:.1f}, Avg: {stats['avg']:.1f}, Median: {stats['median']:.1f}\n")
                if stats.get('p95'):
                    f.write(f"95th percentile: {stats['p95']:.1f}\n")
                f.write(f"Time trend: {analysis['time_trend'] or 'Not enough data'}\n")
            
            if analysis.get('error_patterns'):
                f.write("\nCOMMON ERROR PATTERNS:\n")
                for i, pattern in enumerate(analysis['error_patterns'][:5]):  # Top 5
                    f.write(f"{i+1}. Count: {pattern['count']}, Pattern: {pattern['pattern']}\n")
            
            # Recommendations
            if report.get('recommendations'):
                f.write("\nRECOMMENDATIONS:\n")
                for i, rec in enumerate(report['recommendations']):
                    f.write(f"{i+1}. [{rec['type'].upper()}] {rec['message']}\n")
    
    elif output_format == 'markdown':
        # Markdown format
        with open(output_file, 'w') as f:
            f.write(f"# Job Status Report - {report['job_info']['name']}\n\n")
            f.write(f"Generated: {report['timestamp']}\n\n")
            
            f.write("## Job Information\n\n")
            f.write(f"- **Name**: {report['job_info']['name']}\n")
            f.write(f"- **Project**: {report['job_info']['project']}\n")
            f.write(f"- **Region**: {report['job_info']['region']}\n\n")
            
            # Latest execution
            latest = report['latest_execution']
            f.write("## Latest Execution\n\n")
            status_icon = "✅" if latest['is_successful'] else "❌"
            f.write(f"- **Status**: {status_icon} {latest['status']}\n")
            f.write(f"- **Execution ID**: {latest['execution_id']}\n")
            f.write(f"- **Start time**: {latest['start_time']}\n")
            f.write(f"- **End time**: {latest['end_time'] or 'N/A'}\n")
            f.write(f"- **Duration**: {latest['duration']:.1f} seconds\n" if latest['duration'] else "- **Duration**: N/A\n")
            
            if latest.get('logs_url'):
                f.write(f"- **Logs**: [View logs]({latest['logs_url']})\n")
            
            if not latest['is_successful'] and latest.get('error'):
                f.write("\n### Error Details\n\n")
                f.write("```\n")
                f.write(f"{latest['error'].get('message', 'Unknown error')}\n")
                f.write("```\n")
            
            # Execution analysis
            analysis = report['execution_analysis']
            f.write("\n## Execution Analysis\n\n")
            f.write(f"- **Total executions**: {analysis['total_executions']}\n")
            f.write(f"- **Success rate**: {analysis['success_rate']:.1f}%\n")
            f.write(f"- **Execution breakdown**: {analysis['successful_executions']} successful, {analysis['failed_executions']} failed, {analysis['other_executions']} other\n")
            
            if analysis.get('duration_stats'):
                stats = analysis['duration_stats']
                f.write("\n### Duration Statistics (seconds)\n\n")
                f.write("| Metric | Value |\n")
                f.write("| ------ | ----- |\n")
                f.write(f"| Minimum | {stats['min']:.1f} |\n")
                f.write(f"| Maximum | {stats['max']:.1f} |\n")
                f.write(f"| Average | {stats['avg']:.1f} |\n")
                f.write(f"| Median | {stats['median']:.1f} |\n")
                if stats.get('p95'):
                    f.write(f"| 95th percentile | {stats['p95']:.1f} |\n")
                f.write(f"\n**Time trend**: {analysis['time_trend'] or 'Not enough data'}\n")
            
            if analysis.get('error_patterns'):
                f.write("\n### Common Error Patterns\n\n")
                f.write("| Count | Pattern |\n")
                f.write("| ----- | ------- |\n")
                for pattern in analysis['error_patterns'][:5]:  # Top 5
                    f.write(f"| {pattern['count']} | {pattern['pattern']} |\n")
            
            # Recommendations
            if report.get('recommendations'):
                f.write("\n## Recommendations\n\n")
                for rec in report['recommendations']:
                    icon = "⚠️" if rec['type'] == 'warning' else "🔴"
                    f.write(f"- {icon} **{rec['type'].upper()}**: {rec['message']}\n")
    
    logger.info(f"Saved report to {output_file} in {output_format} format")
    return output_file


def send_alert_email(report: Dict[str, Any], recipient_email: str) -> bool:
    """
    Send an email alert for job execution issues
    
    Args:
        report: Status report dictionary
        recipient_email: Email address to send alert to
        
    Returns:
        True if email sent successfully, False otherwise
    """
    # Check if alert is needed
    needs_alert = False
    critical_issues = []
    warning_issues = []
    
    # Check latest execution
    if not report['latest_execution'].get('is_successful'):
        needs_alert = True
        critical_issues.append(f"Latest job execution failed: {report['latest_execution'].get('error', {}).get('message', 'Unknown error')}")
    
    # Check success rate
    if report['execution_analysis'].get('success_rate', 100) < 80:
        needs_alert = True
        warning_issues.append(f"Low success rate: {report['execution_analysis']['success_rate']:.1f}%")
    
    # Check recommendations
    for rec in report.get('recommendations', []):
        if rec['type'] == 'critical':
            needs_alert = True
            critical_issues.append(rec['message'])
        elif rec['type'] == 'warning':
            warning_issues.append(rec['message'])
    
    if not needs_alert:
        logger.info("No critical issues detected, skipping alert email")
        return False
    
    try:
        from ../../backend.services.authentication_service import AuthenticationService
        
        # Prepare email content
        job_name = report['job_info']['name']
        
        # Subject line with status
        if critical_issues:
            subject = f"🔴 ALERT: {job_name} job execution failure"
        else:
            subject = f"⚠️ WARNING: {job_name} job status issues"
        
        # Email body
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: {'#d32f2f' if critical_issues else '#f57c00'};">
                {'Critical Alert' if critical_issues else 'Warning'}: Budget Management Job Status
            </h2>
            
            <p>The following issues were detected with the <strong>{job_name}</strong> job:</p>
            
            {'<h3 style="color: #d32f2f;">Critical Issues:</h3>' if critical_issues else ''}
            {''.join([f'<p>• {issue}</p>' for issue in critical_issues])}
            
            {'<h3 style="color: #f57c00;">Warnings:</h3>' if warning_issues else ''}
            {''.join([f'<p>• {issue}</p>' for issue in warning_issues])}
            
            <h3>Latest Execution Details:</h3>
            <p>
                <strong>Status:</strong> {report['latest_execution']['status']}<br>
                <strong>Execution ID:</strong> {report['latest_execution']['execution_id']}<br>
                <strong>Start time:</strong> {report['latest_execution']['start_time']}<br>
                <strong>End time:</strong> {report['latest_execution'].get('end_time', 'N/A')}
            </p>
            
            <p>
                <a href="{report['latest_execution'].get('logs_url', '#')}" style="color: #1976d2;">
                    View execution logs
                </a>
            </p>
            
            <p style="margin-top: 30px; font-size: 0.8em; color: #757575;">
                This is an automated alert from the Budget Management Application monitoring system.
            </p>
        </body>
        </html>
        """
        
        # Initialize services
        auth_service = AuthenticationService()
        gmail_client = GmailClient(auth_service=auth_service)
        
        # Send email
        result = gmail_client.send_email(
            subject=subject,
            html_content=body,
            recipients=[recipient_email]
        )
        
        logger.info(f"Alert email sent to {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")
        return False


def main():
    """
    Main function that orchestrates job status checking
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        logger.info(f"Starting job status check for {args.job_name} in project {args.project_id}")
        
        # Get job executions
        try:
            # Try to get executions using the client library
            with LoggingContext(logger, "retrieving job executions"):
                job_checker = JobStatusChecker(args.project_id, args.job_name, args.region)
                executions = job_checker.get_executions(days=args.days)
                
                if not executions and job_checker.client:
                    # If client exists but no executions, try the CLI method
                    logger.warning("No executions found using client library, trying CLI method")
                    executions = get_job_executions_cli(args.project_id, args.job_name, args.region, args.days)
        except Exception as e:
            logger.error(f"Error using JobStatusChecker: {e}")
            logger.info("Falling back to direct execution retrieval methods")
            
            try:
                executions = get_job_executions(args.project_id, args.job_name, args.region, args.days)
            except Exception as e2:
                logger.error(f"Error retrieving job executions: {e2}")
                executions = []
                
            if not executions:
                try:
                    executions = get_job_executions_cli(args.project_id, args.job_name, args.region, args.days)
                except Exception as e3:
                    logger.error(f"Error retrieving job executions via CLI: {e3}")
                    return 1
        
        if not executions:
            logger.error("No job executions found")
            return 1
        
        logger.info(f"Retrieved {len(executions)} job executions")
        
        # Analyze job executions
        with LoggingContext(logger, "analyzing job executions"):
            if hasattr(job_checker, 'analyze_executions'):
                analysis = job_checker.analyze_executions(executions)
            else:
                analysis = analyze_job_executions(executions)
        
        # Check latest execution
        with LoggingContext(logger, "checking latest execution"):
            if hasattr(job_checker, 'check_latest'):
                latest_status = job_checker.check_latest(executions)
            else:
                latest_status = check_latest_execution(executions)
        
        # Try to analyze logs
        log_analysis = None
        try:
            with LoggingContext(logger, "analyzing logs"):
                # Get log file path from latest execution logs_url
                if latest_status.get('logs_url'):
                    # This is a placeholder - actual log analysis would require more complex logic
                    # to download and parse Cloud Run logs
                    logger.info("Log analysis not implemented yet - would analyze logs from latest execution")
                
                # Alternatively, use the LogAnalyzer if we have logs locally
                log_analyzer = LogAnalyzer(os.path.join(os.path.dirname(args.output), 'application.log'))
                if os.path.exists(log_analyzer.log_file):
                    log_analyzer.load_logs()
                    log_analyzer.filter_logs(days=args.days)
                    log_analysis = log_analyzer.analyze()
                    logger.info("Log analysis completed successfully")
        except Exception as e:
            logger.warning(f"Error analyzing logs: {e}")
        
        # Generate status report
        with LoggingContext(logger, "generating status report"):
            if hasattr(job_checker, 'generate_report'):
                report = job_checker.generate_report(executions, analysis, latest_status, log_analysis)
            else:
                report = generate_status_report(executions, analysis, latest_status, log_analysis)
        
        # Save report to file
        with LoggingContext(logger, "saving report"):
            save_report(report, args.format, args.output)
        
        # Send alert email if needed
        if args.email or MAINTENANCE_SETTINGS.get('ALERT_ON_ERROR', False):
            with LoggingContext(logger, "checking if alert needed"):
                recipient = MAINTENANCE_SETTINGS.get('ALERT_EMAIL', 'njdifiore@gmail.com')
                if not latest_status.get('is_successful') or any(rec['type'] == 'critical' for rec in report.get('recommendations', [])):
                    send_alert_email(report, recipient)
        
        # Log job status
        success_status = latest_status.get('is_successful', False)
        if success_status:
            logger.info(f"Job status check completed - latest execution is successful")
        else:
            logger.error(f"Job status check completed - latest execution has failed")
        
        # Exit with appropriate code based on latest execution status
        return 0 if success_status else 1
        
    except Exception as e:
        logger.error(f"Error checking job status: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())