import os  # standard library
import tempfile  # standard library
from typing import Dict, List, Any  # standard library
import pytest  # pytest 7.4.0+
from unittest.mock import MagicMock  # standard library

from src.backend.components.insight_generator import InsightGenerator  # src/backend/components/insight_generator.py
from src.backend.models.report import Report, create_report  # src/backend/models/report.py
from src.backend.utils.error_handlers import APIError, ValidationError  # src/backend/utils/error_handlers.py
from src.test.mocks.gemini_client import MockGeminiClient  # src/test/mocks/gemini_client.py
from src.test.utils.test_helpers import load_test_fixture  # src/test/utils/test_helpers.py
from src.test.utils.test_helpers import create_test_budget  # src/test/utils/test_helpers.py
from src.test.utils.assertion_helpers import assert_matches_fixture  # src/test/utils/assertion_helpers.py
from src.test.utils.assertion_helpers import assert_email_content_valid  # src/test/utils/assertion_helpers.py

TEST_BUDGET_ANALYSIS = load_test_fixture('budget/budget_analysis.json')
TEST_INSIGHTS_TEXT = "Weekly Budget Update: You're $45.67 under budget this week!"

def setup_mock_matplotlib():
    """Setup mock for matplotlib to avoid actual chart generation during tests"""
    # Create a MagicMock for matplotlib.pyplot
    pyplot_mock = MagicMock()
    
    # Configure the mock to return a figure mock when figure() is called
    figure_mock = MagicMock()
    pyplot_mock.figure.return_value = figure_mock
    
    # Configure the savefig method to return a fake file path
    figure_mock.savefig.return_value = "fake_chart_path.png"
    
    # Return the configured mock
    return pyplot_mock

def test_insight_generator_init():
    """Test initialization of InsightGenerator component"""
    # Create an instance of InsightGenerator
    insight_generator = InsightGenerator()
    
    # Assert that the instance is created successfully
    assert isinstance(insight_generator, InsightGenerator)
    
    # Assert that the Gemini client is initialized
    assert insight_generator.gemini_client is not None

def test_authenticate_success():
    """Test successful authentication with Gemini API"""
    # Create a mock Gemini client
    gemini_mock = MagicMock()
    gemini_mock.authenticate.return_value = True
    
    # Create an instance of InsightGenerator with the mock Gemini client
    insight_generator = InsightGenerator(gemini_client=gemini_mock)
    
    # Call the authenticate method
    result = insight_generator.authenticate()
    
    # Assert that the authentication was successful
    assert result is True
    
    # Assert that the authenticate method of the mock Gemini client was called
    gemini_mock.authenticate.assert_called_once()

def test_authenticate_failure():
    """Test authentication failure handling"""
    # Create a mock Gemini client
    gemini_mock = MagicMock()
    gemini_mock.authenticate.return_value = False
    
    # Create an instance of InsightGenerator with the mock Gemini client
    insight_generator = InsightGenerator(gemini_client=gemini_mock)
    
    # Call the authenticate method
    result = insight_generator.authenticate()
    
    # Assert that the authentication failed
    assert result is False
    
    # Assert that the authenticate method of the mock Gemini client was called
    gemini_mock.authenticate.assert_called_once()

def test_generate_insights_success():
    """Test successful generation of insights"""
    # Create a mock Gemini client
    gemini_mock = MagicMock()
    gemini_mock.generate_spending_insights.return_value = TEST_INSIGHTS_TEXT
    
    # Create an instance of InsightGenerator with the mock Gemini client
    insight_generator = InsightGenerator(gemini_client=gemini_mock)
    
    # Call the generate_insights method
    insights = insight_generator.generate_insights(TEST_BUDGET_ANALYSIS)
    
    # Assert that the insights were generated successfully
    assert insights == TEST_INSIGHTS_TEXT
    
    # Assert that the generate_spending_insights method of the mock Gemini client was called
    gemini_mock.generate_spending_insights.assert_called_once()

