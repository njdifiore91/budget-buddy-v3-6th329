"""
Mock implementation of the Gemini AI API client for testing purposes.

This class mimics the behavior of the real GeminiClient but returns predefined
responses instead of making actual API calls. It implements the GeminiClientProtocol
interface to ensure compatibility with components that depend on the Gemini AI integration.
"""

import re
import copy
from typing import Dict, List, Any, Optional

from ..contracts.gemini_contract import (
    GeminiClientProtocol,
    CategorizationResponseContract,
    InsightResponseContract,
    EXAMPLE_CATEGORIZATION_RESPONSE,
    EXAMPLE_INSIGHT_RESPONSE
)
from ..fixtures.api_responses import get_gemini_response
from ..utils.fixture_loader import load_fixture

# Regular expression for parsing categorization responses
DEFAULT_CATEGORIZATION_PATTERN = r"Location:\s*([^\->]+)\s*->\s*Category:\s*([^\n]+)"

def parse_categorization_text(text: str, valid_categories: List[str]) -> Dict[str, str]:
    """
    Parse categorization text to extract location-category mappings.
    
    Args:
        text: Text containing location-category mappings
        valid_categories: List of valid budget categories
        
    Returns:
        Dictionary mapping transaction locations to categories
    """
    result = {}
    matches = re.findall(DEFAULT_CATEGORIZATION_PATTERN, text)
    
    for location, category in matches:
        # Clean up whitespace
        location = location.strip()
        category = category.strip()
        
        # Verify the category is in the valid categories list
        if category in valid_categories:
            result[location] = category
    
    return result


