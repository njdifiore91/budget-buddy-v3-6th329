"""
Unit tests for the Gmail client component of the Budget Management Application.
Tests the functionality for authenticating with Gmail API, creating and sending emails with attachments, and verifying email delivery status.
"""

import pytest  # pytest 7.4.0+
import os  # standard library
import tempfile  # standard library
from unittest.mock import MagicMock, patch, Mock  # standard library
from email.mime.multipart import MIMEMultipart  # standard library

from src.backend.api_clients.gmail_client import GmailClient, create_message, add_attachment, validate_email_addresses  # Class under test
from src.backend.utils.error_handlers import APIError, ValidationError  # Error class for testing exception handling
from src.test.mocks.gmail_client import MockGmailClient  # Mock implementation for testing
from src.test.utils.test_helpers import load_test_fixture, create_temp_file  # Load test fixtures for test data
from src.test.utils.assertion_helpers import assert_dict_subset, assert_email_content_valid, APIAssertions  # API-specific assertions for testing

# Constants for testing
TEST_SENDER = 'njdifiore@gmail.com'
TEST_RECIPIENTS = ['njdifiore@gmail.com', 'nick@blitzy.com']
TEST_SUBJECT = 'Budget Update: $45.67 under budget this week'
TEST_HTML_CONTENT = '<html><body><h1>Weekly Budget Update</h1><p>You are $45.67 under budget this week.</p></body></html>'


def setup_gmail_client_mock(should_fail_authentication: bool = False, should_fail_sending: bool = False,
                            should_fail_verification: bool = False) -> MockGmailClient:
    """
    Set up a mock for the GmailClient with controlled behavior

    Args:
        should_fail_authentication (bool): Whether authentication should fail
        should_fail_sending (bool): Whether sending should fail
        should_fail_verification (bool): Whether verification should fail

    Returns:
        MockGmailClient: Configured mock Gmail client
    """
    # Create a mock AuthenticationService
    mock_auth_service = MagicMock()

    # Create a MockGmailClient instance with the mock auth service
    mock_client = MockGmailClient(auth_service=mock_auth_service)

    # Configure failure behaviors based on parameters
    mock_client.set_should_fail_authentication(should_fail_authentication)
    mock_client.set_should_fail_sending(should_fail_sending)
    mock_client.set_should_fail_verification(should_fail_verification)

    # Return the configured mock client
    return mock_client


class TestValidateEmailAddresses:
    """Test cases for the validate_email_addresses function"""

    def __init__(self):
        """Initialize the test class"""
        pass

    def test_valid_email_addresses(self) -> None:
        """Test that valid email addresses pass validation"""
        # Create a list of valid email addresses
        valid_emails = ['test@example.com', 'another@test.co.uk']

        # Call validate_email_addresses with the list
        result = validate_email_addresses(valid_emails)

        # Assert that the function returns True
        assert result is True

    def test_invalid_email_addresses(self) -> None:
        """Test that invalid email addresses fail validation"""
        # Create a list with at least one invalid email address
        invalid_emails = ['test@example', 'another@test.co.uk', 'invalid']

        # Call validate_email_addresses with the list
        with pytest.raises(ValidationError) as exc_info:
            validate_email_addresses(invalid_emails)

        # Assert that ValidationError is raised
        assert "Invalid email address format" in str(exc_info.value)

        # Verify the error message contains details about the invalid address
        assert "invalid" in str(exc_info.value)

    def test_empty_email_list(self) -> None:
        """Test that an empty email list fails validation"""
        # Call validate_email_addresses with an empty list
        with pytest.raises(ValidationError) as exc_info:
            validate_email_addresses([])

        # Assert that ValidationError is raised
        assert "Email addresses must be a non-empty list" in str(exc_info.value)

        # Verify the error message indicates empty list
        assert "non-empty list" in str(exc_info.value)


