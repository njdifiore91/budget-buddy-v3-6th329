"""
Package initialization file for the manual utility scripts in the Budget Management Application.

This module exposes the main functions from each manual utility script to provide a simplified
import interface for manual operations, debugging, and maintenance tasks.
"""

# Category management
from .reset_categories import reset_categories, reset_specific_category
from .fix_categorization import fix_transaction_categories, get_categorized_transactions

# Email testing
from .send_test_email import main as send_test_email_main

# Financial operations
from .force_transfer import main as force_transfer_main

# Debugging and monitoring
from .debug_job import test_component, test_all_components, get_job_logs, analyze_logs, ComponentTester, LogAnalyzer

# Job management
from .trigger_job import trigger_job, check_gcloud_installed

# Main entry points
from .reset_categories import main as reset_categories_main
from .fix_categorization import main as fix_categorization_main
from .debug_job import main as debug_job_main
from .trigger_job import main as trigger_job_main

__all__ = [
    # Category management
    'reset_categories',
    'reset_specific_category',
    'fix_transaction_categories',
    'get_categorized_transactions',
    
    # Email testing
    'send_test_email_main',
    
    # Financial operations
    'force_transfer_main',
    
    # Debugging and monitoring
    'test_component',
    'test_all_components',
    'get_job_logs',
    'analyze_logs',
    'ComponentTester',
    'LogAnalyzer',
    
    # Job management
    'trigger_job',
    'check_gcloud_installed',
    
    # Main entry points
    'reset_categories_main',
    'fix_categorization_main',
    'debug_job_main',
    'trigger_job_main'
]