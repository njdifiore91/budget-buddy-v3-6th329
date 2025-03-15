#!/usr/bin/env python3
"""
Weekly Health Check Script for Budget Management Application

This script performs comprehensive health checks on the application's components,
verifies API integrations, checks job execution status, and sends notification
emails if issues are detected. It runs on a weekly schedule to ensure the system
is operating correctly.

Usage:
    python weekly_healthcheck.py [--project-id=PROJECT_ID] [--job-name=JOB_NAME] 
                                [--output-dir=OUTPUT_DIR] [--email] [--force]
"""

import os
import sys
import argparse
import json
import datetime
import time
from typing import Dict, List, Optional, Union, Any

# Internal imports
from ...config.logging_setup import get_logger, LoggingContext
from ...config.script_settings import SCRIPT_SETTINGS, MAINTENANCE_SETTINGS
from ...monitoring.check_job_status import JobStatusChecker
from ...utils.api_testing import APITester
from ....backend.api_clients.gmail_client import GmailClient
from ....backend.services.authentication_service import AuthenticationService

# Initialize logger
logger = get_logger('weekly_healthcheck')

# Default values
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'healthchecks')
DEFAULT_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT', None)
DEFAULT_JOB_NAME = 'budget-management-job'
DEFAULT_REGION = 'us-east1'

def parse_arguments():
    """
    Parse command line arguments for the script
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Weekly health check for the Budget Management Application'
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
        '--output-dir',
        default=DEFAULT_OUTPUT_DIR,
        help=f'Directory to store health check reports (default: {DEFAULT_OUTPUT_DIR})'
    )
    
    parser.add_argument(
        '--email',
        action='store_true',
        help='Send email notification if issues are detected'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable detailed output'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Run health check regardless of interval'
    )
    
    return parser.parse_args()


def should_run_healthcheck(interval_hours: int, output_dir: str) -> bool:
    """
    Determine if health check should run based on interval
    
    Args:
        interval_hours: Time interval between health checks in hours
        output_dir: Directory where health check reports are stored
        
    Returns:
        bool: True if health check should run, False otherwise
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Created output directory: {output_dir}")
        return True  # If directory was just created, run health check
    
    # Look for most recent health check report
    report_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
    if not report_files:
        logger.info("No previous health check reports found")
        return True
    
    # Sort files by modification time (most recent first)
    report_files.sort(key=lambda f: os.path.getmtime(os.path.join(output_dir, f)), reverse=True)
    most_recent_file = os.path.join(output_dir, report_files[0])
    
    # Get timestamp from most recent report
    try:
        with open(most_recent_file, 'r') as f:
            report_data = json.load(f)
            if 'timestamp' in report_data:
                report_time = datetime.datetime.fromisoformat(report_data['timestamp'].replace('Z', '+00:00'))
                current_time = datetime.datetime.now(datetime.timezone.utc)
                hours_elapsed = (current_time - report_time).total_seconds() / 3600
                
                logger.info(f"Last health check ran {hours_elapsed:.1f} hours ago")
                return hours_elapsed >= interval_hours
            else:
                logger.warning(f"No timestamp found in report file: {most_recent_file}")
                return True
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Error reading report file: {e}")
        return True


def check_job_status(project_id: str, job_name: str, region: str) -> Dict:
    """
    Check the status of the Cloud Run job
    
    Args:
        project_id: Google Cloud project ID
        job_name: Name of the Cloud Run job
        region: Region where the job is deployed
        
    Returns:
        dict: Job status report
    """
    logger.info(f"Checking job status for {job_name} in project {project_id}")
    
    # Create JobStatusChecker instance
    job_checker = JobStatusChecker(project_id, job_name, region)
    
    # Get job executions for the past 7 days
    executions = job_checker.get_executions(days=7)
    if not executions:
        logger.error("No job executions found")
        return {
            'status': 'error',
            'message': 'No job executions found',
            'executions': []
        }
    
    # Analyze job executions
    analysis = job_checker.analyze_executions(executions)
    
    # Check latest execution status
    latest_status = job_checker.check_latest(executions)
    
    # Generate comprehensive job status report
    job_status = job_checker.generate_report(executions, analysis, latest_status)
    
    logger.info(f"Job status check completed with status: {job_status.get('status', 'unknown')}")
    return job_status


def check_api_integrations() -> Dict:
    """
    Check the status of all API integrations
    
    Returns:
        dict: API integration test results
    """
    logger.info("Checking API integrations")
    
    # Create auth service
    auth_service = AuthenticationService()
    
    # Create API tester
    api_tester = APITester(auth_service=auth_service)
    
    # Test all APIs
    api_results = api_tester.test_all()
    
    logger.info("API integration tests completed")
    return api_results


