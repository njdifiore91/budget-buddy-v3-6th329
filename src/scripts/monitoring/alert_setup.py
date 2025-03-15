#!/usr/bin/env python3
"""
Alert Setup Script for Budget Management Application

This script sets up and configures Google Cloud Monitoring alerts for the Budget Management Application.
It creates alert policies, notification channels, and custom metrics based on predefined configurations.
This script automates the deployment of monitoring infrastructure to detect and notify about system issues.

Usage:
    python alert_setup.py --project-id=your-project-id --update --test
"""

import argparse
import os
import sys
import json
import datetime
from typing import Dict, List, Optional, Union, Any

from google.cloud import monitoring_v3
import google.auth
from google.api_core.exceptions import NotFound, AlreadyExists, GoogleAPIError

# Internal imports
from ..config.logging_setup import get_logger, LoggingContext
from ..config.script_settings import SCRIPT_SETTINGS, MAINTENANCE_SETTINGS
from ...backend.api_clients.gmail_client import GmailClient
from .check_job_status import JobStatusChecker

# Initialize logger
logger = get_logger('alert_setup')

# Default values
DEFAULT_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT', None)
DEFAULT_ALERTS_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 
                                         'infrastructure', 'monitoring', 'alerts', 
                                         'budget_management_alerts.json')
DEFAULT_NOTIFICATION_CHANNELS = ['email']


class AlertConditionBuilder:
    """Helper class to build alert conditions for different alert types"""
    
    def __init__(self):
        """Initialize the condition builder"""
        pass
    
    def build_metric_threshold_condition(self, condition_config):
        """
        Build a metric threshold condition
        
        Args:
            condition_config: Configuration dictionary for the condition
            
        Returns:
            Built condition
        """
        # Extract configuration values
        filter_str = condition_config.get('filter')
        aggregation = condition_config.get('aggregation', {})
        comparison = condition_config.get('comparison', 'COMPARISON_GT')
        threshold = condition_config.get('threshold', 0.0)
        duration = condition_config.get('duration', {})
        
        # Create threshold object
        threshold_obj = monitoring_v3.types.AlertPolicy.Condition.MetricThreshold(
            filter=filter_str,
            comparison=getattr(monitoring_v3.types.ComparisonType, comparison),
            threshold_value=threshold
        )
        
        # Set aggregation if provided
        if aggregation:
            alignment_period = aggregation.get('alignment_period_seconds', 60)
            per_series_aligner = aggregation.get('per_series_aligner', 'ALIGN_RATE')
            cross_series_reducer = aggregation.get('cross_series_reducer', 'REDUCE_SUM')
            group_by_fields = aggregation.get('group_by_fields', [])
            
            threshold_obj.aggregations = [monitoring_v3.types.Aggregation(
                alignment_period={"seconds": alignment_period},
                per_series_aligner=getattr(monitoring_v3.types.Aggregation.Aligner, per_series_aligner),
                cross_series_reducer=getattr(monitoring_v3.types.Aggregation.Reducer, cross_series_reducer),
                group_by_fields=group_by_fields
            )]
        
        # Set duration if provided
        if duration:
            seconds = duration.get('seconds', 60)
            threshold_obj.duration = {"seconds": seconds}
        
        # Create condition
        return monitoring_v3.types.AlertPolicy.Condition(
            display_name=condition_config.get('display_name', 'Metric Threshold Condition'),
            condition_threshold=threshold_obj
        )
    
    def build_log_match_condition(self, condition_config):
        """
        Build a log match condition
        
        Args:
            condition_config: Configuration dictionary for the condition
            
        Returns:
            Built condition
        """
        # Extract configuration values
        filter_str = condition_config.get('filter')
        
        # Create log match object
        log_match = monitoring_v3.types.AlertPolicy.Condition.LogMatch(
            filter=filter_str
        )
        
        # Create condition
        return monitoring_v3.types.AlertPolicy.Condition(
            display_name=condition_config.get('display_name', 'Log Match Condition'),
            condition_log_match=log_match
        )
    
    def build_uptime_check_condition(self, condition_config):
        """
        Build an uptime check condition
        
        Args:
            condition_config: Configuration dictionary for the condition
            
        Returns:
            Built condition
        """
        # Extract configuration values
        uptime_check_id = condition_config.get('uptime_check_id')
        
        # Create uptime check object
        uptime_check = monitoring_v3.types.AlertPolicy.Condition.UptimeCheckCondition(
            uptime_check_id=uptime_check_id
        )
        
        # Create condition
        return monitoring_v3.types.AlertPolicy.Condition(
            display_name=condition_config.get('display_name', 'Uptime Check Condition'),
            condition_uptime_check=uptime_check
        )


