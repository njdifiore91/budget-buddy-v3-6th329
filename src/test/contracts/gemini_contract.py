"""
Defines the contract for the Gemini AI API client interface.

This module provides protocol classes and JSON schemas for validating API responses.
It ensures that both real implementations and mock versions of the Gemini client 
adhere to the same interface and data structures, enabling reliable testing of
components that depend on Gemini AI integration.
"""

from typing import Protocol, List, Dict, Optional, Any
import jsonschema  # version 4.17.0+

# JSON schemas for validating Gemini API responses
CATEGORIZATION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "object",
                        "properties": {
                            "parts": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "text": {"type": "string"}
                                    },
                                    "required": ["text"]
                                }
                            },
                            "role": {"type": "string"}
                        },
                        "required": ["parts", "role"]
                    },
                    "finishReason": {"type": "string"},
                    "index": {"type": "integer"},
                    "safetyRatings": {"type": "array"}
                },
                "required": ["content", "finishReason", "index"]
            }
        },
        "promptFeedback": {"type": "object"}
    },
    "required": ["candidates"]
}

INSIGHT_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "object",
                        "properties": {
                            "parts": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "text": {"type": "string"}
                                    },
                                    "required": ["text"]
                                }
                            },
                            "role": {"type": "string"}
                        },
                        "required": ["parts", "role"]
                    },
                    "finishReason": {"type": "string"},
                    "index": {"type": "integer"},
                    "safetyRatings": {"type": "array"}
                },
                "required": ["content", "finishReason", "index"]
            }
        },
        "promptFeedback": {"type": "object"}
    },
    "required": ["candidates"]
}

CATEGORIZATION_PROMPT_SCHEMA = {
    "type": "object",
    "properties": {
        "transaction_locations": {
            "type": "array",
            "items": {"type": "string"}
        },
        "budget_categories": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["transaction_locations", "budget_categories"]
}

INSIGHT_PROMPT_SCHEMA = {
    "type": "object",
    "properties": {
        "budget_analysis": {
            "type": "object",
            "properties": {
                "total_budget": {"type": "number"},
                "total_spent": {"type": "number"},
                "total_variance": {"type": "number"},
                "status": {"type": "string"},
                "category_variances": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "budget_amount": {"type": "number"},
                            "actual_amount": {"type": "number"},
                            "variance_amount": {"type": "number"},
                            "variance_percentage": {"type": "number"}
                        },
                        "required": [
                            "category", 
                            "budget_amount", 
                            "actual_amount", 
                            "variance_amount", 
                            "variance_percentage"
                        ]
                    }
                }
            },
            "required": ["total_budget", "total_spent", "total_variance", "status", "category_variances"]
        }
    },
    "required": ["budget_analysis"]
}

# Example responses for testing and documentation
EXAMPLE_CATEGORIZATION_RESPONSE = {
    "candidates": [
        {
            "content": {
                "parts": [
                    {
                        "text": "Location: Grocery Store -> Category: Groceries\nLocation: Gas Station -> Category: Transportation\nLocation: Pharmacy -> Category: Health\nLocation: Restaurant -> Category: Dining Out\nLocation: Online Shopping -> Category: Shopping"
                    }
                ],
                "role": "model"
            },
            "finishReason": "STOP",
            "index": 0,
            "safetyRatings": []
        }
    ],
    "promptFeedback": {}
}

EXAMPLE_INSIGHT_RESPONSE = {
    "candidates": [
        {
            "content": {
                "parts": [
                    {
                        "text": "# Weekly Budget Update: $45.67 Under Budget\n\nGreat job this week! You've managed to stay under budget by $45.67, which is about 8% of your total weekly budget.\n\n## Category Performance\n\n**Categories under budget:**\n- Groceries: $32.45 under (21% saved)\n- Transportation: $15.75 under (16% saved)\n- Entertainment: $10.00 under (25% saved)\n\n**Categories over budget:**\n- Dining Out: $12.53 over (25% exceeded)\n\n## Recommendations\n\n1. Consider transferring your surplus of $45.67 to savings\n2. Watch your Dining Out expenses, which consistently exceed budget\n3. Your grocery spending is efficient - keep using those strategies"
                    }
                ],
                "role": "model"
            },
            "finishReason": "STOP",
            "index": 0,
            "safetyRatings": []
        }
    ],
    "promptFeedback": {}
}


def validate_categorization_response(response: Dict[str, Any]) -> bool:
    """
    Validates a Gemini AI categorization response against the schema.
    
    Args:
        response: The response from the Gemini AI API
    
    Returns:
        True if valid, raises ValidationError if invalid
    """
    jsonschema.validate(response, CATEGORIZATION_RESPONSE_SCHEMA)
    return True


