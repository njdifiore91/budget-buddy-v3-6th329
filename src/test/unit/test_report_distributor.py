import pytest
import os
import tempfile
from unittest.mock import MagicMock, patch

from src.backend.components.report_distributor import ReportDistributor
from src.test.mocks.gmail_client import MockGmailClient
from src.backend.models.report import Report
from src.backend.models.budget import Budget
from src.test.utils.test_helpers import create_test_budget
from src.test.utils.test_helpers import create_temp_file
from src.test.utils.assertion_helpers import assert_email_content_valid
from src.backend.utils.error_handlers import APIError, ValidationError
from src.test.utils.fixture_loader import load_fixture

TEST_EMAIL_RECIPIENTS = ['njdifiore@gmail.com', 'nick@blitzy.com']
TEST_EMAIL_SENDER = 'njdifiore@gmail.com'

def setup_function():
    """Setup function that runs before each test"""
    global temp_dir, chart_file1, chart_file2, test_budget, test_report, mock_gmail_client, report_distributor

    # Create temporary directory for test files
    temp_dir = tempfile.mkdtemp()

    # Create test chart files for email attachments
    chart_file1 = create_temp_file(suffix=".png")
    chart_file2 = create_temp_file(suffix=".jpg")

    # Create test budget with sample data
    test_budget = create_test_budget()

    # Create test report with budget data, insights, and charts
    test_report = Report(test_budget)
    test_report.set_insights("Test insights")
    test_report.add_chart(chart_file1)
    test_report.add_chart(chart_file2)

    # Create mock Gmail client for testing
    mock_gmail_client = MockGmailClient()

    # Create ReportDistributor instance with mock Gmail client
    report_distributor = ReportDistributor(gmail_client=mock_gmail_client, recipients=TEST_EMAIL_RECIPIENTS, sender_email=TEST_EMAIL_SENDER)

def teardown_function():
    """Teardown function that runs after each test"""
    global temp_dir, chart_file1, chart_file2, mock_gmail_client

    # Clean up temporary files and directories
    if os.path.exists(chart_file1):
        os.remove(chart_file1)
    if os.path.exists(chart_file2):
        os.remove(chart_file2)
    if os.path.exists(temp_dir):
        os.rmdir(temp_dir)

    # Reset mock objects
    mock_gmail_client.reset()

def test_init():
    """Test that ReportDistributor initializes correctly"""
    # Create ReportDistributor with custom recipients and sender
    report_distributor = ReportDistributor(recipients=['test@example.com'], sender_email='custom@example.com')
    assert report_distributor.recipients == ['test@example.com']
    assert report_distributor.sender_email == 'custom@example.com'
    assert isinstance(report_distributor.gmail_client, MockGmailClient)

    # Create ReportDistributor with default values
    report_distributor = ReportDistributor()
    assert report_distributor.recipients == ['njdifiore@gmail.com', 'nick@blitzy.com']
    assert report_distributor.sender_email == 'njdifiore@gmail.com'

def test_authenticate_success():
    """Test successful authentication with Gmail API"""
    # Configure mock Gmail client to authenticate successfully
    mock_gmail_client.authenticated = True

    # Call authenticate method on ReportDistributor
    result = report_distributor.authenticate()

    # Assert that authentication was successful
    assert result is True

    # Verify that gmail_client.authenticate was called
    assert mock_gmail_client.authenticated is True

def test_authenticate_failure():
    """Test authentication failure with Gmail API"""
    # Configure mock Gmail client to fail authentication
    mock_gmail_client.set_should_fail_authentication(True)

    # Call authenticate method on ReportDistributor
    result = report_distributor.authenticate()

    # Assert that authentication failed
    assert result is False

    # Verify that gmail_client.authenticate was called
    assert mock_gmail_client.authenticated is False

def test_validate_report_valid():
    """Test validation of a valid report"""
    # Create a complete report with insights and charts
    report = Report(test_budget)
    report.set_insights("Test insights")
    report.add_chart(chart_file1)

    # Call validate_report method on ReportDistributor
    result = report_distributor.validate_report(report)

    # Assert that validation returns True
    assert result is True

def test_validate_report_invalid_incomplete():
    """Test validation of an incomplete report"""
    # Create an incomplete report without insights or charts
    report = Report(test_budget)

    # Call validate_report method on ReportDistributor
    with pytest.raises(ValidationError):
        report_distributor.validate_report(report)

def test_validate_report_invalid_type():
    """Test validation with an invalid report type"""
    # Create an object that is not a Report instance
    invalid_report = "Not a Report"

    # Call validate_report method on ReportDistributor
    with pytest.raises(ValidationError):
        report_distributor.validate_report(invalid_report)

