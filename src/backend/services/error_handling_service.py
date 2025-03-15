"""
error_handling_service.py - Core error handling service for the Budget Management Application

This module provides centralized error handling, exception management, and recovery strategies
for the application. It implements circuit breaker patterns, fallback mechanisms, and graceful
degradation to ensure system resilience during failures.
"""

import functools
import time
import random
import traceback
import sys
from typing import Dict, List, Any, Optional, Callable, Union, TypeVar, cast

import requests

from .logging_service import get_component_logger, log_exception, LoggingContext
from ..config.settings import RETRY_SETTINGS, APP_SETTINGS
from ..utils.error_handlers import (
    APIError, ValidationError, AuthenticationError,
    retry_with_backoff, is_retriable_error
)

# Set up logger for the error handling service
logger = get_component_logger('error_handling_service')

# Global circuit breaker state tracker
CIRCUIT_BREAKER_STATES = {'services': {}}

def handle_error(exception: Exception, component: str, operation: str, context: Dict) -> Dict:
    """
    Central error handling function that processes exceptions based on their type.
    
    Args:
        exception: The exception that occurred
        component: Component where the exception occurred
        operation: Operation being performed when exception occurred
        context: Additional context information
        
    Returns:
        Standardized error response with context and recovery information
    """
    # Log the exception with component, operation, and context
    log_exception(logger, exception, f"Error in {component}.{operation}", context)
    
    # Create base error response
    error_response = {
        'status': 'error',
        'component': component,
        'operation': operation,
        'error_message': str(exception),
        'error_type': exception.__class__.__name__,
        'timestamp': time.time()
    }
    
    # Process different exception types
    if isinstance(exception, APIError):
        error_details = handle_api_exception(exception, context)
        error_response['error_type'] = 'api_error'
        error_response.update(error_details)
    
    elif isinstance(exception, ValidationError):
        error_details = handle_validation_exception(exception, context)
        error_response['error_type'] = 'validation_error'
        error_response.update(error_details)
    
    elif isinstance(exception, AuthenticationError):
        error_details = handle_auth_exception(exception, context)
        error_response['error_type'] = 'authentication_error'
        error_response.update(error_details)
    
    else:
        # Generic exception handling
        if APP_SETTINGS['DEBUG']:
            error_response['stack_trace'] = traceback.format_exc()
    
    # Add recovery information if available
    if hasattr(exception, 'recovery_steps'):
        error_response['recovery_steps'] = exception.recovery_steps
    
    # Add context information
    if context:
        error_response['context'] = context
    
    return error_response

def handle_api_exception(exception: APIError, context: Dict) -> Dict:
    """
    Handles API-specific exceptions with retry and circuit breaker patterns.
    
    Args:
        exception: The API exception that occurred
        context: Additional context information
        
    Returns:
        API error response with service status
    """
    # Extract API information from exception
    api_name = exception.api_name
    operation = exception.operation
    status_code = exception.status_code
    
    # Check if error is retriable
    is_retriable = is_retriable_error(exception) if status_code else False
    
    # Update circuit breaker state for this service
    circuit_state = get_circuit_state(api_name)
    
    # Create error response
    error_response = {
        'api_name': api_name,
        'operation': operation,
        'retriable': is_retriable,
        'circuit_state': circuit_state['state']
    }
    
    # Add status code and response text if available
    if status_code:
        error_response['status_code'] = status_code
    
    if hasattr(exception, 'response_text') and exception.response_text:
        error_response['response_text'] = exception.response_text
    
    # Add recovery suggestions based on error type
    if is_retriable:
        error_response['recovery_suggestion'] = (
            "This error is transient and can be retried. "
            f"Circuit breaker state: {circuit_state['state']}"
        )
    else:
        error_response['recovery_suggestion'] = (
            "This error is not retriable and requires manual intervention."
        )
    
    return error_response

