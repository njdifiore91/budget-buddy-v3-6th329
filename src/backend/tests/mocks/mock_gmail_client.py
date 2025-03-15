"""
mock_gmail_client.py - Mock implementation of the Gmail API client for testing purposes

This module simulates the behavior of the real GmailClient without making actual API calls,
allowing for controlled testing of email delivery functionality in the Budget Management Application.
"""

import os  # standard library
import json  # standard library
from typing import List, Dict, Optional, Any  # standard library
from email.mime.multipart import MIMEMultipart  # standard library

from ...api_clients.gmail_client import GmailClient, create_message, add_attachment, validate_email_addresses

# Mock constants for testing
MOCK_AUTH_TOKEN = 'mock-gmail-token'
DEFAULT_SENDER = 'njdifiore@gmail.com'
DEFAULT_RECIPIENTS = ['njdifiore@gmail.com', 'nick@blitzy.com']
DEFAULT_MESSAGE_ID = 'message-id-12345abcdef'


def load_email_confirmation(message_id: str) -> Dict:
    """
    Loads mock email confirmation response from fixture files
    
    Args:
        message_id: Message ID for the confirmation
        
    Returns:
        Mock email confirmation response
    """
    return {
        'id': message_id,
        'threadId': f'thread-{message_id}',
        'labelIds': ['SENT'],
        'status': 'success',
        'statusDescription': 'Email sent successfully'
    }


def load_email_error_response(error_type: str) -> Dict:
    """
    Loads mock email error response from fixture files
    
    Args:
        error_type: Type of error to simulate
        
    Returns:
        Mock email error response
    """
    # Define different error responses based on error type
    error_responses = {
        'authentication': {
            'error': {
                'code': 401,
                'message': 'Invalid credentials',
                'status': 'UNAUTHENTICATED'
            }
        },
        'permission': {
            'error': {
                'code': 403,
                'message': 'Insufficient permission',
                'status': 'PERMISSION_DENIED'
            }
        },
        'rate_limit': {
            'error': {
                'code': 429,
                'message': 'Rate limit exceeded',
                'status': 'RESOURCE_EXHAUSTED'
            }
        },
        'server_error': {
            'error': {
                'code': 500,
                'message': 'Internal server error',
                'status': 'INTERNAL'
            }
        },
        'not_found': {
            'error': {
                'code': 404,
                'message': 'Message not found',
                'status': 'NOT_FOUND'
            }
        }
    }
    
    # Return the requested error response or a generic one if type not found
    return error_responses.get(error_type, {
        'error': {
            'code': 400,
            'message': f'Unknown error: {error_type}',
            'status': 'UNKNOWN'
        }
    })


class MockAuthenticationService:
    """
    Mock authentication service for testing Gmail client
    """
    
    def __init__(self, auth_success: bool = True):
        """
        Initialize the mock authentication service
        
        Args:
            auth_success: Whether authentication should succeed
        """
        self.auth_success = auth_success
        self.token = MOCK_AUTH_TOKEN
    
    def authenticate_gmail(self):
        """
        Mock authentication with Gmail API
        
        Returns:
            Mock authentication response
        
        Raises:
            AuthenticationError: If auth_success is False
        """
        if self.auth_success:
            return {'token': self.token}
        else:
            raise Exception("Authentication failed")
    
    def get_token(self, service_name: str):
        """
        Get mock authentication token
        
        Args:
            service_name: Name of the service
            
        Returns:
            Mock authentication token or None
        """
        if service_name == 'gmail' and self.auth_success:
            return self.token
        return None
    
    def refresh_token(self, service_name: str):
        """
        Mock token refresh
        
        Args:
            service_name: Name of the service
            
        Returns:
            Success status of refresh
        """
        return self.auth_success


