import pytest
import os
import tempfile
from unittest.mock import MagicMock, patch
from email.mime.multipart import MIMEMultipart

from ...api_clients.gmail_client import (
    GmailClient, create_message, add_attachment, validate_email_addresses
)
from ..mocks.mock_gmail_client import MockGmailClient, MockAuthenticationService
from ..fixtures.api_responses import load_gmail_confirmation_response, load_gmail_error_response
from ...utils.error_handlers import APIError, ValidationError

# Test constants
TEST_SENDER = 'njdifiore@gmail.com'
TEST_RECIPIENTS = ['njdifiore@gmail.com', 'nick@blitzy.com']
TEST_SUBJECT = 'Budget Update: $45.67 under budget this week'
TEST_HTML_CONTENT = '<html><body><h1>Budget Report</h1><p>You are under budget this week!</p></body></html>'

def create_temp_image_file():
    """
    Creates a temporary image file for testing attachments
    
    Returns:
        str: Path to the created temporary file
    """
    # Create a temporary file with .png extension
    fd, path = tempfile.mkstemp(suffix='.png')
    
    # Write some dummy binary data to the file
    with os.fdopen(fd, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)  # Simple PNG header and some data
    
    return path

class TestGmailClient:
    """Test suite for the GmailClient class"""
    
    def test_init(self):
        """Test GmailClient initialization"""
        # Create a mock authentication service
        auth_service = MockAuthenticationService()
        
        # Initialize GmailClient with the mock auth service
        client = GmailClient(auth_service, sender_email=TEST_SENDER)
        
        # Assert that the client's auth_service attribute is set correctly
        assert client.auth_service == auth_service
        
        # Assert that the client's sender_email is set correctly
        assert client.sender_email == TEST_SENDER
        
        # Assert that the client's user_id is set to default 'me'
        assert client.user_id == 'me'
    
    @patch('googleapiclient.discovery.build')
    def test_authenticate_success(self, mock_build):
        """Test successful authentication with Gmail API"""
        # Create a mock authentication service that returns valid credentials
        auth_service = MockAuthenticationService(auth_success=True)
        
        # Create a mock Gmail API service
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Initialize GmailClient with the mock auth service
        client = GmailClient(auth_service)
        
        # Call authenticate method
        result = client.authenticate()
        
        # Assert that the method returns True
        assert result is True
        
        # Assert that the service attribute is set to the mock service
        assert client.service == mock_service
        
        # Assert that googleapiclient.discovery.build was called with correct parameters
        mock_build.assert_called_once()
    
    @patch('googleapiclient.discovery.build')
    def test_authenticate_failure(self, mock_build):
        """Test authentication failure with Gmail API"""
        # Create a mock authentication service that raises an exception
        auth_service = MagicMock()
        auth_service.authenticate_gmail.side_effect = Exception("Authentication failed")
        
        # Initialize GmailClient with the mock auth service
        client = GmailClient(auth_service)
        
        # Call authenticate method and expect an APIError
        with pytest.raises(APIError):
            client.authenticate()
        
        # Assert that the service attribute is None
        assert client.service is None
        
        # Assert that googleapiclient.discovery.build was not called
        mock_build.assert_not_called()
    
    def test_is_authenticated(self):
        """Test is_authenticated method"""
        # Create a mock authentication service
        auth_service = MockAuthenticationService()
        
        # Initialize GmailClient with the mock auth service
        client = GmailClient(auth_service)
        
        # Set client.service to None
        client.service = None
        
        # Assert that is_authenticated returns False
        assert client.is_authenticated() is False
        
        # Set client.service to a mock object
        client.service = MagicMock()
        
        # Assert that is_authenticated returns True
        assert client.is_authenticated() is True
    
    def test_send_email_success(self):
        """Test successful email sending"""
        # Create a mock Gmail client
        mock_client = MockGmailClient()
        
        # Call send_email with test subject, content, and recipients
        response = mock_client.send_email(
            TEST_SUBJECT,
            TEST_HTML_CONTENT,
            TEST_RECIPIENTS
        )
        
        # Assert that the method returns a success response with message_id
        assert response['status'] == 'success'
        assert 'message_id' in response
        
        # Assert that the email was sent with correct parameters
        assert mock_client.sent_email_count == 1
        sent_email = mock_client.get_sent_emails()[0]
        
        # Verify the content of the sent email
        assert sent_email['subject'] == TEST_SUBJECT
        assert sent_email['html_content'] == TEST_HTML_CONTENT
        assert sent_email['recipients'] == TEST_RECIPIENTS
        assert sent_email['sender'] == mock_client.sender_email
    
    def test_send_email_with_attachments(self):
        """Test sending email with attachments"""
        # Create a temporary image file
        temp_file = create_temp_image_file()
        
        try:
            # Create a mock Gmail client
            mock_client = MockGmailClient()
            
            # Call send_email with test parameters and attachment path
            response = mock_client.send_email(
                TEST_SUBJECT,
                TEST_HTML_CONTENT,
                TEST_RECIPIENTS,
                attachment_paths=[temp_file]
            )
            
            # Assert that the method returns a success response
            assert response['status'] == 'success'
            
            # Assert that the email was sent with the attachment
            assert mock_client.sent_email_count == 1
            sent_email = mock_client.get_sent_emails()[0]
            
            # Verify the content of the sent email includes the attachment
            assert temp_file in sent_email['attachments']
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_send_email_authentication_failure(self):
        """Test email sending with authentication failure"""
        # Create a mock Gmail client with authentication failure
        mock_client = MockGmailClient(auth_success=False)
        
        # Set api_error to simulate authentication failure
        mock_client.set_api_error(True, 'authentication')
        
        # Call send_email with test parameters
        with pytest.raises(APIError):
            mock_client.send_email(
                TEST_SUBJECT,
                TEST_HTML_CONTENT,
                TEST_RECIPIENTS
            )
        
        # Assert that no email was sent
        assert mock_client.sent_email_count == 0
    
    def test_send_email_api_error(self):
        """Test email sending with API error"""
        # Create a mock Gmail client
        mock_client = MockGmailClient()
        
        # Configure the mock to simulate an API error
        mock_client.set_api_error(True, 'server_error')
        
        # Call send_email with test parameters
        with pytest.raises(APIError):
            mock_client.send_email(
                TEST_SUBJECT,
                TEST_HTML_CONTENT,
                TEST_RECIPIENTS
            )
        
        # Assert that the error contains appropriate details
        try:
            mock_client.send_email(
                TEST_SUBJECT,
                TEST_HTML_CONTENT,
                TEST_RECIPIENTS
            )
        except APIError as e:
            assert 'server_error' in str(e).lower() or 'internal server error' in str(e).lower()
    
    def test_send_email_invalid_recipients(self):
        """Test email sending with invalid recipients"""
        # Create a mock Gmail client
        mock_client = MockGmailClient()
        
        # Call send_email with invalid email addresses
        with pytest.raises(ValidationError):
            mock_client.send_email(
                TEST_SUBJECT,
                TEST_HTML_CONTENT,
                ['not-an-email', 'also@not@an.email']
            )
        
        # Assert that no email was sent
        assert mock_client.sent_email_count == 0
    
    def test_verify_delivery_success(self):
        """Test successful delivery verification"""
        # Create a mock Gmail client
        mock_client = MockGmailClient()
        
        # Configure mock to return a successful delivery status
        message_id = 'test-message-id'
        mock_client.set_delivery_status(message_id, 'SENT')
        
        # Call verify_delivery with a message ID
        response = mock_client.verify_delivery(message_id)
        
        # Assert that the method returns a success response
        assert response['status'] == 'delivered'
        
        # Assert that the response contains delivery status information
        assert response['message_id'] == message_id
        assert response['is_sent'] is True
        assert response['is_delivered'] is True
    
    def test_verify_delivery_failure(self):
        """Test delivery verification failure"""
        # Create a mock Gmail client
        mock_client = MockGmailClient()
        
        # Configure mock to simulate an API error
        mock_client.set_api_error(True, 'not_found')
        
        # Call verify_delivery with a message ID
        with pytest.raises(APIError):
            mock_client.verify_delivery('non-existent-message-id')
        
        # Assert that the error contains appropriate details
        try:
            mock_client.verify_delivery('non-existent-message-id')
        except APIError as e:
            assert 'not_found' in str(e).lower() or 'message not found' in str(e).lower()

