"""
Defines path constants used throughout the Budget Management Application's utility scripts.

This module provides standardized access to important directories and file paths,
ensuring consistency across all scripts and utilities. By centralizing path definitions,
it helps maintain a consistent directory structure and simplifies path management
across the application.

Key directories defined:
- ROOT_DIR: The root directory of the project
- BACKEND_DIR: Directory containing backend source code
- SCRIPTS_DIR: Directory containing utility scripts
- CONFIG_DIR: Directory containing configuration files
- DATA_DIR: Directory for data storage
- LOGS_DIR: Directory for application logs
- BACKUP_DIR: Directory for backups
- CREDENTIALS_DIR: Directory for storing credentials
- TEMPLATES_DIR: Directory for script templates

Key files defined:
- ENV_FILE: Path to the .env file
- ENV_EXAMPLE_FILE: Path to the .env.example file

The module also provides utility functions for common path operations:
- ensure_dir_exists: Creates a directory if it doesn't exist
- get_relative_path: Gets a path relative to the project root
- get_absolute_path: Gets an absolute path from a relative path
- create_directory_structure: Creates the standard directory structure
"""

import os
from pathlib import Path

# Get the absolute path to the project root directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../../..'))

# Define key directories
BACKEND_DIR = os.path.join(ROOT_DIR, 'src', 'backend')
SCRIPTS_DIR = os.path.join(ROOT_DIR, 'src', 'scripts')
CONFIG_DIR = os.path.join(SCRIPTS_DIR, 'config')
DATA_DIR = os.path.join(ROOT_DIR, 'data')
LOGS_DIR = os.path.join(DATA_DIR, 'logs')
BACKUP_DIR = os.path.join(DATA_DIR, 'backups')
CREDENTIALS_DIR = os.path.join(ROOT_DIR, 'credentials')
TEMPLATES_DIR = os.path.join(SCRIPTS_DIR, 'templates')

# Define key files
ENV_FILE = os.path.join(ROOT_DIR, '.env')
ENV_EXAMPLE_FILE = os.path.join(BACKEND_DIR, '.env.example')

def ensure_dir_exists(directory_path: str) -> str:
    """
    Ensures that a directory exists, creating it if necessary.
    
    Args:
        directory_path: The path to the directory to ensure exists.
        
    Returns:
        The path to the directory that was ensured to exist.
    """
    Path(directory_path).mkdir(parents=True, exist_ok=True)
    return directory_path

def get_relative_path(path: str) -> str:
    """
    Gets a path relative to the project root directory.
    
    Args:
        path: The path to convert to a relative path.
        
    Returns:
        The path relative to the project root.
    """
    try:
        return str(Path(path).absolute().relative_to(Path(ROOT_DIR)))
    except ValueError:
        # Handle paths that are not under ROOT_DIR
        return os.path.relpath(os.path.abspath(path), ROOT_DIR)

def get_absolute_path(relative_path: str) -> str:
    """
    Gets the absolute path from a path relative to the project root.
    
    Args:
        relative_path: The relative path to convert to an absolute path.
        
    Returns:
        The absolute path.
    """
    return str(Path(ROOT_DIR).joinpath(relative_path).absolute())

def create_directory_structure() -> bool:
    """
    Creates the standard directory structure for the application.
    
    Returns:
        True if all directories were created successfully, False otherwise.
    """
    try:
        ensure_dir_exists(DATA_DIR)
        ensure_dir_exists(LOGS_DIR)
        ensure_dir_exists(BACKUP_DIR)
        
        # Ensure credentials directory exists with appropriate permissions
        credentials_path = Path(CREDENTIALS_DIR)
        if not credentials_path.exists():
            credentials_path.mkdir(parents=True, exist_ok=True)
            os.chmod(CREDENTIALS_DIR, 0o700)  # Secure permissions for credentials
        
        return True
    except Exception as e:
        print(f"Error creating directory structure: {e}")
        return False