"""
Security tests package for the Budget Management Application.

This package provides utilities and constants for testing security aspects
of the application, including credential handling, data masking, and
secure API interactions.
"""

import os
import re
import pytest

# Define the base directory for security tests
SECURITY_TEST_DIR = os.path.dirname(os.path.abspath(__file__))

# Regular expression patterns for sensitive data detection and masking
ACCOUNT_NUMBER_PATTERN = re.compile(r'\d{4}-\d{4}-\d{4}-\d{4}')
MASKED_ACCOUNT_PATTERN = re.compile(r'XXXX-XXXX-XXXX-\d{4}')
API_KEY_PATTERN = re.compile(r'[A-Za-z0-9_\-]{20,}')
MASKED_API_KEY_PATTERN = re.compile(r'\[REDACTED\]')
OAUTH_TOKEN_PATTERN = re.compile(r'Bearer [A-Za-z0-9_\-\.]+')
MASKED_OAUTH_TOKEN_PATTERN = re.compile(r'Bearer \[REDACTED\]')

def security_test_marker():
    """
    Pytest marker for identifying security tests.
    
    This marker can be used to selectively run security tests or apply
    special handling to security-focused test cases.
    
    Returns:
        pytest.mark: Pytest marker for security tests
    """
    return pytest.mark.security

# Define the public API of the security tests package
__all__ = [
    "ACCOUNT_NUMBER_PATTERN", 
    "MASKED_ACCOUNT_PATTERN", 
    "API_KEY_PATTERN", 
    "MASKED_API_KEY_PATTERN", 
    "OAUTH_TOKEN_PATTERN", 
    "MASKED_OAUTH_TOKEN_PATTERN", 
    "security_test_marker"
]