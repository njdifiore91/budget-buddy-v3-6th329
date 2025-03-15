"""
gmail_client.py - Client for interacting with the Gmail API

This module provides functionality for sending emails via Gmail API, including
authentication, email creation with HTML content and attachments, and delivery verification.
"""

import base64  # standard library
import os  # standard library
import mimetypes  # standard library
import re  # standard library
from email.mime.text import MIMEText  # standard library
from email.mime.multipart import MIMEMultipart  # standard library
from email.mime.image import MIMEImage  # standard library
from email.mime.application import MIMEApplication  # standard library
from typing import List, Dict, Optional, Union, Any  # standard library

from googleapiclient.discovery import build  # google-api-python-client 2.100.0+
from googleapiclient.errors import HttpError  # google-api-python-client 2.100.0+

from ..config.settings import API_SETTINGS, APP_SETTINGS
from ..config.logging_config import get_logger
from ..services.authentication_service import AuthenticationService
from ..utils.error_handlers import (
    retry_with_backoff, handle_api_error, APIError, ValidationError
)

# Set up logger
logger = get_logger('gmail_client')


def create_message(sender: str, recipients: List[str], subject: str, html_content: str) -> Dict:
    """
    Creates an email message suitable for the Gmail API.
    
    Args:
        sender: Email address of the sender
        recipients: List of recipient email addresses
        subject: Email subject line
        html_content: HTML content of the email
        
    Returns:
        Dictionary with the raw message for Gmail API
    """
    # Validate inputs
    if not sender:
        raise ValidationError("Sender email address is required", "email")
    
    if not recipients or not isinstance(recipients, list):
        raise ValidationError("Recipients must be a non-empty list", "email")
    
    if not subject:
        raise ValidationError("Email subject is required", "email")
    
    if not html_content:
        raise ValidationError("Email content is required", "email")
    
    # Create multipart message
    message = MIMEMultipart('related')
    message['From'] = sender
    message['To'] = ', '.join(recipients)
    message['Subject'] = subject
    
    # Attach HTML content
    html_part = MIMEText(html_content, 'html')
    message.attach(html_part)
    
    # Encode the message for Gmail API
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    logger.debug(
        "Created email message",
        context={
            "subject": subject,
            "recipients": recipients,
            "sender": sender
        }
    )
    
    return {'raw': encoded_message}


def add_attachment(message: MIMEMultipart, file_path: str, content_id: Optional[str] = None) -> bool:
    """
    Adds an attachment to an email message.
    
    Args:
        message: The email message to add the attachment to
        file_path: Path to the file to attach
        content_id: Optional Content-ID for inline images
        
    Returns:
        True if attachment was added successfully, False otherwise
    """
    try:
        # Validate file path
        if not os.path.isfile(file_path):
            logger.warning(f"Attachment file not found: {file_path}")
            return False
        
        # Determine content type
        content_type, _ = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = 'application/octet-stream'
        
        # Read file
        with open(file_path, 'rb') as file:
            file_data = file.read()
        
        # Determine if this is an image or other file type
        main_type, sub_type = content_type.split('/', 1)
        
        if main_type == 'image' and content_id:
            # Create image attachment with content-id for inline reference
            attachment = MIMEImage(file_data, _subtype=sub_type)
            attachment.add_header('Content-ID', f'<{content_id}>')
            attachment.add_header('Content-Disposition', 'inline', filename=os.path.basename(file_path))
        else:
            # Create regular attachment
            attachment = MIMEApplication(file_data, _subtype=sub_type)
            attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(file_path))
        
        # Add attachment to message
        message.attach(attachment)
        
        logger.debug(
            f"Added {'inline' if content_id else 'attachment'} to email",
            context={"file": os.path.basename(file_path), "content_type": content_type}
        )
        
        return True
        
    except Exception as e:
        logger.error(
            f"Failed to add attachment: {str(e)}",
            context={"file_path": file_path, "error": str(e)}
        )
        return False


def validate_email_addresses(email_addresses: List[str]) -> bool:
    """
    Validates email addresses format.
    
    Args:
        email_addresses: List of email addresses to validate
        
    Returns:
        True if all email addresses are valid
        
    Raises:
        ValidationError: If any email address is invalid
    """
    if not email_addresses or not isinstance(email_addresses, list):
        raise ValidationError("Email addresses must be a non-empty list", "email")
    
    # Simple regex for email validation
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    invalid_emails = []
    for email in email_addresses:
        if not email_pattern.match(email):
            invalid_emails.append(email)
    
    if invalid_emails:
        raise ValidationError(
            f"Invalid email address format: {', '.join(invalid_emails)}",
            "email",
            {"invalid_emails": invalid_emails}
        )
    
    return True


