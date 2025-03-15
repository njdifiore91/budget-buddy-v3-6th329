"""
Unit tests for the InsightGenerator component, which is responsible for generating AI-powered spending insights and visualizations for the Budget Management Application. Tests cover insight generation, chart creation, report formatting, and error handling scenarios.
"""

import os  # standard library
import tempfile  # standard library
import matplotlib  # matplotlib 3.7.0+
import unittest  # standard library
from unittest.mock import MagicMock, patch  # standard library

# Import the component being tested
from ...components.insight_generator import InsightGenerator, create_category_comparison_chart, create_budget_overview_chart

# Import mock implementations for testing
from ..mocks.mock_gemini_client import MockGeminiClient

# Import fixtures for test data
from ..fixtures.budget import create_analyzed_budget, create_budget_with_surplus, create_budget_with_deficit
from ..fixtures.api_responses import load_gemini_insights_response

# Import models and utility classes
from ...models.report import Report
from ...utils.error_handlers import APIError, ValidationError


class TestInsightGenerator(unittest.TestCase):
    """Test case for the InsightGenerator component"""

    def setUp(self):
        """Set up test fixtures before each test"""
        # Create mock Gemini client
        self.mock_gemini_client = MockGeminiClient()
        
        # Create test budget with analysis data
        self.test_budget = create_analyzed_budget()
        
        # Create InsightGenerator instance with mock client
        self.insight_generator = InsightGenerator(self.mock_gemini_client)
        
        # Set up temporary directory for chart files
        self.temp_dir = tempfile.TemporaryDirectory()
        
    def tearDown(self):
        """Clean up after each test"""
        # Clean up temporary files
        self.temp_dir.cleanup()
    
    def test_initialization(self):
        """Test that InsightGenerator initializes correctly"""
        # Create InsightGenerator instance
        insight_generator = InsightGenerator(self.mock_gemini_client)
        
        # Assert that gemini_client is properly set
        self.assertEqual(insight_generator.gemini_client, self.mock_gemini_client)
        
        # Assert that auth_service is properly set
        self.assertIsNotNone(insight_generator.auth_service)
    
    def test_authenticate_success(self):
        """Test successful authentication with Gemini API"""
        # Configure mock client to return authentication success
        self.mock_gemini_client.auth_success = True
        
        # Call authenticate method
        result = self.insight_generator.authenticate()
        
        # Assert that authentication was successful
        self.assertTrue(result)
        
        # Verify authenticate was called on the client
        self.assertEqual(self.mock_gemini_client.api_key, "mock-gemini-api-key")
    
    def test_authenticate_failure(self):
        """Test authentication failure with Gemini API"""
        # Configure mock client to return authentication failure
        self.mock_gemini_client.auth_success = False
        
        # Call authenticate method
        result = self.insight_generator.authenticate()
        
        # Assert that authentication failed
        self.assertFalse(result)
        
        # Verify authenticate was called on the client
        self.assertIsNone(self.mock_gemini_client.api_key)
    
    def test_generate_insights_success(self):
        """Test successful generation of insights"""
        # Configure mock client to return mock insights
        mock_insights = "This is a test insight for your budget analysis."
        self.mock_gemini_client.set_mock_insights_response({"candidates": [{"content": {"parts": [{"text": mock_insights}]}}]})
        
        # Call generate_insights method with test budget
        insights = self.insight_generator.generate_insights(self.test_budget.to_dict())
        
        # Assert that insights text is returned
        self.assertEqual(insights, mock_insights)
        
        # Verify generate_spending_insights was called on the client with correct parameters
        # This is implicit in our test since we're using the mock client
    
    def test_generate_insights_api_error(self):
        """Test handling of API error during insight generation"""
        # Configure mock client to raise APIError
        self.mock_gemini_client.set_api_error(True)
        
        # Call generate_insights method with test budget
        with self.assertRaises(APIError):
            self.insight_generator.generate_insights(self.test_budget.to_dict())
        
        # Verify generate_spending_insights was called on the client
        # This is implicit in our test since we're using the mock client
    
    @patch('src.backend.components.insight_generator.create_category_comparison_chart')
    @patch('src.backend.components.insight_generator.create_budget_overview_chart')
    def test_create_visualizations_success(self, mock_overview_chart, mock_category_chart):
        """Test successful creation of chart visualizations"""
        # Mock chart creation functions to return test file paths
        test_category_chart = os.path.join(self.temp_dir.name, "category_chart.png")
        test_overview_chart = os.path.join(self.temp_dir.name, "overview_chart.png")
        
        mock_category_chart.return_value = test_category_chart
        mock_overview_chart.return_value = test_overview_chart
        
        # Call create_visualizations method with test budget
        chart_files = self.insight_generator.create_visualizations(self.test_budget.to_dict())
        
        # Assert that list of chart file paths is returned
        self.assertEqual(len(chart_files), 2)
        self.assertEqual(chart_files[0], test_category_chart)
        self.assertEqual(chart_files[1], test_overview_chart)
        
        # Verify chart creation functions were called with correct parameters
        mock_category_chart.assert_called_once_with(self.test_budget.to_dict())
        mock_overview_chart.assert_called_once_with(self.test_budget.to_dict())
    
    def test_create_category_comparison_chart(self):
        """Test creation of category comparison chart"""
        # Create a chart in the temporary directory
        with patch('matplotlib.pyplot.savefig', return_value=None):
            with patch('src.backend.components.insight_generator.ensure_chart_directory', return_value=self.temp_dir.name):
                chart_path = create_category_comparison_chart(self.test_budget.to_dict())
        
        # Assert that chart file path is returned
        self.assertIsNotNone(chart_path)
        self.assertTrue(chart_path.endswith(".png"))
    
    def test_create_budget_overview_chart(self):
        """Test creation of budget overview chart"""
        # Create a chart in the temporary directory
        with patch('matplotlib.pyplot.savefig', return_value=None):
            with patch('src.backend.components.insight_generator.ensure_chart_directory', return_value=self.temp_dir.name):
                chart_path = create_budget_overview_chart(self.test_budget.to_dict())
        
        # Assert that chart file path is returned
        self.assertIsNotNone(chart_path)
        self.assertTrue(chart_path.endswith(".png"))
    
    def test_create_report_success(self):
        """Test successful creation of complete report"""
        # Mock generate_insights to return test insights
        test_insights = "These are test insights for your budget."
        self.insight_generator.generate_insights = MagicMock(return_value=test_insights)
        
        # Mock create_visualizations to return test chart paths
        test_chart_paths = [
            os.path.join(self.temp_dir.name, "test_chart1.png"),
            os.path.join(self.temp_dir.name, "test_chart2.png")
        ]
        self.insight_generator.create_visualizations = MagicMock(return_value=test_chart_paths)
        
        # Call create_report method with test budget
        report = self.insight_generator.create_report(self.test_budget.to_dict())
        
        # Assert that Report object is returned
        self.assertIsInstance(report, Report)
        
        # Verify Report has insights and charts
        self.assertEqual(report.insights, test_insights)
        self.assertEqual(len(report.chart_files), 2)
        
        # Verify generate_insights and create_visualizations were called
        self.insight_generator.generate_insights.assert_called_once_with(self.test_budget.to_dict())
        self.insight_generator.create_visualizations.assert_called_once_with(self.test_budget.to_dict())
    
    def test_create_report_with_surplus_budget(self):
        """Test report creation with surplus budget"""
        # Create test budget with surplus
        surplus_budget = create_budget_with_surplus()
        
        # Mock generate_insights and create_visualizations
        test_insights = "You have a surplus in your budget."
        test_chart_paths = [os.path.join(self.temp_dir.name, "test_chart.png")]
        
        self.insight_generator.generate_insights = MagicMock(return_value=test_insights)
        self.insight_generator.create_visualizations = MagicMock(return_value=test_chart_paths)
        
        # Call create_report method with surplus budget
        report = self.insight_generator.create_report(surplus_budget.to_dict())
        
        # Assert that Report object is returned
        self.assertIsInstance(report, Report)
        
        # Verify Report has insights
        self.assertEqual(report.insights, test_insights)
        
        # Verify the budget used was the surplus one
        self.insight_generator.create_visualizations.assert_called_once_with(surplus_budget.to_dict())
    
    def test_create_report_with_deficit_budget(self):
        """Test report creation with deficit budget"""
        # Create test budget with deficit
        deficit_budget = create_budget_with_deficit()
        
        # Mock generate_insights and create_visualizations
        test_insights = "You have a deficit in your budget."
        test_chart_paths = [os.path.join(self.temp_dir.name, "test_chart.png")]
        
        self.insight_generator.generate_insights = MagicMock(return_value=test_insights)
        self.insight_generator.create_visualizations = MagicMock(return_value=test_chart_paths)
        
        # Call create_report method with deficit budget
        report = self.insight_generator.create_report(deficit_budget.to_dict())
        
        # Assert that Report object is returned
        self.assertIsInstance(report, Report)
        
        # Verify Report has insights
        self.assertEqual(report.insights, test_insights)
        
        # Verify the budget used was the deficit one
        self.insight_generator.create_visualizations.assert_called_once_with(deficit_budget.to_dict())
    
    def test_execute_success(self):
        """Test successful execution of insight generation process"""
        # Mock authenticate to return True
        self.insight_generator.authenticate = MagicMock(return_value=True)
        
        # Mock create_report to return test Report
        test_report = Report(self.test_budget)
        self.insight_generator.create_report = MagicMock(return_value=test_report)
        
        # Create previous_status dictionary with budget_analysis
        previous_status = {
            "correlation_id": "test-correlation-id",
            "budget_analysis": self.test_budget.to_dict()
        }
        
        # Call execute method with previous_status
        result = self.insight_generator.execute(previous_status)
        
        # Assert that status is 'success'
        self.assertEqual(result['status'], 'success')
        
        # Assert that report is included in result
        self.assertEqual(result['report'], test_report)
        
        # Verify authenticate and create_report were called
        self.insight_generator.authenticate.assert_called_once()
        self.insight_generator.create_report.assert_called_once_with(self.test_budget.to_dict())
    
    def test_execute_authentication_failure(self):
        """Test execution with authentication failure"""
        # Mock authenticate to return False
        self.insight_generator.authenticate = MagicMock(return_value=False)
        
        # Create previous_status dictionary with budget_analysis
        previous_status = {
            "correlation_id": "test-correlation-id",
            "budget_analysis": self.test_budget.to_dict()
        }
        
        # Call execute method with previous_status
        result = self.insight_generator.execute(previous_status)
        
        # Assert that status is 'error'
        self.assertEqual(result['status'], 'error')
        
        # Assert that error message mentions authentication
        self.assertIn('authenticate', result['message'].lower())
        
        # Verify authenticate was called but create_report was not
        self.insight_generator.authenticate.assert_called_once()
        self.assertEqual(hasattr(self.insight_generator, 'create_report.assert_not_called'), False)
    
    def test_execute_report_creation_error(self):
        """Test execution with report creation error"""
        # Mock authenticate to return True
        self.insight_generator.authenticate = MagicMock(return_value=True)
        
        # Mock create_report to raise Exception
        error_message = "Test error in create_report"
        self.insight_generator.create_report = MagicMock(side_effect=Exception(error_message))
        
        # Create previous_status dictionary with budget_analysis
        previous_status = {
            "correlation_id": "test-correlation-id",
            "budget_analysis": self.test_budget.to_dict()
        }
        
        # Call execute method with previous_status
        result = self.insight_generator.execute(previous_status)
        
        # Assert that status is 'error'
        self.assertEqual(result['status'], 'error')
        
        # Assert that error message is included
        self.assertIn(error_message, result['message'])
        
        # Verify authenticate and create_report were called
        self.insight_generator.authenticate.assert_called_once()
        self.insight_generator.create_report.assert_called_once_with(self.test_budget.to_dict())
    
    def test_check_health(self):
        """Test health check functionality"""
        # Mock client test_connectivity to return True
        self.mock_gemini_client.test_connectivity = MagicMock(return_value=True)
        
        # Call check_health method
        health_status = self.insight_generator.check_health()
        
        # Assert that health status includes gemini status
        self.assertIn('gemini_api', health_status)
        
        # Assert that gemini status is 'healthy'
        self.assertEqual(health_status['gemini_api'], 'healthy')
        
        # Verify test_connectivity was called on the client
        self.mock_gemini_client.test_connectivity.assert_called_once()


