import pytest  # pytest 7.4.0+
import os  # standard library
from typing import Dict, List, Tuple  # standard library
from src.backend.components.insight_generator import InsightGenerator  # src/backend/components/insight_generator.py
from src.backend.components.report_distributor import ReportDistributor  # src/backend/components/report_distributor.py
from src.backend.models.report import Report  # src/backend/models/report.py
from src.backend.tests.mocks.mock_gemini_client import MockGeminiClient  # src/backend/tests/mocks/mock_gemini_client.py
from src.backend/tests/mocks/mock_gmail_client import MockGmailClient  # src/backend/tests/mocks/mock_gmail_client.py
from src.backend/tests/conftest import analyzed_budget  # src/backend/tests/conftest.py
from src.backend/tests/conftest import budget_with_surplus  # src/backend/tests/conftest.py
from src.backend/tests/conftest import budget_with_deficit  # src/backend/tests/conftest.py

TEST_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fixtures', 'data')


def setup_insight_generator(auth_success: bool = True, api_error: bool = False) -> Tuple[InsightGenerator, MockGeminiClient]:
    """Helper function to set up an InsightGenerator with mock dependencies"""
    mock_client = MockGeminiClient(auth_success=auth_success, api_error=api_error)
    generator = InsightGenerator(gemini_client=mock_client)
    return generator, mock_client


def setup_report_distributor(auth_success: bool = True, api_error: bool = False) -> Tuple[ReportDistributor, MockGmailClient]:
    """Helper function to set up a ReportDistributor with mock dependencies"""
    mock_client = MockGmailClient(auth_success=auth_success, api_error=api_error)
    distributor = ReportDistributor(gmail_client=mock_client)
    return distributor, mock_client


class TestInsightGenerator:
    """Test suite for the InsightGenerator component"""

    def __init__(self):
        """Initialize the test suite"""
        pass

    def test_generate_insights_success(self, analyzed_budget):
        """Test successful generation of insights from budget analysis"""
        generator, mock_client = setup_insight_generator()
        result = generator.execute(previous_status={'budget_analysis': analyzed_budget})
        assert result['status'] == 'success'
        assert 'report' in result
        assert result['report'].is_complete()
        assert result['report'].insights is not None and len(result['report'].chart_files) > 0

    def test_generate_insights_with_surplus(self, budget_with_surplus):
        """Test insight generation with a budget surplus"""
        generator, mock_client = setup_insight_generator()
        result = generator.execute(previous_status={'budget_analysis': budget_with_surplus})
        assert result['status'] == 'success'
        assert 'report' in result
        assert result['report'].is_complete()
        assert "under budget" in result['report'].insights

    def test_generate_insights_with_deficit(self, budget_with_deficit):
        """Test insight generation with a budget deficit"""
        generator, mock_client = setup_insight_generator()
        result = generator.execute(previous_status={'budget_analysis': budget_with_deficit})
        assert result['status'] == 'success'
        assert 'report' in result
        assert result['report'].is_complete()
        assert "over budget" in result['report'].insights

    def test_generate_insights_authentication_failure(self, analyzed_budget):
        """Test handling of authentication failure during insight generation"""
        generator, mock_client = setup_insight_generator(auth_success=False)
        result = generator.execute(previous_status={'budget_analysis': analyzed_budget})
        assert result['status'] == 'error'
        assert "Failed to authenticate" in result['message']

    def test_generate_insights_api_error(self, analyzed_budget):
        """Test handling of API error during insight generation"""
        generator, mock_client = setup_insight_generator(api_error=True)
        result = generator.execute(previous_status={'budget_analysis': analyzed_budget})
        assert result['status'] == 'error'
        assert "Insight generation failed" in result['message']


