#!/usr/bin/env python3
"""
Dashboard Generator for Budget Management Application

This script generates and deploys a Google Cloud Monitoring dashboard for the Budget Management Application.
It creates visualizations for system health, API integration status, component performance, 
financial operations, and resource utilization metrics.

Usage:
    python generate_dashboard.py --project-id=your-project-id [--job-name=budget-management-job] [--update]
"""

import argparse
import os
import sys
import json
import datetime
import subprocess
import re

from google.cloud.monitoring_dashboard_v1 import DashboardsServiceClient
from google.cloud.monitoring_dashboard_v1.types import Dashboard
import google.auth
import jinja2  # jinja2 3.0.0+

# Internal imports
from ..config.logging_setup import get_logger
from ..config.script_settings import SCRIPT_SETTINGS
from .check_job_status import JobStatusChecker
from .analyze_logs import LogAnalyzer

# Initialize logger
logger = get_logger('generate_dashboard')

# Global constants
DEFAULT_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT', None)
DEFAULT_JOB_NAME = 'budget-management-job'
DEFAULT_REGION = 'us-east1'
DEFAULT_DASHBOARD_NAME = 'budget-management-dashboard'
DASHBOARD_TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                       'infrastructure', 'monitoring', 'dashboards', 'budget_management_dashboard.json')

class DashboardGenerator:
    """Class that handles dashboard generation and deployment"""
    
    def __init__(self, project_id, job_name, region, dashboard_name, template_path):
        """
        Initialize the dashboard generator with project and job details
        
        Args:
            project_id: Google Cloud project ID
            job_name: Name of the Cloud Run job
            region: Region where the job is deployed
            dashboard_name: Name for the dashboard
            template_path: Path to the dashboard template file
        """
        self.project_id = project_id
        self.job_name = job_name
        self.region = region
        self.dashboard_name = dashboard_name
        self.dashboard_template = load_dashboard_template(template_path)
        
        # Initialize Monitoring Dashboards client
        try:
            self.client = DashboardsServiceClient()
            logger.info(f"Initialized DashboardGenerator for {job_name} in {project_id}")
        except Exception as e:
            logger.error(f"Error initializing Monitoring Dashboards client: {e}")
            self.client = None
            
        # Validate that project exists
        try:
            credentials, _ = google.auth.default()
            if not credentials.valid:
                credentials.refresh(google.auth.transport.requests.Request())
            logger.info(f"Successfully authenticated with Google Cloud")
        except Exception as e:
            logger.error(f"Error validating Google Cloud credentials: {e}")
    
    def generate_dashboard(self):
        """
        Generate customized dashboard configuration
        
        Returns:
            Customized dashboard configuration
        """
        # Get performance metrics for threshold customization
        performance_metrics = get_performance_metrics(self.project_id, self.job_name, self.region)
        
        # Customize dashboard with project-specific values
        dashboard_config = customize_dashboard(
            self.dashboard_template,
            self.project_id,
            self.job_name,
            self.dashboard_name
        )
        
        # Update dashboard thresholds based on performance metrics
        dashboard_config = update_dashboard_thresholds(dashboard_config, performance_metrics)
        
        return dashboard_config
    
    def deploy_dashboard(self, dashboard_config, update=False):
        """
        Deploy dashboard to Google Cloud Monitoring
        
        Args:
            dashboard_config: Dashboard configuration
            update: Whether to update an existing dashboard
            
        Returns:
            Dashboard URL
        """
        try:
            dashboard_url = create_dashboard_using_api(
                dashboard_config,
                self.project_id,
                self.dashboard_name,
                update
            )
            logger.info(f"Successfully deployed dashboard: {dashboard_url}")
            return dashboard_url
        except Exception as e:
            logger.error(f"Error deploying dashboard with API: {e}")
            logger.info("Falling back to CLI method")
            
            try:
                dashboard_url = create_dashboard_using_cli(
                    dashboard_config,
                    self.project_id,
                    self.dashboard_name,
                    update
                )
                logger.info(f"Successfully deployed dashboard using CLI: {dashboard_url}")
                return dashboard_url
            except Exception as e2:
                logger.error(f"Error deploying dashboard using CLI: {e2}")
                raise
    
    def get_dashboard_url(self):
        """
        Get URL for accessing the dashboard
        
        Returns:
            Dashboard URL
        """
        return f"https://console.cloud.google.com/monitoring/dashboards/builder/{self.dashboard_name}?project={self.project_id}"
    
    def check_dashboard_exists(self):
        """
        Check if dashboard already exists
        
        Returns:
            True if dashboard exists, False otherwise
        """
        if not self.client:
            logger.warning("Monitoring Dashboards client not initialized")
            return False
        
        try:
            dashboard_name = f"projects/{self.project_id}/dashboards/{self.dashboard_name}"
            self.client.get_dashboard(name=dashboard_name)
            logger.info(f"Dashboard exists: {self.dashboard_name}")
            return True
        except Exception:
            logger.info(f"Dashboard does not exist: {self.dashboard_name}")
            return False