def generate_health_report(job_status: Dict, api_status: Dict) -> Dict:
    """
    Generate a comprehensive health report
    
    Args:
        job_status: Job status information
        api_status: API integration status information
        
    Returns:
        dict: Complete health report
    """
    # Create report with timestamp
    report = {
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'job_status': job_status,
        'api_status': api_status
    }
    
    # Calculate overall health status
    health_status = 'healthy'
    critical_issues = []
    warnings = []
    
    # Check job status
    if job_status.get('status') == 'error':
        health_status = 'critical'
        critical_issues.append(f"Job status check failed: {job_status.get('message', 'Unknown error')}")
    elif not job_status.get('latest_execution', {}).get('is_successful', False):
        health_status = 'critical'
        error_msg = job_status.get('latest_execution', {}).get('error', {}).get('message', 'Unknown error')
        critical_issues.append(f"Latest job execution failed: {error_msg}")
    
    # Check job execution frequency
    time_since_hours = job_status.get('latest_execution', {}).get('time_since_hours', 0)
    if time_since_hours > 168:  # > 7 days
        health_status = 'critical' if health_status == 'healthy' else health_status
        critical_issues.append(f"No job execution in over 7 days ({time_since_hours:.1f} hours)")
    elif time_since_hours > 48:  # > 2 days
        health_status = 'warning' if health_status == 'healthy' else health_status
        warnings.append(f"No job execution in over 2 days ({time_since_hours:.1f} hours)")
    
    # Check API status
    for api_name, api_result in api_status.items():
        if api_result.get('status') == 'failed':
            health_status = 'critical'
            error_msg = api_result.get('error', 'Unknown error')
            critical_issues.append(f"API integration failed for {api_name}: {error_msg}")
    
    # Add overall health status to report
    report['health_status'] = health_status
    report['critical_issues'] = critical_issues
    report['warnings'] = warnings
    
    # Add recommendations based on findings
    recommendations = []
    
    for issue in critical_issues:
        recommendations.append({
            'priority': 'high',
            'message': issue,
            'action': 'Immediate attention required'
        })
    
    for warning in warnings:
        recommendations.append({
            'priority': 'medium',
            'message': warning,
            'action': 'Monitor and investigate'
        })
    
    # Add specific recommendations based on findings
    if job_status.get('execution_analysis', {}).get('success_rate', 100) < 80:
        recommendations.append({
            'priority': 'high',
            'message': f"Low job success rate: {job_status['execution_analysis']['success_rate']:.1f}%",
            'action': 'Review job logs and fix recurring errors'
        })
    
    # Add performance recommendations
    if 'performance_analysis' in job_status and 'operations_exceeding_threshold' in job_status['performance_analysis']:
        slow_ops = job_status['performance_analysis']['operations_exceeding_threshold']
        if slow_ops:
            recommendations.append({
                'priority': 'medium',
                'message': f"{len(slow_ops)} operations exceeding performance thresholds",
                'action': 'Optimize slow operations'
            })
    
    report['recommendations'] = recommendations
    
    return report