class TestCreateMessage:
    """Test cases for the create_message function"""

    def __init__(self):
        """Initialize the test class"""
        pass

    def test_create_message_valid_inputs(self) -> None:
        """Test creating a message with valid inputs"""
        # Call create_message with valid sender, recipients, subject, and HTML content
        message = create_message(TEST_SENDER, TEST_RECIPIENTS, TEST_SUBJECT, TEST_HTML_CONTENT)

        # Assert that the returned object is a dictionary
        assert isinstance(message, dict)

        # Assert that the dictionary contains a 'raw' key with base64-encoded content
        assert 'raw' in message
        assert isinstance(message['raw'], str)

        # Decode the raw content and verify it contains the expected headers and content
        decoded_message = base64.urlsafe_b64decode(message['raw'].encode()).decode()
        assert f'From: {TEST_SENDER}' in decoded_message
        assert f'To: {", ".join(TEST_RECIPIENTS)}' in decoded_message
        assert f'Subject: {TEST_SUBJECT}' in decoded_message
        assert TEST_HTML_CONTENT in decoded_message

    def test_create_message_invalid_sender(self) -> None:
        """Test creating a message with invalid sender"""
        # Call create_message with invalid sender email
        with pytest.raises(ValidationError) as exc_info:
            create_message('invalid-sender', TEST_RECIPIENTS, TEST_SUBJECT, TEST_HTML_CONTENT)

        # Assert that ValidationError is raised
        assert "Sender email address is required" in str(exc_info.value)

        # Verify the error message mentions invalid sender
        assert "Sender email address is required" in str(exc_info.value)

    def test_create_message_invalid_recipients(self) -> None:
        """Test creating a message with invalid recipients"""
        # Call create_message with invalid recipient emails
        with pytest.raises(ValidationError) as exc_info:
            create_message(TEST_SENDER, ['invalid-recipient'], TEST_SUBJECT, TEST_HTML_CONTENT)

        # Assert that ValidationError is raised
        assert "Invalid email address format" in str(exc_info.value)

        # Verify the error message mentions invalid recipients
        assert "Invalid email address format" in str(exc_info.value)

    def test_create_message_empty_subject(self) -> None:
        """Test creating a message with empty subject"""
        # Call create_message with empty subject
        with pytest.raises(ValidationError) as exc_info:
            create_message(TEST_SENDER, TEST_RECIPIENTS, '', TEST_HTML_CONTENT)

        # Assert that ValidationError is raised
        assert "Email subject is required" in str(exc_info.value)

        # Verify the error message mentions empty subject
        assert "Email subject is required" in str(exc_info.value)

    def test_create_message_empty_content(self) -> None:
        """Test creating a message with empty content"""
        # Call create_message with empty HTML content
        with pytest.raises(ValidationError) as exc_info:
            create_message(TEST_SENDER, TEST_RECIPIENTS, TEST_SUBJECT, '')

        # Assert that ValidationError is raised
        assert "Email content is required" in str(exc_info.value)

        # Verify the error message mentions empty content
        assert "Email content is required" in str(exc_info.value)


class TestAddAttachment:
    """Test cases for the add_attachment function"""

    def __init__(self):
        """Initialize the test class"""
        self.test_message = None
        self.png_file = None
        self.pdf_file = None
        self.txt_file = None
        self.unusual_file = None

    def setup_method(self) -> None:
        """Set up test environment before each test"""
        # Create a MIMEMultipart message for testing
        self.test_message = MIMEMultipart()

        # Create temporary test files with different extensions (.png, .pdf, .txt)
        self.png_file = create_temp_file(content="PNG Content", suffix=".png")
        self.pdf_file = create_temp_file(content="PDF Content", suffix=".pdf")
        self.txt_file = create_temp_file(content="Text Content", suffix=".txt")
        self.unusual_file = create_temp_file(content="Unusual Content", suffix=".xyz")

    def teardown_method(self) -> None:
        """Clean up test environment after each test"""
        # Remove all temporary files created during setup
        for file_path in [self.png_file, self.pdf_file, self.txt_file, self.unusual_file]:
            if os.path.exists(file_path):
                os.remove(file_path)

    def test_add_inline_image_attachment(self) -> None:
        """Test adding an inline image attachment"""
        # Call add_attachment with the test message, PNG file path, and content ID
        result = add_attachment(self.test_message, self.png_file, content_id="test_image")

        # Assert that the function returns True
        assert result is True

        # Verify that the message now has a new part with the correct Content-ID
        assert len(self.test_message.get_payload()) == 1
        attachment = self.test_message.get_payload()[0]
        assert attachment.get('Content-ID') == "<test_image>"

        # Verify that the Content-Disposition is set to 'inline'
        assert attachment.get('Content-Disposition') == 'inline; filename="test.png"'

    def test_add_regular_attachment(self) -> None:
        """Test adding a regular (non-inline) attachment"""
        # Call add_attachment with the test message, PDF file path, and no content ID
        result = add_attachment(self.test_message, self.pdf_file)

        # Assert that the function returns True
        assert result is True

        # Verify that the message now has a new part with the correct filename
        assert len(self.test_message.get_payload()) == 1
        attachment = self.test_message.get_payload()[0]
        assert attachment.get_filename() == "test.pdf"

        # Verify that the Content-Disposition is set to 'attachment'
        assert attachment.get('Content-Disposition') == 'attachment; filename="test.pdf"'

    def test_add_attachment_nonexistent_file(self) -> None:
        """Test adding a nonexistent file as attachment"""
        # Call add_attachment with the test message and a nonexistent file path
        result = add_attachment(self.test_message, "nonexistent_file.txt")

        # Assert that the function returns False
        assert result is False

        # Verify that the message has no new parts added
        assert len(self.test_message.get_payload()) == 0

    def test_add_attachment_unsupported_type(self) -> None:
        """Test adding a file with unsupported MIME type"""
        # Call add_attachment with the test message and a file with unusual extension
        result = add_attachment(self.test_message, self.unusual_file)

        # Assert that the function still returns True (should handle unknown types)
        assert result is True

        # Verify that the message has a new part with application/octet-stream type
        assert len(self.test_message.get_payload()) == 1
        attachment = self.test_message.get_payload()[0]
        assert attachment.get_content_type() == "application/octet-stream"


