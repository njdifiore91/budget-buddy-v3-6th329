import pytest  # pytest 7.4.0+
import os  # standard library
from typing import Dict, List, Any  # standard library

from src.backend.components.insight_generator import InsightGenerator  # src/backend/components/insight_generator.py
from src.backend.models.report import Report  # src/backend/models/report.py
from src.test.mocks.gemini_client import MockGeminiClient  # src/test/mocks/gemini_client.py
from src.test.mocks.google_sheets_client import MockGoogleSheetsClient  # src/test/mocks/google_sheets_client.py
from src.test.utils.fixture_loader import load_fixture, load_api_response_fixture, load_expected_result_fixture  # src/test/utils/fixture_loader.py

TEST_FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fixtures')


@pytest.fixture
def setup_mock_gemini_client() -> MockGeminiClient:
    """Set up a mock Gemini client with predefined responses"""
    mock_gemini_client = MockGeminiClient()
    insight_response = load_api_response_fixture('gemini', 'insights')
    mock_gemini_client.set_insight_response(insight_response)
    return mock_gemini_client


@pytest.fixture
def setup_mock_sheets_client() -> MockGoogleSheetsClient:
    """Set up a mock Google Sheets client with test data"""
    mock_sheets_client = MockGoogleSheetsClient()
    budget_data = load_fixture('budget/budget_data')
    mock_sheets_client.set_sheet_data('Master Budget', budget_data)
    transaction_data = load_fixture('transactions/transactions')
    mock_sheets_client.set_sheet_data('Weekly Spending', transaction_data)
    return mock_sheets_client


@pytest.fixture
def setup_budget_analysis() -> Dict[str, Any]:
    """Set up test budget analysis data"""
    budget_analysis = load_fixture('budget/budget_analysis')
    return budget_analysis


@pytest.fixture
def setup_insight_generator(mock_gemini_client: MockGeminiClient) -> InsightGenerator:
    """Set up an InsightGenerator instance with mock dependencies"""
    insight_generator = InsightGenerator(gemini_client=mock_gemini_client)
    return insight_generator


@pytest.mark.integration
def test_generate_insights(insight_generator: InsightGenerator, budget_analysis: Dict[str, Any]) -> None:
    """Test that insights are generated correctly from budget analysis data"""
    insights = insight_generator.generate_insights(budget_analysis)
    assert insights is not None
    assert isinstance(insights, str)
    assert len(insights) > 0
    assert "Weekly Budget Update" in insights
    mock_gemini_client_calls = insight_generator.gemini_client.get_call_history('generate_completion')
    assert len(mock_gemini_client_calls) == 1


@pytest.mark.integration
def test_create_visualizations(insight_generator: InsightGenerator, budget_analysis: Dict[str, Any]) -> None:
    """Test that visualizations are created correctly from budget analysis data"""
    chart_files = insight_generator.create_visualizations(budget_analysis)
    assert isinstance(chart_files, list)
    assert len(chart_files) >= 2
    for chart_file in chart_files:
        assert os.path.exists(chart_file)
        assert "category_comparison" in chart_file or "budget_overview" in chart_file
    # Clean up generated chart files after test
    for chart_file in chart_files:
        os.remove(chart_file)


@pytest.mark.integration
def test_create_report(insight_generator: InsightGenerator, budget_analysis: Dict[str, Any]) -> None:
    """Test that a complete report is created with insights and visualizations"""
    report = insight_generator.create_report(budget_analysis)
    assert isinstance(report, Report)
    assert report.is_complete() is True
    email_body = report.generate_email_body()
    assert isinstance(email_body, str)
    assert len(email_body) > 0
    assert "<img src=" in email_body
    mock_gemini_client_calls = insight_generator.gemini_client.get_call_history('generate_completion')
    assert len(mock_gemini_client_calls) == 1


@pytest.mark.integration
def test_execute_flow(insight_generator: InsightGenerator, budget_analysis: Dict[str, Any]) -> None:
    """Test the complete insight generation flow from execution to report creation"""
    previous_status = {
        'budget_analysis': budget_analysis,
        'correlation_id': 'test_correlation_id'
    }
    result = insight_generator.execute(previous_status)
    assert result['status'] == 'success'
    assert 'report' in result
    assert result['report'].is_complete() is True
    assert 'execution_time' in result
    assert 'correlation_id' in result
    mock_gemini_client_calls = insight_generator.gemini_client.get_call_history('generate_completion')
    assert len(mock_gemini_client_calls) == 1


@pytest.mark.integration
def test_error_handling(mock_gemini_client: MockGeminiClient, budget_analysis: Dict[str, Any]) -> None:
    """Test error handling in the insight generation flow"""
    mock_gemini_client.set_failure_mode(True, 'insights')
    insight_generator = InsightGenerator(gemini_client=mock_gemini_client)
    previous_status = {
        'budget_analysis': budget_analysis,
        'correlation_id': 'test_correlation_id'
    }
    result = insight_generator.execute(previous_status)
    assert result['status'] == 'error'
    assert 'message' in result
    assert "Simulated insights generation failure" in result['message']