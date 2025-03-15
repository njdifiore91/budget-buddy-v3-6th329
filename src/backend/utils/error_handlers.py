"""
error_handlers.py - Error handling utilities for the Budget Management Application

This module provides standardized error handling mechanisms including retry logic
with exponential backoff, error classification, and custom exception types to
ensure robust handling of failures across all application components.
"""

import functools  # standard library
import time  # standard library
import random  # standard library
import traceback  # standard library
import sys  # standard library
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union  # standard library
import requests  # requests 2.31.0+

from ..config.settings import RETRY_SETTINGS, APP_SETTINGS
from ..config.logging_config import get_logger

# Set up logger
logger = get_logger('error_handlers')


class APIError(Exception):
    """Custom exception for API-related errors"""
    
    def __init__(self, message: str, api_name: str, operation: str, 
                 status_code: Optional[int] = None, 
                 response_text: Optional[str] = None,
                 context: Optional[Dict] = None):
        """
        Initialize API error with detailed context
        
        Args:
            message: Error message
            api_name: Name of the API where the error occurred
            operation: Operation being performed when the error occurred
            status_code: HTTP status code (if applicable)
            response_text: Response text from the API (if available)
            context: Additional context information
        """
        super().__init__(message)
        self.api_name = api_name
        self.operation = operation
        self.status_code = status_code
        self.response_text = response_text
        self.context = context or {}
    
    def to_dict(self) -> Dict:
        """
        Convert the exception to a dictionary for structured logging
        
        Returns:
            Dictionary representation of the error
        """
        error_dict = {
            'message': str(self),
            'api_name': self.api_name,
            'operation': self.operation
        }
        
        if self.status_code is not None:
            error_dict['status_code'] = self.status_code
            
        if self.response_text is not None:
            error_dict['response_text'] = self.response_text
            
        if self.context:
            error_dict['context'] = self.context
            
        return error_dict


class ValidationError(Exception):
    """Custom exception for data validation errors"""
    
    def __init__(self, message: str, data_type: str, 
                 validation_errors: Optional[Dict] = None,
                 context: Optional[Dict] = None):
        """
        Initialize validation error with detailed context
        
        Args:
            message: Error message
            data_type: Type of data that failed validation
            validation_errors: Detailed validation errors
            context: Additional context information
        """
        super().__init__(message)
        self.data_type = data_type
        self.validation_errors = validation_errors or {}
        self.context = context or {}
    
    def to_dict(self) -> Dict:
        """
        Convert the exception to a dictionary for structured logging
        
        Returns:
            Dictionary representation of the error
        """
        error_dict = {
            'message': str(self),
            'data_type': self.data_type
        }
        
        if self.validation_errors:
            error_dict['validation_errors'] = self.validation_errors
            
        if self.context:
            error_dict['context'] = self.context
            
        return error_dict


class AuthenticationError(Exception):
    """Custom exception for authentication errors"""
    
    def __init__(self, message: str, service_name: str, 
                 auth_context: Optional[Dict] = None):
        """
        Initialize authentication error with service details
        
        Args:
            message: Error message
            service_name: Name of the service authentication failed for
            auth_context: Authentication context information
        """
        super().__init__(message)
        self.service_name = service_name
        self.auth_context = auth_context or {}
    
    def to_dict(self) -> Dict:
        """
        Convert the exception to a dictionary for structured logging
        
        Returns:
            Dictionary representation of the error
        """
        error_dict = {
            'message': str(self),
            'service_name': self.service_name
        }
        
        if self.auth_context:
            # Be careful with auth context - mask sensitive data
            masked_context = {k: '[REDACTED]' if k in ('token', 'key', 'secret', 'password') 
                             else v for k, v in self.auth_context.items()}
            error_dict['auth_context'] = masked_context
            
        return error_dict