class MockGmailClient:
    """
    Mock implementation of the Gmail API client for testing
    """
    
    def __init__(
        self,
        auth_service: Optional[MockAuthenticationService] = None,
        auth_success: bool = True,
        api_error: bool = False,
        error_type: Optional[str] = None,
        sender_email: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Initialize the mock Gmail client
        
        Args:
            auth_service: Optional mock authentication service
            auth_success: Whether authentication should succeed
            api_error: Whether to simulate API errors
            error_type: Type of error to simulate
            sender_email: Email address to send from
            user_id: Gmail user ID
        """
        self.auth_success = auth_success
        self.api_error = api_error
        self.error_type = error_type
        self.auth_service = auth_service or MockAuthenticationService(auth_success)
        self.sender_email = sender_email or DEFAULT_SENDER
        self.user_id = user_id or 'me'
        self.service = None
        self.sent_emails = []
        self.sent_email_count = 0
        self.delivery_statuses = {}
    
    def authenticate(self) -> bool:
        """
        Mock authentication with Gmail API
        
        Returns:
            True if authentication successful, False otherwise
        """
        if self.api_error and self.error_type == 'authentication':
            return False
        
        if self.auth_success:
            self.service = {}  # Just a placeholder, we don't need to simulate the full API structure
        
        return self.auth_success
    
    def is_authenticated(self) -> bool:
        """
        Check if the client is authenticated
        
        Returns:
            True if authenticated, False otherwise
        """
        return self.service is not None
    
    def send_email(
        self,
        subject: str,
        html_content: str,
        recipients: List[str],
        attachment_paths: Optional[List[str]] = None
    ) -> Dict:
        """
        Mock sending an email via Gmail API
        
        Args:
            subject: Email subject line
            html_content: HTML content of the email
            recipients: List of recipient email addresses
            attachment_paths: Optional list of file paths to attach
            
        Returns:
            Mock API response with message ID and status
        """
        # Check if we should simulate an API error
        if self.api_error:
            return load_email_error_response(self.error_type or 'server_error')
        
        # Validate recipients
        validate_email_addresses(recipients)
        
        # Create a message dictionary
        message = {
            'subject': subject,
            'html_content': html_content,
            'recipients': recipients,
            'sender': self.sender_email,
            'attachments': attachment_paths or []
        }
        
        # Add to sent emails
        self.sent_emails.append(message)
        self.sent_email_count += 1
        
        # Generate a message ID
        message_id = DEFAULT_MESSAGE_ID
        
        # Set delivery status
        self.delivery_statuses[message_id] = 'SENT'
        
        # Return success response
        return {
            'status': 'success',
            'message_id': message_id,
            'recipients': recipients
        }
    
    def verify_delivery(self, message_id: str) -> Dict:
        """
        Mock verification of email delivery status
        
        Args:
            message_id: ID of the message to verify
            
        Returns:
            Mock delivery status information
        """
        # Check if we should simulate an API error
        if self.api_error:
            return load_email_error_response(self.error_type or 'server_error')
        
        # Check if message exists
        if message_id in self.delivery_statuses:
            return {
                'message_id': message_id,
                'is_sent': True,
                'is_delivered': True,
                'labels': ['SENT'],
                'status': 'delivered'
            }
        
        # Return error for unknown message ID
        return load_email_error_response('not_found')
    
    def set_api_error(self, error_state: bool, error_type: Optional[str] = None) -> None:
        """
        Set API error flag and type for testing error scenarios
        
        Args:
            error_state: Whether to simulate API errors
            error_type: Type of error to simulate
        """
        self.api_error = error_state
        if error_type:
            self.error_type = error_type
    
    def get_sent_emails(self) -> List[Dict]:
        """
        Get list of emails sent through this mock client
        
        Returns:
            List of sent email dictionaries
        """
        return self.sent_emails
    
    def clear_sent_emails(self) -> None:
        """
        Clear the list of sent emails
        """
        self.sent_emails = []
        self.sent_email_count = 0
    
    def set_delivery_status(self, message_id: str, status: str) -> None:
        """
        Set delivery status for a specific message ID
        
        Args:
            message_id: ID of the message
            status: Delivery status to set
        """
        self.delivery_statuses[message_id] = status
    
    def test_connectivity(self) -> bool:
        """
        Mock test of connectivity to Gmail API
        
        Returns:
            True if connection successful, False otherwise
        """
        return not self.api_error