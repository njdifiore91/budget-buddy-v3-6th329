"""
authentication_service.py - Service for authenticating with external APIs

This service manages authentication flows, token storage, and refresh mechanisms
for Capital One, Google Sheets, Gmail, and Gemini APIs used by the Budget
Management Application.
"""

import os  # standard library
import json  # standard library
import time  # standard library
import requests  # requests 2.31.0+
from typing import Dict, Optional, Any  # standard library
import google.oauth2.service_account  # google-auth 2.22.0+
import google.auth.transport.requests  # google-auth 2.22.0+
import google.auth.exceptions  # google-auth 2.22.0+

from ..config.settings import API_SETTINGS, get_secret, load_json_secret, get_api_credentials
from ..config.logging_config import get_logger
from ..utils.error_handlers import (
    retry_with_backoff, handle_api_error, handle_auth_error,
    APIError, AuthenticationError
)

# Set up logger
logger = get_logger('authentication_service')

# In-memory token cache
TOKEN_CACHE = {}
TOKEN_EXPIRY = {}


def is_token_expired(service_name: str) -> bool:
    """
    Checks if a token has expired based on expiry time
    
    Args:
        service_name: Name of the service to check
        
    Returns:
        True if token is expired or not found, False otherwise
    """
    if service_name not in TOKEN_EXPIRY:
        return True
    
    expiry_time = TOKEN_EXPIRY[service_name]
    current_time = int(time.time())
    
    return current_time >= expiry_time


def cache_token(service_name: str, token: str, expires_in: int) -> None:
    """
    Caches an authentication token with expiry time
    
    Args:
        service_name: Name of the service
        token: Authentication token
        expires_in: Expiration time in seconds
    """
    TOKEN_CACHE[service_name] = token
    
    # Set expiry time with a small buffer (10 seconds) to account for processing time
    expiry_time = int(time.time()) + expires_in - 10
    TOKEN_EXPIRY[service_name] = expiry_time
    
    # Log with masked token for security
    masked_token = token[:5] + "..." + token[-5:] if len(token) > 10 else "***"
    logger.info(f"Cached token for {service_name} with expiry in {expires_in} seconds",
                context={"service": service_name, "expiry": expiry_time})


def clear_token_cache(service_name: Optional[str] = None) -> None:
    """
    Clears the token cache for a specific service or all services
    
    Args:
        service_name: Name of the service, or None to clear all
    """
    if service_name:
        if service_name in TOKEN_CACHE:
            del TOKEN_CACHE[service_name]
        if service_name in TOKEN_EXPIRY:
            del TOKEN_EXPIRY[service_name]
        logger.info(f"Cleared token cache for {service_name}")
    else:
        TOKEN_CACHE.clear()
        TOKEN_EXPIRY.clear()
        logger.info("Cleared all token caches")


