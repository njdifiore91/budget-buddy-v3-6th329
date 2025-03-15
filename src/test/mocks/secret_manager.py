"""
Mock implementation of Google Cloud Secret Manager for testing the Budget Management Application.

Provides simulated Secret Manager functionality to enable testing of credential handling
and authentication without requiring actual Secret Manager access.
"""

import os
import json
from typing import Dict, Any, Optional, List
from unittest.mock import MagicMock

from ..utils.fixture_loader import load_fixture


# Default test secrets for use in tests
DEFAULT_TEST_SECRETS = {
    'capital-one-credentials': '{"client_id": "test_client_id", "client_secret": "test_client_secret"}',
    'google-sheets-credentials': '{"type": "service_account", "project_id": "test-project", "private_key": "test_private_key", "client_email": "test@example.com"}',
    'gmail-credentials': '{"type": "service_account", "project_id": "test-project", "private_key": "test_private_key", "client_email": "test@example.com"}',
    'gemini-api-key': 'test_gemini_api_key'
}


def load_fixture(fixture_name: str) -> Dict[str, Any]:
    """
    Load secret data from test fixtures.
    
    Args:
        fixture_name: Name of the fixture file
        
    Returns:
        Secret data from fixture
    """
    # Construct path to the fixture file in api_responses/secret_manager directory
    fixture_path = f"api_responses/secret_manager/{fixture_name}"
    
    # Load and return the fixture data using the fixture_loader utility
    return load_fixture(fixture_path)


def create_secret_version_response(name: str, payload: bytes) -> MagicMock:
    """
    Create a mock SecretVersion response object.
    
    Args:
        name: Name of the secret version
        payload: Secret payload data as bytes
        
    Returns:
        Mock SecretVersion response
    """
    mock_response = MagicMock()
    mock_response.name = name
    mock_response.payload = MagicMock()
    mock_response.payload.data = payload
    return mock_response


class MockSecretVersion:
    """Mock implementation of Google Cloud Secret Manager SecretVersion."""
    
    def __init__(self, name: str, payload_data: bytes):
        """
        Initialize the MockSecretVersion with name and payload.
        
        Args:
            name: Name of the secret version
            payload_data: Secret payload as bytes
        """
        self.name = name
        self.payload = MagicMock()
        self.payload.data = payload_data
    
    def to_dict(self) -> dict:
        """
        Convert the mock secret version to a dictionary.
        
        Returns:
            Dictionary representation of the secret version
        """
        return {
            'name': self.name,
            'payload': {
                'data': self.payload.data
            }
        }