class TestEmailFunctions:
    """Test suite for standalone email-related functions"""
    
    def test_create_message(self):
        """Test create_message function"""
        # Call create_message with test sender, recipients, subject, and content
        message = create_message(TEST_SENDER, TEST_RECIPIENTS, TEST_SUBJECT, TEST_HTML_CONTENT)
        
        # Assert that the returned message is a dictionary
        assert isinstance(message, dict)
        
        # Assert that the message contains a 'raw' key with base64 encoded content
        assert 'raw' in message
        
        # Decode the raw content and verify it contains the expected headers and content
        raw_content = message['raw']
        assert isinstance(raw_content, str)
        assert len(raw_content) > 0
    
    def test_add_attachment(self):
        """Test add_attachment function"""
        # Create a temporary image file
        temp_file = create_temp_image_file()
        
        try:
            # Create a MIMEMultipart message
            message = MIMEMultipart()
            
            # Call add_attachment with the message and file path
            result = add_attachment(message, temp_file)
            
            # Assert that the function returns True
            assert result is True
            
            # Assert that the message now contains the attachment
            assert len(message.get_payload()) > 0
            
            # Verify the attachment has the correct Content-Type
            attachment = message.get_payload()[-1]
            assert attachment.get_content_type().startswith('image/')
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_add_attachment_with_content_id(self):
        """Test add_attachment function with content ID for inline images"""
        # Create a temporary image file
        temp_file = create_temp_image_file()
        
        try:
            # Create a MIMEMultipart message
            message = MIMEMultipart()
            
            # Call add_attachment with the message, file path, and content ID
            result = add_attachment(message, temp_file, content_id='test-image')
            
            # Assert that the function returns True
            assert result is True
            
            # Assert that the message contains the attachment
            attachment = message.get_payload()[-1]
            
            # Verify the attachment has the correct Content-ID header
            assert attachment.get('Content-ID') == '<test-image>'
            
            # Verify the attachment has Content-Disposition set to inline
            assert 'inline' in attachment.get('Content-Disposition', '')
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_add_attachment_file_not_found(self):
        """Test add_attachment with non-existent file"""
        # Create a MIMEMultipart message
        message = MIMEMultipart()
        
        # Call add_attachment with the message and a non-existent file path
        result = add_attachment(message, '/path/to/nonexistent/file.jpg')
        
        # Assert that the function returns False
        assert result is False
        
        # Assert that the message does not contain any attachments
        assert len(message.get_payload()) == 0
    
    def test_validate_email_addresses_valid(self):
        """Test validate_email_addresses with valid addresses"""
        # Call validate_email_addresses with valid email addresses
        result = validate_email_addresses(TEST_RECIPIENTS)
        
        # Assert that the function returns True
        assert result is True
    
    def test_validate_email_addresses_invalid(self):
        """Test validate_email_addresses with invalid addresses"""
        # Call validate_email_addresses with invalid email addresses
        with pytest.raises(ValidationError):
            validate_email_addresses(['not-an-email', 'also@not@an.email'])
        
        # Assert that the error message contains details about the invalid addresses
        try:
            validate_email_addresses(['not-an-email', 'also@not@an.email'])
        except ValidationError as e:
            assert 'invalid email address format' in str(e).lower()
            assert 'not-an-email' in str(e)
            assert 'also@not@an.email' in str(e)
    
    def test_validate_email_addresses_empty(self):
        """Test validate_email_addresses with empty list"""
        # Call validate_email_addresses with an empty list
        with pytest.raises(ValidationError):
            validate_email_addresses([])
        
        # Assert that the error message indicates that recipients are required
        try:
            validate_email_addresses([])
        except ValidationError as e:
            assert 'non-empty list' in str(e).lower()