def retry_with_backoff(exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = (Exception,), 
                      max_retries: Optional[int] = None, 
                      delay: Optional[int] = None,
                      backoff_factor: Optional[float] = None,
                      jitter: Optional[float] = None) -> Callable:
    """
    Decorator that retries a function with exponential backoff on specified exceptions
    
    Args:
        exceptions: Exception or tuple of exception types to catch and retry
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Multiplier applied to delay between retries
        jitter: Random factor to add to delay to prevent thundering herd
        
    Returns:
        Decorated function with retry logic
    """
    # Use defaults from settings if parameters are None
    max_retries = max_retries if max_retries is not None else RETRY_SETTINGS['DEFAULT_MAX_RETRIES']
    delay = delay if delay is not None else RETRY_SETTINGS['DEFAULT_RETRY_DELAY']
    backoff_factor = backoff_factor if backoff_factor is not None else RETRY_SETTINGS['DEFAULT_RETRY_BACKOFF_FACTOR']
    jitter = jitter if jitter is not None else RETRY_SETTINGS['DEFAULT_RETRY_JITTER']
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Initialize retry counter
            retries = 0
            
            while True:
                try:
                    # Attempt to execute the function
                    return func(*args, **kwargs)
                except exceptions as e:
                    # If we've exceeded max retries, re-raise the exception
                    if retries >= max_retries:
                        logger.warning(
                            f"Maximum retries ({max_retries}) exceeded for {func.__name__}",
                            context={"exception": str(e), "retries": retries}
                        )
                        raise
                    
                    # Calculate backoff with jitter
                    wait_time = delay * (backoff_factor ** retries)
                    if jitter:
                        wait_time = wait_time + (wait_time * random.uniform(-jitter, jitter))
                    
                    # Log retry attempt
                    logger.info(
                        f"Retrying {func.__name__} after exception: {str(e)}. "
                        f"Retry {retries + 1}/{max_retries} in {wait_time:.2f}s",
                        context={"exception": str(e), "retry_count": retries + 1}
                    )
                    
                    # Wait before retrying
                    time.sleep(wait_time)
                    
                    # Increment retry counter
                    retries += 1
                    
        return wrapper
    return decorator


def is_retriable_error(exception: Exception) -> bool:
    """
    Determines if an error should be retried based on its type and attributes
    
    Args:
        exception: The exception to check
        
    Returns:
        True if the error is retriable, False otherwise
    """
    # Handle requests library exceptions
    if isinstance(exception, requests.RequestException):
        # HTTP errors can be checked by status code
        if isinstance(exception, requests.HTTPError) and hasattr(exception, 'response'):
            return exception.response.status_code in RETRY_SETTINGS['RETRIABLE_STATUS_CODES']
        
        # Network-related errors are typically transient
        if isinstance(exception, (requests.ConnectionError, requests.Timeout)):
            return True
    
    # Add more retriable error types as needed
    
    return False


def handle_api_error(exception: Exception, api_name: str, operation: str, 
                   context: Optional[Dict] = None) -> Dict:
    """
    Standardized handling of API errors with context information
    
    Args:
        exception: The exception that occurred
        api_name: Name of the API where the error occurred
        operation: Operation being performed when the error occurred
        context: Additional context information
        
    Returns:
        Standardized error response dictionary
    """
    # Extract status code and response text if available
    status_code = None
    response_text = None
    
    if isinstance(exception, requests.HTTPError) and hasattr(exception, 'response'):
        status_code = exception.response.status_code
        response_text = exception.response.text
    
    # Create error response
    error_response = {
        'status': 'error',
        'api_name': api_name,
        'operation': operation,
        'error_message': str(exception),
    }
    
    # Add status code and response if available
    if status_code:
        error_response['status_code'] = status_code
    
    if response_text:
        error_response['response_text'] = response_text
    
    # Add context if provided
    if context:
        error_response['context'] = context
    
    # Add stack trace in debug mode
    if APP_SETTINGS['DEBUG']:
        error_response['stack_trace'] = traceback.format_exc()
    
    # Log the error with appropriate severity
    log_method = logger.error
    
    # Use critical log level for 5xx errors
    if status_code and status_code >= 500:
        log_method = logger.critical
    
    log_method(
        f"API Error in {api_name}.{operation}: {str(exception)}",
        context=error_response
    )
    
    return error_response


def handle_validation_error(exception: Exception, data_type: str, 
                          validation_context: Optional[Dict] = None) -> Dict:
    """
    Standardized handling of data validation errors
    
    Args:
        exception: The exception that occurred
        data_type: Type of data that failed validation
        validation_context: Additional context about the validation
        
    Returns:
        Standardized validation error response
    """
    # Create error response
    error_response = {
        'status': 'error',
        'error_type': 'validation',
        'data_type': data_type,
        'error_message': str(exception),
    }
    
    # Add validation context if provided
    if validation_context:
        error_response['validation_context'] = validation_context
    
    # Add validation errors if available
    if hasattr(exception, 'validation_errors'):
        error_response['validation_errors'] = exception.validation_errors
    
    # Add stack trace in debug mode
    if APP_SETTINGS['DEBUG']:
        error_response['stack_trace'] = traceback.format_exc()
    
    # Log the error
    logger.warning(
        f"Validation Error for {data_type}: {str(exception)}",
        context=error_response
    )
    
    return error_response


