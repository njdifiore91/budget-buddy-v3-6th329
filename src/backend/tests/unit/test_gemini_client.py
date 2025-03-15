"""
Unit tests for the GeminiClient class that handles interactions with Google's Gemini AI API.
Tests cover authentication, transaction categorization, spending insight generation, and error handling scenarios.
"""

import pytest
from unittest.mock import MagicMock, patch
import requests  # standard library

from ...api_clients.gemini_client import GeminiClient
from ...utils.error_handlers import APIError, ValidationError
from ..fixtures.api_responses import (
    load_gemini_categorization_response,
    load_gemini_insights_response,
    load_gemini_error_response,
    create_mock_api_response,
    create_mock_error_response
)
from ..fixtures.categories import create_test_categories
from ..mocks.mock_gemini_client import MockAuthenticationService


def test_gemini_client_initialization():
    """Test that GeminiClient initializes correctly with authentication service"""
    # Create a mock authentication service
    auth_service = MockAuthenticationService()
    
    # Initialize GeminiClient with the mock auth service
    client = GeminiClient(auth_service)
    
    # Assert that client attributes are set correctly
    assert client.auth_service == auth_service
    assert client.api_key is None  # Should be None until authenticate is called
    assert "categorization" in client.prompt_templates
    assert "insights" in client.prompt_templates


def test_authenticate_success():
    """Test successful authentication with Gemini API"""
    # Create a mock authentication service that returns success
    auth_service = MockAuthenticationService(auth_success=True)
    
    # Initialize GeminiClient with the mock auth service
    client = GeminiClient(auth_service)
    
    # Call authenticate method
    result = client.authenticate()
    
    # Assert that authenticate returns True
    assert result is True
    # Assert that api_key is set correctly
    assert client.api_key == "mock-gemini-api-key"


def test_authenticate_failure():
    """Test authentication failure with Gemini API"""
    # Create a mock authentication service that returns failure
    auth_service = MockAuthenticationService(auth_success=False)
    
    # Initialize GeminiClient with the mock auth service
    client = GeminiClient(auth_service)
    
    # Call authenticate method
    result = client.authenticate()
    
    # Assert that authenticate returns False
    assert result is False
    # Assert that api_key remains None
    assert client.api_key is None


def test_format_prompt():
    """Test formatting a prompt template with variables"""
    # Create a mock authentication service
    auth_service = MockAuthenticationService()
    
    # Initialize GeminiClient with the mock auth service
    client = GeminiClient(auth_service)
    
    # Mock the prompt_templates dictionary with a test template
    client.prompt_templates = {
        "test_template": "Hello, {name}! Your score is {score}."
    }
    
    # Call format_prompt with template name and variables
    result = client.format_prompt("test_template", {"name": "Alice", "score": 95})
    
    # Assert that the returned prompt is correctly formatted
    assert result == "Hello, Alice! Your score is 95."


@patch('requests.post')
def test_generate_completion_success(mock_post):
    """Test successful generation of completion from Gemini AI"""
    # Create a mock authentication service
    auth_service = MockAuthenticationService()
    
    # Initialize GeminiClient with the mock auth service
    client = GeminiClient(auth_service)
    
    # Set up mock response for requests.post
    mock_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": "This is a test response"
                        }
                    ]
                }
            }
        ]
    }
    mock_post.return_value.json.return_value = mock_response
    mock_post.return_value.status_code = 200
    mock_post.return_value.raise_for_status = lambda: None
    
    # Call authenticate to set API key
    client.authenticate()
    
    # Call generate_completion with a test prompt
    result = client.generate_completion("Test prompt")
    
    # Assert that requests.post was called with correct parameters
    mock_post.assert_called_once()
    
    # Assert that the returned text matches expected output
    assert result == "This is a test response"