def handle_validation_exception(exception: ValidationError, context: Dict) -> Dict:
    """
    Handles data validation exceptions with detailed validation context.
    
    Args:
        exception: The validation exception that occurred
        context: Additional context information
        
    Returns:
        Validation error response with detailed validation failures
    """
    # Extract validation information from exception
    data_type = exception.data_type
    validation_errors = exception.validation_errors
    
    # Create error response
    error_response = {
        'data_type': data_type,
        'validation_errors': validation_errors
    }
    
    # Add suggestions for fixing validation issues
    error_response['recovery_suggestion'] = (
        "Check the provided data against the validation requirements. "
        "Correct the validation errors and retry the operation."
    )
    
    return error_response

def handle_auth_exception(exception: AuthenticationError, context: Dict, 
                         refresh_callback: Callable = None) -> Dict:
    """
    Handles authentication exceptions with token refresh capabilities.
    
    Args:
        exception: The authentication exception that occurred
        context: Additional context information
        refresh_callback: Optional callback function to refresh authentication
        
    Returns:
        Authentication error response with refresh status
    """
    # Extract service name from exception
    service_name = exception.service_name
    
    # Create error response
    error_response = {
        'service_name': service_name,
        'refresh_attempted': False,
    }
    
    # Try to refresh authentication if callback provided
    if refresh_callback:
        error_response['refresh_attempted'] = True
        
        try:
            # Attempt to refresh credentials
            logger.info(f"Attempting to refresh authentication for {service_name}")
            refresh_result = refresh_callback()
            
            error_response['refresh_successful'] = True
            error_response['recovery_suggestion'] = (
                "Authentication has been refreshed. Retry the operation."
            )
        except Exception as refresh_error:
            # Log refresh failure
            log_exception(logger, refresh_error, 
                         f"Failed to refresh authentication for {service_name}", 
                         context)
            
            error_response['refresh_successful'] = False
            error_response['refresh_error'] = str(refresh_error)
            error_response['recovery_suggestion'] = (
                "Authentication refresh failed. Manual intervention required."
            )
    else:
        error_response['recovery_suggestion'] = (
            "Authentication failed. Verify credentials and retry."
        )
    
    return error_response

def with_error_handling(component: str, operation: str, context: Dict = None):
    """
    Decorator that wraps functions with standardized error handling.
    
    Args:
        component: Component name for error context
        operation: Operation name for error context
        context: Additional context information
        
    Returns:
        Decorated function with error handling
    """
    if context is None:
        context = {}
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create logging context for consistent logging
            with LoggingContext(logger, f"{component}.{operation}", context) as log_ctx:
                try:
                    # Execute the function
                    return func(*args, **kwargs)
                except Exception as e:
                    # Handle the exception
                    error_response = handle_error(e, component, operation, context)
                    
                    # Return the error response instead of raising
                    return error_response
        
        return wrapper
    
    return decorator