class TestGmailClient:
    """Test cases for the GmailClient class"""

    def __init__(self):
        """Initialize the test class"""
        self.mock_auth_service = None
        self.gmail_client = None
        self.png_file = None
        self.test_message = None

    def setup_method(self) -> None:
        """Set up test environment before each test"""
        # Create a mock AuthenticationService
        self.mock_auth_service = MagicMock()

        # Create temporary test files for attachments
        self.png_file = create_temp_file(content="PNG Content", suffix=".png")

    def teardown_method(self) -> None:
        """Clean up test environment after each test"""
        # Remove all temporary files created during setup
        if os.path.exists(self.png_file):
            os.remove(self.png_file)

    def test_init(self) -> None:
        """Test initialization of GmailClient"""
        # Create a GmailClient instance with the mock auth service
        client = GmailClient(self.mock_auth_service)

        # Assert that the client's auth_service attribute is set correctly
        assert client.auth_service == self.mock_auth_service

        # Assert that the client's sender_email is set to the default or provided value
        assert client.sender_email == 'njdifiore@gmail.com'

        # Assert that the client's user_id is set to the default or provided value
        assert client.user_id == 'me'

        # Assert that the client's service attribute is initially None
        assert client.service is None

    def test_authenticate_success(self) -> None:
        """Test successful authentication with Gmail API"""
        # Set up mocks for authentication service and Google API client
        self.mock_auth_service.authenticate_gmail.return_value = "mock_credentials"
        mock_gmail_service = MagicMock()

        with patch('src.backend.api_clients.gmail_client.build', return_value=mock_gmail_service) as mock_build:
            # Create a GmailClient instance with the mock auth service
            client = GmailClient(self.mock_auth_service)

            # Call the authenticate method
            result = client.authenticate()

            # Assert that the method returns True
            assert result is True

            # Assert that the client's service attribute is now set
            assert client.service is not None

            # Verify that the auth_service.authenticate_gmail method was called
            self.mock_auth_service.authenticate_gmail.assert_called_once()

            # Verify that the build method was called with correct parameters
            mock_build.assert_called_once_with('gmail', 'v1', credentials="mock_credentials")

    def test_authenticate_failure(self) -> None:
        """Test authentication failure with Gmail API"""
        # Set up mocks for authentication service to raise an exception
        self.mock_auth_service.authenticate_gmail.side_effect = Exception("Authentication failed")

        # Create a GmailClient instance with the mock auth service
        client = GmailClient(self.mock_auth_service)

        # Call the authenticate method
        with pytest.raises(APIError) as exc_info:
            client.authenticate()

        # Assert that APIError is raised
        assert "Gmail API authentication failed" in str(exc_info.value)

        # Assert that the client's service attribute remains None
        assert client.service is None

    def test_is_authenticated(self) -> None:
        """Test is_authenticated method"""
        # Create a GmailClient instance with the mock auth service
        client = GmailClient(self.mock_auth_service)

        # Assert that is_authenticated initially returns False
        assert client.is_authenticated() is False

        # Set up the client's service attribute to a non-None value
        client.service = MagicMock()

        # Assert that is_authenticated now returns True
        assert client.is_authenticated() is True

    def test_send_email_success(self) -> None:
        """Test successful email sending"""
        # Set up mocks for Gmail API service with successful response
        mock_gmail_service = MagicMock()
        mock_gmail_service.users().messages().send().execute.return_value = {'id': 'test_message_id'}

        with patch('src.backend.api_clients.gmail_client.build', return_value=mock_gmail_service):
            # Create a GmailClient instance with the mock auth service
            client = GmailClient(self.mock_auth_service)

            # Set up the client's service attribute
            client.service = mock_gmail_service

            # Call send_email with test subject, content, recipients, and attachments
            result = client.send_email(TEST_SUBJECT, TEST_HTML_CONTENT, TEST_RECIPIENTS)

            # Assert that the method returns a dictionary with success status and message ID
            assert isinstance(result, dict)
            assert result['status'] == 'success'
            assert result['message_id'] == 'test_message_id'

            # Verify that the Gmail API's users().messages().send() method was called with correct parameters
            mock_gmail_service.users().messages().send.assert_called_once()

    def test_send_email_not_authenticated(self) -> None:
        """Test sending email when not authenticated"""
        # Create a GmailClient instance with the mock auth service
        client = GmailClient(self.mock_auth_service)

        # Set up mocks for authentication to fail
        self.mock_auth_service.authenticate_gmail.side_effect = Exception("Authentication failed")

        # Call send_email with test parameters
        with pytest.raises(APIError) as exc_info:
            client.send_email(TEST_SUBJECT, TEST_HTML_CONTENT, TEST_RECIPIENTS, attachment_paths=[self.png_file])

        # Assert that APIError is raised with authentication error message
        assert "Gmail API authentication failed" in str(exc_info.value)

    def test_send_email_invalid_recipients(self) -> None:
        """Test sending email with invalid recipients"""
        # Create a GmailClient instance with the mock auth service
        client = GmailClient(self.mock_auth_service)
        client.service = MagicMock()

        # Call send_email with invalid recipients
        with pytest.raises(ValidationError) as exc_info:
            client.send_email(TEST_SUBJECT, TEST_HTML_CONTENT, ['invalid-email'])

        # Assert that ValidationError is raised with invalid recipients message
        assert "Invalid email address format" in str(exc_info.value)

    def test_send_email_api_error(self) -> None:
        """Test handling of API error during email sending"""
        # Set up mocks for Gmail API service to raise an exception
        mock_gmail_service = MagicMock()
        mock_gmail_service.users().messages().send().execute.side_effect = Exception("API error")

        with patch('src.backend.api_clients.gmail_client.build', return_value=mock_gmail_service):
            # Create a GmailClient instance with the mock auth service
            client = GmailClient(self.mock_auth_service)

            # Set up the client's service attribute
            client.service = mock_gmail_service

            # Call send_email with test parameters
            with pytest.raises(APIError) as exc_info:
                client.send_email(TEST_SUBJECT, TEST_HTML_CONTENT, TEST_RECIPIENTS)

            # Assert that APIError is raised with appropriate error message
            assert "Failed to send email" in str(exc_info.value)

            # Verify that error handling logic was triggered
            mock_gmail_service.users().messages().send.assert_called_once()

    def test_send_email_with_attachments(self) -> None:
        """Test sending email with attachments"""
        # Set up mocks for Gmail API service with successful response
        mock_gmail_service = MagicMock()
        mock_gmail_service.users().messages().send().execute.return_value = {'id': 'test_message_id'}

        with patch('src.backend.api_clients.gmail_client.build', return_value=mock_gmail_service):
            # Create a GmailClient instance with the mock auth service
            client = GmailClient(self.mock_auth_service)

            # Set up the client's service attribute
            client.service = mock_gmail_service

            # Call send_email with test parameters including attachment paths
            result = client.send_email(TEST_SUBJECT, TEST_HTML_CONTENT, TEST_RECIPIENTS, attachment_paths=[self.png_file])

            # Assert that the method returns success status
            assert isinstance(result, dict)
            assert result['status'] == 'success'

            # Verify that the Gmail API's users().messages().send() method was called with a message containing attachments
            mock_gmail_service.users().messages().send.assert_called_once()

    def test_verify_delivery_success(self) -> None:
        """Test successful delivery verification"""
        # Set up mocks for Gmail API service with successful delivery response
        mock_gmail_service = MagicMock()
        mock_gmail_service.users().messages().get().execute.return_value = {'labelIds': ['SENT', 'DELIVERED']}

        with patch('src.backend.api_clients.gmail_client.build', return_value=mock_gmail_service):
            # Create a GmailClient instance with the mock auth service
            client = GmailClient(self.mock_auth_service)

            # Set up the client's service attribute
            client.service = mock_gmail_service

            # Call verify_delivery with a test message ID
            result = client.verify_delivery('test_message_id')

            # Assert that the method returns a dictionary with delivery status
            assert isinstance(result, dict)
            assert result['status'] == 'delivered'

            # Verify that the Gmail API's users().messages().get() method was called with correct parameters
            mock_gmail_service.users().messages().get.assert_called_once_with(userId='me', id='test_message_id')

    def test_verify_delivery_not_authenticated(self) -> None:
        """Test verifying delivery when not authenticated"""
        # Create a GmailClient instance with the mock auth service
        client = GmailClient(self.mock_auth_service)

        # Set up mocks for authentication to fail
        self.mock_auth_service.authenticate_gmail.side_effect = Exception("Authentication failed")

        # Call verify_delivery with a test message ID
        with pytest.raises(APIError) as exc_info:
            client.verify_delivery('test_message_id')

        # Assert that APIError is raised with authentication error message
        assert "Gmail API authentication failed" in str(exc_info.value)

    def test_verify_delivery_invalid_message_id(self) -> None:
        """Test verifying delivery with invalid message ID"""
        # Create a GmailClient instance with the mock auth service
        client = GmailClient(self.mock_auth_service)
        client.service = MagicMock()

        # Call verify_delivery with an empty message ID
        with pytest.raises(ValidationError) as exc_info:
            client.verify_delivery('')

        # Assert that ValidationError is raised with invalid message ID message
        assert "Message ID is required for delivery verification" in str(exc_info.value)

    def test_verify_delivery_api_error(self) -> None:
        """Test handling of API error during delivery verification"""
        # Set up mocks for Gmail API service to raise an exception
        mock_gmail_service = MagicMock()
        mock_gmail_service.users().messages().get().execute.side_effect = Exception("API error")

        with patch('src.backend.api_clients.gmail_client.build', return_value=mock_gmail_service):
            # Create a GmailClient instance with the mock auth service
            client = GmailClient(self.mock_auth_service)

            # Set up the client's service attribute
            client.service = mock_gmail_service

            # Call verify_delivery with a test message ID
            with pytest.raises(APIError) as exc_info:
                client.verify_delivery('test_message_id')

            # Assert that APIError is raised with appropriate error message
            assert "Failed to verify email delivery" in str(exc_info.value)

            # Verify that error handling logic was triggered
            mock_gmail_service.users().messages().get.assert_called_once()

    def test_retry_mechanism(self) -> None:
        """Test retry mechanism for transient errors"""
        # Set up mock Gmail client that fails authentication twice then succeeds
        mock_client = setup_gmail_client_mock(should_fail_authentication=True)
        mock_client.authenticate.side_effect = [Exception("Authentication failed"),
                                                 Exception("Authentication failed"),
                                                 True]  # Succeed on the third attempt

        # Call authenticate method
        result = mock_client.authenticate()

        # Assert that the method eventually returns True
        assert result is True

        # Verify that the authentication method was called multiple times
        assert mock_client.authenticate.call_count == 3

        # Verify that the retry count matches expected number of attempts
        assert mock_client.retry_count == 1

    def test_integration_with_mock(self) -> None:
        """Test full integration using MockGmailClient"""
        # Create a MockGmailClient instance
        mock_client = MockGmailClient()

        # Call authenticate method
        result = mock_client.authenticate()

        # Assert that authentication returns True
        assert result is True

        # Call send_email with test parameters
        send_result = mock_client.send_email(TEST_SUBJECT, TEST_HTML_CONTENT, TEST_RECIPIENTS)

        # Assert that send_email returns success status
        assert send_result['status'] == 'sent'

        # Call verify_delivery with the returned message ID
        message_id = send_result['id']
        verify_result = mock_client.verify_delivery(message_id)

        # Assert that verify_delivery returns delivery status
        assert verify_result['status'] == 'sent'

        # Verify that the mock client recorded the expected interactions
        assert mock_client.get_sent_email_count() == 1
        last_email = mock_client.get_last_sent_email()
        assert last_email['subject'] == TEST_SUBJECT
        assert last_email['html_content'] == TEST_HTML_CONTENT


def setup_gmail_client_mock(should_fail_authentication: bool = False, should_fail_sending: bool = False,
                            should_fail_verification: bool = False) -> MockGmailClient:
    """
    Set up a mock for the GmailClient with controlled behavior

    Args:
        should_fail_authentication (bool): Whether authentication should fail
        should_fail_sending (bool): Whether sending should fail
        should_fail_verification (bool): Whether verification should fail

    Returns:
        MockGmailClient: Configured mock Gmail client
    """
    # Create a mock AuthenticationService
    mock_auth_service = MagicMock()

    # Create a MockGmailClient instance with the mock auth service
    mock_client = MockGmailClient(auth_service=mock_auth_service)

    # Configure failure behaviors based on parameters
    mock_client.set_should_fail_authentication(should_fail_authentication)
    mock_client.set_should_fail_sending(should_fail_sending)
    mock_client.set_should_fail_verification(should_fail_verification)

    # Return the configured mock client
    return mock_client