def test_generate_insights_api_error():
    """Test handling of API errors during insight generation"""
    # Create a mock Gemini client
    gemini_mock = MagicMock()
    gemini_mock.generate_spending_insights.side_effect = APIError("Simulated API error", "Gemini", "generate_insights")
    
    # Create an instance of InsightGenerator with the mock Gemini client
    insight_generator = InsightGenerator(gemini_client=gemini_mock)
    
    # Call the generate_insights method and assert that it raises an APIError
    with pytest.raises(APIError):
        insight_generator.generate_insights(TEST_BUDGET_ANALYSIS)
    
    # Assert that the generate_spending_insights method of the mock Gemini client was called
    gemini_mock.generate_spending_insights.assert_called_once()

def test_create_category_comparison_chart(monkeypatch):
    """Test creation of category comparison chart"""
    # Mock matplotlib.pyplot
    pyplot_mock = setup_mock_matplotlib()
    monkeypatch.setattr("src.backend.components.insight_generator.plt", pyplot_mock)
    
    # Call the create_category_comparison_chart function
    chart_path = InsightGenerator.create_category_comparison_chart(TEST_BUDGET_ANALYSIS)
    
    # Assert that the chart path is a string
    assert isinstance(chart_path, str)
    
    # Assert that the chart was saved
    assert pyplot_mock.figure.return_value.savefig.called

def test_create_budget_overview_chart(monkeypatch):
    """Test creation of budget overview chart"""
    # Mock matplotlib.pyplot
    pyplot_mock = setup_mock_matplotlib()
    monkeypatch.setattr("src.backend.components.insight_generator.plt", pyplot_mock)
    
    # Call the create_budget_overview_chart function
    chart_path = InsightGenerator.create_budget_overview_chart(TEST_BUDGET_ANALYSIS)
    
    # Assert that the chart path is a string
    assert isinstance(chart_path, str)
    
    # Assert that the chart was saved
    assert pyplot_mock.figure.return_value.savefig.called

def test_create_visualizations(monkeypatch):
    """Test creation of all visualizations"""
    # Mock matplotlib.pyplot
    pyplot_mock = setup_mock_matplotlib()
    monkeypatch.setattr("src.backend.components.insight_generator.plt", pyplot_mock)
    
    # Create an instance of InsightGenerator
    insight_generator = InsightGenerator()
    
    # Call the create_visualizations method
    chart_files = insight_generator.create_visualizations(TEST_BUDGET_ANALYSIS)
    
    # Assert that the chart files is a list
    assert isinstance(chart_files, list)
    
    # Assert that the list contains two chart files
    assert len(chart_files) == 2

def test_create_report():
    """Test creation of complete report with insights and charts"""
    # Create a mock Gemini client
    gemini_mock = MagicMock()
    gemini_mock.generate_spending_insights.return_value = TEST_INSIGHTS_TEXT
    
    # Create an instance of InsightGenerator with the mock Gemini client
    insight_generator = InsightGenerator(gemini_client=gemini_mock)
    
    # Call the create_report method
    report = insight_generator.create_report(TEST_BUDGET_ANALYSIS)
    
    # Assert that the report is an instance of Report
    assert isinstance(report, Report)
    
    # Assert that the report has insights
    assert report.insights == TEST_INSIGHTS_TEXT
    
    # Assert that the report has charts
    assert len(report.chart_files) == 2

def test_execute_success():
    """Test successful execution of the insight generation process"""
    # Create a mock Gemini client
    gemini_mock = MagicMock()
    gemini_mock.authenticate.return_value = True
    gemini_mock.generate_spending_insights.return_value = TEST_INSIGHTS_TEXT
    
    # Create an instance of InsightGenerator with the mock Gemini client
    insight_generator = InsightGenerator(gemini_client=gemini_mock)
    
    # Call the execute method
    previous_status = {'budget_analysis': TEST_BUDGET_ANALYSIS, 'correlation_id': 'test_correlation_id'}
    result = insight_generator.execute(previous_status)
    
    # Assert that the execution was successful
    assert result['status'] == 'success'
    
    # Assert that the report is in the result
    assert 'report' in result
    
    # Assert that the correlation ID is in the result
    assert result['correlation_id'] == 'test_correlation_id'
    
    # Assert that the component is in the result
    assert result['component'] == 'insight_generator'

