"""
Mock implementation of the Gmail API client for testing the Budget Management Application.
Simulates the behavior of the real Gmail client without making actual API calls,
allowing tests to verify email sending functionality in isolation.
"""

import os  # standard library
import json  # standard library
import re  # standard library
import uuid  # standard library
import base64  # standard library
from email.mime.multipart import MIMEMultipart  # standard library
from email.mime.text import MIMEText  # standard library
from email.mime.image import MIMEImage  # standard library

from ..utils.fixture_loader import load_fixture
from ...backend.utils.error_handlers import APIError, ValidationError

# Regular expression for email validation
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# Fixture directory for Gmail API responses
FIXTURE_DIR = os.path.join('api_responses', 'gmail')


def load_fixture(fixture_name):
    """
    Load a Gmail API response fixture
    
    Args:
        fixture_name (str): Name of the fixture file
        
    Returns:
        dict: Loaded fixture data
    """
    # Construct the path to the fixture file using FIXTURE_DIR
    fixture_path = os.path.join(FIXTURE_DIR, fixture_name)
    
    # Use the imported load_fixture function to load the fixture
    from ..utils.fixture_loader import load_fixture as load_fixture_util
    fixture_data = load_fixture_util(fixture_path)
    
    # Return the loaded fixture data
    return fixture_data


def validate_email_addresses(email_addresses):
    """
    Validates email addresses format
    
    Args:
        email_addresses (list): List of email addresses to validate
        
    Returns:
        bool: True if all email addresses are valid
        
    Raises:
        ValidationError: If any email address is invalid
    """
    if not isinstance(email_addresses, list) or not email_addresses:
        raise ValidationError("Email addresses must be a non-empty list", "email")
    
    invalid_emails = []
    for email in email_addresses:
        if not isinstance(email, str) or not EMAIL_REGEX.match(email):
            invalid_emails.append(email)
    
    if invalid_emails:
        raise ValidationError(
            f"Invalid email addresses: {', '.join(str(e) for e in invalid_emails)}",
            "email",
            validation_errors={"invalid_emails": invalid_emails}
        )
    
    return True


def create_message(sender, recipients, subject, html_content):
    """
    Creates a mock email message for testing
    
    Args:
        sender (str): Sender email address
        recipients (list): List of recipient email addresses
        subject (str): Email subject line
        html_content (str): HTML content of the email
        
    Returns:
        dict: Mock message dictionary for Gmail API
    """
    # Validate inputs
    if not sender or not isinstance(sender, str):
        raise ValidationError("Sender email is required", "email")
    
    if not EMAIL_REGEX.match(sender):
        raise ValidationError(f"Invalid sender email address: {sender}", "email")
    
    validate_email_addresses(recipients)
    
    if not subject or not isinstance(subject, str):
        raise ValidationError("Subject is required", "email")
    
    if not html_content or not isinstance(html_content, str):
        raise ValidationError("HTML content is required", "email")
    
    # Create the MIMEMultipart message
    message = MIMEMultipart('related')
    message['From'] = sender
    message['To'] = ', '.join(recipients)
    message['Subject'] = subject
    
    # Attach HTML content
    html_part = MIMEText(html_content, 'html')
    message.attach(html_part)
    
    # Encode the message
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    # Return a dictionary similar to Gmail API's response
    return {'raw': encoded_message}


def add_attachment(message, file_path, content_id=None):
    """
    Simulates adding an attachment to an email message
    
    Args:
        message (MIMEMultipart): The message to add the attachment to
        file_path (str): Path to the attachment file
        content_id (str): Content ID for inline images
        
    Returns:
        bool: True if attachment was added successfully
    """
    try:
        # Validate that file_path exists
        if not os.path.exists(file_path):
            raise ValidationError(f"Attachment file not found: {file_path}", "attachment")
        
        # Determine MIME type based on file extension
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # If content_id is provided, create MIMEImage for inline image
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
            with open(file_path, 'rb') as img_file:
                img_data = img_file.read()
            
            image = MIMEImage(img_data)
            
            # Set Content-Disposition header appropriately
            if content_id:
                image.add_header('Content-ID', f'<{content_id}>')
                image.add_header('Content-Disposition', 'inline')
            else:
                image.add_header('Content-Disposition', 'attachment', filename=os.path.basename(file_path))
            
            # Add the attachment to the message
            message.attach(image)
            return True
        
        # Handle file errors and log them
        return False
    except Exception as e:
        return False


