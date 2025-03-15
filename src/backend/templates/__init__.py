"""
Templates package initialization for the Budget Management Application.

This module exports template resources used throughout the application,
including email templates and AI prompt templates for various operations.
"""

import os
from .ai_prompts import (
    categorization_prompt_template,
    insight_generation_prompt_template,
    PROMPT_TEMPLATES,
    load_prompt
)

# Define the path to the templates directory
TEMPLATES_DIR = os.path.dirname(os.path.abspath(__file__))

# Define the path to the email template
EMAIL_TEMPLATE_PATH = os.path.join(TEMPLATES_DIR, 'email_template.html')

def load_email_template():
    """
    Loads the HTML email template for budget reports.
    
    Returns:
        str: Content of the email template file
    """
    try:
        with open(EMAIL_TEMPLATE_PATH, 'r') as file:
            return file.read()
    except Exception as e:
        # Log the error rather than raising to allow for fallback templates
        import logging
        logging.error(f"Error loading email template: {str(e)}")
        return ""

def get_template_path(template_name):
    """
    Gets the absolute path to a template file.
    
    Args:
        template_name (str): Name of the template file
        
    Returns:
        str: Absolute path to the template file
    """
    return os.path.join(TEMPLATES_DIR, template_name)

# Define what should be accessible when importing from this package
__all__ = [
    'load_email_template',
    'get_template_path',
    'EMAIL_TEMPLATE_PATH',
    'TEMPLATES_DIR',
    'categorization_prompt_template',
    'insight_generation_prompt_template',
    'PROMPT_TEMPLATES',
    'load_prompt'
]