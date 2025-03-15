import pytest
import os
import tempfile
from typing import List, Dict, Tuple
from unittest.mock import patch, MagicMock

from src.backend.components.insight_generator import InsightGenerator
from src.backend.components.report_distributor import ReportDistributor
from src.test.mocks.gemini_client import MockGeminiClient
from src.test.mocks.gmail_client import MockGmailClient
from src.test.utils.test_helpers import create_test_budget, create_temp_file, TestEnvironment, load_test_fixture
from src.test.utils.assertion_helpers import assert_email_content_valid

INSIGHTS_FIXTURE_PATH = 'api_responses/gemini/insights.json'
EMAIL_CONTENT_FIXTURE_PATH = 'expected/email_content.json'
TEST_EMAIL_RECIPIENTS = ['njdifiore@gmail.com', 'nick@blitzy.com']
TEST_EMAIL_SENDER = 'njdifiore@gmail.com'


def setup_mocks(with_authentication_failure: bool = False, with_sending_failure: bool = False) -> Tuple[MockGeminiClient, MockGmailClient]:
    """
    Set up mock clients for testing the reporting flow
    """
    gemini_client = MockGeminiClient()
    gmail_client = MockGmailClient()

    if with_authentication_failure:
        gmail_client.set_should_fail_authentication(True)

    if with_sending_failure:
        gmail_client.set_should_fail_sending(True)

    return gemini_client, gmail_client


def setup_test_data(gemini_client: MockGeminiClient) -> Dict:
    """
    Set up test data for the reporting flow
    """
    budget = create_test_budget()
    budget_analysis_data = budget.to_dict()

    insights_fixture = load_test_fixture(INSIGHTS_FIXTURE_PATH)
    gemini_client.set_insight_response(insights_fixture)

    return budget_analysis_data


def setup_components(gemini_client: MockGeminiClient, gmail_client: MockGmailClient) -> Tuple[InsightGenerator, ReportDistributor]:
    """
    Set up components needed for testing the reporting flow
    """
    insight_generator = InsightGenerator(gemini_client=gemini_client)
    report_distributor = ReportDistributor(gmail_client=gmail_client, recipients=TEST_EMAIL_RECIPIENTS)
    return insight_generator, report_distributor


def test_reporting_flow_success():
    """
    Test successful execution of the complete reporting flow
    """
    gemini_client, gmail_client = setup_mocks()
    budget_analysis_data = setup_test_data(gemini_client)
    insight_generator, report_distributor = setup_components(gemini_client, gmail_client)

    # Execute InsightGenerator
    insight_result = insight_generator.execute({'budget_analysis': budget_analysis_data, 'correlation_id': 'test_correlation_id'})
    assert insight_result['status'] == 'success'
    report = insight_result['report']

    # Execute ReportDistributor
    report_dist_result = report_distributor.execute({'report': report, 'correlation_id': 'test_correlation_id'})
    assert report_dist_result['status'] == 'success'

    # Verify that email was sent correctly
    assert gmail_client.get_sent_email_count() == 1
    last_email = gmail_client.get_last_sent_email()
    assert last_email['recipients'] == TEST_EMAIL_RECIPIENTS
    assert last_email['sender'] == TEST_EMAIL_SENDER

    # Verify that email content matches expected format
    expected_email_content = load_test_fixture(EMAIL_CONTENT_FIXTURE_PATH)
    assert_email_content_valid(last_email['html_content'], budget_analysis_data)