class GmailClient:
    """
    Client for interacting with Gmail API to send emails.
    """
    
    def __init__(
        self,
        auth_service: AuthenticationService,
        sender_email: Optional[str] = None,
        user_id: str = 'me'
    ):
        """
        Initialize the Gmail client with authentication.
        
        Args:
            auth_service: Authentication service for Gmail API
            sender_email: Email address to send from (defaults to APP_SETTINGS.EMAIL_SENDER)
            user_id: Gmail user ID ('me' refers to the authenticated user)
        """
        self.auth_service = auth_service
        self.sender_email = sender_email or APP_SETTINGS.get('EMAIL_SENDER')
        self.user_id = user_id
        self.service = None
        
        logger.info(
            "Gmail client initialized",
            context={"sender": self.sender_email, "user_id": self.user_id}
        )
    
    @retry_with_backoff(exceptions=(APIError, HttpError), max_retries=3)
    def authenticate(self) -> bool:
        """
        Authenticates with Gmail API.
        
        Returns:
            True if authentication is successful
            
        Raises:
            APIError: If authentication fails
        """
        try:
            logger.info("Authenticating with Gmail API")
            
            # Get Gmail credentials from authentication service
            credentials = self.auth_service.authenticate_gmail()
            
            # Build the Gmail API service
            self.service = build(
                'gmail',
                API_SETTINGS['GMAIL']['API_VERSION'],
                credentials=credentials
            )
            
            logger.info("Successfully authenticated with Gmail API")
            return True
            
        except Exception as e:
            logger.error(
                f"Gmail API authentication failed: {str(e)}",
                context={"error": str(e)}
            )
            self.service = None
            raise APIError(
                f"Gmail API authentication failed: {str(e)}",
                "Gmail API",
                "authenticate"
            )
    
    @retry_with_backoff(exceptions=(APIError, HttpError), max_retries=3)
    def send_email(
        self,
        subject: str,
        html_content: str,
        recipients: List[str],
        attachment_paths: Optional[List[str]] = None
    ) -> Dict:
        """
        Sends an email via Gmail API.
        
        Args:
            subject: Email subject line
            html_content: HTML content of the email
            recipients: List of recipient email addresses
            attachment_paths: Optional list of file paths to attach
            
        Returns:
            Dictionary with message ID and status
            
        Raises:
            ValidationError: If email validation fails
            APIError: If sending fails
        """
        try:
            # Validate email addresses
            validate_email_addresses(recipients)
            
            # Ensure authenticated
            if not self.is_authenticated():
                self.authenticate()
            
            # Create message
            message = create_message(self.sender_email, recipients, subject, html_content)
            message_obj = MIMEMultipart('related')
            message_obj['From'] = self.sender_email
            message_obj['To'] = ', '.join(recipients)
            message_obj['Subject'] = subject
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            message_obj.attach(html_part)
            
            # Add attachments if provided
            if attachment_paths:
                for i, file_path in enumerate(attachment_paths):
                    # Use the filename as content ID for inline images
                    content_id = f"image_{i}" if file_path.lower().endswith(('png', 'jpg', 'jpeg', 'gif')) else None
                    add_attachment(message_obj, file_path, content_id)
            
            # Encode the message for Gmail API
            encoded_message = base64.urlsafe_b64encode(message_obj.as_bytes()).decode()
            message = {'raw': encoded_message}
            
            # Send the message
            send_response = self.service.users().messages().send(
                userId=self.user_id,
                body=message
            ).execute()
            
            message_id = send_response.get('id', '')
            
            logger.info(
                f"Email sent successfully. Subject: {subject}",
                context={
                    "message_id": message_id,
                    "recipients": recipients,
                    "subject": subject
                }
            )
            
            return {
                "status": "success",
                "message_id": message_id,
                "recipients": recipients
            }
            
        except ValidationError as e:
            # Re-raise validation errors
            raise
            
        except HttpError as e:
            error_details = handle_api_error(
                e,
                "Gmail API",
                "send_email",
                {"subject": subject, "recipients": recipients}
            )
            raise APIError(
                f"Failed to send email: {str(e)}",
                "Gmail API",
                "send_email",
                getattr(e, 'status_code', None),
                getattr(e, 'content', None),
                error_details
            )
            
        except Exception as e:
            logger.error(
                f"Error sending email: {str(e)}",
                context={
                    "subject": subject,
                    "recipients": recipients,
                    "error": str(e)
                }
            )
            raise APIError(
                f"Error sending email: {str(e)}",
                "Gmail API",
                "send_email",
                context={"subject": subject, "recipients": recipients}
            )
    
    @retry_with_backoff(exceptions=(APIError, HttpError), max_retries=2)
    def verify_delivery(self, message_id: str) -> Dict:
        """
        Verifies that an email was delivered successfully.
        
        Args:
            message_id: ID of the message to verify
            
        Returns:
            Dictionary with delivery status information
            
        Raises:
            APIError: If verification fails
        """
        try:
            if not message_id:
                raise ValidationError("Message ID is required for delivery verification", "email")
            
            # Ensure authenticated
            if not self.is_authenticated():
                self.authenticate()
            
            # Get message details
            message = self.service.users().messages().get(
                userId=self.user_id,
                id=message_id
            ).execute()
            
            # Check label IDs for status
            labels = message.get('labelIds', [])
            
            # Determine delivery status based on labels
            is_sent = 'SENT' in labels
            is_delivered = not ('UNDELIVERED' in labels or 'BOUNCED' in labels)
            
            delivery_status = {
                "message_id": message_id,
                "is_sent": is_sent,
                "is_delivered": is_delivered,
                "labels": labels,
                "status": "delivered" if is_delivered else "failed"
            }
            
            logger.info(
                f"Email delivery verification: {delivery_status['status']}",
                context=delivery_status
            )
            
            return delivery_status
            
        except HttpError as e:
            error_details = handle_api_error(
                e,
                "Gmail API",
                "verify_delivery",
                {"message_id": message_id}
            )
            raise APIError(
                f"Failed to verify email delivery: {str(e)}",
                "Gmail API",
                "verify_delivery",
                getattr(e, 'status_code', None),
                getattr(e, 'content', None),
                error_details
            )
            
        except Exception as e:
            logger.error(
                f"Error verifying email delivery: {str(e)}",
                context={"message_id": message_id, "error": str(e)}
            )
            raise APIError(
                f"Error verifying email delivery: {str(e)}",
                "Gmail API",
                "verify_delivery",
                context={"message_id": message_id}
            )
    
    def is_authenticated(self) -> bool:
        """
        Checks if the client is authenticated with Gmail API.
        
        Returns:
            True if authenticated, False otherwise
        """
        # Check if service exists
        if self.service is None:
            try:
                return self.authenticate()
            except:
                return False
        
        return True