class TestReportDistributor:
    """Test suite for the ReportDistributor component"""

    def __init__(self):
        """Initialize the test suite"""
        pass

    def test_send_report_success(self, analyzed_budget):
        """Test successful sending of a report via email"""
        generator, mock_gemini = setup_insight_generator()
        report_result = generator.execute(previous_status={'budget_analysis': analyzed_budget})
        report = report_result['report']
        distributor, mock_gmail = setup_report_distributor()
        result = distributor.execute(previous_status={'report': report})
        assert result['status'] == 'success'
        assert 'delivery_status' in result
        assert mock_gmail.sent_email_count == 1
        sent_email = mock_gmail.sent_emails[0]
        assert sent_email['subject'] == report.email_subject
        assert sent_email['html_content'] == report.email_body

    def test_send_report_with_surplus(self, budget_with_surplus):
        """Test sending a report with budget surplus"""
        generator, mock_gemini = setup_insight_generator()
        report_result = generator.execute(previous_status={'budget_analysis': budget_with_surplus})
        report = report_result['report']
        distributor, mock_gmail = setup_report_distributor()
        result = distributor.execute(previous_status={'report': report})
        assert result['status'] == 'success'
        sent_email = mock_gmail.sent_emails[0]
        assert "under budget" in sent_email['subject']
        assert "under budget" in sent_email['html_content']

    def test_send_report_with_deficit(self, budget_with_deficit):
        """Test sending a report with budget deficit"""
        generator, mock_gemini = setup_insight_generator()
        report_result = generator.execute(previous_status={'budget_analysis': budget_with_deficit})
        report = report_result['report']
        distributor, mock_gmail = setup_report_distributor()
        result = distributor.execute(previous_status={'report': report})
        assert result['status'] == 'success'
        sent_email = mock_gmail.sent_emails[0]
        assert "over budget" in sent_email['subject']
        assert "over budget" in sent_email['html_content']

    def test_send_report_authentication_failure(self, analyzed_budget):
        """Test handling of authentication failure during report sending"""
        generator, mock_gemini = setup_insight_generator()
        report_result = generator.execute(previous_status={'budget_analysis': analyzed_budget})
        report = report_result['report']
        distributor, mock_gmail = setup_report_distributor(auth_success=False)
        result = distributor.execute(previous_status={'report': report})
        assert result['status'] == 'error'
        assert "Failed to authenticate" in result['message']
        assert mock_gmail.sent_email_count == 0

    def test_send_report_api_error(self, analyzed_budget):
        """Test handling of API error during report sending"""
        generator, mock_gemini = setup_insight_generator()
        report_result = generator.execute(previous_status={'budget_analysis': analyzed_budget})
        report = report_result['report']
        distributor, mock_gmail = setup_report_distributor(api_error=True)
        result = distributor.execute(previous_status={'report': report})
        assert result['status'] == 'error'
        assert "Failed to send email" in result['message']
        assert mock_gmail.sent_email_count == 0


class TestReportingFlow:
    """Test suite for the end-to-end reporting flow"""

    def __init__(self):
        """Initialize the test suite"""
        pass

    def test_end_to_end_reporting_flow(self, analyzed_budget):
        """Test the complete reporting flow from insight generation to email delivery"""
        generator, mock_gemini = setup_insight_generator()
        distributor, mock_gmail = setup_report_distributor()
        insight_result = generator.execute(previous_status={'budget_analysis': analyzed_budget})
        assert insight_result['status'] == 'success'
        report = insight_result['report']
        result = distributor.execute(previous_status={'report': report})
        assert result['status'] == 'success'
        assert mock_gmail.sent_email_count == 1
        sent_email = mock_gmail.sent_emails[0]
        assert sent_email['html_content'] == report.email_body
        assert sent_email['recipients'] == distributor.recipients

    def test_reporting_flow_with_surplus(self, budget_with_surplus):
        """Test the complete reporting flow with a budget surplus"""
        generator, mock_gemini = setup_insight_generator()
        distributor, mock_gmail = setup_report_distributor()
        insight_result = generator.execute(previous_status={'budget_analysis': budget_with_surplus})
        assert insight_result['status'] == 'success'
        report = insight_result['report']
        result = distributor.execute(previous_status={'report': report})
        assert result['status'] == 'success'
        sent_email = mock_gmail.sent_emails[0]
        assert "under budget" in sent_email['subject']
        assert "under budget" in sent_email['html_content']

    def test_reporting_flow_with_deficit(self, budget_with_deficit):
        """Test the complete reporting flow with a budget deficit"""
        generator, mock_gemini = setup_insight_generator()
        distributor, mock_gmail = setup_report_distributor()
        insight_result = generator.execute(previous_status={'budget_analysis': budget_with_deficit})
        assert insight_result['status'] == 'success'
        report = insight_result['report']
        result = distributor.execute(previous_status={'report': report})
        assert result['status'] == 'success'
        sent_email = mock_gmail.sent_emails[0]
        assert "over budget" in sent_email['subject']
        assert "over budget" in sent_email['html_content']

    def test_reporting_flow_insight_generation_failure(self, analyzed_budget):
        """Test handling of insight generation failure in the reporting flow"""
        generator, mock_gemini = setup_insight_generator(api_error=True)
        distributor, mock_gmail = setup_report_distributor()
        insight_result = generator.execute(previous_status={'budget_analysis': analyzed_budget})
        assert insight_result['status'] == 'error'
        assert mock_gmail.sent_email_count == 0

    def test_reporting_flow_email_delivery_failure(self, analyzed_budget):
        """Test handling of email delivery failure in the reporting flow"""
        generator, mock_gemini = setup_insight_generator()
        distributor, mock_gmail = setup_report_distributor(api_error=True)
        insight_result = generator.execute(previous_status={'budget_analysis': analyzed_budget})
        assert insight_result['status'] == 'success'
        report = insight_result['report']
        result = distributor.execute(previous_status={'report': report})
        assert result['status'] == 'error'
        assert mock_gmail.sent_email_count == 0