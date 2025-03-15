"""
Main initialization file for the Budget Management Application's utility scripts package.
This module serves as the entry point for the scripts package, exposing commonly used functions and classes from submodules while providing version information and package metadata. It simplifies imports for script users and establishes a consistent interface for utility scripts.
"""

import os  # standard library
import sys  # standard library
import logging  # standard library

# Internal imports
from .config import *  # Import all configuration utilities and constants
from .utils import test_all_apis  # Import utility function for testing all APIs
from .utils import read_sheet  # Import utility function for reading Google Sheets
from .utils import write_sheet  # Import utility function for writing to Google Sheets
from .utils import append_to_sheet  # Import utility function for appending to Google Sheets
from .utils import get_sheet_as_dataframe  # Import utility function for converting sheet data to DataFrame
from .tools import ResponseAnalyzer  # Import class for analyzing API responses
from .tools import SheetValidator  # Import class for validating Google Sheets
from .tools import TransactionSimulator  # Import class for simulating transactions
from .tools import BudgetCalculator  # Import class for budget calculations
from .config import setup_logging  # Import logging setup function
from .config import get_logger  # Import function to get a configured logger
from .config import initialize_script_environment  # Import function to initialize script environment
from .config import ROOT_DIR  # Import path to the project root directory
from .config import SCRIPTS_DIR  # Import path to the scripts directory
from .config import DATA_DIR  # Import path to the data directory
from .config import LOGS_DIR  # Import path to the logs directory
from .config import BACKUP_DIR  # Import path to the backups directory
from .config import CREDENTIALS_DIR  # Import path to the credentials directory
from .config import TEMPLATES_DIR  # Import path to the templates directory

__version__ = "1.0.0"
__author__ = "Nick DiFiore"
__email__ = "njdifiore@gmail.com"

__all__ = ["test_all_apis", "read_sheet", "write_sheet", "append_to_sheet", "get_sheet_as_dataframe", "ResponseAnalyzer", "SheetValidator", "TransactionSimulator", "BudgetCalculator", "setup_logging", "get_logger", "initialize_script_environment", "ROOT_DIR", "SCRIPTS_DIR", "DATA_DIR", "LOGS_DIR", "BACKUP_DIR", "CREDENTIALS_DIR", "TEMPLATES_DIR", "get_version", "setup_script_paths"]


def setup_script_paths():
    """
    Ensures that the script directory is in the Python path
    """
    # Get the absolute path to the scripts directory
    scripts_dir = os.path.abspath(os.path.dirname(__file__))
    
    # Check if the scripts directory is in sys.path
    if scripts_dir not in sys.path:
        # If not, add the scripts directory to sys.path
        sys.path.insert(0, scripts_dir)
        
    # Add the parent directory (src) to sys.path if not already present
    src_dir = os.path.abspath(os.path.join(scripts_dir, '..'))
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)


def get_version() -> str:
    """
    Returns the current version of the scripts package
    
    Returns:
        str: Version string
    """
    return __version__