"""
mock_gemini_client.py - Mock implementation of the Gemini AI API client for testing purposes.

This mock simulates the behavior of the real GeminiClient without making actual API calls,
allowing for controlled testing of transaction categorization and insight generation operations.
"""

import re  # standard library
from typing import List, Dict, Optional, Any  # standard library

# Import the real client to mock its interface
from ...api_clients.gemini_client import GeminiClient

# Import fixture loaders
from ..fixtures.api_responses import (
    load_gemini_categorization_response,
    load_gemini_insights_response,
    load_gemini_error_response
)
from ..fixtures.categories import create_test_categories

# Mock API key for testing
MOCK_API_KEY = "mock-gemini-api-key"

# Default responses
DEFAULT_CATEGORIZATION_RESPONSE = load_gemini_categorization_response()
DEFAULT_INSIGHTS_RESPONSE = load_gemini_insights_response()
DEFAULT_ERROR_RESPONSE = load_gemini_error_response()


def parse_mock_categorization_response(response: Dict, valid_categories: List) -> Dict:
    """
    Parses the mock categorization response to extract category assignments.
    
    Args:
        response: The mock response from Gemini API
        valid_categories: List of valid budget categories
        
    Returns:
        Dictionary mapping transaction locations to categories
    """
    # Extract the generated text from the response
    text = ""
    try:
        text = response["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return {}
    
    # Split the text into lines
    lines = text.strip().split('\n')
    result = {}
    
    # Regular expression to extract location and category
    pattern = r".*?(?:Location|location):\s*(.*?)\s*->\s*(?:Category|category):\s*(.*?)$"
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Try to extract location and category using regex
        match = re.match(pattern, line)
        if match:
            location = match.group(1).strip()
            category = match.group(2).strip()
            
            # Validate category is in the list of valid categories
            if category not in valid_categories:
                continue
            
            result[location] = category
    
    return result


def create_mock_completion_response(text: str) -> Dict:
    """
    Creates a mock completion response with the specified text.
    
    Args:
        text: The text to include in the response
        
    Returns:
        Mock Gemini API response with the provided text
    """
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": text
                        }
                    ],
                    "role": "model"
                },
                "finishReason": "STOP",
                "index": 0,
                "safetyRatings": []
            }
        ],
        "promptFeedback": {
            "safetyRatings": []
        }
    }


class MockAuthenticationService:
    """Mock authentication service for testing."""
    
    def __init__(self, auth_success=True):
        """
        Initialize the mock authentication service.
        
        Args:
            auth_success: Whether authentication should succeed
        """
        self.auth_success = auth_success
        self.api_key = MOCK_API_KEY
    
    def authenticate_gemini(self):
        """
        Mock authentication with Gemini API.
        
        Returns:
            Dictionary with mock API key on success,
            Raises exception on failure
        """
        if self.auth_success:
            return {"api_key": self.api_key}
        
        # Use a generic exception for simplicity in tests
        class AuthenticationError(Exception):
            pass
        
        raise AuthenticationError("Mock authentication failed")
    
    def get_token(self, service_name):
        """
        Get mock authentication token.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Mock API key if service is 'gemini' and auth_success is True,
            None otherwise
        """
        if service_name == 'gemini' and self.auth_success:
            return self.api_key
        return None
    
    def refresh_token(self, service_name):
        """
        Mock token refresh.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Success status of refresh (auth_success value)
        """
        return self.auth_success


