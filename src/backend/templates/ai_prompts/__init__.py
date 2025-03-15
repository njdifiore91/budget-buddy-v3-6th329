"""
AI prompt templates for the Budget Management Application.

This module provides prompt templates for Gemini AI operations used in the application,
particularly for transaction categorization and spending insight generation.
"""

import os

# Define the directory where the prompt templates are located
_PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Read the prompt templates from text files
with open(os.path.join(_PROMPTS_DIR, 'categorization_prompt.txt'), 'r') as f:
    categorization_prompt_template = f.read()

with open(os.path.join(_PROMPTS_DIR, 'insight_generation_prompt.txt'), 'r') as f:
    insight_generation_prompt_template = f.read()

# Define a dictionary mapping template names to their content
PROMPT_TEMPLATES = {
    "categorization": categorization_prompt_template,
    "insight_generation": insight_generation_prompt_template
}

def load_prompt(template_name: str) -> str:
    """
    Load a prompt template by name.
    
    Args:
        template_name: The name of the template to load
        
    Returns:
        The requested prompt template text
        
    Raises:
        ValueError: If the requested template name is not found
    """
    if template_name not in PROMPT_TEMPLATES:
        raise ValueError(f"Unknown prompt template: {template_name}")
    
    return PROMPT_TEMPLATES[template_name]

# Make prompts and utilities available for import
__all__ = [
    "categorization_prompt_template",
    "insight_generation_prompt_template",
    "PROMPT_TEMPLATES",
    "load_prompt"
]