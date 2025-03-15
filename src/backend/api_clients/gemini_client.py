"""
gemini_client.py - Client for interacting with Google's Gemini AI API

This module provides a client for the Gemini AI API that handles authentication,
request formatting, response parsing, and error handling for transaction categorization
and spending insight generation in the Budget Management Application.
"""

import os  # standard library
import json  # standard library
import requests  # requests 2.31.0+
import re  # standard library
from typing import Dict, List, Optional, Any  # standard library

# Internal imports
from ..config.settings import API_SETTINGS, RETRY_SETTINGS
from ..config.logging_config import get_logger
from ..services.authentication_service import AuthenticationService
from ..utils.error_handlers import (
    retry_with_backoff, handle_api_error, APIError, ValidationError
)

# Set up logger
logger = get_logger('gemini_client')

# Path to prompt templates directory
PROMPT_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'ai_prompts')


def load_prompt_template(template_name: str) -> str:
    """
    Loads a prompt template from the templates directory.
    
    Args:
        template_name: The name of the template file to load
        
    Returns:
        Content of the prompt template file
    """
    try:
        template_path = os.path.join(PROMPT_TEMPLATES_DIR, f"{template_name}.txt")
        with open(template_path, 'r') as file:
            return file.read()
    except Exception as e:
        logger.error(f"Failed to load prompt template '{template_name}': {str(e)}")
        raise ValueError(f"Could not load prompt template: {str(e)}")