class MockGmailClient:
    """
    Mock implementation of the Gmail client for testing
    """
    
    def __init__(self, auth_service=None, sender_email=None, user_id=None):
        """
        Initialize the mock Gmail client
        
        Args:
            auth_service: Optional mock authentication service
            sender_email (str): Email address to send from
            user_id (str): Gmail user ID
        """
        # Initialize authenticated to False
        self.authenticated = False
        
        # Set sender_email to provided value or default to 'njdifiore@gmail.com'
        self.sender_email = sender_email or 'njdifiore@gmail.com'
        
        # Set user_id to provided value or default to 'me'
        self.user_id = user_id or 'me'
        
        # Initialize sent_emails as empty list
        self.sent_emails = []
        
        # Initialize message_statuses as empty dictionary
        self.message_statuses = {}
        
        # Load error response fixtures
        self.error_responses = {
            'authentication_error': load_fixture('authentication_error'),
            'server_error': load_fixture('server_error'),
            'invalid_argument': load_fixture('invalid_argument')
        }
        
        # Initialize failure flags to False
        self.should_fail_authentication = False
        self.should_fail_sending = False
        self.should_fail_verification = False
        
        # Initialize retry_count to 0
        self.retry_count = 0
        
        # Log initialization of mock Gmail client
    
    def authenticate(self):
        """
        Simulates authentication with Gmail API
        
        Returns:
            bool: True if authentication successful
        """
        # Increment retry_count
        self.retry_count += 1
        
        # If should_fail_authentication is True, raise APIError with authentication_error fixture
        if self.should_fail_authentication:
            raise APIError(
                "Authentication failed",
                "Gmail",
                "authenticate",
                status_code=401,
                response_text=json.dumps(self.error_responses['authentication_error'])
            )
        
        # Set authenticated to True
        self.authenticated = True
        
        # Return True
        return True
    
    def send_email(self, subject, html_content, recipients, attachment_paths=None):
        """
        Simulates sending an email via Gmail API
        
        Args:
            subject (str): Email subject line
            html_content (str): HTML content of the email
            recipients (list): List of recipient email addresses
            attachment_paths (list): List of paths to attachment files
            
        Returns:
            dict: Response with message ID and status
        """
        # Validate recipients using validate_email_addresses
        validate_email_addresses(recipients)
        
        # Ensure client is authenticated
        if not self.authenticated:
            raise APIError(
                "Not authenticated",
                "Gmail",
                "send_email",
                status_code=401,
                response_text="Client not authenticated"
            )
        
        # If should_fail_sending is True, raise APIError with server_error fixture
        if self.should_fail_sending:
            raise APIError(
                "Failed to send email",
                "Gmail",
                "send_email",
                status_code=500,
                response_text=json.dumps(self.error_responses['server_error'])
            )
        
        # Create message using create_message function
        message = create_message(self.sender_email, recipients, subject, html_content)
        
        # If attachment_paths provided, add each attachment to the message
        if attachment_paths:
            for path in attachment_paths:
                add_attachment(message, path)
        
        # Generate a unique message ID using uuid
        message_id = f"message-{uuid.uuid4()}"
        
        # Create a record of the sent email with all details
        email_record = {
            'message_id': message_id,
            'subject': subject,
            'html_content': html_content,
            'recipients': recipients,
            'sender': self.sender_email,
            'timestamp': str(uuid.uuid4()),  # Using uuid as timestamp for testing
            'has_attachments': bool(attachment_paths)
        }
        
        # Add the email to sent_emails list
        self.sent_emails.append(email_record)
        
        # Set message status to 'sent' in message_statuses dictionary
        self.message_statuses[message_id] = 'sent'
        
        # Return success response with message ID
        return {
            'id': message_id,
            'status': 'sent'
        }
    
    def verify_delivery(self, message_id):
        """
        Simulates verifying email delivery status
        
        Args:
            message_id (str): ID of the message to check
            
        Returns:
            dict: Delivery status information
        """
        # Validate message_id is not empty
        if not message_id:
            raise ValidationError("Message ID is required", "message_id")
        
        # Ensure client is authenticated
        if not self.authenticated:
            raise APIError(
                "Not authenticated",
                "Gmail",
                "verify_delivery",
                status_code=401,
                response_text="Client not authenticated"
            )
        
        # If should_fail_verification is True, raise APIError with server_error fixture
        if self.should_fail_verification:
            raise APIError(
                "Failed to verify email delivery",
                "Gmail",
                "verify_delivery",
                status_code=500,
                response_text=json.dumps(self.error_responses['server_error'])
            )
        
        # Check if message_id exists in message_statuses
        if message_id in self.message_statuses:
            # If found, return success response with delivery status
            return {
                'id': message_id,
                'status': self.message_statuses[message_id]
            }
        
        # If not found, raise APIError with invalid_argument fixture
        raise APIError(
            f"Message not found: {message_id}",
            "Gmail",
            "verify_delivery",
            status_code=400,
            response_text=json.dumps(self.error_responses['invalid_argument'])
        )
    
    def is_authenticated(self):
        """
        Checks if the client is authenticated
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        # Return the value of authenticated property
        return self.authenticated
    
    def set_should_fail_authentication(self, should_fail):
        """
        Sets whether authentication should fail
        
        Args:
            should_fail (bool): Whether authentication should fail
            
        Returns:
            None: None
        """
        # Set should_fail_authentication to the provided value
        self.should_fail_authentication = should_fail
    
    def set_should_fail_sending(self, should_fail):
        """
        Sets whether email sending should fail
        
        Args:
            should_fail (bool): Whether email sending should fail
            
        Returns:
            None: None
        """
        # Set should_fail_sending to the provided value
        self.should_fail_sending = should_fail
    
    def set_should_fail_verification(self, should_fail):
        """
        Sets whether delivery verification should fail
        
        Args:
            should_fail (bool): Whether delivery verification should fail
            
        Returns:
            None: None
        """
        # Set should_fail_verification to the provided value
        self.should_fail_verification = should_fail
    
    def reset(self):
        """
        Resets the mock client state
        
        Returns:
            None: None
        """
        # Set authenticated to False
        self.authenticated = False
        
        # Clear sent_emails list
        self.sent_emails = []
        
        # Clear message_statuses dictionary
        self.message_statuses = {}
        
        # Reset all failure flags to False
        self.should_fail_authentication = False
        self.should_fail_sending = False
        self.should_fail_verification = False
        
        # Reset retry_count to 0
        self.retry_count = 0
    
    def get_sent_email_count(self):
        """
        Returns the number of sent emails
        
        Returns:
            int: Number of sent emails
        """
        # Return the length of sent_emails list
        return len(self.sent_emails)
    
    def get_last_sent_email(self):
        """
        Returns the last sent email
        
        Returns:
            dict: Last sent email details
        """
        # If sent_emails is empty, return None
        if not self.sent_emails:
            return None
        
        # Otherwise, return the last item in sent_emails list
        return self.sent_emails[-1]
    
    def get_sent_emails(self):
        """
        Returns all sent emails
        
        Returns:
            list: List of all sent emails
        """
        # Return the sent_emails list
        return self.sent_emails
    
    def get_retry_count(self):
        """
        Returns the number of authentication retries
        
        Returns:
            int: Number of retries
        """
        # Return the retry_count value
        return self.retry_count