class AlertManager:
    """Class that manages Google Cloud Monitoring alerts for the Budget Management Application"""
    
    def __init__(self, project_id):
        """
        Initialize the alert manager with project details and clients
        
        Args:
            project_id: Google Cloud project ID
        """
        self.project_id = project_id
        self.alert_client = monitoring_v3.AlertPolicyServiceClient()
        self.channel_client = monitoring_v3.NotificationChannelServiceClient()
        self.metric_client = monitoring_v3.MetricServiceClient()
        
        # Validate that project exists and clients can connect
        try:
            # Format project name for API
            self.project_name = f"projects/{self.project_id}"
            
            # Check if we can access the project
            self.alert_client.list_alert_policies(name=self.project_name)
            logger.info(f"Successfully connected to project {self.project_id}")
        except Exception as e:
            logger.error(f"Error connecting to project {self.project_id}: {e}")
            raise
    
    def setup_notification_channels(self, channels_config, update_existing=False):
        """
        Set up notification channels from configuration
        
        Args:
            channels_config: List of notification channel configurations
            update_existing: Whether to update existing channels
            
        Returns:
            Dictionary mapping channel names to channel IDs
        """
        channel_mapping = {}
        
        # Get existing channels if updating
        existing_channels = {}
        if update_existing:
            try:
                for channel in self.channel_client.list_notification_channels(name=self.project_name):
                    display_name = channel.display_name
                    existing_channels[display_name] = channel.name
                    logger.info(f"Found existing channel: {display_name}")
            except Exception as e:
                logger.error(f"Error listing existing notification channels: {e}")
        
        # Process each channel configuration
        for channel_config in channels_config:
            channel_type = channel_config.get('type')
            display_name = channel_config.get('display_name')
            
            if not channel_type or not display_name:
                logger.warning(f"Skipping channel with missing type or display_name: {channel_config}")
                continue
            
            # Check if channel already exists and update flag is set
            if update_existing and display_name in existing_channels:
                logger.info(f"Channel {display_name} already exists, skipping")
                channel_mapping[display_name] = existing_channels[display_name]
                continue
            
            try:
                # Create notification channel object
                channel = monitoring_v3.types.NotificationChannel(
                    type_=channel_type,
                    display_name=display_name,
                    labels=channel_config.get('labels', {})
                )
                
                # Set description if provided
                if 'description' in channel_config:
                    channel.description = channel_config['description']
                
                # Set enabled state if provided
                if 'enabled' in channel_config:
                    channel.enabled = channel_config['enabled']
                
                # Create the channel
                created_channel = self.channel_client.create_notification_channel(
                    name=self.project_name,
                    notification_channel=channel
                )
                
                # Store mapping
                channel_mapping[display_name] = created_channel.name
                logger.info(f"Created notification channel: {display_name} ({created_channel.name})")
                
            except Exception as e:
                logger.error(f"Error creating notification channel {display_name}: {e}")
        
        return channel_mapping
    
    def setup_alert_policies(self, policies_config, channel_mapping, update_existing=False):
        """
        Set up alert policies from configuration
        
        Args:
            policies_config: List of alert policy configurations
            channel_mapping: Dictionary mapping channel names to channel IDs
            update_existing: Whether to update existing policies
            
        Returns:
            List of created or updated policy IDs
        """
        policy_ids = []
        condition_builder = AlertConditionBuilder()
        
        # Get existing policies if updating
        existing_policies = {}
        if update_existing:
            try:
                for policy in self.alert_client.list_alert_policies(name=self.project_name):
                    display_name = policy.display_name
                    existing_policies[display_name] = policy
                    logger.info(f"Found existing policy: {display_name}")
            except Exception as e:
                logger.error(f"Error listing existing alert policies: {e}")
        
        # Process each policy configuration
        for policy_config in policies_config:
            display_name = policy_config.get('display_name')
            
            if not display_name:
                logger.warning(f"Skipping policy with missing display_name: {policy_config}")
                continue
            
            try:
                # Check if policy exists and update flag is set
                if update_existing and display_name in existing_policies:
                    # Update existing policy
                    policy = existing_policies[display_name]
                    
                    # Update description if provided
                    if 'description' in policy_config:
                        policy.documentation.content = policy_config['description']
                    
                    # Update notification channels if provided
                    if 'notification_channels' in policy_config:
                        policy.notification_channels = []
                        for channel_name in policy_config['notification_channels']:
                            if channel_name in channel_mapping:
                                policy.notification_channels.append(channel_mapping[channel_name])
                            else:
                                logger.warning(f"Notification channel {channel_name} not found")
                    
                    # Update conditions if provided
                    if 'conditions' in policy_config:
                        # Clear existing conditions
                        policy.conditions = []
                        
                        # Add new conditions
                        for condition_config in policy_config['conditions']:
                            condition_type = condition_config.get('condition_type', 'metric_threshold')
                            
                            if condition_type == 'metric_threshold':
                                condition = condition_builder.build_metric_threshold_condition(condition_config)
                            elif condition_type == 'log_match':
                                condition = condition_builder.build_log_match_condition(condition_config)
                            elif condition_type == 'uptime_check':
                                condition = condition_builder.build_uptime_check_condition(condition_config)
                            else:
                                logger.warning(f"Unsupported condition type: {condition_type}")
                                continue
                            
                            policy.conditions.append(condition)
                    
                    # Update the policy
                    updated_policy = self.alert_client.update_alert_policy(alert_policy=policy)
                    policy_ids.append(updated_policy.name)
                    logger.info(f"Updated alert policy: {display_name} ({updated_policy.name})")
                    
                else:
                    # Create new policy
                    # Prepare conditions
                    conditions = []
                    for condition_config in policy_config.get('conditions', []):
                        condition_type = condition_config.get('condition_type', 'metric_threshold')
                        
                        if condition_type == 'metric_threshold':
                            condition = condition_builder.build_metric_threshold_condition(condition_config)
                        elif condition_type == 'log_match':
                            condition = condition_builder.build_log_match_condition(condition_config)
                        elif condition_type == 'uptime_check':
                            condition = condition_builder.build_uptime_check_condition(condition_config)
                        else:
                            logger.warning(f"Unsupported condition type: {condition_type}")
                            continue
                        
                        conditions.append(condition)
                    
                    # Prepare notification channels
                    notification_channels = []
                    for channel_name in policy_config.get('notification_channels', []):
                        if channel_name in channel_mapping:
                            notification_channels.append(channel_mapping[channel_name])
                        else:
                            logger.warning(f"Notification channel {channel_name} not found")
                    
                    # Create policy object
                    policy = monitoring_v3.types.AlertPolicy(
                        display_name=display_name,
                        conditions=conditions,
                        notification_channels=notification_channels,
                        combiner=getattr(monitoring_v3.types.AlertPolicy.ConditionCombinerType, 
                                         policy_config.get('combiner', 'OR'))
                    )
                    
                    # Set documentation if provided
                    if 'description' in policy_config:
                        policy.documentation = monitoring_v3.types.AlertPolicy.Documentation(
                            content=policy_config['description'],
                            mime_type="text/markdown"
                        )
                    
                    # Create the policy
                    created_policy = self.alert_client.create_alert_policy(
                        name=self.project_name,
                        alert_policy=policy
                    )
                    
                    policy_ids.append(created_policy.name)
                    logger.info(f"Created alert policy: {display_name} ({created_policy.name})")
            
            except Exception as e:
                logger.error(f"Error creating/updating alert policy {display_name}: {e}")
        
        return policy_ids
    
    def setup_custom_metrics(self):
        """
        Set up custom metrics for monitoring
        
        Returns:
            List of created metric descriptors
        """
        custom_metrics = []
        
        # Define custom metrics for the Budget Management Application
        metrics_to_create = [
            {
                'type': 'custom.googleapis.com/budget_management/categorization_accuracy',
                'display_name': 'Transaction Categorization Accuracy',
                'description': 'Accuracy percentage of AI-based transaction categorization',
                'metric_kind': 'GAUGE',
                'value_type': 'DOUBLE',
                'unit': '%',
                'labels': [
                    {'key': 'source', 'description': 'Source of the transactions'}
                ]
            },
            {
                'type': 'custom.googleapis.com/budget_management/budget_variance_percentage',
                'display_name': 'Budget Variance Percentage',
                'description': 'Percentage variance between actual spending and budget',
                'metric_kind': 'GAUGE',
                'value_type': 'DOUBLE',
                'unit': '%',
                'labels': [
                    {'key': 'category', 'description': 'Budget category'},
                    {'key': 'direction', 'description': 'Over or under budget'}
                ]
            },
            {
                'type': 'custom.googleapis.com/budget_management/savings_transfer_amount',
                'display_name': 'Savings Transfer Amount',
                'description': 'Amount transferred to savings account',
                'metric_kind': 'GAUGE',
                'value_type': 'DOUBLE',
                'unit': '{USD}',
                'labels': []
            },
            {
                'type': 'custom.googleapis.com/budget_management/job_execution_duration',
                'display_name': 'Job Execution Duration',
                'description': 'Duration of job execution in seconds',
                'metric_kind': 'GAUGE',
                'value_type': 'DOUBLE',
                'unit': 's',
                'labels': [
                    {'key': 'component', 'description': 'Application component'}
                ]
            },
            {
                'type': 'custom.googleapis.com/budget_management/api_response_time',
                'display_name': 'API Response Time',
                'description': 'Response time of external API calls',
                'metric_kind': 'GAUGE',
                'value_type': 'DOUBLE',
                'unit': 's',
                'labels': [
                    {'key': 'api', 'description': 'API name'},
                    {'key': 'operation', 'description': 'API operation'}
                ]
            }
        ]
        
        # Create each metric descriptor
        for metric_config in metrics_to_create:
            try:
                # Convert labels to proper format
                labels = []
                for label in metric_config.get('labels', []):
                    labels.append(monitoring_v3.types.LabelDescriptor(
                        key=label['key'],
                        description=label.get('description', ''),
                        value_type=monitoring_v3.types.LabelDescriptor.ValueType.STRING
                    ))
                
                # Create metric descriptor
                descriptor = monitoring_v3.types.MetricDescriptor(
                    type=metric_config['type'],
                    display_name=metric_config['display_name'],
                    description=metric_config['description'],
                    metric_kind=getattr(monitoring_v3.types.MetricDescriptor.MetricKind, 
                                       metric_config['metric_kind']),
                    value_type=getattr(monitoring_v3.types.MetricDescriptor.ValueType, 
                                      metric_config['value_type']),
                    unit=metric_config.get('unit', ''),
                    labels=labels
                )
                
                # Create the metric descriptor
                created_descriptor = self.metric_client.create_metric_descriptor(
                    name=self.project_name,
                    metric_descriptor=descriptor
                )
                
                custom_metrics.append(created_descriptor)
                logger.info(f"Created custom metric: {metric_config['display_name']} ({metric_config['type']})")
                
            except Exception as e:
                logger.error(f"Error creating custom metric {metric_config['display_name']}: {e}")
        
        return custom_metrics
    
    def test_alerts(self, channel_mapping):
        """
        Test alert notifications
        
        Args:
            channel_mapping: Dictionary mapping channel names to channel IDs
            
        Returns:
            True if test was successful
        """
        try:
            # Check if we have a Gmail channel
            email_channel_found = False
            email_address = None
            
            for channel_name, channel_id in channel_mapping.items():
                if 'email' in channel_name.lower():
                    email_channel_found = True
                    try:
                        # Extract email from channel ID if possible
                        channel = self.channel_client.get_notification_channel(name=channel_id)
                        email_address = channel.labels.get('email')
                    except Exception:
                        email_address = MAINTENANCE_SETTINGS.get('ALERT_EMAIL', 'njdifiore@gmail.com')
                    break
            
            if not email_channel_found:
                email_address = MAINTENANCE_SETTINGS.get('ALERT_EMAIL', 'njdifiore@gmail.com')
            
            # Send test email using GmailClient
            try:
                logger.info(f"Sending test alert email to {email_address}")
                
                from ...backend.services.authentication_service import AuthenticationService
                auth_service = AuthenticationService()
                gmail_client = GmailClient(auth_service=auth_service)
                
                # Send test email
                subject = "Budget Management - Alert System Test"
                html_content = f"""
                <html>
                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #2196F3;">Budget Management Alert System Test</h2>
                    
                    <p>This is a test alert from the Budget Management Application monitoring system.</p>
                    
                    <p>If you received this email, alert notifications are working correctly.</p>
                    
                    <p style="color: #666;">
                        Test timestamp: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                    </p>
                </body>
                </html>
                """
                
                result = gmail_client.send_email(
                    subject=subject,
                    html_content=html_content,
                    recipients=[email_address]
                )
                
                logger.info(f"Test alert email sent: {result}")
                return True
                
            except Exception as e:
                logger.error(f"Error sending test alert email: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error testing alerts: {e}")
            return False
    
    def generate_report(self, channel_results, policy_results, metric_results):
        """
        Generate a comprehensive setup report
        
        Args:
            channel_results: Results of notification channel setup
            policy_results: Results of alert policy setup
            metric_results: Results of custom metric setup
            
        Returns:
            Setup report
        """
        # Count success/failure
        channel_count = len(channel_results)
        policy_count = len(policy_results)
        metric_count = len(metric_results)
        
        # Compile report
        report = {
            'timestamp': datetime.datetime.now().isoformat(),
            'project_id': self.project_id,
            'notification_channels': {
                'count': channel_count,
                'channels': channel_results
            },
            'alert_policies': {
                'count': policy_count,
                'policies': policy_results
            },
            'custom_metrics': {
                'count': metric_count,
                'metrics': [metric.type for metric in metric_results]
            },
            'summary': {
                'total_setup_items': channel_count + policy_count + metric_count,
                'status': 'success' if (channel_count > 0 and policy_count > 0) else 'partial_success'
            }
        }
        
        return report