class GeminiClient:
    """
    Client for interacting with Google's Gemini AI API.
    
    This client handles authentication, request formatting, response parsing,
    and error handling for all Gemini AI operations in the Budget Management Application.
    """
    
    def __init__(self, auth_service: AuthenticationService):
        """
        Initialize the Gemini API client.
        
        Args:
            auth_service: Authentication service for Gemini API
        """
        self.auth_service = auth_service
        self.api_key = None
        
        # Get API settings from configuration
        gemini_settings = API_SETTINGS['GEMINI']
        self.api_url = f"{gemini_settings['API_URL']}/{gemini_settings['API_VERSION']}"
        self.model = gemini_settings['MODEL']
        
        # Load prompt templates
        self.prompt_templates = {
            'categorization': load_prompt_template('categorization_prompt'),
            'insights': load_prompt_template('insights_prompt')
        }
        
        logger.info("Gemini AI client initialized")
    
    def authenticate(self) -> bool:
        """
        Authenticate with the Gemini API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Use authentication service to get API key
            auth_result = self.auth_service.authenticate_gemini()
            self.api_key = auth_result.get('api_key', '')
            
            if not self.api_key:
                logger.error("Failed to retrieve Gemini API key")
                return False
            
            logger.info("Successfully authenticated with Gemini API")
            return True
        except Exception as e:
            logger.error(f"Gemini API authentication failed: {str(e)}")
            return False
    
    def format_prompt(self, template_name: str, variables: Dict) -> str:
        """
        Format a prompt template with provided variables.
        
        Args:
            template_name: Name of the template to format
            variables: Dictionary of variables to insert into the template
            
        Returns:
            Formatted prompt
        """
        try:
            template = self.prompt_templates.get(template_name)
            if not template:
                raise ValueError(f"Unknown template: {template_name}")
            
            # Format the template with variables
            return template.format(**variables)
        except KeyError as e:
            logger.error(f"Missing variable for prompt template '{template_name}': {str(e)}")
            raise ValueError(f"Missing variable for prompt template: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to format prompt template '{template_name}': {str(e)}")
            raise ValueError(f"Could not format prompt template: {str(e)}")
    
    @retry_with_backoff(exceptions=(requests.RequestException,), max_retries=RETRY_SETTINGS['DEFAULT_MAX_RETRIES'])
    def generate_completion(self, prompt: str, generation_config: Optional[Dict] = None) -> str:
        """
        Generate a completion from Gemini AI.
        
        Args:
            prompt: The prompt to send to Gemini
            generation_config: Optional configuration for generation
            
        Returns:
            Generated text from Gemini AI
        """
        # Ensure we're authenticated
        if not self.api_key:
            if not self.authenticate():
                raise APIError(
                    "Not authenticated with Gemini API", 
                    "Gemini", 
                    "generate_completion"
                )
        
        # Set default generation config if not provided
        if generation_config is None:
            generation_config = {
                "temperature": 0.2,
                "topP": 0.8,
                "topK": 40,
                "maxOutputTokens": 1024,
            }
        
        # Prepare request payload
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": generation_config
        }
        
        # Construct API endpoint URL
        url = f"{self.api_url}/models/{self.model}:generateContent"
        
        try:
            # Add API key as query parameter
            params = {"key": self.api_key}
            
            # Make request to Gemini API
            response = requests.post(
                url, 
                json=payload,
                params=params,
                headers={"Content-Type": "application/json"}
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse JSON response
            response_json = response.json()
            
            # Validate response format
            if not self.validate_api_response(response_json):
                raise APIError(
                    "Invalid response format from Gemini API", 
                    "Gemini", 
                    "generate_completion",
                    response_text=response.text
                )
            
            # Extract generated text
            generated_text = self.extract_generated_text(response_json)
            
            return generated_text
            
        except requests.RequestException as e:
            error_context = {"prompt_length": len(prompt)}
            raise APIError(
                f"Gemini API request failed: {str(e)}", 
                "Gemini", 
                "generate_completion",
                status_code=e.response.status_code if hasattr(e, 'response') else None,
                response_text=e.response.text if hasattr(e, 'response') else None,
                context=error_context
            )
        except Exception as e:
            logger.error(f"Gemini generation failed: {str(e)}")
            raise APIError(
                f"Gemini generation failed: {str(e)}", 
                "Gemini", 
                "generate_completion"
            )
    
    def categorize_transactions(self, transaction_locations: List[str], budget_categories: List[str]) -> Dict[str, str]:
        """
        Categorize transactions using Gemini AI.
        
        Args:
            transaction_locations: List of transaction locations to categorize
            budget_categories: List of valid budget categories
            
        Returns:
            Mapping of transaction locations to categories
        """
        try:
            # Validate input
            if not transaction_locations:
                raise ValidationError(
                    "No transaction locations provided for categorization",
                    "transaction_locations"
                )
            
            if not budget_categories:
                raise ValidationError(
                    "No budget categories provided for categorization",
                    "budget_categories"
                )
            
            # Format transaction locations as newline-separated string
            locations_str = "\n".join(transaction_locations)
            
            # Format budget categories as newline-separated string
            categories_str = "\n".join(budget_categories)
            
            # Prepare variables for prompt template
            variables = {
                "transaction_locations": locations_str,
                "budget_categories": categories_str
            }
            
            # Format the categorization prompt
            prompt = self.format_prompt("categorization", variables)
            
            # Call Gemini API
            response_text = self.generate_completion(prompt)
            
            # Parse the response to extract category assignments
            category_mapping = self.parse_categorization_response(response_text, budget_categories)
            
            # Validate that all transactions were categorized
            if len(category_mapping) < len(transaction_locations):
                missing_locations = set(transaction_locations) - set(category_mapping.keys())
                logger.warning(
                    f"Not all transactions were categorized. Missing: {missing_locations}",
                    context={"missing_count": len(missing_locations)}
                )
            
            return category_mapping
            
        except ValidationError as e:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Transaction categorization failed: {str(e)}")
            raise APIError(
                f"Transaction categorization failed: {str(e)}",
                "Gemini",
                "categorize_transactions"
            )
    
    def parse_categorization_response(self, response_text: str, valid_categories: List[str]) -> Dict[str, str]:
        """
        Parse the categorization response from Gemini AI.
        
        Args:
            response_text: Response text from Gemini
            valid_categories: List of valid budget categories
            
        Returns:
            Mapping of transaction locations to categories
        """
        try:
            # Split response into lines
            lines = response_text.strip().split('\n')
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
                        logger.warning(
                            f"Invalid category '{category}' for location '{location}'",
                            context={"location": location, "category": category}
                        )
                        continue
                    
                    result[location] = category
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse categorization response: {str(e)}")
            raise APIError(
                f"Failed to parse categorization response: {str(e)}",
                "Gemini",
                "parse_categorization_response"
            )
    
    def generate_spending_insights(self, budget_analysis: Dict) -> str:
        """
        Generate spending insights using Gemini AI.
        
        Args:
            budget_analysis: Budget analysis data with category variances
            
        Returns:
            Generated insights text
        """
        try:
            # Validate input
            if not budget_analysis:
                raise ValidationError(
                    "No budget analysis data provided for insight generation",
                    "budget_analysis"
                )
            
            # Extract required data
            total_budget = budget_analysis.get('total_budget', 0)
            total_spent = budget_analysis.get('total_spent', 0)
            total_variance = budget_analysis.get('total_variance', 0)
            status = "surplus" if total_variance >= 0 else "deficit"
            
            # Format category breakdown
            category_breakdown = ""
            for category in budget_analysis.get('category_variances', []):
                category_name = category.get('category', '')
                budget_amount = category.get('budget_amount', 0)
                actual_amount = category.get('actual_amount', 0)
                variance_amount = category.get('variance_amount', 0)
                variance_percentage = category.get('variance_percentage', 0)
                
                category_breakdown += (
                    f"Category: {category_name}\n"
                    f"Budget: ${budget_amount:.2f}\n"
                    f"Actual: ${actual_amount:.2f}\n"
                    f"Variance: ${variance_amount:.2f} ({variance_percentage:.1f}%)\n\n"
                )
            
            # Prepare variables for prompt template
            variables = {
                "total_budget": f"{total_budget:.2f}",
                "total_spent": f"{total_spent:.2f}",
                "total_variance": f"{abs(total_variance):.2f}",
                "status": status,
                "category_breakdown": category_breakdown
            }
            
            # Format the insights prompt
            prompt = self.format_prompt("insights", variables)
            
            # Call Gemini API
            insights_text = self.generate_completion(prompt)
            
            return insights_text
            
        except ValidationError as e:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Spending insight generation failed: {str(e)}")
            raise APIError(
                f"Spending insight generation failed: {str(e)}",
                "Gemini",
                "generate_spending_insights"
            )
    
    def validate_api_response(self, response_json: Dict) -> bool:
        """
        Validate the API response from Gemini.
        
        Args:
            response_json: Response JSON from API
            
        Returns:
            True if response is valid, False otherwise
        """
        # Check if response has the expected structure
        if not response_json:
            logger.warning("Empty response from Gemini API")
            return False
        
        # Check for candidates
        if 'candidates' not in response_json or not response_json['candidates']:
            logger.warning("No candidates in Gemini API response")
            return False
        
        # Check for content in the first candidate
        first_candidate = response_json['candidates'][0]
        if 'content' not in first_candidate:
            logger.warning("No content in first candidate of Gemini API response")
            return False
        
        return True
    
    def extract_generated_text(self, response_json: Dict) -> str:
        """
        Extract generated text from Gemini API response.
        
        Args:
            response_json: Response JSON from API
            
        Returns:
            Extracted text from response
        """
        try:
            # Extract text from the first candidate's content
            first_candidate = response_json['candidates'][0]
            content = first_candidate['content']
            
            # Extract text from parts
            parts = content.get('parts', [])
            if not parts:
                raise ValueError("No parts in content")
            
            text = parts[0].get('text', '')
            return text
            
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to extract text from Gemini response: {str(e)}")
            raise APIError(
                f"Failed to extract text from Gemini response: {str(e)}",
                "Gemini",
                "extract_generated_text",
                response_text=json.dumps(response_json)
            )