def test_execute_authentication_failure():
    """Test execution with authentication failure"""
    # Create a mock Gemini client
    gemini_mock = MagicMock()
    gemini_mock.authenticate.return_value = False
    
    # Create an instance of InsightGenerator with the mock Gemini client
    insight_generator = InsightGenerator(gemini_client=gemini_mock)
    
    # Call the execute method
    previous_status = {'budget_analysis': TEST_BUDGET_ANALYSIS, 'correlation_id': 'test_correlation_id'}
    result = insight_generator.execute(previous_status)
    
    # Assert that the execution failed
    assert result['status'] == 'error'
    
    # Assert that the message is correct
    assert result['message'] == 'Failed to authenticate with Gemini AI API'
    
    # Assert that the correlation ID is in the result
    assert result['correlation_id'] == 'test_correlation_id'
    
    # Assert that the component is in the result
    assert result['component'] == 'insight_generator'

def test_execute_insight_generation_error():
    """Test execution with insight generation error"""
    # Create a mock Gemini client
    gemini_mock = MagicMock()
    gemini_mock.authenticate.return_value = True
    gemini_mock.generate_spending_insights.side_effect = APIError("Simulated API error", "Gemini", "generate_insights")
    
    # Create an instance of InsightGenerator with the mock Gemini client
    insight_generator = InsightGenerator(gemini_client=gemini_mock)
    
    # Call the execute method
    previous_status = {'budget_analysis': TEST_BUDGET_ANALYSIS, 'correlation_id': 'test_correlation_id'}
    result = insight_generator.execute(previous_status)
    
    # Assert that the execution failed
    assert result['status'] == 'error'
    
    # Assert that the message is correct
    assert result['message'] == 'Insight generation failed: Simulated API error'
    
    # Assert that the correlation ID is in the result
    assert result['correlation_id'] == 'test_correlation_id'
    
    # Assert that the component is in the result
    assert result['component'] == 'insight_generator'

def test_execute_visualization_error():
    """Test execution with visualization error"""
    # Create a mock Gemini client
    gemini_mock = MagicMock()
    gemini_mock.authenticate.return_value = True
    gemini_mock.generate_spending_insights.return_value = TEST_INSIGHTS_TEXT
    
    # Create an instance of InsightGenerator with the mock Gemini client
    insight_generator = InsightGenerator(gemini_client=gemini_mock)
    
    # Mock the create_visualizations method to raise an exception
    insight_generator.create_visualizations = MagicMock(side_effect=Exception("Simulated visualization error"))
    
    # Call the execute method
    previous_status = {'budget_analysis': TEST_BUDGET_ANALYSIS, 'correlation_id': 'test_correlation_id'}
    result = insight_generator.execute(previous_status)
    
    # Assert that the execution failed
    assert result['status'] == 'error'
    
    # Assert that the message is correct
    assert result['message'] == "Insight generation failed: Simulated visualization error"
    
    # Assert that the correlation ID is in the result
    assert result['correlation_id'] == 'test_correlation_id'
    
    # Assert that the component is in the result
    assert result['component'] == 'insight_generator'

def test_check_health():
    """Test health check functionality"""
    # Create a mock Gemini client
    gemini_mock = MagicMock()
    gemini_mock.authenticate.return_value = True
    
    # Create an instance of InsightGenerator with the mock Gemini client
    insight_generator = InsightGenerator(gemini_client=gemini_mock)
    
    # Call the check_health method
    health_status = insight_generator.check_health()
    
    # Assert that the health status is a dictionary
    assert isinstance(health_status, dict)
    
    # Assert that the Gemini API health status is healthy
    assert health_status['gemini_api'] == 'healthy'
    
    # Assert that the authenticate method of the mock Gemini client was called
    gemini_mock.authenticate.assert_called_once()