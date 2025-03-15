#!/usr/bin/env python3
"""
A utility script for debugging the Budget Management Application's Cloud Run job.
This script provides a command-line interface to diagnose issues, inspect component states,
and troubleshoot failures in the weekly budget processing job. It offers detailed logging,
component-level testing, and API connectivity validation to help identify and resolve problems.
"""

import os
import sys
import argparse
import subprocess
import json
import time
import importlib
import traceback

# Import internal modules
from ..config.logging_setup import get_script_logger, LoggingContext
from ..config.script_settings import SCRIPT_SETTINGS, get_env_var
from ..utils.api_testing import test_all_apis, format_test_results
from .trigger_job import trigger_job, check_gcloud_installed

# Set up logger
logger = get_script_logger('debug_job', debug=True)

# Default values from environment
DEFAULT_PROJECT_ID = get_env_var('GCP_PROJECT_ID', '')
DEFAULT_REGION = get_env_var('GCP_REGION', 'us-east1')
DEFAULT_JOB_NAME = get_env_var('CLOUD_RUN_JOB_NAME', 'budget-management-job')

# List of application components
COMPONENTS = ['transaction_retriever', 'transaction_categorizer', 'budget_analyzer', 'insight_generator', 'report_distributor', 'savings_automator']


def get_job_logs(project_id: str, job_name: str, execution_id: str, limit: int = 100) -> list:
    """
    Retrieves logs for a specific Cloud Run job execution.
    
    Args:
        project_id: Google Cloud project ID
        job_name: Name of the Cloud Run job
        execution_id: Execution ID to retrieve logs for
        limit: Maximum number of log entries to retrieve
        
    Returns:
        List of log entries for the specified job execution
    """
    try:
        # Construct filter for the specific job execution
        filter_str = (
            f'resource.type="cloud_run_job" AND '
            f'resource.labels.job_name="{job_name}" AND '
            f'resource.labels.execution_name="{execution_id}"'
        )
        
        # Construct gcloud command to retrieve logs
        cmd = [
            'gcloud', 'logging', 'read',
            filter_str,
            f'--project={project_id}',
            '--format=json',
            f'--limit={limit}'
        ]
        
        logger.debug(f"Executing command: {' '.join(cmd)}")
        
        # Execute command
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        
        # Check if command was successful
        if result.returncode == 0:
            # Parse JSON output
            logs = json.loads(result.stdout.decode())
            logger.info(f"Retrieved {len(logs)} log entries for execution {execution_id}")
            return logs
        else:
            error = result.stderr.decode().strip()
            logger.error(f"Failed to retrieve logs: {error}")
            return []
    
    except Exception as e:
        logger.error(f"Error retrieving job logs: {str(e)}")
        return []


def analyze_logs(logs: list) -> dict:
    """
    Analyzes job logs to identify errors and issues.
    
    Args:
        logs: List of log entries to analyze
        
    Returns:
        Analysis results with error counts, warnings, and potential issues
    """
    try:
        # Initialize analysis results
        results = {
            'error_count': 0,
            'warning_count': 0,
            'info_count': 0,
            'errors_by_component': {},
            'warnings_by_component': {},
            'api_errors': {},
            'error_patterns': {},
            'potential_issues': []
        }
        
        # Process each log entry
        for entry in logs:
            # Extract severity and component
            severity = entry.get('severity', '').upper()
            
            # Extract component from jsonPayload if available
            component = 'unknown'
            if 'jsonPayload' in entry:
                component = entry.get('jsonPayload', {}).get('component', 'unknown')
            
            # Count by severity
            if severity == 'ERROR' or severity == 'CRITICAL':
                results['error_count'] += 1
                
                # Track errors by component
                if component not in results['errors_by_component']:
                    results['errors_by_component'][component] = 0
                results['errors_by_component'][component] += 1
                
                # Check for API errors
                message = entry.get('jsonPayload', {}).get('message', '')
                if 'API Error' in message or 'failed to connect' in message.lower():
                    api_name = 'unknown'
                    
                    # Try to extract API name
                    if 'Capital One' in message:
                        api_name = 'Capital One'
                    elif 'Google Sheets' in message:
                        api_name = 'Google Sheets'
                    elif 'Gemini' in message:
                        api_name = 'Gemini'
                    elif 'Gmail' in message:
                        api_name = 'Gmail'
                    
                    if api_name not in results['api_errors']:
                        results['api_errors'][api_name] = 0
                    results['api_errors'][api_name] += 1
            
            elif severity == 'WARNING':
                results['warning_count'] += 1
                
                # Track warnings by component
                if component not in results['warnings_by_component']:
                    results['warnings_by_component'][component] = 0
                results['warnings_by_component'][component] += 1
            
            elif severity == 'INFO':
                results['info_count'] += 1
        
        # Identify common error patterns
        if results['error_count'] > 0:
            # Add potential issues based on error patterns
            if 'Capital One' in results['api_errors']:
                results['potential_issues'].append('Capital One API connectivity issues detected')
            
            if 'Google Sheets' in results['api_errors']:
                results['potential_issues'].append('Google Sheets API access issues detected')
            
            if 'authentication' in str(logs).lower():
                results['potential_issues'].append('Authentication issues detected - check credentials')
            
            if 'timeout' in str(logs).lower():
                results['potential_issues'].append('API timeout issues detected - check network connectivity')
                
            # Check for component-specific issues
            for component, count in results['errors_by_component'].items():
                if count > 2:  # If a component has multiple errors
                    results['potential_issues'].append(f'Multiple errors in {component} component')
        
        return results
    
    except Exception as e:
        logger.error(f"Error analyzing logs: {str(e)}")
        return {
            'error_count': 0,
            'warning_count': 0,
            'info_count': 0,
            'error': f"Analysis failed: {str(e)}"
        }


