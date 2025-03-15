"""Initialization module for the monitoring package in the Budget Management Application.
This module exposes key monitoring components and utilities for tracking application health, performance, and operational metrics. 
It provides a unified interface to access monitoring functionality across the application.
"""

# Internal imports
from .check_job_status import check_job_status  # Import job status checking functionality
from .analyze_logs import analyze_logs  # Import log analysis functionality
from .alert_setup import alert_setup  # Import alert setup functionality
from .performance_report import performance_report  # Import performance reporting functionality
from .generate_dashboard import generate_dashboard  # Import dashboard generation functionality
from ..config.logging_setup import get_logger  # Get configured logger for the module

# Initialize logger
logger = get_logger('monitoring')

# Version information for the monitoring package
__version__ = '1.0.0'

# Export classes and modules for external use
__all__ = [
    'JobStatusChecker',
    'LogAnalyzer',
    'AlertManager',
    'PerformanceAnalyzer',
    'DashboardGenerator',
    'check_job_status',
    'analyze_logs',
    'alert_setup',
    'performance_report',
    'generate_dashboard',
    '__version__'
]

# Import classes and modules to be exported
from .check_job_status import JobStatusChecker
from .analyze_logs import LogAnalyzer
from .alert_setup import AlertManager
from .performance_report import PerformanceAnalyzer
from .generate_dashboard import DashboardGenerator

logger.info(f"Monitoring package initialized. Version: {__version__}")