def with_circuit_breaker(service_name: str, failure_threshold: int = 5, 
                        recovery_timeout: int = 60, fallback_function: Callable = None):
    """
    Implements circuit breaker pattern to prevent repeated calls to failing services.
    
    Args:
        service_name: Name of the service to protect
        failure_threshold: Number of failures before tripping the circuit
        recovery_timeout: Time in seconds before testing if service has recovered
        fallback_function: Function to call when circuit is open
        
    Returns:
        Decorated function with circuit breaker protection
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get current circuit state
            circuit = get_circuit_state(service_name)
            current_time = time.time()
            
            # Check if circuit is OPEN (tripped)
            if circuit['state'] == 'OPEN':
                # Check if recovery timeout has elapsed
                if current_time - circuit['last_failure_time'] > recovery_timeout:
                    # Set to HALF_OPEN to test if service has recovered
                    CIRCUIT_BREAKER_STATES['services'][service_name]['state'] = 'HALF_OPEN'
                    logger.info(f"Circuit for {service_name} changed from OPEN to HALF_OPEN")
                else:
                    # Circuit is still OPEN, use fallback or return error
                    logger.warning(
                        f"Circuit for {service_name} is OPEN. "
                        f"Will try again in {int(recovery_timeout - (current_time - circuit['last_failure_time']))}s")
                    
                    if fallback_function:
                        return fallback_function(*args, **kwargs)
                    else:
                        return {
                            'status': 'error',
                            'error_type': 'circuit_open',
                            'service_name': service_name,
                            'message': f"Circuit breaker for {service_name} is open",
                            'retry_after': int(recovery_timeout - (current_time - circuit['last_failure_time']))
                        }
            
            # Circuit is CLOSED or HALF_OPEN, try the function
            try:
                result = func(*args, **kwargs)
                
                # If successful and was HALF_OPEN, reset to CLOSED
                if circuit['state'] == 'HALF_OPEN':
                    CIRCUIT_BREAKER_STATES['services'][service_name] = {
                        'state': 'CLOSED',
                        'failure_count': 0,
                        'last_success_time': current_time,
                        'last_failure_time': circuit['last_failure_time']
                    }
                    logger.info(f"Circuit for {service_name} reset to CLOSED after successful test")
                
                return result
            
            except Exception as e:
                # Increment failure count
                service_circuit = CIRCUIT_BREAKER_STATES['services'].get(service_name, {
                    'state': 'CLOSED',
                    'failure_count': 0,
                    'last_success_time': 0,
                    'last_failure_time': 0
                })
                
                service_circuit['failure_count'] += 1
                service_circuit['last_failure_time'] = current_time
                
                # Trip circuit if failure threshold exceeded
                if service_circuit['failure_count'] >= failure_threshold:
                    service_circuit['state'] = 'OPEN'
                    logger.warning(
                        f"Circuit for {service_name} tripped to OPEN after {service_circuit['failure_count']} failures")
                
                CIRCUIT_BREAKER_STATES['services'][service_name] = service_circuit
                
                # Re-raise the exception
                raise
        
        return wrapper
    
    return decorator

def get_circuit_state(service_name: str) -> Dict:
    """
    Gets the current circuit breaker state for a service.
    
    Args:
        service_name: Name of the service to check
        
    Returns:
        Circuit breaker state information
    """
    # Initialize state if it doesn't exist
    if service_name not in CIRCUIT_BREAKER_STATES['services']:
        CIRCUIT_BREAKER_STATES['services'][service_name] = {
            'state': 'CLOSED',
            'failure_count': 0,
            'last_success_time': 0,
            'last_failure_time': 0
        }
    
    return CIRCUIT_BREAKER_STATES['services'][service_name]

def reset_circuit(service_name: str) -> bool:
    """
    Manually resets the circuit breaker for a service.
    
    Args:
        service_name: Name of the service to reset
        
    Returns:
        True if reset was successful, False if service not found
    """
    if service_name in CIRCUIT_BREAKER_STATES['services']:
        CIRCUIT_BREAKER_STATES['services'][service_name] = {
            'state': 'CLOSED',
            'failure_count': 0,
            'last_success_time': time.time(),
            'last_failure_time': 0
        }
        
        logger.info(f"Circuit for {service_name} manually reset to CLOSED")
        return True
    
    return False

def with_fallback(fallback_function: Callable, exception_types: tuple = (Exception,)):
    """
    Decorator that provides fallback mechanism when a function fails.
    
    Args:
        fallback_function: Function to call when primary function fails
        exception_types: Tuple of exception types to catch
        
    Returns:
        Decorated function with fallback capability
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Attempt to execute the function
                return func(*args, **kwargs)
            except exception_types as e:
                # Call fallback function with original args and the exception
                return fallback_function(*args, exception=e, **kwargs)
        
        return wrapper
    
    return decorator