class MockGeminiClient(GeminiClientProtocol):
    """
    Mock implementation of the Gemini AI client for testing.
    
    This class mimics the behavior of the real GeminiClient but returns predefined
    responses instead of making actual API calls. It provides additional methods
    for configuring test scenarios and verifying interactions.
    """
    
    def __init__(self, auth_service: Optional[Any] = None, authenticated: bool = True, 
                 should_fail: bool = False, failure_mode: str = 'authentication'):
        """
        Initialize the mock Gemini client.
        
        Args:
            auth_service: Optional authentication service (not used in mock)
            authenticated: Whether the client starts in authenticated state
            should_fail: Whether operations should fail (for testing error handling)
            failure_mode: Which operation should fail ('authentication', 'completion',
                         'categorization', 'insights', or 'connectivity')
        """
        self.is_authenticated = authenticated
        
        # Initialize with default responses
        self.responses = {
            'categorization': copy.deepcopy(EXAMPLE_CATEGORIZATION_RESPONSE),
            'insights': copy.deepcopy(EXAMPLE_INSIGHT_RESPONSE)
        }
        
        # Track method calls for test verification
        self.call_history = {
            'authenticate': [],
            'generate_completion': [],
            'categorize_transactions': [],
            'generate_spending_insights': [],
            'test_connectivity': []
        }
        
        # Settings for simulating failures
        self.should_fail = should_fail
        self.failure_mode = failure_mode
        
        # Initialize response contracts
        self.categorization_contract = CategorizationResponseContract()
        self.insight_contract = InsightResponseContract()
    
    def authenticate(self) -> bool:
        """
        Mock authentication with Gemini API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        if self.should_fail and self.failure_mode == 'authentication':
            self.is_authenticated = False
        else:
            self.is_authenticated = True
        
        # Record the method call
        self.call_history['authenticate'].append({
            'result': self.is_authenticated
        })
        
        return self.is_authenticated
    
    def generate_completion(self, prompt: str, generation_config: Optional[Dict[str, Any]] = None) -> str:
        """
        Mock generation of completions from Gemini AI.
        
        Args:
            prompt: The prompt to send to Gemini AI
            generation_config: Optional configuration for generation
            
        Returns:
            Generated text from mock response
            
        Raises:
            Exception: If authentication fails or should_fail is True with appropriate failure_mode
        """
        if self.should_fail and self.failure_mode == 'completion':
            raise Exception("Simulated completion failure")
        
        if not self.is_authenticated:
            raise Exception("Authentication required before generating completions")
        
        # Record the method call
        self.call_history['generate_completion'].append({
            'prompt': prompt,
            'generation_config': generation_config
        })
        
        # Determine response type based on prompt content
        response_type = None
        if 'transaction' in prompt.lower() and 'category' in prompt.lower():
            response_type = 'categorization'
        elif 'budget' in prompt.lower() and 'analysis' in prompt.lower():
            response_type = 'insights'
        else:
            # Default to insights for unknown prompts
            response_type = 'insights'
        
        # Get appropriate mock response
        response = self.responses.get(response_type, self.responses['insights'])
        
        # Extract text from response
        if response_type == 'categorization':
            return self.categorization_contract.extract_text(response)
        else:
            return self.insight_contract.extract_text(response)
    
    def categorize_transactions(self, transaction_locations: List[str], budget_categories: List[str]) -> Dict[str, str]:
        """
        Mock categorization of transactions.
        
        Args:
            transaction_locations: List of transaction locations to categorize
            budget_categories: List of valid budget categories
            
        Returns:
            Mapping of transaction locations to categories
            
        Raises:
            Exception: If authentication fails or should_fail is True with appropriate failure_mode
        """
        if self.should_fail and self.failure_mode == 'categorization':
            raise Exception("Simulated categorization failure")
        
        if not self.is_authenticated:
            raise Exception("Authentication required before categorizing transactions")
        
        # Record the method call
        self.call_history['categorize_transactions'].append({
            'transaction_locations': transaction_locations,
            'budget_categories': budget_categories
        })
        
        # Get categorization response
        response = self.responses.get('categorization', EXAMPLE_CATEGORIZATION_RESPONSE)
        
        # Extract text from response
        text = self.categorization_contract.extract_text(response)
        
        # Parse the text to get location-category mappings
        categorization = parse_categorization_text(text, budget_categories)
        
        return categorization
    
    def generate_spending_insights(self, budget_analysis: Dict[str, Any]) -> str:
        """
        Mock generation of spending insights.
        
        Args:
            budget_analysis: Budget analysis data
            
        Returns:
            Generated insights text
            
        Raises:
            Exception: If authentication fails or should_fail is True with appropriate failure_mode
        """
        if self.should_fail and self.failure_mode == 'insights':
            raise Exception("Simulated insights generation failure")
        
        if not self.is_authenticated:
            raise Exception("Authentication required before generating insights")
        
        # Record the method call
        self.call_history['generate_spending_insights'].append({
            'budget_analysis': budget_analysis
        })
        
        # Get insight response
        response = self.responses.get('insights', EXAMPLE_INSIGHT_RESPONSE)
        
        # Extract text from response
        text = self.insight_contract.extract_text(response)
        
        return text
    
    def test_connectivity(self) -> bool:
        """
        Mock test of connectivity to Gemini API.
        
        Returns:
            True if connection successful, False otherwise
        """
        if self.should_fail and self.failure_mode == 'connectivity':
            result = False
        else:
            result = self.is_authenticated
        
        # Record the method call
        self.call_history['test_connectivity'].append({
            'result': result
        })
        
        return result
    
    def set_response(self, response_type: str, response: Dict[str, Any]) -> None:
        """
        Set a custom response for a specific request type.
        
        Args:
            response_type: Type of response ('categorization' or 'insights')
            response: Custom response dictionary
        """
        self.responses[response_type] = response
    
    def set_categorization_response(self, response: Dict[str, Any]) -> None:
        """
        Set a custom categorization response.
        
        Args:
            response: Custom categorization response dictionary
        """
        self.set_response('categorization', response)
    
    def set_insight_response(self, response: Dict[str, Any]) -> None:
        """
        Set a custom insight response.
        
        Args:
            response: Custom insight response dictionary
        """
        self.set_response('insights', response)
    
    def get_call_history(self, method_name: str) -> List[Dict[str, Any]]:
        """
        Get the history of method calls.
        
        Args:
            method_name: Name of the method to get history for
            
        Returns:
            List of method calls with arguments
        """
        return self.call_history.get(method_name, [])
    
    def reset(self) -> None:
        """
        Reset the mock client to its initial state.
        """
        # Reset authentication state
        self.is_authenticated = True
        
        # Clear call history
        for method in self.call_history:
            self.call_history[method] = []
        
        # Reset responses to defaults
        self.responses = {
            'categorization': copy.deepcopy(EXAMPLE_CATEGORIZATION_RESPONSE),
            'insights': copy.deepcopy(EXAMPLE_INSIGHT_RESPONSE)
        }
        
        # Reset failure settings
        self.should_fail = False
        self.failure_mode = 'authentication'
    
    def set_failure_mode(self, should_fail: bool, failure_mode: str) -> None:
        """
        Configure the client to simulate failures.
        
        Args:
            should_fail: Whether operations should fail
            failure_mode: Which operation should fail ('authentication', 'completion',
                         'categorization', 'insights', or 'connectivity')
        """
        self.should_fail = should_fail
        
        # Validate failure mode
        valid_modes = ['authentication', 'completion', 'categorization', 'insights', 'connectivity']
        if failure_mode not in valid_modes:
            raise ValueError(f"Invalid failure mode: {failure_mode}. Must be one of {valid_modes}")
        
        self.failure_mode = failure_mode


class MockGeminiClientFactory:
    """
    Factory class for creating configured MockGeminiClient instances.
    
    This class provides convenience methods for creating mock clients with
    various configurations for different testing scenarios.
    """
    
    @staticmethod
    def create_default_client() -> MockGeminiClient:
        """
        Create a default mock client.
        
        Returns:
            Configured mock client
        """
        return MockGeminiClient()
    
    @staticmethod
    def create_failing_client(failure_mode: str) -> MockGeminiClient:
        """
        Create a mock client that simulates failures.
        
        Args:
            failure_mode: Type of failure to simulate
            
        Returns:
            Configured mock client
        """
        return MockGeminiClient(should_fail=True, failure_mode=failure_mode)
    
    @staticmethod
    def create_client_with_custom_responses(responses: Dict[str, Dict[str, Any]]) -> MockGeminiClient:
        """
        Create a mock client with custom responses.
        
        Args:
            responses: Dictionary mapping response types to response dictionaries
            
        Returns:
            Configured mock client
        """
        client = MockGeminiClient()
        for response_type, response in responses.items():
            client.set_response(response_type, response)
        return client
    
    @staticmethod
    def create_unauthenticated_client() -> MockGeminiClient:
        """
        Create a mock client that is not authenticated.
        
        Returns:
            Configured mock client
        """
        return MockGeminiClient(authenticated=False)