def parse_arguments():
    """
    Parse command line arguments for the script
    
    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Set up Google Cloud Monitoring alerts for Budget Management Application'
    )
    
    parser.add_argument(
        '--project-id',
        default=DEFAULT_PROJECT_ID,
        help='Google Cloud project ID (defaults to GOOGLE_CLOUD_PROJECT env var)'
    )
    
    parser.add_argument(
        '--config-file',
        default=DEFAULT_ALERTS_CONFIG_PATH,
        help=f'Path to alert configuration file (default: {DEFAULT_ALERTS_CONFIG_PATH})'
    )
    
    parser.add_argument(
        '--notification-channels',
        nargs='+',
        default=DEFAULT_NOTIFICATION_CHANNELS,
        help=f'Notification channels to set up (default: {DEFAULT_NOTIFICATION_CHANNELS})'
    )
    
    parser.add_argument(
        '--update',
        action='store_true',
        help='Update existing alerts instead of creating new ones'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making any changes'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test alerts by sending test notifications'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser.parse_args()


def load_alerts_config(config_file):
    """
    Load alert configuration from JSON file
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        Alert configuration dictionary
    """
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        logger.info(f"Loaded alert configuration from {config_file}")
        return config
    except FileNotFoundError:
        logger.error(f"Alert configuration file not found: {config_file}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in alert configuration file: {config_file}")
        raise
    except Exception as e:
        logger.error(f"Error loading alert configuration: {e}")
        raise


def validate_alerts_config(config):
    """
    Validate the structure and content of the alerts configuration
    
    Args:
        config: Alert configuration dictionary
        
    Returns:
        True if configuration is valid, False otherwise
    """
    if not isinstance(config, dict):
        logger.error("Invalid configuration format: root must be a dictionary")
        return False
    
    # Check for required keys
    required_keys = ['alert_policies', 'notification_channels']
    missing_keys = [key for key in required_keys if key not in config]
    
    if missing_keys:
        logger.error(f"Missing required configuration keys: {', '.join(missing_keys)}")
        return False
    
    # Validate notification channels
    if not isinstance(config['notification_channels'], list):
        logger.error("Invalid notification_channels: must be a list")
        return False
    
    for i, channel in enumerate(config['notification_channels']):
        if not isinstance(channel, dict):
            logger.error(f"Invalid notification channel #{i+1}: must be a dictionary")
            return False
        
        if 'type' not in channel:
            logger.error(f"Invalid notification channel #{i+1}: missing 'type'")
            return False
        
        if 'display_name' not in channel:
            logger.error(f"Invalid notification channel #{i+1}: missing 'display_name'")
            return False
    
    # Validate alert policies
    if not isinstance(config['alert_policies'], list):
        logger.error("Invalid alert_policies: must be a list")
        return False
    
    for i, policy in enumerate(config['alert_policies']):
        if not isinstance(policy, dict):
            logger.error(f"Invalid alert policy #{i+1}: must be a dictionary")
            return False
        
        if 'display_name' not in policy:
            logger.error(f"Invalid alert policy #{i+1}: missing 'display_name'")
            return False
        
        if 'conditions' not in policy or not isinstance(policy['conditions'], list) or not policy['conditions']:
            logger.error(f"Invalid alert policy #{i+1}: missing or invalid 'conditions'")
            return False
    
    logger.info("Alert configuration validation successful")
    return True


def create_notification_channels(client, project_id, channels_config):
    """
    Create notification channels in Google Cloud Monitoring
    
    Args:
        client: NotificationChannelServiceClient instance
        project_id: Google Cloud project ID
        channels_config: List of notification channel configurations
        
    Returns:
        Dictionary mapping channel names to channel IDs
    """
    channel_mapping = {}
    
    # Format project name for API
    project_name = f"projects/{project_id}"
    
    # Process each channel configuration
    for channel_config in channels_config:
        channel_type = channel_config.get('type')
        display_name = channel_config.get('display_name')
        
        if not channel_type or not display_name:
            logger.warning(f"Skipping channel with missing type or display_name: {channel_config}")
            continue
        
        try:
            # Create notification channel object
            channel = monitoring_v3.types.NotificationChannel(
                type_=channel_type,
                display_name=display_name,
                labels=channel_config.get('labels', {})
            )
            
            # Set description if provided
            if 'description' in channel_config:
                channel.description = channel_config['description']
            
            # Set enabled state if provided
            if 'enabled' in channel_config:
                channel.enabled = channel_config['enabled']
            
            # Create the channel
            created_channel = client.create_notification_channel(
                name=project_name,
                notification_channel=channel
            )
            
            # Store mapping
            channel_mapping[display_name] = created_channel.name
            logger.info(f"Created notification channel: {display_name} ({created_channel.name})")
            
        except Exception as e:
            logger.error(f"Error creating notification channel {display_name}: {e}")
    
    return channel_mapping


def get_existing_notification_channels(client, project_id):
    """
    Get existing notification channels from Google Cloud Monitoring
    
    Args:
        client: NotificationChannelServiceClient instance
        project_id: Google Cloud project ID
        
    Returns:
        Dictionary mapping channel names to channel IDs
    """
    channel_mapping = {}
    
    # Format project name for API
    project_name = f"projects/{project_id}"
    
    try:
        # List existing channels
        for channel in client.list_notification_channels(name=project_name):
            display_name = channel.display_name
            channel_mapping[display_name] = channel.name
        
        logger.info(f"Found {len(channel_mapping)} existing notification channels")
        return channel_mapping
        
    except Exception as e:
        logger.error(f"Error listing notification channels: {e}")
        return {}


def create_alert_policies(client, project_id, policies_config, channel_mapping):
    """
    Create alert policies in Google Cloud Monitoring
    
    Args:
        client: AlertPolicyServiceClient instance
        project_id: Google Cloud project ID
        policies_config: List of alert policy configurations
        channel_mapping: Dictionary mapping channel names to channel IDs
        
    Returns:
        List of created alert policy IDs
    """
    policy_ids = []
    condition_builder = AlertConditionBuilder()
    
    # Format project name for API
    project_name = f"projects/{project_id}"
    
    # Process each policy configuration
    for policy_config in policies_config:
        display_name = policy_config.get('display_name')
        
        if not display_name:
            logger.warning(f"Skipping policy with missing display_name: {policy_config}")
            continue
        
        try:
            # Prepare conditions
            conditions = []
            for condition_config in policy_config.get('conditions', []):
                condition_type = condition_config.get('condition_type', 'metric_threshold')
                
                if condition_type == 'metric_threshold':
                    condition = condition_builder.build_metric_threshold_condition(condition_config)
                elif condition_type == 'log_match':
                    condition = condition_builder.build_log_match_condition(condition_config)
                elif condition_type == 'uptime_check':
                    condition = condition_builder.build_uptime_check_condition(condition_config)
                else:
                    logger.warning(f"Unsupported condition type: {condition_type}")
                    continue
                
                conditions.append(condition)
            
            # Prepare notification channels
            notification_channels = []
            for channel_name in policy_config.get('notification_channels', []):
                if channel_name in channel_mapping:
                    notification_channels.append(channel_mapping[channel_name])
                else:
                    logger.warning(f"Notification channel {channel_name} not found")
            
            # Create policy object
            policy = monitoring_v3.types.AlertPolicy(
                display_name=display_name,
                conditions=conditions,
                notification_channels=notification_channels,
                combiner=getattr(monitoring_v3.types.AlertPolicy.ConditionCombinerType, 
                                 policy_config.get('combiner', 'OR'))
            )
            
            # Set documentation if provided
            if 'description' in policy_config:
                policy.documentation = monitoring_v3.types.AlertPolicy.Documentation(
                    content=policy_config['description'],
                    mime_type="text/markdown"
                )
            
            # Create the policy
            created_policy = client.create_alert_policy(
                name=project_name,
                alert_policy=policy
            )
            
            policy_ids.append(created_policy.name)
            logger.info(f"Created alert policy: {display_name} ({created_policy.name})")
            
        except Exception as e:
            logger.error(f"Error creating alert policy {display_name}: {e}")
    
    return policy_ids


def get_existing_alert_policies(client, project_id):
    """
    Get existing alert policies from Google Cloud Monitoring
    
    Args:
        client: AlertPolicyServiceClient instance
        project_id: Google Cloud project ID
        
    Returns:
        Dictionary mapping policy names to policy objects
    """
    policy_mapping = {}
    
    # Format project name for API
    project_name = f"projects/{project_id}"
    
    try:
        # List existing policies
        for policy in client.list_alert_policies(name=project_name):
            display_name = policy.display_name
            policy_mapping[display_name] = policy
        
        logger.info(f"Found {len(policy_mapping)} existing alert policies")
        return policy_mapping
        
    except Exception as e:
        logger.error(f"Error listing alert policies: {e}")
        return {}


def update_alert_policies(client, project_id, policies_config, existing_policies, channel_mapping):
    """
    Update existing alert policies in Google Cloud Monitoring
    
    Args:
        client: AlertPolicyServiceClient instance
        project_id: Google Cloud project ID
        policies_config: List of alert policy configurations
        existing_policies: Dictionary mapping policy names to policy objects
        channel_mapping: Dictionary mapping channel names to channel IDs
        
    Returns:
        List of updated alert policy IDs
    """
    policy_ids = []
    condition_builder = AlertConditionBuilder()
    
    # Process each policy configuration
    for policy_config in policies_config:
        display_name = policy_config.get('display_name')
        
        if not display_name:
            logger.warning(f"Skipping policy with missing display_name: {policy_config}")
            continue
        
        try:
            # Check if policy exists
            if display_name in existing_policies:
                # Update existing policy
                policy = existing_policies[display_name]
                
                # Update description if provided
                if 'description' in policy_config:
                    policy.documentation.content = policy_config['description']
                
                # Update notification channels if provided
                if 'notification_channels' in policy_config:
                    policy.notification_channels = []
                    for channel_name in policy_config['notification_channels']:
                        if channel_name in channel_mapping:
                            policy.notification_channels.append(channel_mapping[channel_name])
                        else:
                            logger.warning(f"Notification channel {channel_name} not found")
                
                # Update conditions if provided
                if 'conditions' in policy_config:
                    # Clear existing conditions
                    policy.conditions = []
                    
                    # Add new conditions
                    for condition_config in policy_config['conditions']:
                        condition_type = condition_config.get('condition_type', 'metric_threshold')
                        
                        if condition_type == 'metric_threshold':
                            condition = condition_builder.build_metric_threshold_condition(condition_config)
                        elif condition_type == 'log_match':
                            condition = condition_builder.build_log_match_condition(condition_config)
                        elif condition_type == 'uptime_check':
                            condition = condition_builder.build_uptime_check_condition(condition_config)
                        else:
                            logger.warning(f"Unsupported condition type: {condition_type}")
                            continue
                        
                        policy.conditions.append(condition)
                
                # Update the policy
                updated_policy = client.update_alert_policy(alert_policy=policy)
                policy_ids.append(updated_policy.name)
                logger.info(f"Updated alert policy: {display_name} ({updated_policy.name})")
                
            else:
                # Create new policy
                logger.info(f"Policy {display_name} does not exist, creating new policy")
                new_policy_ids = create_alert_policies(client, project_id, [policy_config], channel_mapping)
                policy_ids.extend(new_policy_ids)
                
        except Exception as e:
            logger.error(f"Error updating alert policy {display_name}: {e}")
    
    return policy_ids


def delete_alert_policy(client, policy_id):
    """
    Delete an alert policy from Google Cloud Monitoring
    
    Args:
        client: AlertPolicyServiceClient instance
        policy_id: ID of the policy to delete
        
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        client.delete_alert_policy(name=policy_id)
        logger.info(f"Deleted alert policy: {policy_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting alert policy {policy_id}: {e}")
        return False