def create_error_response(error_type: str, message: str, details: Dict = None, context: Dict = None) -> Dict:
    """
    Creates a standardized error response dictionary.
    
    Args:
        error_type: Type of error (api, validation, authentication, etc.)
        message: Error message
        details: Additional error details
        context: Context information
        
    Returns:
        Standardized error response
    """
    response = {
        'status': 'error',
        'error_type': error_type,
        'message': message,
        'timestamp': time.time()
    }
    
    # Add details if provided
    if details:
        response['details'] = details
    
    # Add context if provided (with sensitive data masked)
    if context:
        # Simple masking of sensitive keys for this response
        masked_context = {}
        sensitive_keys = ['password', 'token', 'secret', 'key', 'credential']
        
        for k, v in context.items():
            if any(sensitive in k.lower() for sensitive in sensitive_keys):
                masked_context[k] = '[REDACTED]'
            else:
                masked_context[k] = v
        
        response['context'] = masked_context
    
    # Add stack trace in debug mode
    if APP_SETTINGS['DEBUG']:
        response['stack_trace'] = traceback.format_exc()
    
    return response

def graceful_degradation(exception: Exception, component: str, operation: str, 
                         context: Dict, default_value: Any = None) -> tuple:
    """
    Implements graceful degradation by continuing with reduced functionality.
    
    Args:
        exception: The exception that occurred
        component: Component where the exception occurred
        operation: Operation being performed when exception occurred
        context: Additional context information
        default_value: Default value to return when degrading
        
    Returns:
        Tuple of (success, result_or_error)
    """
    # Log the exception with degradation notice
    logger.warning(
        f"Gracefully degrading {component}.{operation} due to error: {str(exception)}",
        extra={'context': context}
    )
    
    # Create error response
    error_response = handle_error(exception, component, operation, context)
    
    # Add degradation information
    error_response['degraded'] = True
    error_response['degradation_reason'] = str(exception)
    
    # Return with default value if provided, otherwise return error response
    if default_value is not None:
        return False, default_value
    else:
        return False, error_response

class ErrorHandlingService:
    """
    Service that provides centralized error handling for the application.
    """
    
    def __init__(self):
        """
        Initializes the error handling service.
        """
        # Initialize error handlers for different error types
        self.error_handlers = {}
        
        # Initialize fallback handlers for different components
        self.fallback_handlers = {}
        
        # Register default handlers for common error types
        self.register_error_handler(APIError, handle_api_exception)
        self.register_error_handler(ValidationError, handle_validation_exception)
        self.register_error_handler(AuthenticationError, handle_auth_exception)
        
        logger.info("ErrorHandlingService initialized")
    
    def register_error_handler(self, error_type: type, handler_function: Callable) -> None:
        """
        Registers a custom error handler for a specific error type.
        
        Args:
            error_type: The exception type to handle
            handler_function: Function that handles this exception type
        """
        if not callable(handler_function):
            raise ValueError("Handler function must be callable")
        
        self.error_handlers[error_type] = handler_function
        logger.info(f"Registered handler for {error_type.__name__}")
    
    def register_fallback(self, component: str, operation: str, fallback_function: Callable) -> None:
        """
        Registers a fallback handler for a specific component and operation.
        
        Args:
            component: Component name
            operation: Operation name
            fallback_function: Function to call as fallback
        """
        if not callable(fallback_function):
            raise ValueError("Fallback function must be callable")
        
        if component not in self.fallback_handlers:
            self.fallback_handlers[component] = {}
        
        self.fallback_handlers[component][operation] = fallback_function
        logger.info(f"Registered fallback for {component}.{operation}")
    
    def handle_exception(self, exception: Exception, component: str, operation: str, context: Dict = None) -> Dict:
        """
        Handles an exception using registered handlers or defaults.
        
        Args:
            exception: The exception that occurred
            component: Component where the exception occurred
            operation: Operation being performed when exception occurred
            context: Additional context information
            
        Returns:
            Error response from appropriate handler
        """
        if context is None:
            context = {}
        
        # Determine the appropriate handler based on exception type
        handler = None
        for exc_type, exc_handler in self.error_handlers.items():
            if isinstance(exception, exc_type):
                handler = exc_handler
                break
        
        # Use the handler if found, otherwise use generic handling
        if handler:
            error_response = handler(exception, context)
        else:
            error_response = handle_error(exception, component, operation, context)
        
        # Check if a fallback exists for this component and operation
        fallback = None
        if component in self.fallback_handlers and operation in self.fallback_handlers[component]:
            fallback = self.fallback_handlers[component][operation]
        
        # Use fallback if available and appropriate
        if fallback and error_response.get('retriable', False) is False:
            try:
                fallback_result = fallback(context=context, error=error_response)
                error_response['fallback_used'] = True
                error_response['fallback_result'] = fallback_result
            except Exception as fallback_error:
                log_exception(logger, fallback_error, f"Fallback for {component}.{operation} failed", context)
                error_response['fallback_used'] = False
                error_response['fallback_error'] = str(fallback_error)
        
        return error_response
    
    def with_component_error_handling(self, component: str, operation: str, context: Dict = None) -> Callable:
        """
        Creates a decorator for component-specific error handling.
        
        Args:
            component: Component name
            operation: Operation name
            context: Additional context information
            
        Returns:
            Decorator function for error handling
        """
        if context is None:
            context = {}
        
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    return self.handle_exception(e, component, operation, context)
            
            return wrapper
        
        return decorator