def test_reporting_flow_with_test_environment():
    """
    Test reporting flow using the TestEnvironment context manager
    """
    with TestEnvironment() as test_env:
        # Set up components using clients from the environment
        insight_generator = InsightGenerator(gemini_client=test_env.get_mock('gemini'))
        report_distributor = ReportDistributor(gmail_client=test_env.get_mock('gmail'), recipients=TEST_EMAIL_RECIPIENTS)

        # Execute InsightGenerator
        budget_analysis_data = setup_test_data(test_env.get_mock('gemini'))
        insight_result = insight_generator.execute({'budget_analysis': budget_analysis_data, 'correlation_id': 'test_correlation_id'})
        assert insight_result['status'] == 'success'
        report = insight_result['report']

        # Execute ReportDistributor
        report_dist_result = report_distributor.execute({'report': report, 'correlation_id': 'test_correlation_id'})
        assert report_dist_result['status'] == 'success'

        # Verify that email was sent correctly
        gmail_client = test_env.get_mock('gmail')
        assert gmail_client.get_sent_email_count() == 1
        last_email = gmail_client.get_last_sent_email()
        assert last_email['recipients'] == TEST_EMAIL_RECIPIENTS

        # Verify that email content matches expected format
        assert_email_content_valid(last_email['html_content'], budget_analysis_data)


@patch('src.backend.components.insight_generator.create_category_comparison_chart')
@patch('src.backend.components.insight_generator.create_budget_overview_chart')
def test_reporting_flow_with_chart_generation(mock_create_budget_overview_chart, mock_create_category_comparison_chart):
    """
    Test reporting flow with actual chart generation
    """
    gemini_client, gmail_client = setup_mocks()
    budget_analysis_data = setup_test_data(gemini_client)

    # Configure patched chart generation functions to return paths to temporary test files
    temp_chart_1 = create_temp_file(suffix=".png")
    temp_chart_2 = create_temp_file(suffix=".png")
    mock_create_category_comparison_chart.return_value = temp_chart_1
    mock_create_budget_overview_chart.return_value = temp_chart_2

    insight_generator, report_distributor = setup_components(gemini_client, gmail_client)

    # Execute InsightGenerator
    insight_result = insight_generator.execute({'budget_analysis': budget_analysis_data, 'correlation_id': 'test_correlation_id'})
    assert insight_result['status'] == 'success'
    report = insight_result['report']

    # Verify that chart generation functions were called
    assert mock_create_category_comparison_chart.called
    assert mock_create_budget_overview_chart.called

    # Execute ReportDistributor
    report_dist_result = report_distributor.execute({'report': report, 'correlation_id': 'test_correlation_id'})
    assert report_dist_result['status'] == 'success'

    # Verify that email was sent with charts attached
    assert gmail_client.get_sent_email_count() == 1
    last_email = gmail_client.get_last_sent_email()
    assert last_email['has_attachments']

    # Verify that email content contains references to charts
    assert "<img src=\"cid:image_0\"" in last_email['html_content']
    assert "<img src=\"cid:image_1\"" in last_email['html_content']

def test_reporting_flow_gemini_authentication_failure():
    """
    Test reporting flow with Gemini API authentication failure
    """
    gemini_client, gmail_client = setup_mocks(with_authentication_failure=True)
    budget_analysis_data = setup_test_data(gemini_client)
    insight_generator, report_distributor = setup_components(gemini_client, gmail_client)

    # Execute InsightGenerator
    insight_result = insight_generator.execute({'budget_analysis': budget_analysis_data, 'correlation_id': 'test_correlation_id'})
    assert insight_result['status'] == 'error'
    assert "Failed to authenticate with Gemini AI API" in insight_result['message']

    # Verify that ReportDistributor was not executed
    assert gmail_client.get_sent_email_count() == 0


def test_reporting_flow_gmail_authentication_failure():
    """
    Test reporting flow with Gmail API authentication failure
    """
    gemini_client, gmail_client = setup_mocks(with_authentication_failure=True)
    budget_analysis_data = setup_test_data(gemini_client)
    insight_generator, report_distributor = setup_components(gemini_client, gmail_client)

    # Execute InsightGenerator
    insight_result = insight_generator.execute({'budget_analysis': budget_analysis_data, 'correlation_id': 'test_correlation_id'})
    assert insight_result['status'] == 'success'
    report = insight_result['report']

    # Execute ReportDistributor
    report_dist_result = report_distributor.execute({'report': report, 'correlation_id': 'test_correlation_id'})
    assert report_dist_result['status'] == 'error'
    assert "Failed to authenticate with Gmail API" in report_dist_result['message']