def handle_auth_error(exception: Exception, service_name: str, 
                    refresh_function: Optional[Callable] = None,
                    auth_context: Optional[Dict] = None) -> Tuple[bool, Any]:
    """
    Handle authentication errors with token refresh capability
    
    Args:
        exception: The authentication exception
        service_name: Name of the service authentication failed for
        refresh_function: Optional function to refresh credentials
        auth_context: Authentication context information
        
    Returns:
        Tuple of (success: bool, new_token_or_error: Any)
    """
    # Log the authentication error
    logger.warning(
        f"Authentication error for {service_name}: {str(exception)}",
        context={'service': service_name, 'context': auth_context or {}}
    )
    
    # If refresh function is provided, attempt to refresh the token
    if refresh_function:
        try:
            # Attempt to refresh credentials
            logger.info(f"Attempting to refresh credentials for {service_name}")
            new_token = refresh_function()
            logger.info(f"Successfully refreshed credentials for {service_name}")
            
            # Return success and the new token
            return True, new_token
        except Exception as refresh_error:
            # Log the refresh failure
            error_response = {
                'status': 'error',
                'error_type': 'authentication',
                'service': service_name,
                'error_message': f"Failed to refresh token: {str(refresh_error)}",
                'original_error': str(exception)
            }
            
            # Add stack trace in debug mode
            if APP_SETTINGS['DEBUG']:
                error_response['stack_trace'] = traceback.format_exc()
            
            logger.error(
                f"Token refresh failed for {service_name}: {str(refresh_error)}",
                context=error_response
            )
            
            # Return failure and the error response
            return False, error_response
    
    # If no refresh function, just return failure and format the error
    error_response = {
        'status': 'error',
        'error_type': 'authentication',
        'service': service_name,
        'error_message': str(exception)
    }
    
    # Add context if provided
    if auth_context:
        # Mask sensitive information in auth context
        masked_context = {k: '[REDACTED]' if k in ('token', 'key', 'secret', 'password') 
                        else v for k, v in auth_context.items()}
        error_response['auth_context'] = masked_context
    
    # Add stack trace in debug mode
    if APP_SETTINGS['DEBUG']:
        error_response['stack_trace'] = traceback.format_exc()
    
    return False, error_response


def format_exception_for_log(exception: Exception) -> Dict:
    """
    Formats an exception for structured logging
    
    Args:
        exception: The exception to format
        
    Returns:
        Formatted exception details as a dictionary
    """
    exception_details = {
        'type': exception.__class__.__name__,
        'message': str(exception)
    }
    
    # Add status code if available
    if hasattr(exception, 'status_code'):
        exception_details['status_code'] = exception.status_code
    
    # Add response text if available
    if hasattr(exception, 'response') and hasattr(exception.response, 'text'):
        exception_details['response_text'] = exception.response.text
    
    # Add traceback in debug mode
    if APP_SETTINGS['DEBUG']:
        exception_details['traceback'] = traceback.format_exc()
    
    return exception_details


def safe_execute(func: Callable, *args, default_value: Any = None, **kwargs) -> Tuple[bool, Any]:
    """
    Safely execute a function with fallback on error
    
    Args:
        func: Function to execute
        *args: Positional arguments for the function
        default_value: Value to return on error
        **kwargs: Keyword arguments for the function
        
    Returns:
        Tuple of (success: bool, result_or_error: Any)
    """
    try:
        # Attempt to execute the function
        result = func(*args, **kwargs)
        return True, result
    except Exception as e:
        # Log the error
        logger.warning(
            f"Error in safe_execute for {func.__name__}: {str(e)}",
            context={'args': args, 'kwargs': kwargs, 'exception': str(e)}
        )
        
        # Return default value or formatted exception
        if default_value is not None:
            return False, default_value
        else:
            return False, format_exception_for_log(e)