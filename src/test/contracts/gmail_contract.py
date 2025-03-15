"""
gmail_contract.py - Contract definition for Gmail API client interfaces

This module defines the contract that Gmail API client implementations must follow,
including interface protocols, response validation schemas, and example responses.
Both real implementations and mock versions must adhere to this contract to ensure
reliable testing of components that depend on Gmail API integration.
"""

from typing import Protocol, List, Dict, Optional, Union, Any
from email.mime.multipart import MIMEMultipart
import jsonschema
import json
import os

from ...backend.models.report import Report

# JSON schema for validating Gmail email send response
EMAIL_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "threadId": {"type": "string"},
        "labelIds": {"type": "array", "items": {"type": "string"}},
        "snippet": {"type": "string"},
        "historyId": {"type": "string"},
        "internalDate": {"type": "string"}
    },
    "required": ["id", "threadId", "labelIds"]
}

# JSON schema for validating Gmail delivery status response
EMAIL_DELIVERY_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "status": {"type": "string", "enum": ["SENT", "DELIVERED", "FAILED"]},
        "timestamp": {"type": "string"}
    },
    "required": ["id", "status"]
}

# Example response for email sending
EXAMPLE_EMAIL_RESPONSE = {
    "id": "message-id-12345",
    "threadId": "thread-id-12345",
    "labelIds": ["SENT"],
    "snippet": "Weekly Budget Update",
    "historyId": "12345",
    "internalDate": "1624982400000"
}

# Example response for delivery status
EXAMPLE_DELIVERY_RESPONSE = {
    "id": "message-id-12345",
    "status": "DELIVERED",
    "timestamp": "2023-07-23T12:01:15.123Z"
}


def validate_email_response(response: Dict[str, Any]) -> bool:
    """
    Validates a Gmail email response against the schema
    
    Args:
        response: Response from Gmail API email send operation
        
    Returns:
        True if valid, raises ValidationError if invalid
    """
    jsonschema.validate(response, EMAIL_RESPONSE_SCHEMA)
    return True


def validate_delivery_response(response: Dict[str, Any]) -> bool:
    """
    Validates a Gmail delivery status response against the schema
    
    Args:
        response: Response from Gmail API delivery status check
        
    Returns:
        True if valid, raises ValidationError if invalid
    """
    jsonschema.validate(response, EMAIL_DELIVERY_SCHEMA)
    return True


def load_fixture(fixture_path: str) -> Dict[str, Any]:
    """
    Internal helper to load test fixtures without external dependencies
    
    Args:
        fixture_path: Path to the fixture file, relative to fixtures directory
        
    Returns:
        Loaded fixture data
    """
    # When running in CI environment, return predefined examples
    if os.environ.get("TESTS_RUNNING_IN_CI"):
        if "email_response" in fixture_path:
            return EXAMPLE_EMAIL_RESPONSE
        elif "delivery_response" in fixture_path:
            return EXAMPLE_DELIVERY_RESPONSE
        else:
            return {}
    
    # In local environment, load from fixtures directory
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    full_path = os.path.join(base_dir, "test", "fixtures", fixture_path)
    
    with open(full_path, "r") as f:
        return json.load(f)


class GmailClientProtocol(Protocol):
    """Protocol defining the interface for the Gmail API client"""
    
    def __init__(self, auth_service: Optional[Any] = None, sender_email: Optional[str] = None, user_id: Optional[str] = None) -> None:
        """
        Initialize the Gmail API client
        
        Args:
            auth_service: Authentication service for Gmail API
            sender_email: Email address to send from
            user_id: Gmail user ID (typically 'me')
        """
        ...
    
    def authenticate(self) -> bool:
        """
        Authenticate with the Gmail API
        
        Returns:
            True if authentication successful, False otherwise
        """
        ...
    
    def is_authenticated(self) -> bool:
        """
        Check if the client is authenticated with Gmail API
        
        Returns:
            True if authenticated, False otherwise
        """
        ...
    
    def send_email(self, subject: str, html_content: str, recipients: List[str], 
                  attachment_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send an email via Gmail API
        
        Args:
            subject: Email subject line
            html_content: HTML content of the email body
            recipients: List of email addresses to send to
            attachment_paths: Optional list of file paths to attach
            
        Returns:
            Response with message ID and status
        """
        ...
    
    def verify_delivery(self, message_id: str) -> Dict[str, Any]:
        """
        Verify that an email was delivered successfully
        
        Args:
            message_id: ID of the sent message to check
            
        Returns:
            Delivery status information
        """
        ...
    
    def test_connectivity(self) -> bool:
        """
        Test connectivity to the Gmail API
        
        Returns:
            True if connection successful, False otherwise
        """
        ...


class EmailResponseContract:
    """Contract class for Gmail email responses"""
    
    def __init__(self):
        """Initialize the email response contract"""
        self.schema = EMAIL_RESPONSE_SCHEMA
        self.example = EXAMPLE_EMAIL_RESPONSE
    
    def validate(self, response: Dict[str, Any]) -> bool:
        """
        Validate an email response against the schema
        
        Args:
            response: Email response to validate
            
        Returns:
            True if valid, raises ValidationError if invalid
        """
        return validate_email_response(response)
    
    def get_example(self) -> Dict[str, Any]:
        """
        Get an example email response
        
        Returns:
            Example email response
        """
        return self.example


class DeliveryResponseContract:
    """Contract class for Gmail delivery status responses"""
    
    def __init__(self):
        """Initialize the delivery response contract"""
        self.schema = EMAIL_DELIVERY_SCHEMA
        self.example = EXAMPLE_DELIVERY_RESPONSE
    
    def validate(self, response: Dict[str, Any]) -> bool:
        """
        Validate a delivery response against the schema
        
        Args:
            response: Delivery response to validate
            
        Returns:
            True if valid, raises ValidationError if invalid
        """
        return validate_delivery_response(response)
    
    def get_example(self) -> Dict[str, Any]:
        """
        Get an example delivery response
        
        Returns:
            Example delivery response
        """
        return self.example