class MockSecretManagerClient:
    """Core implementation of Secret Manager mock functionality."""
    
    def __init__(self, test_secrets: Optional[Dict[str, str]] = None, 
                 should_fail: bool = False, failure_mode: str = 'not_found'):
        """
        Initialize the MockSecretManagerClient with optional test secrets.
        
        Args:
            test_secrets: Dictionary mapping secret IDs to secret values
            should_fail: Whether operations should simulate failures
            failure_mode: Type of failure to simulate ('not_found', 'permission_denied', etc.)
        """
        self.secrets = {}
        
        # Initialize with test secrets if provided
        if test_secrets:
            for secret_id, secret_value in test_secrets.items():
                self.add_secret(secret_id, secret_value)
        
        self.should_fail = should_fail
        self.failure_mode = failure_mode
    
    def add_secret(self, secret_id: str, secret_value: str) -> None:
        """
        Add a secret to the mock Secret Manager.
        
        Args:
            secret_id: ID of the secret
            secret_value: Value of the secret
        """
        # Convert string value to bytes for consistency with real Secret Manager
        self.secrets[secret_id] = secret_value.encode('utf-8')
    
    def get_secret(self, secret_id: str) -> str:
        """
        Retrieve a secret from the mock Secret Manager.
        
        Args:
            secret_id: ID of the secret to retrieve
            
        Returns:
            Secret value as string
            
        Raises:
            KeyError: If the secret doesn't exist
            Exception: If should_fail is True
        """
        # Simulate failure if requested
        if self.should_fail:
            if self.failure_mode == 'not_found':
                raise KeyError(f"Secret {secret_id} not found")
            elif self.failure_mode == 'permission_denied':
                raise PermissionError(f"Permission denied for secret {secret_id}")
            else:
                raise Exception(f"Failed to access secret {secret_id}")
        
        # Check if secret exists
        if secret_id not in self.secrets:
            raise KeyError(f"Secret {secret_id} not found")
        
        # Return secret value as string
        return self.secrets[secret_id].decode('utf-8')
    
    def access_secret_version(self, name: str) -> MockSecretVersion:
        """
        Access a specific version of a secret.
        
        Args:
            name: Resource name of the secret version
                 Format: projects/*/secrets/*/versions/*
            
        Returns:
            MockSecretVersion instance
            
        Raises:
            KeyError: If the secret doesn't exist
            Exception: If should_fail is True
        """
        # Simulate failure if requested
        if self.should_fail:
            if self.failure_mode == 'not_found':
                raise KeyError(f"Secret version {name} not found")
            elif self.failure_mode == 'permission_denied':
                raise PermissionError(f"Permission denied for secret version {name}")
            else:
                raise Exception(f"Failed to access secret version {name}")
        
        # Parse secret ID from name
        # Expected format: projects/{project}/secrets/{secret_id}/versions/{version}
        parts = name.split('/')
        if len(parts) < 4 or 'secrets' not in parts:
            raise ValueError(f"Invalid secret version name format: {name}")
        
        secret_index = parts.index('secrets')
        if secret_index + 1 >= len(parts):
            raise ValueError(f"Invalid secret version name format: {name}")
        
        secret_id = parts[secret_index + 1]
        
        # Check if secret exists
        if secret_id not in self.secrets:
            raise KeyError(f"Secret {secret_id} not found")
        
        # Return MockSecretVersion instance
        return MockSecretVersion(name, self.secrets[secret_id])
    
    def list_secrets(self, parent: str) -> List[str]:
        """
        List all secrets in the mock Secret Manager.
        
        Args:
            parent: Parent resource name
                   Format: projects/*
            
        Returns:
            List of secret IDs
            
        Raises:
            Exception: If should_fail is True
        """
        # Simulate failure if requested
        if self.should_fail:
            if self.failure_mode == 'permission_denied':
                raise PermissionError(f"Permission denied for listing secrets in {parent}")
            else:
                raise Exception(f"Failed to list secrets in {parent}")
        
        # Return list of secret IDs
        return list(self.secrets.keys())


class MockSecretManagerServiceClient:
    """Mock implementation of Google Cloud Secret Manager service client."""
    
    def __init__(self, test_secrets: Optional[Dict[str, str]] = None, 
                 should_fail: bool = False, failure_mode: str = 'not_found'):
        """
        Initialize the MockSecretManagerServiceClient.
        
        Args:
            test_secrets: Dictionary mapping secret IDs to secret values
            should_fail: Whether operations should simulate failures
            failure_mode: Type of failure to simulate
        """
        if test_secrets is None:
            test_secrets = DEFAULT_TEST_SECRETS
            
        self.client = MockSecretManagerClient(test_secrets, should_fail, failure_mode)
    
    def get_client(self) -> MockSecretManagerClient:
        """
        Get the underlying mock client.
        
        Returns:
            The mock client instance
        """
        return self.client
    
    def access_secret_version(self, request: dict) -> MockSecretVersion:
        """
        Access a specific version of a secret.
        
        Args:
            request: Dictionary containing request parameters
                    Must include 'name' field
            
        Returns:
            MockSecretVersion instance
        """
        name = request.get('name')
        return self.client.access_secret_version(name)
    
    def list_secrets(self, request: dict) -> List[str]:
        """
        List all secrets in the mock Secret Manager.
        
        Args:
            request: Dictionary containing request parameters
                    Must include 'parent' field
            
        Returns:
            List of secret IDs
        """
        parent = request.get('parent')
        return self.client.list_secrets(parent)