def test_alert_notification(project_id, channel_mapping):
    """
    Test alert notification by sending a test alert
    
    Args:
        project_id: Google Cloud project ID
        channel_mapping: Dictionary mapping channel names to channel IDs
        
    Returns:
        True if test was successful, False otherwise
    """
    try:
        # Check if we have a Gmail channel
        email_channel_found = False
        email_address = None
        
        for channel_name, channel_id in channel_mapping.items():
            if 'email' in channel_name.lower():
                email_channel_found = True
                # For now, use the default email address
                email_address = MAINTENANCE_SETTINGS.get('ALERT_EMAIL', 'njdifiore@gmail.com')
                break
        
        if not email_channel_found:
            email_address = MAINTENANCE_SETTINGS.get('ALERT_EMAIL', 'njdifiore@gmail.com')
        
        # Send test email using GmailClient
        try:
            logger.info(f"Sending test alert email to {email_address}")
            
            # Initialize GmailClient
            from ...backend.services.authentication_service import AuthenticationService
            auth_service = AuthenticationService()
            gmail_client = GmailClient(auth_service=auth_service)
            
            # Send test email
            subject = "Budget Management - Alert System Test"
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #2196F3;">Budget Management Alert System Test</h2>
                
                <p>This is a test alert from the Budget Management Application monitoring system.</p>
                
                <p>If you received this email, alert notifications are working correctly.</p>
                
                <p style="color: #666;">
                    Test timestamp: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                </p>
            </body>
            </html>
            """
            
            result = gmail_client.send_email(
                subject=subject,
                html_content=html_content,
                recipients=[email_address]
            )
            
            logger.info(f"Test alert email sent: {result}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending test alert email: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Error testing alerts: {e}")
        return False


def create_custom_metrics(client, project_id):
    """
    Create custom metrics for Budget Management Application
    
    Args:
        client: MetricServiceClient instance
        project_id: Google Cloud project ID
        
    Returns:
        List of created metric descriptors
    """
    custom_metrics = []
    
    # Format project name for API
    project_name = f"projects/{project_id}"
    
    # Define custom metrics for the Budget Management Application
    metrics_to_create = [
        {
            'type': 'custom.googleapis.com/budget_management/categorization_accuracy',
            'display_name': 'Transaction Categorization Accuracy',
            'description': 'Accuracy percentage of AI-based transaction categorization',
            'metric_kind': 'GAUGE',
            'value_type': 'DOUBLE',
            'unit': '%',
            'labels': [
                {'key': 'source', 'description': 'Source of the transactions'}
            ]
        },
        {
            'type': 'custom.googleapis.com/budget_management/budget_variance_percentage',
            'display_name': 'Budget Variance Percentage',
            'description': 'Percentage variance between actual spending and budget',
            'metric_kind': 'GAUGE',
            'value_type': 'DOUBLE',
            'unit': '%',
            'labels': [
                {'key': 'category', 'description': 'Budget category'},
                {'key': 'direction', 'description': 'Over or under budget'}
            ]
        },
        {
            'type': 'custom.googleapis.com/budget_management/savings_transfer_amount',
            'display_name': 'Savings Transfer Amount',
            'description': 'Amount transferred to savings account',
            'metric_kind': 'GAUGE',
            'value_type': 'DOUBLE',
            'unit': '{USD}',
            'labels': []
        },
        {
            'type': 'custom.googleapis.com/budget_management/job_execution_duration',
            'display_name': 'Job Execution Duration',
            'description': 'Duration of job execution in seconds',
            'metric_kind': 'GAUGE',
            'value_type': 'DOUBLE',
            'unit': 's',
            'labels': [
                {'key': 'component', 'description': 'Application component'}
            ]
        },
        {
            'type': 'custom.googleapis.com/budget_management/api_response_time',
            'display_name': 'API Response Time',
            'description': 'Response time of external API calls',
            'metric_kind': 'GAUGE',
            'value_type': 'DOUBLE',
            'unit': 's',
            'labels': [
                {'key': 'api', 'description': 'API name'},
                {'key': 'operation', 'description': 'API operation'}
            ]
        }
    ]
    
    # Create each metric descriptor
    for metric_config in metrics_to_create:
        try:
            # Convert labels to proper format
            labels = []
            for label in metric_config.get('labels', []):
                labels.append(monitoring_v3.types.LabelDescriptor(
                    key=label['key'],
                    description=label.get('description', ''),
                    value_type=monitoring_v3.types.LabelDescriptor.ValueType.STRING
                ))
            
            # Create metric descriptor
            descriptor = monitoring_v3.types.MetricDescriptor(
                type=metric_config['type'],
                display_name=metric_config['display_name'],
                description=metric_config['description'],
                metric_kind=getattr(monitoring_v3.types.MetricDescriptor.MetricKind, 
                                   metric_config['metric_kind']),
                value_type=getattr(monitoring_v3.types.MetricDescriptor.ValueType, 
                                  metric_config['value_type']),
                unit=metric_config.get('unit', ''),
                labels=labels
            )
            
            # Create the metric descriptor
            created_descriptor = client.create_metric_descriptor(
                name=project_name,
                metric_descriptor=descriptor
            )
            
            custom_metrics.append(created_descriptor)
            logger.info(f"Created custom metric: {metric_config['display_name']} ({metric_config['type']})")
            
        except Exception as e:
            logger.error(f"Error creating custom metric {metric_config['display_name']}: {e}")
    
    return custom_metrics


def generate_setup_report(channel_results, policy_results, metric_results):
    """
    Generate a report of the alert setup process
    
    Args:
        channel_results: Dictionary mapping channel names to channel IDs
        policy_results: List of created alert policy IDs
        metric_results: List of created metric descriptors
        
    Returns:
        Setup report dictionary
    """
    # Count success/failure
    channel_count = len(channel_results)
    policy_count = len(policy_results)
    metric_count = len(metric_results)
    
    # Compile report
    report = {
        'timestamp': datetime.datetime.now().isoformat(),
        'notification_channels': {
            'count': channel_count,
            'channels': [{'display_name': name, 'id': id} for name, id in channel_results.items()]
        },
        'alert_policies': {
            'count': policy_count,
            'policies': policy_results
        },
        'custom_metrics': {
            'count': metric_count,
            'metrics': [metric.type for metric in metric_results] if metric_results else []
        },
        'summary': {
            'total_setup_items': channel_count + policy_count + metric_count,
            'status': 'success' if (channel_count > 0 and policy_count > 0) else 'partial_success'
        }
    }
    
    return report


def save_setup_report(report, output_file):
    """
    Save the alert setup report to a file
    
    Args:
        report: Setup report dictionary
        output_file: Path to output file
        
    Returns:
        Path to the saved report file
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Write report to file
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Saved setup report to {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"Error saving setup report: {e}")
        return None