@patch('requests.post')
def test_generate_completion_api_error(mock_post):
    """Test handling of API error during completion generation"""
    # Create a mock authentication service
    auth_service = MockAuthenticationService()
    
    # Initialize GeminiClient with the mock auth service
    client = GeminiClient(auth_service)
    
    # Set up mock response for requests.post with error status code
    mock_post.return_value.raise_for_status.side_effect = requests.RequestException("API Error")
    
    # Call authenticate to set API key
    client.authenticate()
    
    # Use pytest.raises to assert that APIError is raised
    with pytest.raises(APIError):
        # Call generate_completion with a test prompt
        client.generate_completion("Test prompt")
    
    # Assert that requests.post was called with correct parameters
    mock_post.assert_called_once()


def test_generate_completion_not_authenticated():
    """Test that generate_completion fails when not authenticated"""
    # Create a mock authentication service
    auth_service = MockAuthenticationService()
    
    # Initialize GeminiClient with the mock auth service
    client = GeminiClient(auth_service)
    
    # Do not call authenticate (api_key remains None)
    
    # Use pytest.raises to assert that APIError is raised
    with pytest.raises(APIError):
        # Call generate_completion with a test prompt
        client.generate_completion("Test prompt")


def test_categorize_transactions_success():
    """Test successful categorization of transactions"""
    # Create a mock authentication service
    auth_service = MockAuthenticationService()
    
    # Initialize GeminiClient with the mock auth service
    client = GeminiClient(auth_service)
    
    # Mock generate_completion to return a predefined categorization response
    client.generate_completion = MagicMock(return_value="""
Location: Grocery Store -> Category: Groceries
Location: Starbucks -> Category: Dining Out
Location: Amazon -> Category: Shopping
""")
    
    # Create test transaction locations and budget categories
    transaction_locations = ["Grocery Store", "Starbucks", "Amazon"]
    budget_categories = ["Groceries", "Dining Out", "Shopping", "Transportation"]
    
    # Call categorize_transactions with test data
    result = client.categorize_transactions(transaction_locations, budget_categories)
    
    # Assert that the returned mapping matches expected categorization
    expected = {
        "Grocery Store": "Groceries",
        "Starbucks": "Dining Out",
        "Amazon": "Shopping"
    }
    assert result == expected
    
    # Assert that generate_completion was called with correct parameters
    client.generate_completion.assert_called_once()


def test_categorize_transactions_validation_error():
    """Test validation error handling in transaction categorization"""
    # Create a mock authentication service
    auth_service = MockAuthenticationService()
    
    # Initialize GeminiClient with the mock auth service
    client = GeminiClient(auth_service)
    
    # Call authenticate to set API key
    client.authenticate()
    
    # Use pytest.raises to assert that ValidationError is raised
    with pytest.raises(ValidationError):
        # Call categorize_transactions with invalid parameters (empty lists)
        client.categorize_transactions([], [])


def test_parse_categorization_response():
    """Test parsing of categorization response from Gemini AI"""
    # Create a mock authentication service
    auth_service = MockAuthenticationService()
    
    # Initialize GeminiClient with the mock auth service
    client = GeminiClient(auth_service)
    
    # Create test response text with location-category mappings
    response_text = """
Location: Grocery Store -> Category: Groceries
Some other text that should be ignored
Location: Starbucks -> Category: Dining Out
Location: Amazon -> Category: Shopping
"""
    
    # Create list of valid categories
    valid_categories = ["Groceries", "Dining Out", "Shopping", "Transportation"]
    
    # Call parse_categorization_response with test data
    result = client.parse_categorization_response(response_text, valid_categories)
    
    # Assert that the returned mapping matches expected categorization
    expected = {
        "Grocery Store": "Groceries",
        "Starbucks": "Dining Out",
        "Amazon": "Shopping"
    }
    assert result == expected