def parse_arguments():
    """
    Parse command line arguments for the script
    
    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Generate and deploy a Google Cloud Monitoring dashboard for the Budget Management Application'
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
        '--dashboard-name',
        default=DEFAULT_DASHBOARD_NAME,
        help=f'Name for the dashboard (default: {DEFAULT_DASHBOARD_NAME})'
    )
    
    parser.add_argument(
        '--template',
        default=DASHBOARD_TEMPLATE_PATH,
        help='Path to dashboard template file'
    )
    
    parser.add_argument(
        '--update',
        action='store_true',
        help='Update existing dashboard if it exists'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Generate dashboard but do not deploy'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser.parse_args()

def load_dashboard_template(template_path):
    """
    Load dashboard template from file
    
    Args:
        template_path: Path to the template file
        
    Returns:
        Dashboard template as dictionary
    """
    if not os.path.exists(template_path):
        logger.error(f"Dashboard template not found: {template_path}")
        raise FileNotFoundError(f"Dashboard template not found: {template_path}")
    
    try:
        with open(template_path, 'r') as f:
            template = json.load(f)
        
        logger.info(f"Loaded dashboard template from {template_path}")
        return template
    except Exception as e:
        logger.error(f"Error loading dashboard template: {e}")
        raise

def customize_dashboard(dashboard_template, project_id, job_name, dashboard_name):
    """
    Customize dashboard template with project-specific values
    
    Args:
        dashboard_template: Dashboard template as dictionary
        project_id: Google Cloud project ID
        job_name: Name of the Cloud Run job
        dashboard_name: Name for the dashboard
        
    Returns:
        Customized dashboard template
    """
    import copy
    
    # Create a deep copy to avoid modifying the original template
    dashboard = copy.deepcopy(dashboard_template)
    
    # Set dashboard name
    dashboard['displayName'] = dashboard_name
    
    # Replace [PROJECT_ID] placeholders with actual project ID
    dashboard_str = json.dumps(dashboard)
    dashboard_str = dashboard_str.replace('[PROJECT_ID]', project_id)
    
    # Replace job name in filter expressions
    dashboard_str = dashboard_str.replace('[JOB_NAME]', job_name)
    
    # Convert back to dictionary
    dashboard = json.loads(dashboard_str)
    
    # Update dashboard labels with project information
    if 'labels' not in dashboard:
        dashboard['labels'] = {}
    
    dashboard['labels']['project_id'] = project_id
    dashboard['labels']['job_name'] = job_name
    
    # Update dashboard etag with current timestamp
    dashboard['etag'] = f"dashboard-{int(datetime.datetime.now().timestamp())}"
    
    logger.info(f"Customized dashboard template for project {project_id}, job {job_name}")
    return dashboard

def create_dashboard_using_api(dashboard_config, project_id, dashboard_name, update=False):
    """
    Create or update dashboard using Google Cloud Monitoring Dashboards API
    
    Args:
        dashboard_config: Dashboard configuration
        project_id: Google Cloud project ID
        dashboard_name: Name for the dashboard
        update: Whether to update an existing dashboard
        
    Returns:
        Dashboard URL
    """
    try:
        # Initialize client
        client = DashboardsServiceClient()
        
        # Construct parent resource name
        parent = f"projects/{project_id}"
        
        if update:
            # Check if dashboard exists
            try:
                dashboard_path = f"projects/{project_id}/dashboards/{dashboard_name}"
                client.get_dashboard(name=dashboard_path)
                
                # If dashboard exists, update it
                dashboard = Dashboard()
                dashboard.name = dashboard_path
                
                # Update fields from config
                for key, value in dashboard_config.items():
                    if key != 'name':  # Skip the name field
                        setattr(dashboard, key, value)
                
                response = client.update_dashboard(dashboard=dashboard)
                logger.info(f"Updated existing dashboard: {dashboard_name}")
            
            except Exception:
                # Dashboard doesn't exist, create a new one
                response = client.create_dashboard(parent=parent, dashboard=dashboard_config)
                logger.info(f"Created new dashboard: {dashboard_name}")
        else:
            # Create new dashboard
            response = client.create_dashboard(parent=parent, dashboard=dashboard_config)
            logger.info(f"Created new dashboard: {dashboard_name}")
        
        # Construct the dashboard URL
        dashboard_url = f"https://console.cloud.google.com/monitoring/dashboards/builder/{dashboard_name}?project={project_id}"
        return dashboard_url
        
    except Exception as e:
        logger.error(f"Error creating dashboard using API: {e}")
        raise

def create_dashboard_using_cli(dashboard_config, project_id, dashboard_name, update=False):
    """
    Fallback method to create or update dashboard using gcloud CLI
    
    Args:
        dashboard_config: Dashboard configuration
        project_id: Google Cloud project ID
        dashboard_name: Name for the dashboard
        update: Whether to update an existing dashboard
        
    Returns:
        Dashboard URL
    """
    try:
        # Create temporary JSON file with dashboard configuration
        temp_file = f"/tmp/dashboard_{int(datetime.datetime.now().timestamp())}.json"
        with open(temp_file, 'w') as f:
            json.dump(dashboard_config, f)
        
        # Construct gcloud command
        if update:
            command = [
                'gcloud', 'monitoring', 'dashboards', 'update',
                dashboard_name,
                f'--project={project_id}',
                f'--config-from-file={temp_file}',
                '--format=json'
            ]
        else:
            command = [
                'gcloud', 'monitoring', 'dashboards', 'create',
                f'--project={project_id}',
                f'--config-from-file={temp_file}',
                '--format=json'
            ]
        
        # Execute command
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        # Parse response to get dashboard ID
        response = json.loads(result.stdout)
        dashboard_id = response.get('name', '').split('/')[-1]
        
        # Remove temporary file
        os.remove(temp_file)
        
        # Construct the dashboard URL
        dashboard_url = f"https://console.cloud.google.com/monitoring/dashboards/builder/{dashboard_id}?project={project_id}"
        return dashboard_url
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing gcloud command: {e}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Command error: {e.stderr}")
        raise
        
    except Exception as e:
        logger.error(f"Error creating dashboard using CLI: {e}")
        raise
        
    finally:
        # Ensure temporary file is removed
        if os.path.exists(temp_file):
            os.remove(temp_file)

def get_performance_metrics(project_id, job_name, region):
    """
    Retrieve performance metrics for dashboard customization
    
    Args:
        project_id: Google Cloud project ID
        job_name: Name of the Cloud Run job
        region: Region where the job is deployed
        
    Returns:
        Performance metrics data
    """
    try:
        metrics = {}
        
        # Initialize job status checker to get execution data
        job_checker = JobStatusChecker(project_id, job_name, region)
        
        # Get recent job executions
        executions = job_checker.get_executions(days=14)  # Get last 2 weeks of data
        
        # Analyze executions to extract performance metrics
        if executions:
            execution_analysis = job_checker.analyze_executions(executions)
            metrics['job_executions'] = {
                'success_rate': execution_analysis.get('success_rate', 0),
                'duration_stats': execution_analysis.get('duration_stats', {})
            }
        
        # Initialize log analyzer to extract metrics from logs
        log_analyzer = LogAnalyzer(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'application.log'))
        
        # Try to load and analyze logs
        try:
            log_analyzer.load_logs()
            log_analyzer.filter_logs(days=14)  # Filter to last 2 weeks
            log_analysis = log_analyzer.analyze()
            
            # Extract performance metrics from log analysis
            if 'performance_analysis' in log_analysis:
                metrics['performance'] = log_analysis['performance_analysis']
            
            # Extract error patterns
            if 'error_patterns' in log_analysis:
                metrics['error_patterns'] = log_analysis['error_patterns']
        except Exception as e:
            logger.warning(f"Error analyzing logs: {e}")
        
        # Extract component-specific performance metrics
        metrics['component_metrics'] = log_analyzer.extract_performance_metrics(executions)
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error retrieving performance metrics: {e}")
        return {}

def update_dashboard_thresholds(dashboard_config, performance_metrics):
    """
    Update dashboard thresholds based on actual performance metrics
    
    Args:
        dashboard_config: Dashboard configuration
        performance_metrics: Performance metrics data
        
    Returns:
        Updated dashboard configuration
    """
    import copy
    
    # Create a deep copy to avoid modifying the original config
    dashboard = copy.deepcopy(dashboard_config)
    
    # Extract performance thresholds from metrics
    thresholds = {}
    
    # Get execution time thresholds
    if 'job_executions' in performance_metrics and 'duration_stats' in performance_metrics['job_executions']:
        duration_stats = performance_metrics['job_executions']['duration_stats']
        
        if duration_stats:
            # Set thresholds based on p95 or max times
            thresholds['execution_time'] = {
                'warning': duration_stats.get('avg', 300) * 1.2,  # 20% above average
                'critical': duration_stats.get('p95', duration_stats.get('max', 600))
            }
    
    # Get API response time thresholds
    if 'performance' in performance_metrics and 'component_averages' in performance_metrics['performance']:
        for component in performance_metrics['performance']['component_averages']:
            if 'api_client' in component['component'].lower():
                thresholds['api_response_time'] = {
                    'warning': component['avg_time'] * 1.5,  # 50% above average
                    'critical': component['avg_time'] * 3.0   # 3x average
                }
    
    # Get component duration thresholds
    if 'performance' in performance_metrics and 'slowest_operations' in performance_metrics['performance']:
        # Group by component
        component_times = {}
        for operation in performance_metrics['performance']['slowest_operations']:
            component = operation['component']
            if component not in component_times:
                component_times[component] = []
            component_times[component].append(operation['avg_time'])
        
        # Calculate thresholds by component
        for component, times in component_times.items():
            if times:
                avg_time = sum(times) / len(times)
                max_time = max(times)
                
                thresholds[f"{component.lower()}_duration"] = {
                    'warning': avg_time * 1.5,  # 50% above average
                    'critical': max_time
                }
    
    # Update dashboard widgets with calculated thresholds
    if 'dashboardWidgets' in dashboard:
        for widget in dashboard['dashboardWidgets']:
            if 'xyChart' in widget and 'thresholds' in widget['xyChart']:
                widget_title = widget.get('title', '').lower()
                
                # Update execution time thresholds
                if 'execution time' in widget_title and 'execution_time' in thresholds:
                    for threshold in widget['xyChart']['thresholds']:
                        if threshold.get('label') == 'Warning':
                            threshold['value'] = thresholds['execution_time']['warning']
                        elif threshold.get('label') == 'Critical':
                            threshold['value'] = thresholds['execution_time']['critical']
                
                # Update API response time thresholds
                elif 'api' in widget_title and 'response time' in widget_title and 'api_response_time' in thresholds:
                    for threshold in widget['xyChart']['thresholds']:
                        if threshold.get('label') == 'Warning':
                            threshold['value'] = thresholds['api_response_time']['warning']
                        elif threshold.get('label') == 'Critical':
                            threshold['value'] = thresholds['api_response_time']['critical']
                
                # Update component-specific thresholds
                else:
                    for component, threshold_values in thresholds.items():
                        if component.endswith('_duration') and component.split('_')[0] in widget_title:
                            for threshold in widget['xyChart']['thresholds']:
                                if threshold.get('label') == 'Warning':
                                    threshold['value'] = threshold_values['warning']
                                elif threshold.get('label') == 'Critical':
                                    threshold['value'] = threshold_values['critical']
    
    logger.info("Updated dashboard thresholds based on performance metrics")
    return dashboard

def preview_dashboard(dashboard_config):
    """
    Generate a preview of the dashboard configuration
    
    Args:
        dashboard_config: Dashboard configuration
    """
    # Print dashboard name and description
    print(f"\nDASHBOARD PREVIEW: {dashboard_config.get('displayName', 'Unnamed Dashboard')}")
    
    if 'etag' in dashboard_config:
        print(f"Last modified: {dashboard_config['etag']}")
    
    # Print widgets count and layout
    widgets = dashboard_config.get('dashboardWidgets', [])
    print(f"\nTotal widgets: {len(widgets)}")
    
    # Print metrics being monitored
    metrics = set()
    for widget in widgets:
        if 'xyChart' in widget:
            for data_set in widget['xyChart'].get('dataSets', []):
                if 'timeSeriesQuery' in data_set:
                    query = data_set['timeSeriesQuery'].get('timeSeriesFilter', {}).get('filter', '')
                    for metric in re.findall(r'metric.type="([^"]+)"', query):
                        metrics.add(metric)
    
    print(f"\nMetrics monitored: {len(metrics)}")
    for metric in sorted(metrics):
        print(f"  - {metric}")
    
    # Print thresholds for key metrics
    print("\nThresholds:")
    for widget in widgets:
        if 'xyChart' in widget and 'thresholds' in widget['xyChart']:
            print(f"  Widget: {widget.get('title', 'Unnamed Widget')}")
            for threshold in widget['xyChart']['thresholds']:
                value = threshold.get('value', 'N/A')
                label = threshold.get('label', 'Unnamed threshold')
                color = threshold.get('color', 'DEFAULT')
                print(f"    - {label}: {value} ({color})")
    
    # If verbose mode, print full JSON
    if SCRIPT_SETTINGS.get('VERBOSE', False):
        print("\nFull Dashboard JSON:")
        print(json.dumps(dashboard_config, indent=2))

def main():
    """
    Main function that orchestrates dashboard generation and deployment
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Log script start
        logger.info(f"Starting dashboard generation for {args.job_name} in {args.project_id}")
        
        # Load dashboard template
        dashboard_template = load_dashboard_template(args.template)
        
        # Get performance metrics for threshold customization
        performance_metrics = get_performance_metrics(args.project_id, args.job_name, args.region)
        
        # Customize dashboard with project-specific values
        dashboard_config = customize_dashboard(
            dashboard_template,
            args.project_id,
            args.job_name,
            args.dashboard_name
        )
        
        # Update dashboard thresholds based on performance metrics
        dashboard_config = update_dashboard_thresholds(dashboard_config, performance_metrics)
        
        # If dry-run, just print the dashboard configuration and exit
        if args.dry_run:
            logger.info("Dry run mode - previewing dashboard")
            preview_dashboard(dashboard_config)
            return 0
        
        # Deploy the dashboard
        try:
            dashboard_url = create_dashboard_using_api(
                dashboard_config,
                args.project_id,
                args.dashboard_name,
                args.update
            )
        except Exception as e:
            logger.error(f"Error deploying dashboard with API: {e}")
            logger.info("Falling back to CLI method")
            
            dashboard_url = create_dashboard_using_cli(
                dashboard_config,
                args.project_id,
                args.dashboard_name,
                args.update
            )
        
        logger.info(f"Dashboard deployed: {dashboard_url}")
        print(f"\nDashboard URL: {dashboard_url}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error generating dashboard: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())