class AuthenticationService:
    """
    Service for handling authentication with external APIs
    """
    
    def __init__(self):
        """
        Initialize the authentication service
        """
        self.credentials_cache = {}
        logger.info("Authentication service initialized")
    
    @retry_with_backoff(exceptions=(requests.RequestException,), max_retries=3)
    def authenticate_capital_one(self) -> Dict:
        """
        Authenticate with Capital One API using OAuth 2.0
        
        Returns:
            Authentication response with token
        """
        try:
            # Check if we have a valid token in cache
            if 'CAPITAL_ONE' in TOKEN_CACHE and not is_token_expired('CAPITAL_ONE'):
                logger.debug("Using cached Capital One token")
                return {"access_token": TOKEN_CACHE['CAPITAL_ONE']}
            
            # Get Capital One API credentials
            credentials = get_api_credentials('CAPITAL_ONE')
            client_id = credentials.get('client_id')
            client_secret = credentials.get('client_secret')
            
            if not client_id or not client_secret:
                raise AuthenticationError(
                    "Missing required Capital One credentials", 
                    'CAPITAL_ONE',
                    {"error": "Missing client_id or client_secret"}
                )
            
            # Prepare OAuth 2.0 token request
            auth_url = API_SETTINGS['CAPITAL_ONE']['AUTH_URL']
            data = {
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            # Make authentication request
            response = requests.post(auth_url, data=data, headers=headers)
            response.raise_for_status()
            
            # Parse response
            auth_data = response.json()
            
            if 'access_token' not in auth_data or 'expires_in' not in auth_data:
                raise AuthenticationError(
                    "Invalid authentication response from Capital One API", 
                    'CAPITAL_ONE',
                    {"response": auth_data}
                )
            
            # Cache the token
            access_token = auth_data['access_token']
            expires_in = auth_data['expires_in']
            cache_token('CAPITAL_ONE', access_token, expires_in)
            
            logger.info("Successfully authenticated with Capital One API")
            return auth_data
            
        except requests.RequestException as e:
            error_msg = f"Capital One API authentication request failed: {str(e)}"
            logger.error(error_msg, context={"error": str(e)})
            raise AuthenticationError(error_msg, 'CAPITAL_ONE')
            
        except Exception as e:
            error_msg = f"Capital One API authentication failed: {str(e)}"
            logger.error(error_msg, context={"error": str(e)})
            raise AuthenticationError(error_msg, 'CAPITAL_ONE')
    
    @retry_with_backoff(exceptions=(google.auth.exceptions.GoogleAuthError,), max_retries=3)
    def authenticate_google_sheets(self):
        """
        Authenticate with Google Sheets API using service account
        
        Returns:
            Google credentials object
        """
        try:
            # Check if we have cached credentials
            if 'GOOGLE_SHEETS' in self.credentials_cache:
                logger.debug("Using cached Google Sheets credentials")
                return self.credentials_cache['GOOGLE_SHEETS']
            
            # Get Google Sheets API credentials
            credentials_json = get_api_credentials('GOOGLE_SHEETS')
            
            # Create service account credentials
            credentials = google.oauth2.service_account.Credentials.from_service_account_info(
                credentials_json,
                scopes=API_SETTINGS['GOOGLE_SHEETS']['SCOPES']
            )
            
            # Ensure credentials are valid
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)
            
            # Cache credentials
            self.credentials_cache['GOOGLE_SHEETS'] = credentials
            
            logger.info("Successfully authenticated with Google Sheets API")
            return credentials
            
        except google.auth.exceptions.GoogleAuthError as e:
            error_msg = f"Google Sheets API authentication failed: {str(e)}"
            logger.error(error_msg, context={"error": str(e)})
            raise AuthenticationError(error_msg, 'GOOGLE_SHEETS')
            
        except Exception as e:
            error_msg = f"Google Sheets API authentication failed: {str(e)}"
            logger.error(error_msg, context={"error": str(e)})
            raise AuthenticationError(error_msg, 'GOOGLE_SHEETS')
    
    @retry_with_backoff(exceptions=(google.auth.exceptions.GoogleAuthError,), max_retries=3)
    def authenticate_gmail(self):
        """
        Authenticate with Gmail API using service account
        
        Returns:
            Google credentials object
        """
        try:
            # Check if we have cached credentials
            if 'GMAIL' in self.credentials_cache:
                logger.debug("Using cached Gmail credentials")
                return self.credentials_cache['GMAIL']
            
            # Get Gmail API credentials
            credentials_json = get_api_credentials('GMAIL')
            
            # Create service account credentials
            credentials = google.oauth2.service_account.Credentials.from_service_account_info(
                credentials_json,
                scopes=API_SETTINGS['GMAIL']['SCOPES']
            )
            
            # Ensure credentials are valid
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)
            
            # Cache credentials
            self.credentials_cache['GMAIL'] = credentials
            
            logger.info("Successfully authenticated with Gmail API")
            return credentials
            
        except google.auth.exceptions.GoogleAuthError as e:
            error_msg = f"Gmail API authentication failed: {str(e)}"
            logger.error(error_msg, context={"error": str(e)})
            raise AuthenticationError(error_msg, 'GMAIL')
            
        except Exception as e:
            error_msg = f"Gmail API authentication failed: {str(e)}"
            logger.error(error_msg, context={"error": str(e)})
            raise AuthenticationError(error_msg, 'GMAIL')
    
    def authenticate_gemini(self) -> Dict:
        """
        Authenticate with Gemini API using API key
        
        Returns:
            Authentication response with API key
        """
        try:
            # Get Gemini API key
            api_key = get_secret(API_SETTINGS['GEMINI']['API_KEY_SECRET'])
            
            if not api_key:
                raise AuthenticationError(
                    "Missing Gemini API key", 
                    'GEMINI',
                    {"error": "API key not found"}
                )
            
            logger.info("Successfully retrieved Gemini API key")
            return {"api_key": api_key}
            
        except Exception as e:
            error_msg = f"Gemini API authentication failed: {str(e)}"
            logger.error(error_msg, context={"error": str(e)})
            raise AuthenticationError(error_msg, 'GEMINI')
    
    def get_token(self, service_name: str) -> str:
        """
        Get authentication token for a specific service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Authentication token
        """
        try:
            # Validate service name
            if service_name not in ['CAPITAL_ONE', 'GOOGLE_SHEETS', 'GMAIL', 'GEMINI']:
                raise ValueError(f"Unknown service: {service_name}")
            
            # Check if token exists and is not expired
            if service_name in TOKEN_CACHE and not is_token_expired(service_name):
                return TOKEN_CACHE[service_name]
            
            # Get new token based on service
            if service_name == 'CAPITAL_ONE':
                auth_data = self.authenticate_capital_one()
                return auth_data.get('access_token', '')
            
            elif service_name == 'GEMINI':
                auth_data = self.authenticate_gemini()
                return auth_data.get('api_key', '')
            
            # Google services use different authentication pattern
            else:
                return None
                
        except Exception as e:
            error_msg = f"Failed to get token for {service_name}: {str(e)}"
            logger.error(error_msg, context={"service": service_name, "error": str(e)})
            raise AuthenticationError(error_msg, service_name)
    
    def refresh_token(self, service_name: str) -> bool:
        """
        Refresh authentication token for a specific service
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if refresh successful, False otherwise
        """
        try:
            # Clear cached token for the service
            clear_token_cache(service_name)
            
            # Attempt to authenticate again
            if service_name == 'CAPITAL_ONE':
                self.authenticate_capital_one()
            elif service_name == 'GEMINI':
                self.authenticate_gemini()
            elif service_name == 'GOOGLE_SHEETS':
                # For Google services, refresh credentials
                if service_name in self.credentials_cache:
                    credentials = self.credentials_cache[service_name]
                    auth_req = google.auth.transport.requests.Request()
                    credentials.refresh(auth_req)
                else:
                    self.authenticate_google_sheets()
            elif service_name == 'GMAIL':
                if service_name in self.credentials_cache:
                    credentials = self.credentials_cache[service_name]
                    auth_req = google.auth.transport.requests.Request()
                    credentials.refresh(auth_req)
                else:
                    self.authenticate_gmail()
            else:
                raise ValueError(f"Unknown service: {service_name}")
            
            logger.info(f"Successfully refreshed token for {service_name}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to refresh token for {service_name}: {str(e)}"
            logger.error(error_msg, context={"service": service_name, "error": str(e)})
            return False
    
    def get_auth_headers(self, service_name: str) -> Dict:
        """
        Get authentication headers for API requests
        
        Args:
            service_name: Name of the service
            
        Returns:
            Headers dictionary with authentication
        """
        try:
            token = self.get_token(service_name)
            
            # Create appropriate headers based on service
            if service_name == 'CAPITAL_ONE':
                return {"Authorization": f"Bearer {token}"}
            
            elif service_name == 'GEMINI':
                return {"x-api-key": token}
            
            # Google services use the credentials object directly
            else:
                return {}
                
        except Exception as e:
            error_msg = f"Failed to get auth headers for {service_name}: {str(e)}"
            logger.error(error_msg, context={"service": service_name, "error": str(e)})
            raise AuthenticationError(error_msg, service_name)
    
    def validate_credentials(self) -> bool:
        """
        Validate that all required API credentials are accessible
        
        Returns:
            True if all credentials are valid, False otherwise
        """
        validation_results = {}
        
        # Attempt to authenticate with each required API
        try:
            # Capital One
            self.authenticate_capital_one()
            validation_results['CAPITAL_ONE'] = True
        except Exception as e:
            logger.error(f"Capital One credential validation failed: {str(e)}")
            validation_results['CAPITAL_ONE'] = False
        
        try:
            # Google Sheets
            self.authenticate_google_sheets()
            validation_results['GOOGLE_SHEETS'] = True
        except Exception as e:
            logger.error(f"Google Sheets credential validation failed: {str(e)}")
            validation_results['GOOGLE_SHEETS'] = False
        
        try:
            # Gmail
            self.authenticate_gmail()
            validation_results['GMAIL'] = True
        except Exception as e:
            logger.error(f"Gmail credential validation failed: {str(e)}")
            validation_results['GMAIL'] = False
        
        try:
            # Gemini
            self.authenticate_gemini()
            validation_results['GEMINI'] = True
        except Exception as e:
            logger.error(f"Gemini credential validation failed: {str(e)}")
            validation_results['GEMINI'] = False
        
        # Check if all validations passed
        all_valid = all(validation_results.values())
        
        if all_valid:
            logger.info("All API credentials validated successfully")
        else:
            failed_services = [service for service, result in validation_results.items() if not result]
            logger.error(f"Credential validation failed for: {', '.join(failed_services)}")
        
        return all_valid