def send_setup_notification(report, recipient_email):
    """
    Send email notification about alert setup status
    
    Args:
        report: Setup report dictionary
        recipient_email: Email address to send notification to
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Initialize GmailClient
        from ...backend.services.authentication_service import AuthenticationService
        auth_service = AuthenticationService()
        gmail_client = GmailClient(auth_service=auth_service)
        
        # Prepare email content
        status = report['summary']['status']
        total_items = report['summary']['total_setup_items']
        
        subject = f"Budget Management - Alert Setup {status.title()}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2196F3;">Budget Management Alert Setup Report</h2>
            
            <p>The alert setup process has completed with status: <strong>{status.title()}</strong>.</p>
            
            <h3>Summary:</h3>
            <ul>
                <li>Total setup items: {total_items}</li>
                <li>Notification channels: {report['notification_channels']['count']}</li>
                <li>Alert policies: {report['alert_policies']['count']}</li>
                <li>Custom metrics: {report['custom_metrics']['count']}</li>
            </ul>
            
            <p style="color: #666;">
                Setup timestamp: {report['timestamp']}
            </p>
        </body>
        </html>
        """
        
        # Send email
        result = gmail_client.send_email(
            subject=subject,
            html_content=html_content,
            recipients=[recipient_email]
        )
        
        logger.info(f"Setup notification email sent to {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending setup notification: {e}")
        return False