def test_reporting_flow_email_sending_failure():
    """
    Test reporting flow with email sending failure
    """
    gemini_client, gmail_client = setup_mocks(with_sending_failure=True)
    budget_analysis_data = setup_test_data(gemini_client)
    insight_generator, report_distributor = setup_components(gemini_client, gmail_client)

    # Execute InsightGenerator
    insight_result = insight_generator.execute({'budget_analysis': budget_analysis_data, 'correlation_id': 'test_correlation_id'})
    assert insight_result['status'] == 'success'
    report = insight_result['report']

    # Execute ReportDistributor
    report_dist_result = report_distributor.execute({'report': report, 'correlation_id': 'test_correlation_id'})
    assert report_dist_result['status'] == 'error'
    assert "Failed to send email" in report_dist_result['message']


def test_reporting_flow_with_retry_mechanism():
    """
    Test reporting flow with retry mechanism for transient failures
    """
    gemini_client, gmail_client = setup_mocks()

    # Configure mock clients to fail initially but succeed on retry
    gemini_client.set_failure_mode(True, 'insights')
    gmail_client.set_should_fail_sending(True)

    budget_analysis_data = setup_test_data(gemini_client)
    insight_generator, report_distributor = setup_components(gemini_client, gmail_client)

    # Execute InsightGenerator
    insight_result = insight_generator.execute({'budget_analysis': budget_analysis_data, 'correlation_id': 'test_correlation_id'})
    assert insight_result['status'] == 'success'
    report = insight_result['report']

    # Execute ReportDistributor
    report_dist_result = report_distributor.execute({'report': report, 'correlation_id': 'test_correlation_id'})
    assert report_dist_result['status'] == 'success'

    # Verify that retry mechanisms were triggered appropriately
    assert len(gemini_client.get_call_history('generate_spending_insights')) > 1
    assert len(gmail_client.get_sent_emails()) == 1


def test_reporting_flow_with_budget_surplus():
    """
    Test reporting flow with a budget surplus
    """
    gemini_client, gmail_client = setup_mocks()
    budget_analysis_data = setup_test_data(gemini_client)
    insight_generator, report_distributor = setup_components(gemini_client, gmail_client)

    # Execute InsightGenerator
    insight_result = insight_generator.execute({'budget_analysis': budget_analysis_data, 'correlation_id': 'test_correlation_id'})
    assert insight_result['status'] == 'success'
    report = insight_result['report']

    # Execute ReportDistributor
    report_dist_result = report_distributor.execute({'report': report, 'correlation_id': 'test_correlation_id'})
    assert report_dist_result['status'] == 'success'

    # Verify that email content mentions budget surplus
    last_email = gmail_client.get_last_sent_email()
    assert "under budget" in last_email['html_content']


def test_reporting_flow_with_budget_deficit():
    """
    Test reporting flow with a budget deficit
    """
    gemini_client, gmail_client = setup_mocks()
    budget_analysis_data = setup_test_data(gemini_client)
    insight_generator, report_distributor = setup_components(gemini_client, gmail_client)

    # Execute InsightGenerator
    insight_result = insight_generator.execute({'budget_analysis': budget_analysis_data, 'correlation_id': 'test_correlation_id'})
    assert insight_result['status'] == 'success'
    report = insight_result['report']

    # Execute ReportDistributor
    report_dist_result = report_distributor.execute({'report': report, 'correlation_id': 'test_correlation_id'})
    assert report_dist_result['status'] == 'success'

    # Verify that email content mentions budget deficit
    last_email = gmail_client.get_last_sent_email()
    assert "over budget" in last_email['html_content']