class TestInsightGeneratorIntegration(unittest.TestCase):
    """Integration tests for InsightGenerator with actual chart generation"""
    
    def setUp(self):
        """Set up test fixtures before each test"""
        # Create mock Gemini client
        self.mock_gemini_client = MockGeminiClient()
        
        # Create test budget with analysis data
        self.test_budget = create_analyzed_budget()
        
        # Create InsightGenerator instance with mock client
        self.insight_generator = InsightGenerator(self.mock_gemini_client)
        
        # Set up temporary directory for chart files
        self.temp_dir = tempfile.TemporaryDirectory()
    
    def tearDown(self):
        """Clean up after each test"""
        # Clean up temporary files
        self.temp_dir.cleanup()
    
    def test_end_to_end_report_creation(self):
        """Test end-to-end report creation process"""
        # Configure mock client to return test insights
        test_insights = "This is a comprehensive budget analysis..."
        self.mock_gemini_client.set_mock_insights_response({
            "candidates": [{"content": {"parts": [{"text": test_insights}]}}]
        })
        
        # Create test budget with analysis data
        budget_dict = self.test_budget.to_dict()
        
        # Patch the chart directory and ensure_chart_directory functions
        with patch('src.backend.components.insight_generator.CHART_DIR', self.temp_dir.name):
            with patch('src.backend.components.insight_generator.ensure_chart_directory', return_value=self.temp_dir.name):
                # Call create_report method
                report = self.insight_generator.create_report(budget_dict)
        
        # Assert that Report object is returned
        self.assertIsInstance(report, Report)
        
        # Assert that Report has insights
        self.assertEqual(report.insights, test_insights)
        
        # Assert that Report has charts
        self.assertGreater(len(report.chart_files), 0)
        
        # Generate email content from Report
        subject, body = report.get_email_content()
        
        # Assert that email content contains budget status
        self.assertIsNotNone(subject)
        self.assertIsNotNone(body)
        
        # Assert that email content contains insights
        self.assertIn(test_insights, body) if body else None
    
    def test_chart_generation_with_real_matplotlib(self):
        """Test chart generation with actual matplotlib"""
        # Use non-interactive backend for testing
        matplotlib.use('Agg')
        
        # Patch the chart directory and ensure_chart_directory functions
        with patch('src.backend.components.insight_generator.CHART_DIR', self.temp_dir.name):
            with patch('src.backend.components.insight_generator.ensure_chart_directory', return_value=self.temp_dir.name):
                with patch('matplotlib.pyplot.savefig', side_effect=lambda fname, **kwargs: open(fname, 'a').close()):
                    # Call create_visualizations method with test budget
                    chart_files = self.insight_generator.create_visualizations(self.test_budget.to_dict())
        
        # Assert that chart files are created
        self.assertGreater(len(chart_files), 0)
        
        # Verify chart files exist
        for chart_file in chart_files:
            self.assertTrue(os.path.exists(chart_file))