def main():
    """
    Main function that orchestrates alert setup process
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Log script start
        logger.info(f"Starting alert setup for project {args.project_id}")
        logger.info(f"Using config file: {args.config_file}")
        logger.info(f"Update mode: {args.update}, Dry run: {args.dry_run}, Test: {args.test}")
        
        # Load alert configuration
        config = load_alerts_config(args.config_file)
        
        # Validate configuration
        if not validate_alerts_config(config):
            logger.error("Invalid alert configuration, aborting")
            return 1
        
        # If dry run, just log what would be done
        if args.dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
            logger.info(f"Would create {len(config['notification_channels'])} notification channels")
            logger.info(f"Would create {len(config['alert_policies'])} alert policies")
            logger.info("Would create custom metrics for budget management")
            return 0
        
        # Initialize Google Cloud Monitoring clients
        try:
            alert_client = monitoring_v3.AlertPolicyServiceClient()
            channel_client = monitoring_v3.NotificationChannelServiceClient()
            metric_client = monitoring_v3.MetricServiceClient()
            logger.info("Initialized Google Cloud Monitoring clients")
        except Exception as e:
            logger.error(f"Error initializing Google Cloud Monitoring clients: {e}")
            return 1
        
        # Create or update notification channels
        channel_mapping = {}
        if args.update:
            # Get existing channels
            existing_channels = get_existing_notification_channels(channel_client, args.project_id)
            channel_mapping.update(existing_channels)
            
        # Filter channels based on command line arguments
        selected_channels = [c for c in config['notification_channels'] 
                             if c.get('type') in args.notification_channels]
        
        # Create notification channels
        if not args.update:
            new_channels = create_notification_channels(channel_client, args.project_id, selected_channels)
            channel_mapping.update(new_channels)
        
        # Create or update alert policies
        policy_ids = []
        if args.update:
            # Get existing policies
            existing_policies = get_existing_alert_policies(alert_client, args.project_id)
            
            # Update existing policies
            policy_ids = update_alert_policies(
                alert_client, 
                args.project_id, 
                config['alert_policies'], 
                existing_policies,
                channel_mapping
            )
        else:
            # Create new policies
            policy_ids = create_alert_policies(
                alert_client,
                args.project_id,
                config['alert_policies'],
                channel_mapping
            )
        
        # Create custom metrics
        custom_metrics = create_custom_metrics(metric_client, args.project_id)
        
        # Test alert notifications if requested
        if args.test:
            logger.info("Testing alert notifications")
            test_result = test_alert_notification(args.project_id, channel_mapping)
            if test_result:
                logger.info("Alert notification test successful")
            else:
                logger.warning("Alert notification test failed")
        
        # Generate setup report
        setup_report = generate_setup_report(channel_mapping, policy_ids, custom_metrics)
        
        # Save report to file
        report_dir = os.path.join(os.path.dirname(args.config_file), 'reports')
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = os.path.join(report_dir, f'alert_setup_report_{timestamp}.json')
        save_setup_report(setup_report, report_file)
        
        # Send notification email if requested
        if MAINTENANCE_SETTINGS.get('ALERT_ON_ERROR', False):
            recipient = MAINTENANCE_SETTINGS.get('ALERT_EMAIL', 'njdifiore@gmail.com')
            send_setup_notification(setup_report, recipient)
        
        # Log completion and return success code
        status = setup_report['summary']['status']
        logger.info(f"Alert setup completed with status: {status}")
        return 0 if status == 'success' else 1
        
    except Exception as e:
        logger.error(f"Error during alert setup: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())