"""
Initialization file for the tests package in the Budget Management Application.

This file marks the tests directory as a Python package, defines package-level
constants, and provides centralized access to test utilities, fixtures, and mock
objects to simplify imports across test modules.
"""

import os  # standard library
import typing  # standard library
import pytest  # pytest 7.4.0+

# Define directory paths for easy access in test modules
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TESTS_DIR)
SRC_DIR = os.path.dirname(BACKEND_DIR)
PROJECT_ROOT = os.path.dirname(SRC_DIR)

# Import subpackage paths
from .unit import UNIT_TESTS_DIR
from .fixtures import FIXTURES_DIR, DATA_DIR

# Define package version
__version__ = "1.0.0"


def get_test_file_path(relative_path: str) -> str:
    """
    Helper function to get the absolute path to a test file.
    
    Args:
        relative_path: Relative path from the tests directory
        
    Returns:
        Absolute path to the test file
    """
    return os.path.join(TESTS_DIR, relative_path)


def get_fixture_file_path(relative_path: str) -> str:
    """
    Helper function to get the absolute path to a fixture file.
    
    Args:
        relative_path: Relative path from the fixtures data directory
        
    Returns:
        Absolute path to the fixture file
    """
    return os.path.join(DATA_DIR, relative_path)