def validate_insight_response(response: Dict[str, Any]) -> bool:
    """
    Validates a Gemini AI insight response against the schema.
    
    Args:
        response: The response from the Gemini AI API
    
    Returns:
        True if valid, raises ValidationError if invalid
    """
    jsonschema.validate(response, INSIGHT_RESPONSE_SCHEMA)
    return True


def validate_categorization_prompt(prompt_data: Dict[str, Any]) -> bool:
    """
    Validates a Gemini AI categorization prompt against the schema.
    
    Args:
        prompt_data: The prompt data to validate
    
    Returns:
        True if valid, raises ValidationError if invalid
    """
    jsonschema.validate(prompt_data, CATEGORIZATION_PROMPT_SCHEMA)
    return True


def validate_insight_prompt(prompt_data: Dict[str, Any]) -> bool:
    """
    Validates a Gemini AI insight prompt against the schema.
    
    Args:
        prompt_data: The prompt data to validate
    
    Returns:
        True if valid, raises ValidationError if invalid
    """
    jsonschema.validate(prompt_data, INSIGHT_PROMPT_SCHEMA)
    return True


class GeminiClientProtocol(Protocol):
    """
    Protocol defining the interface for the Gemini AI API client.
    
    This protocol ensures that both real implementations and mocks
    adhere to the same interface.
    """
    
    def __init__(self, auth_service: Optional[Any] = None) -> None:
        """
        Initialize the Gemini AI client.
        
        Args:
            auth_service: Optional authentication service
        """
        ...
        
    def authenticate(self) -> bool:
        """
        Authenticate with the Gemini AI API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        ...
        
    def generate_completion(
        self, prompt: str, generation_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a completion from Gemini AI.
        
        Args:
            prompt: The prompt to send to Gemini AI
            generation_config: Optional configuration for generation
            
        Returns:
            Generated text from Gemini AI
        """
        ...
        
    def categorize_transactions(
        self, transaction_locations: List[str], budget_categories: List[str]
    ) -> Dict[str, str]:
        """
        Categorize transactions using Gemini AI.
        
        Args:
            transaction_locations: List of transaction locations to categorize
            budget_categories: List of valid budget categories
            
        Returns:
            Mapping of transaction locations to categories
        """
        ...
        
    def generate_spending_insights(self, budget_analysis: Dict[str, Any]) -> str:
        """
        Generate spending insights using Gemini AI.
        
        Args:
            budget_analysis: Budget analysis data
            
        Returns:
            Generated insights text
        """
        ...
        
    def test_connectivity(self) -> bool:
        """
        Test connectivity to the Gemini API.
        
        Returns:
            True if connection successful, False otherwise
        """
        ...


class CategorizationResponseContract:
    """
    Contract class for Gemini AI categorization responses.
    
    This class provides validation and utility methods for working with
    categorization responses from the Gemini AI API.
    """
    
    def __init__(self):
        """Initialize the categorization response contract."""
        self.schema = CATEGORIZATION_RESPONSE_SCHEMA
        self.example = EXAMPLE_CATEGORIZATION_RESPONSE
        
    def validate(self, response: Dict[str, Any]) -> bool:
        """
        Validate a categorization response against the schema.
        
        Args:
            response: The response to validate
            
        Returns:
            True if valid, raises ValidationError if invalid
        """
        return validate_categorization_response(response)
        
    def get_example(self) -> Dict[str, Any]:
        """
        Get an example categorization response.
        
        Returns:
            Example categorization response
        """
        return self.example
        
    def extract_text(self, response: Dict[str, Any]) -> str:
        """
        Extract the text content from a categorization response.
        
        Args:
            response: The response from which to extract text
            
        Returns:
            Extracted text content
        """
        try:
            return response["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid response structure: {e}")


class InsightResponseContract:
    """
    Contract class for Gemini AI insight responses.
    
    This class provides validation and utility methods for working with
    insight responses from the Gemini AI API.
    """
    
    def __init__(self):
        """Initialize the insight response contract."""
        self.schema = INSIGHT_RESPONSE_SCHEMA
        self.example = EXAMPLE_INSIGHT_RESPONSE
        
    def validate(self, response: Dict[str, Any]) -> bool:
        """
        Validate an insight response against the schema.
        
        Args:
            response: The response to validate
            
        Returns:
            True if valid, raises ValidationError if invalid
        """
        return validate_insight_response(response)
        
    def get_example(self) -> Dict[str, Any]:
        """
        Get an example insight response.
        
        Returns:
            Example insight response
        """
        return self.example
        
    def extract_text(self, response: Dict[str, Any]) -> str:
        """
        Extract the text content from an insight response.
        
        Args:
            response: The response from which to extract text
            
        Returns:
            Extracted text content
        """
        try:
            return response["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid response structure: {e}")