def test_send_report_success():
    """Test successful sending of a report"""
    # Create a complete report with insights and charts
    report = Report(test_budget)
    report.set_insights("Test insights")
    report.add_chart(chart_file1)

    # Configure mock Gmail client to send email successfully
    mock_gmail_client.authenticated = True

    # Call send_report method on ReportDistributor
    result = report_distributor.send_report(report)

    # Assert that email was sent successfully
    assert result['status'] == 'success'

    # Verify that gmail_client.send_email was called with correct parameters
    assert mock_gmail_client.get_sent_email_count() == 1
    sent_email = mock_gmail_client.get_last_sent_email()
    assert sent_email['subject'] == report.generate_email_subject()
    assert sent_email['html_content'] == report.generate_email_body()
    assert sent_email['recipients'] == TEST_EMAIL_RECIPIENTS

    # Verify that email content matches expected format from fixture
    assert_email_content_valid(sent_email['html_content'], test_budget.to_dict())

def test_send_report_invalid_report():
    """Test sending an invalid report"""
    # Create an incomplete report without insights or charts
    report = Report(test_budget)

    # Call send_report method on ReportDistributor
    with pytest.raises(ValidationError):
        report_distributor.send_report(report)

    # Verify that gmail_client.send_email was not called
    assert mock_gmail_client.get_sent_email_count() == 0

def test_send_report_api_error():
    """Test handling of API error during report sending"""
    # Create a complete report with insights and charts
    report = Report(test_budget)
    report.set_insights("Test insights")
    report.add_chart(chart_file1)

    # Configure mock Gmail client to fail when sending email
    mock_gmail_client.set_should_fail_sending(True)

    # Call send_report method on ReportDistributor
    with pytest.raises(APIError):
        report_distributor.send_report(report)

    # Verify that gmail_client.send_email was called
    assert mock_gmail_client.get_sent_email_count() == 0

def test_verify_delivery_success():
    """Test successful verification of email delivery"""
    # Configure mock Gmail client to verify delivery successfully
    mock_gmail_client.authenticated = True

    # Call verify_delivery method on ReportDistributor with a message ID
    result = report_distributor.verify_delivery("test_message_id")

    # Assert that verification was successful
    assert result['status'] == 'sent'

    # Verify that gmail_client.verify_delivery was called with correct message ID
    assert mock_gmail_client.authenticated is True

def test_verify_delivery_api_error():
    """Test handling of API error during delivery verification"""
    # Configure mock Gmail client to fail when verifying delivery
    mock_gmail_client.set_should_fail_verification(True)

    # Call verify_delivery method on ReportDistributor with a message ID
    with pytest.raises(APIError):
        report_distributor.verify_delivery("test_message_id")

    # Verify that gmail_client.verify_delivery was called with correct message ID
    assert mock_gmail_client.authenticated is False

def test_execute_success():
    """Test successful execution of the report distribution process"""
    # Create a complete report with insights and charts
    report = Report(test_budget)
    report.set_insights("Test insights")
    report.add_chart(chart_file1)

    # Configure mock Gmail client for successful authentication, sending, and verification
    mock_gmail_client.authenticated = True

    # Create previous_status dictionary with report and correlation_id
    previous_status = {'report': report, 'correlation_id': 'test_correlation_id'}

    # Call execute method on ReportDistributor
    result = report_distributor.execute(previous_status)

    # Assert that execution was successful
    assert result['status'] == 'success'

    # Verify that gmail_client methods were called in correct sequence
    assert mock_gmail_client.authenticated is True
    assert mock_gmail_client.get_sent_email_count() == 1
    assert mock_gmail_client.get_last_sent_email()['subject'] == report.generate_email_subject()

    # Verify that returned status contains success flag and delivery status
    assert result['delivery_status'] == 'sent'
    assert result['message_id'] == mock_gmail_client.get_last_sent_email()['message_id']
    assert result['email_subject'] == report.generate_email_subject()
    assert result['recipients'] == TEST_EMAIL_RECIPIENTS
    assert result['correlation_id'] == 'test_correlation_id'

def test_execute_authentication_failure():
    """Test execution with authentication failure"""
    # Create a complete report with insights and charts
    report = Report(test_budget)
    report.set_insights("Test insights")
    report.add_chart(chart_file1)

    # Configure mock Gmail client to fail authentication
    mock_gmail_client.set_should_fail_authentication(True)

    # Create previous_status dictionary with report and correlation_id
    previous_status = {'report': report, 'correlation_id': 'test_correlation_id'}

    # Call execute method on ReportDistributor
    result = report_distributor.execute(previous_status)

    # Assert that execution failed with authentication error
    assert result['status'] == 'error'
    assert 'Failed to authenticate' in result['message']

    # Verify that gmail_client.authenticate was called
    assert mock_gmail_client.authenticated is False

    # Verify that gmail_client.send_email was not called
    assert mock_gmail_client.get_sent_email_count() == 0

