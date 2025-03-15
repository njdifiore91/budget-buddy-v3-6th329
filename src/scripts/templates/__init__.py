"""
Initialization module for the templates package that provides access to standardized
templates used throughout the Budget Management Application.

This module exports template files for shell scripts, Python scripts, maintenance
checklists, recovery runbooks, and deployment reports, ensuring consistency across
the application's tools and documentation.

Exports:
    shell_template: Standard shell script template
    python_template: Standard Python script template
    maintenance_checklist_template: Template for maintenance checklists
    recovery_runbook_template: Template for disaster recovery procedures
    deployment_report_template: Template for deployment reporting
    TEMPLATES_DIR: Directory containing template files
    TEMPLATE_FILES: Dictionary mapping template names to their content
    load_template: Function to load a specific template by name
    get_template_path: Function to get the absolute path to a template file
    list_available_templates: Function to list all available templates
"""

import os
import pathlib

# Import template files as strings
from .shell_template import shell_template
from .python_template import python_template
from .maintenance_checklist import maintenance_checklist_template
from .recovery_runbook import recovery_runbook_template
from .deployment_report import deployment_report_template

# Define the templates directory path
TEMPLATES_DIR = os.path.dirname(os.path.abspath(__file__))

# Map template names to their content for easy access
TEMPLATE_FILES = {
    'shell': shell_template,
    'python': python_template,
    'maintenance_checklist': maintenance_checklist_template,
    'recovery_runbook': recovery_runbook_template,
    'deployment_report': deployment_report_template
}

def load_template(template_name):
    """
    Loads a template file by name from the TEMPLATE_FILES dictionary.
    
    Args:
        template_name (str): The name of the template to load.
        
    Returns:
        str: The requested template content.
        
    Raises:
        ValueError: If the template_name is not found in the TEMPLATE_FILES dictionary.
    """
    if template_name in TEMPLATE_FILES:
        return TEMPLATE_FILES[template_name]
    else:
        raise ValueError(f"Template '{template_name}' not found. Available templates: {', '.join(TEMPLATE_FILES.keys())}")

def get_template_path(template_name):
    """
    Gets the absolute file path for a template file.
    
    Args:
        template_name (str): The name of the template file.
        
    Returns:
        str: Absolute path to the template file.
        
    Raises:
        ValueError: If the template_name is not found in the TEMPLATE_FILES dictionary.
        FileNotFoundError: If the template file does not exist on disk.
    """
    if template_name not in TEMPLATE_FILES:
        raise ValueError(f"Template '{template_name}' not found. Available templates: {', '.join(TEMPLATE_FILES.keys())}")
    
    # Map template name to filename
    filename_map = {
        'shell': 'shell_template.sh',
        'python': 'python_template.py',
        'maintenance_checklist': 'maintenance_checklist.md',
        'recovery_runbook': 'recovery_runbook.md',
        'deployment_report': 'deployment_report.md'
    }
    
    template_path = os.path.join(TEMPLATES_DIR, filename_map[template_name])
    
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template file '{template_path}' does not exist.")
    
    return template_path

def list_available_templates():
    """
    Returns a list of all available template names.
    
    Returns:
        list: List of available template names.
    """
    return list(TEMPLATE_FILES.keys())