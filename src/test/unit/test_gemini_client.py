"""
test_gemini_client.py - Unit tests for the GeminiClient class

This module contains comprehensive tests for the GeminiClient class, which handles
interactions with Google's Gemini AI API for transaction categorization and
spending insight generation in the Budget Management Application.
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
import json
import requests

from src.backend.api_clients.gemini_client import GeminiClient
from src.backend.utils.error_handlers import APIError, ValidationError
from src.backend.services.authentication_service import AuthenticationService
from src.test.utils.fixture_loader import load_fixture, load_api_response_fixture
from src.test.mocks.gemini_client import MockGeminiClient
from src.test.contracts.gemini_contract import (
    GeminiClientProtocol,
    EXAMPLE_CATEGORIZATION_RESPONSE,
    EXAMPLE_INSIGHT_RESPONSE
)


def setup_gemini_client(mock_auth_service=None, auth_success=True):
    """
    Helper function to set up a GeminiClient instance with mocked dependencies
    
    Args:
        mock_auth_service: Mock authentication service
        auth_success: Whether authentication should succeed
        
    Returns:
        GeminiClient: Configured client for testing
    """
    if mock_auth_service is None:
        mock_auth_service = MagicMock(spec=AuthenticationService)
    
    # Configure mock authentication service
    if auth_success:
        mock_auth_service.authenticate_gemini.return_value = {"api_key": "test_api_key"}
        mock_auth_service.get_token.return_value = "test_api_key"
    else:
        mock_auth_service.authenticate_gemini.return_value = {}
        mock_auth_service.get_token.return_value = None
    
    # Create and return the client
    return GeminiClient(auth_service=mock_auth_service)


class TestGeminiClient:
    """
    Test suite for the GeminiClient class
    """
    
    def test_init(self):
        """Test that GeminiClient initializes correctly"""
        mock_auth_service = MagicMock(spec=AuthenticationService)
        client = GeminiClient(auth_service=mock_auth_service)
        
        assert client.auth_service == mock_auth_service
        assert client.api_key is None
        assert hasattr(client, 'api_url')
        assert hasattr(client, 'model')
    
    def test_authenticate_success(self):
        """Test successful authentication with Gemini API"""
        client = setup_gemini_client(auth_success=True)
        
        result = client.authenticate()
        
        assert result is True
        assert client.api_key == "test_api_key"
        client.auth_service.authenticate_gemini.assert_called_once()
    
    def test_authenticate_failure(self):
        """Test authentication failure with Gemini API"""
        client = setup_gemini_client(auth_success=False)
        
        result = client.authenticate()
        
        assert result is False
        assert client.api_key is None
        client.auth_service.authenticate_gemini.assert_called_once()
    
    @patch('requests.post')
    def test_generate_completion_success(self, mock_post):
        """Test successful generation of completions from Gemini AI"""
        # Setup
        client = setup_gemini_client(auth_success=True)
        client.api_key = "test_api_key"  # Ensure API key is set
        
        # Configure mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": "Generated text from Gemini"
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # Call the function
        result = client.generate_completion("Test prompt")
        
        # Verify the result
        assert result == "Generated text from Gemini"
        mock_post.assert_called_once()
        
        # Verify the API was called correctly
        args, kwargs = mock_post.call_args
        url = args[0]  # URL is first positional argument
        assert "generateContent" in url
        assert client.model in url
        assert "Content-Type" in kwargs['headers']
        assert "application/json" == kwargs['headers']["Content-Type"]
        assert "key" in kwargs['params']
        assert "test_api_key" == kwargs['params']["key"]
        assert "prompt" in str(kwargs['json'])
    
    def test_generate_completion_not_authenticated(self):
        """Test generate_completion when client is not authenticated"""
        client = setup_gemini_client(auth_success=False)
        
        # Ensure authentication fails
        client.authenticate()
        
        # Call should raise APIError
        with pytest.raises(APIError) as excinfo:
            client.generate_completion("Test prompt")
        
        assert "Not authenticated with Gemini API" in str(excinfo.value)
    
    @patch('requests.post')
    def test_generate_completion_api_error(self, mock_post):
        """Test handling of API errors in generate_completion"""
        # Setup
        client = setup_gemini_client(auth_success=True)
        
        # Configure mock to raise exception
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = requests.HTTPError("API Error")
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        # Call should raise APIError
        with pytest.raises(APIError) as excinfo:
            client.generate_completion("Test prompt")
        
        assert "Gemini API request failed" in str(excinfo.value)
        assert mock_post.called
    
    @patch('requests.post')
    def test_generate_completion_with_retry(self, mock_post):
        """Test retry mechanism for transient failures"""
        # Setup
        client = setup_gemini_client(auth_success=True)
        
        # Configure mock to fail once, then succeed
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": "Generated text after retry"
                            }
                        ]
                    }
                }
            ]
        }
        
        # First call raises exception, second call succeeds
        mock_post.side_effect = [
            requests.RequestException("Temporary failure"),
            mock_success_response
        ]
        
        # Call the function
        result = client.generate_completion("Test prompt")
        
        # Verify the result
        assert result == "Generated text after retry"
        assert mock_post.call_count == 2
    
    def test_categorize_transactions_success(self):
        """Test successful categorization of transactions"""
        # Setup
        client = setup_gemini_client(auth_success=True)
        
        # Mock the generate_completion method
        client.generate_completion = MagicMock()
        client.generate_completion.return_value = """
        Location: Grocery Store -> Category: Groceries
        Location: Gas Station -> Category: Transportation
        Location: Restaurant -> Category: Dining Out
        """
        
        # Sample data
        transaction_locations = ["Grocery Store", "Gas Station", "Restaurant"]
        budget_categories = ["Groceries", "Transportation", "Dining Out", "Shopping"]
        
        # Call the function
        result = client.categorize_transactions(transaction_locations, budget_categories)
        
        # Verify the result
        assert "Grocery Store" in result
        assert result["Grocery Store"] == "Groceries"
        assert "Gas Station" in result
        assert result["Gas Station"] == "Transportation"
        assert "Restaurant" in result
        assert result["Restaurant"] == "Dining Out"
        
        # Verify the prompt included the transaction locations and categories
        prompt_arg = client.generate_completion.call_args[0][0]
        assert "Grocery Store" in prompt_arg
        assert "Gas Station" in prompt_arg
        assert "Restaurant" in prompt_arg
        assert "Groceries" in prompt_arg
        assert "Transportation" in prompt_arg
        assert "Dining Out" in prompt_arg
    
    def test_categorize_transactions_validation_error(self):
        """Test validation error handling in categorize_transactions"""
        client = setup_gemini_client(auth_success=True)
        
        # Call should raise ValidationError if empty lists are provided
        with pytest.raises(ValidationError) as excinfo:
            client.categorize_transactions([], ["Groceries"])
        
        assert "No transaction locations provided" in str(excinfo.value)
        
        with pytest.raises(ValidationError) as excinfo:
            client.categorize_transactions(["Grocery Store"], [])
        
        assert "No budget categories provided" in str(excinfo.value)
    
    def test_parse_categorization_response(self):
        """Test parsing of categorization response text"""
        client = setup_gemini_client(auth_success=True)
        
        # Sample response text
        response_text = """
        Location: Grocery Store -> Category: Groceries
        Location: Gas Station -> Category: Transportation
        Location: Restaurant -> Category: Dining Out
        """
        
        valid_categories = ["Groceries", "Transportation", "Dining Out", "Shopping"]
        
        # Call the function
        result = client.parse_categorization_response(response_text, valid_categories)
        
        # Verify the result
        assert len(result) == 3
        assert result["Grocery Store"] == "Groceries"
        assert result["Gas Station"] == "Transportation"
        assert result["Restaurant"] == "Dining Out"
    
    def test_parse_categorization_response_invalid_category(self):
        """Test parsing response with invalid categories"""
        client = setup_gemini_client(auth_success=True)
        
        # Sample response text with an invalid category
        response_text = """
        Location: Grocery Store -> Category: Groceries
        Location: Gas Station -> Category: Transportation
        Location: Restaurant -> Category: Invalid Category
        """
        
        valid_categories = ["Groceries", "Transportation", "Dining Out", "Shopping"]
        
        # Call the function
        result = client.parse_categorization_response(response_text, valid_categories)
        
        # Verify the result - should only include valid categories
        assert len(result) == 2
        assert result["Grocery Store"] == "Groceries"
        assert result["Gas Station"] == "Transportation"
        assert "Restaurant" not in result
    
    def test_generate_spending_insights_success(self):
        """Test successful generation of spending insights"""
        # Setup
        client = setup_gemini_client(auth_success=True)
        
        # Mock the generate_completion method
        client.generate_completion = MagicMock()
        client.generate_completion.return_value = "Generated spending insights"
        
        # Sample budget analysis
        budget_analysis = {
            "total_budget": 1000.0,
            "total_spent": 800.0,
            "total_variance": 200.0,
            "category_variances": [
                {
                    "category": "Groceries",
                    "budget_amount": 200.0,
                    "actual_amount": 180.0,
                    "variance_amount": 20.0,
                    "variance_percentage": 10.0
                }
            ]
        }
        
        # Call the function
        result = client.generate_spending_insights(budget_analysis)
        
        # Verify the result
        assert result == "Generated spending insights"
        
        # Verify the prompt included budget analysis data
        prompt_arg = client.generate_completion.call_args[0][0]
        assert "total_budget" in prompt_arg.lower()
        assert "total_spent" in prompt_arg.lower()
        assert "Groceries" in prompt_arg
    
    def test_generate_spending_insights_validation_error(self):
        """Test validation error handling in generate_spending_insights"""
        client = setup_gemini_client(auth_success=True)
        
        # Call should raise ValidationError if empty budget analysis is provided
        with pytest.raises(ValidationError) as excinfo:
            client.generate_spending_insights({})
        
        assert "No budget analysis data provided" in str(excinfo.value)
        
        # Call should raise ValidationError if budget analysis is missing required fields
        with pytest.raises(ValidationError) as excinfo:
            client.generate_spending_insights({"total_budget": 1000.0})
        
        assert "budget analysis" in str(excinfo.value).lower()
    
    def test_validate_api_response(self):
        """Test validation of API responses"""
        client = setup_gemini_client(auth_success=True)
        
        # Valid response
        valid_response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": "Valid response text"
                            }
                        ]
                    }
                }
            ]
        }
        
        # Invalid response (missing parts)
        invalid_response = {
            "candidates": [
                {
                    "content": {}
                }
            ]
        }
        
        # Verify validation results
        assert client.validate_api_response(valid_response) is True
        assert client.validate_api_response(invalid_response) is False
    
    def test_extract_generated_text(self):
        """Test extraction of generated text from API response"""
        client = setup_gemini_client(auth_success=True)
        
        # Valid response
        valid_response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": "Generated text"
                            }
                        ]
                    }
                }
            ]
        }
        
        # Invalid response (missing parts)
        invalid_response = {
            "candidates": [
                {
                    "content": {}
                }
            ]
        }
        
        # Verify extraction results
        assert client.extract_generated_text(valid_response) == "Generated text"
        
        # Should raise APIError for invalid response
        with pytest.raises(APIError) as excinfo:
            client.extract_generated_text(invalid_response)
        
        assert "Failed to extract text" in str(excinfo.value)
    
    @patch('src.backend.api_clients.gemini_client.load_prompt_template')
    def test_format_prompt(self, mock_load_template):
        """Test formatting of prompt templates"""
        client = setup_gemini_client(auth_success=True)
        
        # Mock the template loading
        mock_load_template.return_value = "Template with {variable1} and {variable2}"
        
        # Call the function
        result = client.format_prompt("template_name", {
            "variable1": "value1",
            "variable2": "value2"
        })
        
        # Verify the result
        assert result == "Template with value1 and value2"
        mock_load_template.assert_called_once_with("template_name")


class TestGeminiClientIntegration:
    """
    Integration tests for GeminiClient with mocked external dependencies
    """
    
    @patch('requests.post')
    def test_end_to_end_categorization(self, mock_post):
        """Test the complete transaction categorization flow"""
        # Setup
        mock_auth_service = MagicMock(spec=AuthenticationService)
        mock_auth_service.authenticate_gemini.return_value = {"api_key": "test_api_key"}
        
        client = GeminiClient(auth_service=mock_auth_service)
        
        # Configure mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": """
                                Location: Grocery Store -> Category: Groceries
                                Location: Gas Station -> Category: Transportation
                                Location: Restaurant -> Category: Dining Out
                                """
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # Sample data
        transaction_locations = ["Grocery Store", "Gas Station", "Restaurant"]
        budget_categories = ["Groceries", "Transportation", "Dining Out", "Shopping"]
        
        # Authenticate
        client.authenticate()
        
        # Call the categorize_transactions function
        result = client.categorize_transactions(transaction_locations, budget_categories)
        
        # Verify the result
        assert len(result) == 3
        assert result["Grocery Store"] == "Groceries"
        assert result["Gas Station"] == "Transportation"
        assert result["Restaurant"] == "Dining Out"
        
        # Verify the API was called
        assert mock_post.called
        args, kwargs = mock_post.call_args
        assert "generateContent" in args[0]
        assert "Content-Type" in kwargs['headers']
        assert "test_api_key" == kwargs['params']["key"]
    
    @patch('requests.post')
    def test_end_to_end_insights(self, mock_post):
        """Test the complete spending insights generation flow"""
        # Setup
        mock_auth_service = MagicMock(spec=AuthenticationService)
        mock_auth_service.authenticate_gemini.return_value = {"api_key": "test_api_key"}
        
        client = GeminiClient(auth_service=mock_auth_service)
        
        # Configure mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": "Generated spending insights text"
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # Sample budget analysis
        budget_analysis = {
            "total_budget": 1000.0,
            "total_spent": 800.0,
            "total_variance": 200.0,
            "category_variances": [
                {
                    "category": "Groceries",
                    "budget_amount": 200.0,
                    "actual_amount": 180.0,
                    "variance_amount": 20.0,
                    "variance_percentage": 10.0
                }
            ]
        }
        
        # Authenticate
        client.authenticate()
        
        # Call the generate_spending_insights function
        result = client.generate_spending_insights(budget_analysis)
        
        # Verify the result
        assert result == "Generated spending insights text"
        
        # Verify the API was called
        assert mock_post.called