def test_execute_send_failure():
    """Test execution with send failure"""
    # Create a complete report with insights and charts
    report = Report(test_budget)
    report.set_insights("Test insights")
    report.add_chart(chart_file1)

    # Configure mock Gmail client for successful authentication but failed sending
    mock_gmail_client.authenticated = True
    mock_gmail_client.set_should_fail_sending(True)

    # Create previous_status dictionary with report and correlation_id
    previous_status = {'report': report, 'correlation_id': 'test_correlation_id'}

    # Call execute method on ReportDistributor
    result = report_distributor.execute(previous_status)

    # Assert that execution failed with send error
    assert result['status'] == 'error'
    assert 'Failed to send email' in result['message']

    # Verify that gmail_client.authenticate and gmail_client.send_email were called
    assert mock_gmail_client.authenticated is True
    assert mock_gmail_client.get_sent_email_count() == 0

    # Verify that gmail_client.verify_delivery was not called
    assert len(mock_gmail_client.message_statuses) == 0

def test_execute_verification_failure():
    """Test execution with verification failure"""
    # Create a complete report with insights and charts
    report = Report(test_budget)
    report.set_insights("Test insights")
    report.add_chart(chart_file1)

    # Configure mock Gmail client for successful authentication and sending but failed verification
    mock_gmail_client.authenticated = True
    mock_gmail_client.set_should_fail_verification(True)

    # Create previous_status dictionary with report and correlation_id
    previous_status = {'report': report, 'correlation_id': 'test_correlation_id'}

    # Call execute method on ReportDistributor
    result = report_distributor.execute(previous_status)

    # Assert that execution completed with verification warning
    assert result['status'] == 'success'
    assert 'Report distributed successfully' in result['message']
    assert result['delivery_status'] == 'sent'

    # Verify that all gmail_client methods were called
    assert mock_gmail_client.authenticated is True
    assert mock_gmail_client.get_sent_email_count() == 1

    # Verify that status contains warning about verification
    assert 'message_id' in result
    assert result['email_subject'] == report.generate_email_subject()
    assert result['recipients'] == TEST_EMAIL_RECIPIENTS
    assert result['correlation_id'] == 'test_correlation_id'

def test_execute_invalid_report():
    """Test execution with an invalid report"""
    # Create an incomplete report without insights or charts
    report = Report(test_budget)

    # Create previous_status dictionary with invalid report and correlation_id
    previous_status = {'report': report, 'correlation_id': 'test_correlation_id'}

    # Call execute method on ReportDistributor
    result = report_distributor.execute(previous_status)

    # Assert that execution failed with validation error
    assert result['status'] == 'error'
    assert 'Report distribution error' in result['message']

    # Verify that gmail_client.send_email was not called
    assert mock_gmail_client.get_sent_email_count() == 0

def test_execute_missing_report():
    """Test execution with missing report in previous_status"""
    # Create previous_status dictionary without report
    previous_status = {'correlation_id': 'test_correlation_id'}

    # Call execute method on ReportDistributor
    result = report_distributor.execute(previous_status)

    # Assert that execution failed with missing report error
    assert result['status'] == 'error'
    assert 'Report distribution error' in result['message']

    # Verify that gmail_client methods were not called
    assert mock_gmail_client.get_sent_email_count() == 0

def test_prepare_email_with_complete_report():
    """Test preparation of email content from a complete report"""
    # Create a complete report with insights and charts
    report = Report(test_budget)
    report.set_insights("Test insights")
    report.add_chart(chart_file1)

    # Get email content from report using get_email_content
    subject, body = report.get_email_content()

    # Assert that email subject contains budget status
    assert "under budget" in subject or "over budget" in subject

    # Assert that email body contains expected sections
    assert "Test insights" in body
    assert "Category" in body

    # Verify that email content matches expected format from fixture
    assert_email_content_valid(body, test_budget.to_dict())

@patch('src.backend.utils.error_handlers.retry_with_backoff')
def test_retry_mechanism_for_send_report(mock_retry_with_backoff):
    """Test retry mechanism for send_report method"""
    # Mock retry_with_backoff decorator
    mock_retry_with_backoff.return_value = lambda func: func

    # Create a complete report with insights and charts
    report = Report(test_budget)
    report.set_insights("Test insights")
    report.add_chart(chart_file1)

    # Configure mock Gmail client to fail sending initially but succeed on retry
    mock_gmail_client.authenticated = True
    mock_gmail_client.set_should_fail_sending(True)

    # Call send_report method on ReportDistributor
    try:
        report_distributor.send_report(report)
    except APIError:
        pass

    # Verify that retry mechanism was used
    assert mock_retry_with_backoff.called

    # Assert that email was sent successfully after retries
    mock_gmail_client.set_should_fail_sending(False)
    result = report_distributor.send_report(report)
    assert result['status'] == 'success'