class CircuitBreaker:
    """
    Implementation of the circuit breaker pattern for service resilience.
    """
    
    def __init__(self, default_failure_threshold: int = 5, default_recovery_timeout: int = 60):
        """
        Initializes the circuit breaker.
        
        Args:
            default_failure_threshold: Default number of failures before tripping circuit
            default_recovery_timeout: Default time in seconds before testing recovery
        """
        # Dictionary to track circuit state for each service
        self.circuits = {}
        
        # Default settings
        self.default_failure_threshold = default_failure_threshold
        self.default_recovery_timeout = default_recovery_timeout
        
        logger.info(f"CircuitBreaker initialized with threshold={default_failure_threshold}, "
                   f"timeout={default_recovery_timeout}s")
    
    def get_circuit(self, service_name: str) -> Dict:
        """
        Gets the current circuit state for a service.
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            Circuit state information
        """
        # Initialize circuit if it doesn't exist
        if service_name not in self.circuits:
            self.circuits[service_name] = {
                'state': 'CLOSED',
                'failure_count': 0,
                'last_success_time': 0,
                'last_failure_time': 0
            }
        
        return self.circuits[service_name]
    
    def record_success(self, service_name: str) -> None:
        """
        Records a successful operation for a service.
        
        Args:
            service_name: Name of the service
        """
        circuit = self.get_circuit(service_name)
        current_time = time.time()
        
        # If circuit was HALF_OPEN, reset to CLOSED
        if circuit['state'] == 'HALF_OPEN':
            circuit['state'] = 'CLOSED'
            logger.info(f"Circuit for {service_name} reset to CLOSED after successful test")
        
        # Reset failure count and update last success time
        circuit['failure_count'] = 0
        circuit['last_success_time'] = current_time
        
        # Update circuit
        self.circuits[service_name] = circuit
    
    def record_failure(self, service_name: str, exception: Exception, 
                      failure_threshold: int = None) -> bool:
        """
        Records a failed operation for a service.
        
        Args:
            service_name: Name of the service
            exception: The exception that occurred
            failure_threshold: Number of failures before tripping circuit
            
        Returns:
            True if circuit is now open, False otherwise
        """
        circuit = self.get_circuit(service_name)
        current_time = time.time()
        
        # Use provided threshold or default
        if failure_threshold is None:
            failure_threshold = self.default_failure_threshold
        
        # Increment failure count and update last failure time
        circuit['failure_count'] += 1
        circuit['last_failure_time'] = current_time
        
        # Trip circuit if failure threshold exceeded
        if circuit['failure_count'] >= failure_threshold:
            old_state = circuit['state']
            circuit['state'] = 'OPEN'
            
            if old_state != 'OPEN':
                logger.warning(
                    f"Circuit for {service_name} tripped to OPEN after {circuit['failure_count']} failures: {str(exception)}")
        
        # Update circuit
        self.circuits[service_name] = circuit
        
        # Return whether circuit is open
        return circuit['state'] == 'OPEN'
    
    def is_circuit_open(self, service_name: str) -> bool:
        """
        Checks if the circuit for a service is open (tripped).
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if circuit is open, False otherwise
        """
        circuit = self.get_circuit(service_name)
        current_time = time.time()
        
        # If circuit is OPEN, check if recovery timeout has elapsed
        if circuit['state'] == 'OPEN':
            recovery_time_elapsed = current_time - circuit['last_failure_time'] > self.default_recovery_timeout
            
            if recovery_time_elapsed:
                # Change to HALF_OPEN to test if service has recovered
                circuit['state'] = 'HALF_OPEN'
                self.circuits[service_name] = circuit
                logger.info(f"Circuit for {service_name} changed from OPEN to HALF_OPEN for testing")
                return False
            
            return True
        
        return False
    
    def reset(self, service_name: str) -> bool:
        """
        Manually resets the circuit for a service to closed state.
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if reset was successful, False if service not found
        """
        if service_name in self.circuits:
            self.circuits[service_name] = {
                'state': 'CLOSED',
                'failure_count': 0,
                'last_success_time': time.time(),
                'last_failure_time': 0
            }
            
            logger.info(f"Circuit for {service_name} manually reset to CLOSED")
            return True
        
        return False
    
    def execute(self, service_name: str, function: Callable, args: tuple = None, kwargs: Dict = None,
                fallback: Callable = None, failure_threshold: int = None, recovery_timeout: int = None):
        """
        Executes a function with circuit breaker protection.
        
        Args:
            service_name: Name of the service
            function: Function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            fallback: Function to call when circuit is open
            failure_threshold: Number of failures before tripping circuit
            recovery_timeout: Time in seconds before testing recovery
            
        Returns:
            Result of function or fallback
        """
        args = args or ()
        kwargs = kwargs or {}
        
        # Use provided thresholds or defaults
        if failure_threshold is None:
            failure_threshold = self.default_failure_threshold
        
        if recovery_timeout is None:
            recovery_timeout = self.default_recovery_timeout
        
        # Check if circuit is open
        if self.is_circuit_open(service_name):
            logger.warning(f"Circuit for {service_name} is OPEN, preventing execution")
            
            # Use fallback if provided
            if fallback:
                return fallback(*args, **kwargs)
            else:
                raise Exception(f"Circuit breaker for {service_name} is open")
        
        # Execute the function
        try:
            result = function(*args, **kwargs)
            self.record_success(service_name)
            return result
        except Exception as e:
            # Record failure and check if circuit is now open
            circuit_open = self.record_failure(service_name, e, failure_threshold)
            
            # Use fallback if circuit is now open and fallback provided
            if circuit_open and fallback:
                return fallback(*args, **kwargs)
            
            # Re-raise the exception
            raise
    
    def decorator(self, service_name: str, fallback: Callable = None,
                 failure_threshold: int = None, recovery_timeout: int = None):
        """
        Creates a decorator for circuit breaker protection.
        
        Args:
            service_name: Name of the service
            fallback: Function to call when circuit is open
            failure_threshold: Number of failures before tripping circuit
            recovery_timeout: Time in seconds before testing recovery
            
        Returns:
            Decorator function
        """
        def circuit_decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return self.execute(
                    service_name, 
                    func, 
                    args, 
                    kwargs,
                    fallback, 
                    failure_threshold, 
                    recovery_timeout
                )
            return wrapper
        
        return circuit_decorator