def test_parse_categorization_response_invalid_category():
    """Test handling of invalid categories in response parsing"""
    # Create a mock authentication service
    auth_service = MockAuthenticationService()
    
    # Initialize GeminiClient with the mock auth service
    client = GeminiClient(auth_service)
    
    # Create test response text with location-category mappings including invalid categories
    response_text = """
Location: Grocery Store -> Category: Groceries
Location: Starbucks -> Category: Coffee  # Invalid category
Location: Amazon -> Category: Shopping
"""
    
    # Create list of valid categories
    valid_categories = ["Groceries", "Dining Out", "Shopping", "Transportation"]
    
    # Call parse_categorization_response with test data
    result = client.parse_categorization_response(response_text, valid_categories)
    
    # Assert that invalid categories are filtered out
    expected = {
        "Grocery Store": "Groceries",
        "Amazon": "Shopping"
    }
    assert result == expected


def test_generate_spending_insights_success():
    """Test successful generation of spending insights"""
    # Create a mock authentication service
    auth_service = MockAuthenticationService()
    
    # Initialize GeminiClient with the mock auth service
    client = GeminiClient(auth_service)
    
    # Mock generate_completion to return a predefined insights response
    client.generate_completion = MagicMock(return_value="This is a spending insight analysis.")
    
    # Create test budget analysis data
    budget_analysis = {
        "total_budget": 1000,
        "total_spent": 800,
        "total_variance": 200,
        "category_variances": [
            {"category": "Groceries", "budget_amount": 300, "actual_amount": 250, "variance_amount": 50, "variance_percentage": 16.67}
        ]
    }
    
    # Call generate_spending_insights with test data
    result = client.generate_spending_insights(budget_analysis)
    
    # Assert that the returned insights match expected output
    assert result == "This is a spending insight analysis."
    
    # Assert that generate_completion was called with correct parameters
    client.generate_completion.assert_called_once()


def test_generate_spending_insights_validation_error():
    """Test validation error handling in insights generation"""
    # Create a mock authentication service
    auth_service = MockAuthenticationService()
    
    # Initialize GeminiClient with the mock auth service
    client = GeminiClient(auth_service)
    
    # Call authenticate to set API key
    client.authenticate()
    
    # Use pytest.raises to assert that ValidationError is raised
    with pytest.raises(ValidationError):
        # Call generate_spending_insights with invalid parameters (empty dict)
        client.generate_spending_insights({})


def test_validate_api_response():
    """Test validation of API response from Gemini"""
    # Create a mock authentication service
    auth_service = MockAuthenticationService()
    
    # Initialize GeminiClient with the mock auth service
    client = GeminiClient(auth_service)
    
    # Create valid test response JSON
    valid_response = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Test content"}]
                }
            }
        ]
    }
    
    # Call validate_api_response with valid response
    result = client.validate_api_response(valid_response)
    
    # Assert that validation returns True
    assert result is True
    
    # Create invalid test response JSON (missing keys)
    invalid_response = {
        "candidates": []
    }
    
    # Call validate_api_response with invalid response
    result = client.validate_api_response(invalid_response)
    
    # Assert that validation returns False
    assert result is False


def test_extract_generated_text():
    """Test extraction of generated text from API response"""
    # Create a mock authentication service
    auth_service = MockAuthenticationService()
    
    # Initialize GeminiClient with the mock auth service
    client = GeminiClient(auth_service)
    
    # Create test response JSON with text content
    response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": "Generated text content"
                        }
                    ]
                }
            }
        ]
    }
    
    # Call extract_generated_text with test response
    result = client.extract_generated_text(response)
    
    # Assert that extracted text matches expected content
    assert result == "Generated text content"


def test_extract_generated_text_invalid_response():
    """Test handling of invalid response in text extraction"""
    # Create a mock authentication service
    auth_service = MockAuthenticationService()
    
    # Initialize GeminiClient with the mock auth service
    client = GeminiClient(auth_service)
    
    # Create invalid test response JSON (missing required keys)
    invalid_response = {
        "candidates": [
            {
                "content": {}  # Missing "parts" key
            }
        ]
    }
    
    # Use pytest.raises to assert that APIError is raised
    with pytest.raises(APIError):
        # Call extract_generated_text with invalid response
        client.extract_generated_text(invalid_response)