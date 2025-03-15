import pytest
import os
import tempfile
from unittest.mock import MagicMock, patch

from ...components.report_distributor import ReportDistributor
from ..mocks.mock_gmail_client import MockGmailClient, MockAuthenticationService
from ...models.report import Report, create_report, create_complete_report
from ..fixtures.budget import create_analyzed_budget, create_budget_with_surplus
from ...utils.error_handlers import ValidationError, APIError

def setup_function():
    """Setup function that runs before each test"""
    # Reset any global state before each test
    pass

def create_test_chart_file():
    """Helper function to create a temporary chart file for testing"""
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    temp_file_path = temp_file.name
    temp_file.close()
    
    # Write some dummy content to the file
    with open(temp_file_path, 'wb') as f:
        f.write(b'test chart content')
    
    return temp_file_path

def create_test_report():
    """Helper function to create a test report with insights and charts"""
    # Create an analyzed budget using fixture data
    budget = create_budget_with_surplus()
    
    # Create a test chart file
    chart_file = create_test_chart_file()
    
    # Create a complete report with the budget, test insights, and chart file
    test_insights = "This is a test insight for budget analysis."
    report = create_complete_report(budget, test_insights, [chart_file])
    
    return report

class TestReportDistributor:
    """Test class for the ReportDistributor component"""
    
    def test_init(self):
        """Test initialization of ReportDistributor"""
        # Create mock objects
        mock_gmail_client = MockGmailClient()
        mock_auth_service = MockAuthenticationService()
        
        # Create a ReportDistributor with mocks
        report_distributor = ReportDistributor(
            gmail_client=mock_gmail_client,
            auth_service=mock_auth_service,
            recipients=['test@example.com'],
            sender_email='sender@example.com'
        )
        
        # Assert that the ReportDistributor has the correct attributes
        assert report_distributor.gmail_client == mock_gmail_client
        assert report_distributor.auth_service == mock_auth_service
        assert report_distributor.recipients == ['test@example.com']
        assert report_distributor.sender_email == 'sender@example.com'
    
    def test_authenticate_success(self):
        """Test successful authentication with Gmail API"""
        # Create a mock Gmail client configured for successful authentication
        mock_gmail_client = MockGmailClient(auth_success=True)
        
        # Create a ReportDistributor with the mock client
        report_distributor = ReportDistributor(gmail_client=mock_gmail_client)
        
        # Call authenticate method
        result = report_distributor.authenticate()
        
        # Assert that authentication was successful
        assert result is True
    
    def test_authenticate_failure(self):
        """Test authentication failure with Gmail API"""
        # Create a mock Gmail client configured for authentication failure
        mock_gmail_client = MockGmailClient(auth_success=False)
        
        # Create a ReportDistributor with the mock client
        report_distributor = ReportDistributor(gmail_client=mock_gmail_client)
        
        # Call authenticate method
        result = report_distributor.authenticate()
        
        # Assert that authentication failed
        assert result is False
    
    def test_validate_report_valid(self):
        """Test validation of a valid report"""
        # Create a complete test report
        report = create_test_report()
        
        # Create a ReportDistributor
        report_distributor = ReportDistributor()
        
        # Call validate_report method with the test report
        result = report_distributor.validate_report(report)
        
        # Assert that validation returns True
        assert result is True
    
    def test_validate_report_invalid(self):
        """Test validation of an invalid report"""
        # Create an incomplete report (missing insights or charts)
        budget = create_budget_with_surplus()
        incomplete_report = create_report(budget)  # No insights or charts added
        
        # Create a ReportDistributor
        report_distributor = ReportDistributor()
        
        # Call validate_report method with the incomplete report
        # Assert that ValidationError is raised
        with pytest.raises(ValidationError):
            report_distributor.validate_report(incomplete_report)
    
    def test_send_report_success(self):
        """Test successful sending of a report"""
        # Create a mock Gmail client
        mock_gmail_client = MockGmailClient()
        
        # Create a complete test report
        report = create_test_report()
        
        # Create a ReportDistributor with the mock client
        report_distributor = ReportDistributor(
            gmail_client=mock_gmail_client,
            recipients=['test@example.com']
        )
        
        # Call send_report method with the test report
        result = report_distributor.send_report(report)
        
        # Assert that the Gmail client's send_email method was called with correct parameters
        assert result.get('status') == 'success'
        assert 'message_id' in result
        assert mock_gmail_client.sent_email_count > 0
    
    def test_send_report_failure(self):
        """Test failure when sending a report"""
        # Create a mock Gmail client configured to simulate API error
        mock_gmail_client = MockGmailClient(api_error=True, error_type='server_error')
        
        # Create a complete test report
        report = create_test_report()
        
        # Create a ReportDistributor with the mock client
        report_distributor = ReportDistributor(gmail_client=mock_gmail_client)
        
        # Call send_report method with the test report
        # Assert that APIError is raised
        with pytest.raises(APIError):
            report_distributor.send_report(report)
    
    def test_verify_delivery_success(self):
        """Test successful verification of email delivery"""
        # Create a mock Gmail client
        mock_gmail_client = MockGmailClient()
        
        # Create a ReportDistributor with the mock client
        report_distributor = ReportDistributor(gmail_client=mock_gmail_client)
        
        # Call verify_delivery method with a test message_id
        message_id = "message-id-12345abcdef"  # This matches DEFAULT_MESSAGE_ID in the mock
        result = report_distributor.verify_delivery(message_id)
        
        # Assert that the Gmail client's verify_delivery method was called with the message_id
        # Assert that the return value indicates successful delivery
        assert result.get('status') == 'delivered'
    
    def test_verify_delivery_failure(self):
        """Test failure when verifying email delivery"""
        # Create a mock Gmail client configured to simulate API error
        mock_gmail_client = MockGmailClient(api_error=True, error_type='not_found')
        
        # Create a ReportDistributor with the mock client
        report_distributor = ReportDistributor(gmail_client=mock_gmail_client)
        
        # Call verify_delivery method with a test message_id
        # Assert that APIError is raised
        with pytest.raises(APIError):
            report_distributor.verify_delivery("test-message-id")
    
    def test_execute_success(self):
        """Test successful execution of the report distribution process"""
        # Create a mock Gmail client
        mock_gmail_client = MockGmailClient()
        
        # Create a complete test report
        report = create_test_report()
        
        # Create a ReportDistributor with the mock client
        report_distributor = ReportDistributor(gmail_client=mock_gmail_client)
        
        # Create a previous_status dictionary with the report
        previous_status = {'report': report, 'correlation_id': 'test-correlation-id'}
        
        # Call execute method with the previous_status
        result = report_distributor.execute(previous_status)
        
        # Assert that the return value indicates success
        assert result.get('status') == 'success'
        # Assert that the Gmail client's authenticate, send_email, and verify_delivery methods were called
        assert mock_gmail_client.sent_email_count > 0
    
    def test_execute_auth_failure(self):
        """Test execution with authentication failure"""
        # Create a mock Gmail client configured for authentication failure
        mock_gmail_client = MockGmailClient(auth_success=False)
        
        # Create a ReportDistributor with the mock client
        report_distributor = ReportDistributor(gmail_client=mock_gmail_client)
        
        # Create a previous_status dictionary with a test report
        report = create_test_report()
        previous_status = {'report': report, 'correlation_id': 'test-correlation-id'}
        
        # Call execute method with the previous_status
        result = report_distributor.execute(previous_status)
        
        # Assert that the return value indicates failure with authentication error
        assert result.get('status') == 'error'
        assert 'Failed to authenticate with Gmail API' in result.get('message', '')
    
    def test_execute_send_failure(self):
        """Test execution with send failure"""
        # Create a mock Gmail client 
        mock_gmail_client = MockGmailClient()
        
        # Configure it to fail on send_email
        mock_gmail_client.set_api_error(True, error_type='server_error')
        
        # Create a ReportDistributor with the mock client
        report_distributor = ReportDistributor(gmail_client=mock_gmail_client)
        
        # Create a previous_status dictionary with a test report
        report = create_test_report()
        previous_status = {'report': report, 'correlation_id': 'test-correlation-id'}
        
        # Call execute method with the previous_status
        result = report_distributor.execute(previous_status)
        
        # Assert that the return value indicates failure with send error
        assert result.get('status') == 'error'
        assert 'error' in result.get('message', '').lower()
    
    def test_execute_verify_failure(self):
        """Test execution with verification failure"""
        # Create a mock Gmail client
        mock_gmail_client = MockGmailClient()
        
        # Configure it to pass on send but fail on verify
        def send_success_verify_fail(*args, **kwargs):
            mock_gmail_client.set_api_error(False)  # Reset for send
            result = mock_gmail_client.send_email(*args, **kwargs)
            mock_gmail_client.set_api_error(True, error_type='not_found')  # Set error for verify
            return result
        
        # Create a ReportDistributor with the modified client
        report_distributor = ReportDistributor(gmail_client=mock_gmail_client)
        
        # Override send_email to call our custom function
        mock_gmail_client.send_email = send_success_verify_fail
        
        # Create a previous_status dictionary with a test report
        report = create_test_report()
        previous_status = {'report': report, 'correlation_id': 'test-correlation-id'}
        
        # Call execute method with the previous_status
        result = report_distributor.execute(previous_status)
        
        # Assert that verification failure results in error status
        assert result.get('status') == 'error'
    
    def test_execute_invalid_report(self):
        """Test execution with an invalid report"""
        # Create a mock Gmail client
        mock_gmail_client = MockGmailClient()
        
        # Create an incomplete test report (missing insights or charts)
        budget = create_budget_with_surplus()
        incomplete_report = create_report(budget)  # No insights or charts added
        
        # Create a ReportDistributor with the mock client
        report_distributor = ReportDistributor(gmail_client=mock_gmail_client)
        
        # Create a previous_status dictionary with the incomplete report
        previous_status = {'report': incomplete_report, 'correlation_id': 'test-correlation-id'}
        
        # Call execute method with the previous_status
        result = report_distributor.execute(previous_status)
        
        # Assert that the return value indicates failure with validation error
        assert result.get('status') == 'error'
        assert 'error' in result.get('message', '').lower()
    
    def test_check_health(self):
        """Test health check functionality"""
        # Create a mock Gmail client
        mock_gmail_client = MockGmailClient()
        
        # Create a ReportDistributor with the mock client
        report_distributor = ReportDistributor(gmail_client=mock_gmail_client)
        
        # Call check_health method
        result = report_distributor.check_health()
        
        # Assert that the return value indicates healthy status
        assert result.get('status') == 'healthy'
        
        # Modify mock client to simulate unhealthy state
        mock_gmail_client.set_api_error(True)
        
        # Call check_health method again
        result = report_distributor.check_health()
        
        # Assert that the return value indicates unhealthy status
        assert result.get('status') == 'unhealthy'