def save_health_report(report: Dict, output_dir: str) -> str:
    """
    Save the health report to a file
    
    Args:
        report: Health report to save
        output_dir: Directory to save the report in
        
    Returns:
        str: Path to the saved report file
    """
    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"health_report_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    # Write report to file
    with open(filepath, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Health report saved to {filepath}")
    return filepath


def send_notification_email(report: Dict, recipient_email: str, 
                           alert_on_warning: bool, alert_on_error: bool) -> bool:
    """
    Send notification email with health check results
    
    Args:
        report: Health report with findings
        recipient_email: Email address to send notification to
        alert_on_warning: Whether to send alerts for warnings
        alert_on_error: Whether to send alerts for errors
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # Check if notification is needed based on health status
    health_status = report.get('health_status', 'healthy')
    
    if health_status == 'healthy':
        logger.info("System is healthy, no notification needed")
        return False
    
    if health_status == 'warning' and not alert_on_warning:
        logger.info("System has warnings but alert_on_warning is disabled")
        return False
    
    if health_status == 'critical' and not alert_on_error:
        logger.info("System has critical issues but alert_on_error is disabled")
        return False
    
    # Format email subject based on health status
    if health_status == 'critical':
        subject = "🚨 CRITICAL: Budget Management Application Health Check Failed"
    else:
        subject = "⚠️ WARNING: Budget Management Application Health Issues Detected"
    
    # Format email body
    html_content = format_email_content(report)
    
    try:
        # Initialize authentication service and Gmail client
        auth_service = AuthenticationService()
        gmail_client = GmailClient(auth_service=auth_service)
        
        # Send email
        result = gmail_client.send_email(
            subject=subject,
            html_content=html_content,
            recipients=[recipient_email]
        )
        
        logger.info(f"Notification email sent to {recipient_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send notification email: {e}")
        return False


def format_email_content(report: Dict) -> str:
    """
    Format health report as HTML email content
    
    Args:
        report: Health report to format
        
    Returns:
        str: HTML formatted email content
    """
    # Determine status color
    health_status = report.get('health_status', 'healthy')
    if health_status == 'critical':
        status_color = '#d32f2f'  # red
        status_icon = '🚨'
    elif health_status == 'warning':
        status_color = '#ff9800'  # orange
        status_icon = '⚠️'
    else:
        status_color = '#4caf50'  # green
        status_icon = '✅'
    
    # Create HTML email template
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }}
            .header {{ background-color: {status_color}; color: white; padding: 10px; border-radius: 5px; }}
            .section {{ margin: 20px 0; }}
            .issue {{ margin: 10px 0; padding: 10px; border-radius: 5px; }}
            .critical {{ background-color: #ffebee; border-left: 4px solid #d32f2f; }}
            .warning {{ background-color: #fff8e1; border-left: 4px solid #ff9800; }}
            .recommendation {{ background-color: #e8f5e9; border-left: 4px solid #4caf50; margin: 10px 0; padding: 10px; border-radius: 5px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f5f5f5; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>{status_icon} Budget Management Application Health Check</h2>
            <p>Status: <strong>{health_status.upper()}</strong></p>
            <p>Report generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    """
    
    # Add critical issues section if any
    if report.get('critical_issues'):
        html_content += """
        <div class="section">
            <h3>🚨 Critical Issues</h3>
        """
        
        for issue in report['critical_issues']:
            html_content += f"""
            <div class="issue critical">
                <p>{issue}</p>
            </div>
            """
        
        html_content += "</div>"
    
    # Add warnings section if any
    if report.get('warnings'):
        html_content += """
        <div class="section">
            <h3>⚠️ Warnings</h3>
        """
        
        for warning in report['warnings']:
            html_content += f"""
            <div class="issue warning">
                <p>{warning}</p>
            </div>
            """
        
        html_content += "</div>"
    
    # Add job status section
    job_status = report.get('job_status', {})
    latest_execution = job_status.get('latest_execution', {})
    
    html_content += """
    <div class="section">
        <h3>Job Status</h3>
        <table>
            <tr>
                <th>Parameter</th>
                <th>Value</th>
            </tr>
    """
    
    # Add job details
    job_name = job_status.get('job_info', {}).get('name', 'Unknown')
    html_content += f"""
        <tr>
            <td>Job Name</td>
            <td>{job_name}</td>
        </tr>
        <tr>
            <td>Latest Execution Status</td>
            <td>{latest_execution.get('status', 'Unknown')}</td>
        </tr>
        <tr>
            <td>Last Run</td>
            <td>{latest_execution.get('start_time', 'Unknown')}</td>
        </tr>
        <tr>
            <td>Execution Duration</td>
            <td>{latest_execution.get('duration', 'Unknown')} seconds</td>
        </tr>
        <tr>
            <td>Success Rate (7 days)</td>
            <td>{job_status.get('execution_analysis', {}).get('success_rate', 0):.1f}%</td>
        </tr>
    """
    
    html_content += """
        </table>
    </div>
    """
    
    # Add API status section
    html_content += """
    <div class="section">
        <h3>API Integration Status</h3>
        <table>
            <tr>
                <th>API</th>
                <th>Status</th>
            </tr>
    """
    
    # Add API details
    for api_name, api_result in report.get('api_status', {}).items():
        status = api_result.get('status', 'Unknown')
        status_cell = f'<span style="color: {"#4caf50" if status == "success" else "#d32f2f"}">{status}</span>'
        
        html_content += f"""
        <tr>
            <td>{api_name}</td>
            <td>{status_cell}</td>
        </tr>
        """
    
    html_content += """
        </table>
    </div>
    """
    
    # Add recommendations section
    if report.get('recommendations'):
        html_content += """
        <div class="section">
            <h3>Recommendations</h3>
        """
        
        for recommendation in report['recommendations']:
            priority = recommendation.get('priority', 'medium')
            icon = '🔴' if priority == 'high' else '🟠' if priority == 'medium' else '🟢'
            
            html_content += f"""
            <div class="recommendation">
                <p><strong>{icon} {recommendation.get('message', '')}</strong></p>
                <p>Recommended action: {recommendation.get('action', 'No action specified')}</p>
            </div>
            """
        
        html_content += "</div>"
    
    # Close HTML
    html_content += """
    <div style="margin-top: 30px; font-size: 0.8em; color: #777;">
        <p>This is an automated health check report from the Budget Management Application.</p>
    </div>
    </body>
    </html>
    """
    
    return html_content


def main():
    """
    Main function that orchestrates the weekly health check
    
    Returns:
        int: Exit code (0 for success, non-zero for errors)
    """
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        logger.info(f"Starting weekly health check. Project: {args.project_id}, Job: {args.job_name}")
        
        # Check if health check should run based on interval
        interval_hours = MAINTENANCE_SETTINGS.get('HEALTH_CHECK_INTERVAL', 24)
        
        if not args.force and not should_run_healthcheck(interval_hours, args.output_dir):
            logger.info(f"Health check ran less than {interval_hours} hours ago, skipping")
            return 0
        
        # Create HealthChecker instance
        health_checker = HealthChecker(
            project_id=args.project_id,
            job_name=args.job_name,
            region=args.region,
            output_dir=args.output_dir,
            send_email=args.email,
            verbose=args.verbose
        )
        
        # Run health check
        with LoggingContext(logger, "weekly health check"):
            report = health_checker.run()
        
        # Return appropriate exit code based on health status
        if report.get('health_status') == 'critical':
            logger.warning("Health check detected CRITICAL issues")
            return 2
        elif report.get('health_status') == 'warning':
            logger.warning("Health check detected WARNING issues")
            return 1
        else:
            logger.info("Health check completed successfully - system is healthy")
            return 0
            
    except Exception as e:
        logger.error(f"Error during health check: {e}", exc_info=True)
        return 3


class HealthChecker:
    """Class that manages the weekly health check process"""
    
    def __init__(self, project_id: str, job_name: str, region: str, 
                output_dir: str, send_email: bool, verbose: bool):
        """
        Initialize the health checker with configuration
        
        Args:
            project_id: Google Cloud project ID
            job_name: Name of the Cloud Run job
            region: Region where the job is deployed
            output_dir: Directory to store health check reports
            send_email: Whether to send email notifications
            verbose: Whether to enable verbose output
        """
        self.project_id = project_id
        self.job_name = job_name
        self.region = region
        self.output_dir = output_dir
        self.send_email = send_email
        self.verbose = verbose
        
        # Initialize services
        self.auth_service = AuthenticationService()
        self.job_checker = JobStatusChecker(project_id, job_name, region)
        self.api_tester = APITester(auth_service=self.auth_service)
        
        logger.info("HealthChecker initialized")
    
    def run(self) -> Dict:
        """
        Run the complete health check process
        
        Returns:
            dict: Health check report
        """
        logger.info("Starting health check process")
        
        # Check job status
        job_status = self.check_job()
        
        # Check API integrations
        api_status = self.check_apis()
        
        # Generate comprehensive health report
        report = self.generate_report(job_status, api_status)
        
        # Save report to file
        report_path = self.save_report(report)
        
        # Send notification email if needed
        if self.send_email:
            self.send_notification(report)
        
        logger.info("Health check process completed")
        return report
    
    def check_job(self) -> Dict:
        """
        Check Cloud Run job status
        
        Returns:
            dict: Job status report
        """
        return check_job_status(self.project_id, self.job_name, self.region)
    
    def check_apis(self) -> Dict:
        """
        Check API integration status
        
        Returns:
            dict: API integration status report
        """
        return check_api_integrations()
    
    def generate_report(self, job_status: Dict, api_status: Dict) -> Dict:
        """
        Generate comprehensive health report
        
        Args:
            job_status: Job status information
            api_status: API integration status information
            
        Returns:
            dict: Complete health report
        """
        return generate_health_report(job_status, api_status)
    
    def save_report(self, report: Dict) -> str:
        """
        Save health report to file
        
        Args:
            report: Health report to save
            
        Returns:
            str: Path to saved report file
        """
        return save_health_report(report, self.output_dir)
    
    def send_notification(self, report: Dict) -> bool:
        """
        Send notification email if needed
        
        Args:
            report: Health report with findings
            
        Returns:
            bool: True if email sent, False otherwise
        """
        recipient_email = MAINTENANCE_SETTINGS.get('ALERT_EMAIL', 'njdifiore@gmail.com')
        alert_on_warning = MAINTENANCE_SETTINGS.get('ALERT_ON_WARNING', True)
        alert_on_error = MAINTENANCE_SETTINGS.get('ALERT_ON_ERROR', True)
        
        return send_notification_email(
            report,
            recipient_email,
            alert_on_warning,
            alert_on_error
        )


if __name__ == "__main__":
    sys.exit(main())