class MockGeminiClient:
    """Mock implementation of the Gemini AI API client for testing."""
    
    def __init__(
        self,
        auth_service=None,
        auth_success=True,
        api_error=False,
        mock_categorization_response=None,
        mock_insights_response=None
    ):
        """
        Initialize the mock Gemini client.
        
        Args:
            auth_service: Optional mock authentication service
            auth_success: Whether authentication should succeed
            api_error: Whether to simulate API errors
            mock_categorization_response: Custom response for categorization
            mock_insights_response: Custom response for insights
        """
        self.api_url = "https://api.mock.gemini.com"
        self.model = "gemini-pro"
        self.auth_success = auth_success
        self.api_error = api_error
        
        # Set up authentication service
        self.auth_service = auth_service or MockAuthenticationService(auth_success=auth_success)
        
        # Mock prompt templates
        self.prompt_templates = {
            "categorization": "You are a financial transaction categorizer. Please match each transaction location to the most appropriate budget category.\n\nTRANSACTION LOCATIONS:\n{transaction_locations}\n\nVALID BUDGET CATEGORIES:\n{budget_categories}\n\nFor each transaction location, respond with the location followed by the best matching category in this format:\n\"Location: [transaction location] -> Category: [matching category]\"",
            "insights": "You are a personal finance advisor analyzing weekly budget performance. Create a comprehensive analysis of the following budget data:\n\nTOTAL BUDGET STATUS:\nTotal Budget: ${total_budget}\nTotal Spent: ${total_spent}\nVariance: ${total_variance} ({status})\n\nCATEGORY BREAKDOWN:\n{category_breakdown}\n\nPlease provide a detailed analysis including..."
        }
        
        # Set mock responses
        self.categorization_responses = mock_categorization_response or DEFAULT_CATEGORIZATION_RESPONSE
        self.insight_responses = mock_insights_response or DEFAULT_INSIGHTS_RESPONSE
        self.completion_responses = {}  # For custom prompts
        
        # Set API key based on auth success
        self.api_key = MOCK_API_KEY if auth_success else None
    
    def authenticate(self):
        """
        Mock authentication with Gemini API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        if self.auth_success:
            self.api_key = MOCK_API_KEY
            return True
        self.api_key = None
        return False
    
    def set_api_error(self, error_state):
        """
        Set API error flag for testing error scenarios.
        
        Args:
            error_state: Whether to simulate API errors
        """
        self.api_error = error_state
    
    def set_mock_categorization_response(self, response):
        """
        Set custom mock response for categorization.
        
        Args:
            response: Custom mock response
        """
        self.categorization_responses = response
    
    def set_mock_insights_response(self, response):
        """
        Set custom mock response for insights generation.
        
        Args:
            response: Custom mock response
        """
        self.insight_responses = response
    
    def set_mock_completion_response(self, prompt, response):
        """
        Set custom mock response for specific prompt.
        
        Args:
            prompt: The prompt to match
            response: Custom mock response
        """
        self.completion_responses[prompt] = response
    
    def format_prompt(self, template_name, variables):
        """
        Mock implementation of prompt formatting.
        
        Args:
            template_name: Name of the template to format
            variables: Dictionary of variables to insert into the template
            
        Returns:
            Formatted prompt
        """
        template = self.prompt_templates.get(template_name, "")
        return template.format(**variables)
    
    def generate_completion(self, prompt, generation_config=None):
        """
        Mock generation of completion from Gemini AI.
        
        Args:
            prompt: The prompt to send to Gemini
            generation_config: Optional configuration for generation
            
        Returns:
            Generated text from mock response
        """
        if self.api_error:
            # Use a generic API error for simplicity in tests
            class APIError(Exception):
                pass
            
            raise APIError("Mock API error")
        
        # Check if we have a specific response for this prompt
        if prompt in self.completion_responses:
            return self.extract_generated_text(self.completion_responses[prompt])
        
        # Choose response based on prompt content
        if "categorization" in prompt.lower():
            return self.extract_generated_text(self.categorization_responses)
        elif "insight" in prompt.lower() or "spending" in prompt.lower():
            return self.extract_generated_text(self.insight_responses)
        
        # Generic response if no specific match
        return "Mock Gemini response for prompt: " + prompt[:50] + "..."
    
    def categorize_transactions(self, transaction_locations, budget_categories):
        """
        Mock categorization of transactions.
        
        Args:
            transaction_locations: List of transaction locations to categorize
            budget_categories: List of valid budget categories
            
        Returns:
            Dictionary mapping transaction locations to categories
        """
        if self.api_error:
            # Use a generic API error for simplicity in tests
            class APIError(Exception):
                pass
            
            raise APIError("Mock API error during categorization")
        
        # Get the mock response
        mock_response = self.categorization_responses
        
        # Parse the response to extract category assignments
        return parse_mock_categorization_response(mock_response, budget_categories)
    
    def generate_spending_insights(self, budget_analysis):
        """
        Mock generation of spending insights.
        
        Args:
            budget_analysis: Budget analysis data
            
        Returns:
            Generated insights text from mock response
        """
        if self.api_error:
            # Use a generic API error for simplicity in tests
            class APIError(Exception):
                pass
            
            raise APIError("Mock API error during insight generation")
        
        # Get the mock response
        mock_response = self.insight_responses
        
        # Extract the text content from the response
        return self.extract_generated_text(mock_response)
    
    def extract_generated_text(self, response_json):
        """
        Extract generated text from mock Gemini API response.
        
        Args:
            response_json: Response JSON from API
            
        Returns:
            Extracted text from response
        """
        try:
            # Extract text from the first candidate's content
            return response_json["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return "Unable to extract text from response"
    
    def test_connectivity(self):
        """
        Mock test of connectivity to Gemini API.
        
        Returns:
            True if connection successful, False otherwise
        """
        return not self.api_error