def get_job_details(project_id: str, region: str, job_name: str) -> dict:
    """
    Gets detailed information about a Cloud Run job.
    
    Args:
        project_id: Google Cloud project ID
        region: Google Cloud region
        job_name: Name of the Cloud Run job
        
    Returns:
        Job details including configuration, status, and recent executions
    """
    try:
        # Get job description
        cmd = [
            'gcloud', 'run', 'jobs', 'describe', job_name,
            '--project', project_id,
            '--region', region,
            '--format', 'json'
        ]
        
        logger.debug(f"Executing command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        
        if result.returncode != 0:
            error = result.stderr.decode().strip()
            logger.error(f"Failed to get job details: {error}")
            return {'error': error}
        
        # Parse job details
        job_details = json.loads(result.stdout.decode())
        
        # Get recent executions
        recent_executions = get_recent_executions(project_id, region, job_name, 5)
        
        # Combine job details with recent executions
        job_details['recent_executions'] = recent_executions
        
        return job_details
    
    except Exception as e:
        logger.error(f"Error getting job details: {str(e)}")
        return {'error': str(e)}


def get_recent_executions(project_id: str, region: str, job_name: str, limit: int = 5) -> list:
    """
    Gets a list of recent job executions.
    
    Args:
        project_id: Google Cloud project ID
        region: Google Cloud region
        job_name: Name of the Cloud Run job
        limit: Maximum number of executions to retrieve
        
    Returns:
        List of recent job executions with status and timestamps
    """
    try:
        cmd = [
            'gcloud', 'run', 'jobs', 'executions', 'list',
            '--job', job_name,
            '--project', project_id,
            '--region', region,
            '--limit', str(limit),
            '--format', 'json'
        ]
        
        logger.debug(f"Executing command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        
        if result.returncode != 0:
            error = result.stderr.decode().strip()
            logger.error(f"Failed to get recent executions: {error}")
            return []
        
        # Parse executions list
        executions = json.loads(result.stdout.decode())
        
        # Extract relevant information
        simplified_executions = []
        for execution in executions:
            simplified_executions.append({
                'id': execution.get('name', '').split('/')[-1],
                'status': execution.get('status', {}).get('condition', {}).get('state', 'UNKNOWN'),
                'start_time': execution.get('status', {}).get('startTime', ''),
                'completion_time': execution.get('status', {}).get('completionTime', '')
            })
        
        return simplified_executions
    
    except Exception as e:
        logger.error(f"Error getting recent executions: {str(e)}")
        return []


def test_component(component_name: str) -> dict:
    """
    Tests a specific component of the Budget Management Application.
    
    Args:
        component_name: Name of the component to test
        
    Returns:
        Test results for the component
    """
    if component_name not in COMPONENTS:
        logger.error(f"Invalid component name: {component_name}")
        return {
            'component': component_name,
            'status': 'error',
            'error': f"Invalid component name: {component_name}"
        }
    
    try:
        logger.info(f"Testing component: {component_name}")
        
        # Try to import the component module
        try:
            module_path = f"../../backend.components.{component_name}"
            module = importlib.import_module(module_path)
            logger.debug(f"Successfully imported module: {module_path}")
        except ImportError as e:
            logger.error(f"Failed to import component module: {str(e)}")
            return {
                'component': component_name,
                'status': 'error',
                'error': f"Module import failed: {str(e)}"
            }
        
        # Try to create an instance of the component class
        try:
            # Get the class name by converting snake_case to CamelCase
            class_name = ''.join(word.capitalize() for word in component_name.split('_'))
            component_class = getattr(module, class_name)
            
            # Create an instance
            component = component_class()
            logger.debug(f"Successfully created instance of {class_name}")
        except (AttributeError, TypeError) as e:
            logger.error(f"Failed to create component instance: {str(e)}")
            return {
                'component': component_name,
                'status': 'error',
                'error': f"Component instantiation failed: {str(e)}"
            }
        
        # Test component initialization
        initialization_results = {
            'initialized': hasattr(component, 'execute'),
        }
        
        # Test authentication if available
        auth_results = {}
        if hasattr(component, 'authenticate'):
            try:
                auth_result = component.authenticate()
                auth_results = {
                    'authentication': 'success' if auth_result else 'failed'
                }
            except Exception as e:
                auth_results = {
                    'authentication': 'failed',
                    'error': str(e)
                }
        
        # Test health check if available
        health_results = {}
        if hasattr(component, 'health_check'):
            try:
                health_result = component.health_check()
                health_results = {
                    'health_check': 'success' if health_result else 'failed'
                }
            except Exception as e:
                health_results = {
                    'health_check': 'failed',
                    'error': str(e)
                }
        
        # Combine results
        results = {
            'component': component_name,
            'status': 'success',
            'initialization': initialization_results,
        }
        
        if auth_results:
            results['authentication'] = auth_results
        
        if health_results:
            results['health_check'] = health_results
        
        logger.info(f"Component test completed successfully: {component_name}")
        return results
    
    except Exception as e:
        logger.error(f"Error testing component {component_name}: {str(e)}")
        return {
            'component': component_name,
            'status': 'error',
            'error': str(e)
        }


def test_all_components() -> dict:
    """
    Tests all components of the Budget Management Application.
    
    Returns:
        Test results for all components
    """
    results = {
        'overall_status': 'success',
        'component_results': {}
    }
    
    for component in COMPONENTS:
        logger.info(f"Testing component: {component}")
        component_results = test_component(component)
        results['component_results'][component] = component_results
        
        # If any component test fails, set overall status to failed
        if component_results.get('status') == 'error':
            results['overall_status'] = 'failed'
    
    logger.info(f"All component tests completed. Overall status: {results['overall_status']}")
    return results


def check_environment() -> dict:
    """
    Checks the execution environment for required configurations.
    
    Returns:
        Environment check results
    """
    results = {
        'status': 'success',
        'checks': {}
    }
    
    # Check required environment variables
    env_vars = [
        'GOOGLE_CLOUD_PROJECT',
        'WEEKLY_SPENDING_SHEET_ID',
        'MASTER_BUDGET_SHEET_ID'
    ]
    
    missing_vars = []
    for var in env_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        results['checks']['environment_variables'] = {
            'status': 'failed',
            'missing_variables': missing_vars
        }
        results['status'] = 'failed'
    else:
        results['checks']['environment_variables'] = {
            'status': 'success'
        }
    
    # Check for credential files
    credential_files = [
        'credentials/capital-one-credentials.json',
        'credentials/google-sheets-credentials.json',
        'credentials/gmail-credentials.json'
    ]
    
    missing_files = []
    for file in credential_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        results['checks']['credential_files'] = {
            'status': 'failed',
            'missing_files': missing_files
        }
        results['status'] = 'failed'
    else:
        results['checks']['credential_files'] = {
            'status': 'success'
        }
    
    # Check for gcloud CLI
    if not check_gcloud_installed():
        results['checks']['gcloud_cli'] = {
            'status': 'failed',
            'error': 'gcloud CLI not installed or not in PATH'
        }
        results['status'] = 'failed'
    else:
        results['checks']['gcloud_cli'] = {
            'status': 'success'
        }
    
    # Check for Python dependencies
    try:
        import requests
        import google.cloud
        import pandas
        
        results['checks']['python_dependencies'] = {
            'status': 'success'
        }
    except ImportError as e:
        results['checks']['python_dependencies'] = {
            'status': 'failed',
            'error': f"Missing dependency: {str(e)}"
        }
        results['status'] = 'failed'
    
    logger.info(f"Environment check completed. Status: {results['status']}")
    return results


def simulate_error(error_type: str, component: str) -> bool:
    """
    Simulates a specific error condition for testing error handling.
    
    Args:
        error_type: Type of error to simulate
        component: Component to simulate the error in
        
    Returns:
        True if error simulation was successful
    """
    # Validate error type
    valid_error_types = [
        'api_timeout', 
        'authentication_failure', 
        'data_validation', 
        'network_error',
        'out_of_memory'
    ]
    
    if error_type not in valid_error_types:
        logger.error(f"Invalid error type: {error_type}")
        return False
    
    # Validate component
    if component not in COMPONENTS and component != 'all':
        logger.error(f"Invalid component: {component}")
        return False
    
    try:
        logger.info(f"Simulating {error_type} error in {component}")
        
        # Set environment variables to trigger the error simulation
        os.environ['SIMULATE_ERROR_TYPE'] = error_type
        os.environ['SIMULATE_ERROR_COMPONENT'] = component
        
        # Trigger the job with error simulation
        logger.info("Triggering job with error simulation...")
        job_result = trigger_job(
            project_id=DEFAULT_PROJECT_ID,
            region=DEFAULT_REGION,
            job_name=DEFAULT_JOB_NAME,
            wait=True,
            env_vars={
                'SIMULATE_ERROR_TYPE': error_type,
                'SIMULATE_ERROR_COMPONENT': component
            }
        )
        
        # Clear the environment variables
        os.environ.pop('SIMULATE_ERROR_TYPE', None)
        os.environ.pop('SIMULATE_ERROR_COMPONENT', None)
        
        if job_result.get('status') in ['triggered', 'succeeded']:
            logger.info("Error simulation job triggered successfully")
            return True
        else:
            logger.error(f"Error simulation job failed: {job_result.get('error', 'Unknown error')}")
            return False
    
    except Exception as e:
        logger.error(f"Error simulating {error_type} in {component}: {str(e)}")
        return False


def format_component_results(results: dict, verbose: bool = False) -> str:
    """
    Formats component test results for display.
    
    Args:
        results: Test results to format
        verbose: Whether to include detailed results
        
    Returns:
        Formatted test results string
    """
    output = "Component Test Results\n" + "=" * 22 + "\n\n"
    
    # Add overall status if present
    if 'overall_status' in results:
        status_color = "\033[92m" if results['overall_status'] == 'success' else "\033[91m"
        output += f"Overall Status: {status_color}{results['overall_status']}\033[0m\n\n"
        
        # Format individual component results
        for component, component_results in results.get('component_results', {}).items():
            status = component_results.get('status', 'unknown')
            status_color = "\033[92m" if status == 'success' else "\033[91m"
            
            output += f"Component: {component}\n"
            output += f"Status: {status_color}{status}\033[0m\n"
            
            if verbose and status == 'success':
                # Add initialization results
                init_results = component_results.get('initialization', {})
                output += "Initialization:\n"
                for key, value in init_results.items():
                    output += f"  - {key}: {value}\n"
                
                # Add authentication results if available
                auth_results = component_results.get('authentication', {})
                if auth_results:
                    output += "Authentication:\n"
                    for key, value in auth_results.items():
                        if key != 'error':
                            value_color = "\033[92m" if value == 'success' else "\033[91m"
                            output += f"  - {key}: {value_color}{value}\033[0m\n"
                    
                    if 'error' in auth_results:
                        output += f"  - error: {auth_results['error']}\n"
                
                # Add health check results if available
                health_results = component_results.get('health_check', {})
                if health_results:
                    output += "Health Check:\n"
                    for key, value in health_results.items():
                        if key != 'error':
                            value_color = "\033[92m" if value == 'success' else "\033[91m"
                            output += f"  - {key}: {value_color}{value}\033[0m\n"
                    
                    if 'error' in health_results:
                        output += f"  - error: {health_results['error']}\n"
            
            elif verbose and status == 'error':
                # Show error details
                output += f"Error: {component_results.get('error', 'Unknown error')}\n"
            
            output += "\n"
    else:
        # Format single component test results
        status = results.get('status', 'unknown')
        status_color = "\033[92m" if status == 'success' else "\033[91m"
        
        output += f"Component: {results.get('component', 'unknown')}\n"
        output += f"Status: {status_color}{status}\033[0m\n"
        
        if verbose and status == 'success':
            # Add detailed results
            for key, value in results.items():
                if key not in ['component', 'status'] and isinstance(value, dict):
                    output += f"{key.capitalize()}:\n"
                    for subkey, subvalue in value.items():
                        output += f"  - {subkey}: {subvalue}\n"
        
        elif verbose and status == 'error':
            # Show error details
            output += f"Error: {results.get('error', 'Unknown error')}\n"
    
    return output


def parse_arguments():
    """
    Parses command line arguments for the script.
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Debug utility for the Budget Management Application Cloud Run job'
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
        '--execution-id',
        help='Specific execution ID to debug',
        default=None
    )
    
    parser.add_argument(
        '--component',
        help=f'Specific component to test (one of: {", ".join(COMPONENTS)})',
        choices=COMPONENTS,
        default=None
    )
    
    parser.add_argument(
        '--test-all-components',
        help='Test all components',
        action='store_true'
    )
    
    parser.add_argument(
        '--test-apis',
        help='Test API connectivity',
        action='store_true'
    )
    
    parser.add_argument(
        '--check-environment',
        help='Check execution environment',
        action='store_true'
    )
    
    parser.add_argument(
        '--get-logs',
        help='Retrieve job logs',
        action='store_true'
    )
    
    parser.add_argument(
        '--analyze-logs',
        help='Analyze job logs for issues',
        action='store_true'
    )
    
    parser.add_argument(
        '--simulate-error',
        help='Simulate a specific error for testing error handling',
        choices=['api_timeout', 'authentication_failure', 'data_validation', 'network_error', 'out_of_memory'],
        default=None
    )
    
    parser.add_argument(
        '--verbose',
        help='Enable verbose output',
        action='store_true'
    )
    
    parser.add_argument(
        '--trigger-after-debug',
        help='Trigger job after debugging',
        action='store_true'
    )
    
    return parser.parse_args()


class ComponentTester:
    """
    Class for testing individual components of the Budget Management Application.
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the component tester.
        
        Args:
            verbose: Whether to enable verbose output
        """
        self.results = {}
        self.verbose = verbose
        logger.info("ComponentTester initialized")
    
    def test_component(self, component_name: str) -> dict:
        """
        Tests a specific component by name.
        
        Args:
            component_name: Name of the component to test
            
        Returns:
            Test results for the component
        """
        if component_name not in COMPONENTS:
            logger.error(f"Invalid component name: {component_name}")
            return {
                'component': component_name,
                'status': 'error',
                'error': f"Invalid component name: {component_name}"
            }
        
        with LoggingContext(logger, f"test_component_{component_name}"):
            result = test_component(component_name)
            self.results[component_name] = result
            return result
    
    def test_all(self) -> dict:
        """
        Tests all components.
        
        Returns:
            Test results for all components
        """
        for component in COMPONENTS:
            self.test_component(component)
        
        # Calculate overall status
        overall_status = 'success'
        for component, result in self.results.items():
            if result.get('status') == 'error':
                overall_status = 'failed'
                break
        
        return {
            'overall_status': overall_status,
            'component_results': self.results
        }
    
    def get_results(self) -> dict:
        """
        Gets the current test results.
        
        Returns:
            Current test results
        """
        return self.results
    
    def format_results(self) -> str:
        """
        Formats the test results for display.
        
        Returns:
            Formatted test results string
        """
        if not self.results:
            return "No test results available."
        
        if len(self.results) == 1:
            # Single component test
            component = list(self.results.keys())[0]
            return format_component_results(self.results[component], self.verbose)
        else:
            # Multiple component tests
            overall_status = 'success'
            for component, result in self.results.items():
                if result.get('status') == 'error':
                    overall_status = 'failed'
                    break
            
            return format_component_results({
                'overall_status': overall_status,
                'component_results': self.results
            }, self.verbose)


class LogAnalyzer:
    """
    Class for analyzing job execution logs to identify issues.
    """
    
    def __init__(self, logs: list):
        """
        Initialize the log analyzer with logs.
        
        Args:
            logs: List of log entries to analyze
        """
        self.logs = logs
        self.analysis = {}
        logger.info(f"LogAnalyzer initialized with {len(logs)} log entries")
    
    def analyze(self) -> dict:
        """
        Analyzes the logs to identify issues.
        
        Returns:
            Analysis results
        """
        self.analysis = analyze_logs(self.logs)
        return self.analysis
    
    def get_component_errors(self, component_name: str) -> list:
        """
        Extracts errors specific to a component.
        
        Args:
            component_name: Name of the component to get errors for
            
        Returns:
            List of errors for the specified component
        """
        component_errors = []
        
        for entry in self.logs:
            # Check if log entry is an error for the specified component
            if (entry.get('severity', '').upper() in ['ERROR', 'CRITICAL'] and
                    entry.get('jsonPayload', {}).get('component', '') == component_name):
                component_errors.append({
                    'timestamp': entry.get('timestamp', ''),
                    'message': entry.get('jsonPayload', {}).get('message', '')
                })
        
        return component_errors
    
    def get_api_errors(self) -> dict:
        """
        Extracts API-related errors.
        
        Returns:
            Dictionary of API errors by service
        """
        api_errors = {}
        
        for entry in self.logs:
            # Check if log entry is an API error
            if entry.get('severity', '').upper() in ['ERROR', 'CRITICAL']:
                message = entry.get('jsonPayload', {}).get('message', '')
                
                if 'API Error' in message or 'failed to connect' in message.lower():
                    api_name = 'unknown'
                    
                    # Try to extract API name
                    if 'Capital One' in message:
                        api_name = 'Capital One'
                    elif 'Google Sheets' in message:
                        api_name = 'Google Sheets'
                    elif 'Gemini' in message:
                        api_name = 'Gemini'
                    elif 'Gmail' in message:
                        api_name = 'Gmail'
                    
                    if api_name not in api_errors:
                        api_errors[api_name] = []
                    
                    api_errors[api_name].append({
                        'timestamp': entry.get('timestamp', ''),
                        'message': message
                    })
        
        return api_errors
    
    def get_summary(self) -> str:
        """
        Gets a summary of the log analysis.
        
        Returns:
            Formatted summary string
        """
        if not self.analysis:
            self.analyze()
        
        summary = "Log Analysis Summary\n" + "=" * 20 + "\n\n"
        
        # Add error counts
        summary += f"Total Errors: {self.analysis.get('error_count', 0)}\n"
        summary += f"Total Warnings: {self.analysis.get('warning_count', 0)}\n"
        summary += f"Total Info: {self.analysis.get('info_count', 0)}\n\n"
        
        # Add component errors
        component_errors = self.analysis.get('errors_by_component', {})
        if component_errors:
            summary += "Errors by Component:\n"
            for component, count in component_errors.items():
                summary += f"  - {component}: {count}\n"
            summary += "\n"
        
        # Add API errors
        api_errors = self.analysis.get('api_errors', {})
        if api_errors:
            summary += "API Errors:\n"
            for api, count in api_errors.items():
                summary += f"  - {api}: {count}\n"
            summary += "\n"
        
        # Add potential issues
        potential_issues = self.analysis.get('potential_issues', [])
        if potential_issues:
            summary += "Potential Issues:\n"
            for issue in potential_issues:
                summary += f"  - {issue}\n"
            summary += "\n"
        
        return summary


def main():
    """
    Main function that orchestrates the debugging process.
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    start_time = time.time()
    
    # Parse command line arguments
    args = parse_arguments()
    
    logger.info("Starting debug job script")
    logger.debug(f"Arguments: {args}")
    
    # Check if gcloud is installed
    if not check_gcloud_installed():
        logger.error("gcloud CLI is not installed or not properly configured")
        return 1
    
    # Verify Google Cloud project ID
    if not args.project_id:
        logger.error("No Google Cloud project ID specified. Use --project-id or set GOOGLE_CLOUD_PROJECT environment variable")
        return 1
    
    # Check environment if requested
    if args.check_environment:
        logger.info("Checking execution environment")
        env_results = check_environment()
        print("\nEnvironment Check Results:")
        
        for check, result in env_results['checks'].items():
            status = "✅" if result['status'] == 'success' else "❌"
            print(f"{status} {check}")
            
            if result['status'] == 'failed':
                if 'missing_variables' in result:
                    print(f"  Missing environment variables: {', '.join(result['missing_variables'])}")
                if 'missing_files' in result:
                    print(f"  Missing credential files: {', '.join(result['missing_files'])}")
                if 'error' in result:
                    print(f"  Error: {result['error']}")
        
        overall_status = "✅ PASSED" if env_results['status'] == 'success' else "❌ FAILED"
        print(f"\nOverall environment check: {overall_status}")
    
    # Test API connectivity if requested
    if args.test_apis:
        logger.info("Testing API connectivity")
        api_results = test_all_apis()
        print("\nAPI Connectivity Test Results:")
        print(format_test_results(api_results, args.verbose))
    
    # Test specific component if requested
    if args.component:
        logger.info(f"Testing component: {args.component}")
        tester = ComponentTester(verbose=args.verbose)
        result = tester.test_component(args.component)
        print("\nComponent Test Results:")
        print(format_component_results(result, args.verbose))
    
    # Test all components if requested
    if args.test_all_components:
        logger.info("Testing all components")
        tester = ComponentTester(verbose=args.verbose)
        results = tester.test_all()
        print("\nAll Components Test Results:")
        print(format_component_results(results, args.verbose))
    
    # Get job details and logs if execution ID is provided
    if args.execution_id:
        logger.info(f"Getting details for execution: {args.execution_id}")
        job_details = get_job_details(args.project_id, args.region, args.job_name)
        
        if 'error' in job_details:
            logger.error(f"Failed to get job details: {job_details['error']}")
        else:
            print("\nJob Details:")
            print(f"Name: {job_details.get('metadata', {}).get('name', 'Unknown')}")
            print(f"Region: {args.region}")
            print(f"Last Updated: {job_details.get('updateTime', 'Unknown')}")
            
            # Get job logs
            if args.get_logs:
                logger.info(f"Getting logs for execution: {args.execution_id}")
                logs = get_job_logs(args.project_id, args.job_name, args.execution_id)
                
                print(f"\nRetrieved {len(logs)} log entries for execution {args.execution_id}")
                
                if args.verbose:
                    print("\nLog Entries:")
                    for entry in logs[:10]:  # Show only the first 10 logs in verbose mode
                        timestamp = entry.get('timestamp', 'Unknown')
                        severity = entry.get('severity', 'INFO')
                        message = entry.get('jsonPayload', {}).get('message', 'No message')
                        component = entry.get('jsonPayload', {}).get('component', 'Unknown')
                        
                        print(f"[{timestamp}] {severity} - {component}: {message}")
                    
                    if len(logs) > 10:
                        print(f"... and {len(logs) - 10} more entries. Use --analyze-logs for a summary.")
                
                # Analyze logs if requested
                if args.analyze_logs:
                    logger.info("Analyzing job logs")
                    analyzer = LogAnalyzer(logs)
                    analyzer.analyze()
                    print("\nLog Analysis Results:")
                    print(analyzer.get_summary())
    
    # Simulate an error if requested
    if args.simulate_error:
        logger.info(f"Simulating error: {args.simulate_error}")
        
        # Default to all components if not specified
        component = args.component or 'all'
        
        success = simulate_error(args.simulate_error, component)
        
        if success:
            print(f"\nSuccessfully triggered job with {args.simulate_error} error simulation in {component}")
        else:
            print(f"\nFailed to trigger job with error simulation")
            return 1
    
    # Trigger job after debugging if requested
    if args.trigger_after_debug:
        logger.info("Triggering job after debugging")
        job_result = trigger_job(
            project_id=args.project_id,
            region=args.region,
            job_name=args.job_name,
            wait=True
        )
        
        if job_result.get('status') in ['triggered', 'succeeded']:
            print("\nJob triggered successfully after debugging")
        else:
            print(f"\nFailed to trigger job after debugging: {job_result.get('error', 'Unknown error')}")
    
    # Calculate and display execution time
    execution_time = time.time() - start_time
    logger.info(f"Debug job completed in {execution_time:.2f} seconds")
    print(f"\nDebug job completed in {execution_time:.2f} seconds")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())