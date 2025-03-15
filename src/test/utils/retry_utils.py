"""
retry_utils.py - Utility module for testing retry behavior in the Budget Management Application

This module provides test helpers for verifying retry behavior, including functions
for simulating transient failures, tracking retry attempts, and validating retry patterns
to ensure the application's resilience mechanisms work correctly.
"""

import time
import functools
import pytest
from unittest.mock import MagicMock, patch, call
from typing import List, Dict, Any, Optional, Union, Callable, TypeVar, Tuple
import requests

# Import retry decorator for testing
from ...backend.utils.error_handlers import retry_with_backoff, is_retriable_error
# Import retry settings
from ...backend.config.settings import RETRY_SETTINGS

# Default test retry settings (smaller values for faster tests)
DEFAULT_TEST_RETRY_COUNT = 3
DEFAULT_TEST_RETRY_DELAY = 0.01  # Small value for faster tests
DEFAULT_TEST_BACKOFF_FACTOR = 2.0


def create_failing_function(fail_count: int, exception_type: Exception, return_value: Any) -> Callable:
    """
    Create a function that fails a specified number of times before succeeding.
    
    Args:
        fail_count: Number of times the function should fail
        exception_type: Type of exception to raise on failure
        return_value: Value to return after successful execution
        
    Returns:
        Function that fails 'fail_count' times then returns 'return_value'
    """
    counter = {'attempts': 0}
    
    def failing_function(*args, **kwargs):
        counter['attempts'] += 1
        if counter['attempts'] <= fail_count:
            raise exception_type(f"Simulated failure {counter['attempts']} of {fail_count}")
        return return_value
    
    return failing_function


def create_http_error(status_code: int, message: Optional[str] = None) -> requests.HTTPError:
    """
    Create a requests.HTTPError with a specified status code.
    
    Args:
        status_code: HTTP status code for the error
        message: Optional error message
        
    Returns:
        HTTP error with the specified status code
    """
    # Create a mock response with the specified status code
    response = MagicMock()
    response.status_code = status_code
    
    # Create and configure the HTTPError
    error = requests.HTTPError(message or f"HTTP Error: {status_code}")
    error.response = response
    
    return error


def create_connection_error(message: Optional[str] = None) -> requests.ConnectionError:
    """
    Create a requests.ConnectionError with a specified message.
    
    Args:
        message: Optional error message
        
    Returns:
        Connection error with the specified message
    """
    return requests.ConnectionError(message or "Connection error")


def create_timeout_error(message: Optional[str] = None) -> requests.Timeout:
    """
    Create a requests.Timeout with a specified message.
    
    Args:
        message: Optional error message
        
    Returns:
        Timeout error with the specified message
    """
    return requests.Timeout(message or "Request timed out")


def retry_tracker(func: Callable) -> Callable:
    """
    Decorator that tracks retry attempts of a function.
    
    Args:
        func: Function to track
        
    Returns:
        Wrapped function that tracks retry attempts
    """
    # List to store call information
    calls = []
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Record this call
        timestamp = time.time()
        calls.append({
            'timestamp': timestamp,
            'args': args,
            'kwargs': kwargs
        })
        
        # Call the original function
        return func(*args, **kwargs)
    
    # Attach the call history to the wrapper
    wrapper.calls = calls
    wrapper.tracked_func = func
    
    return wrapper


def verify_retry_attempts(tracked_func: Callable, expected_attempts: int) -> bool:
    """
    Verify that a function was retried the expected number of times.
    
    Args:
        tracked_func: Function decorated with retry_tracker
        expected_attempts: Number of expected attempts
        
    Returns:
        True if the function was called the expected number of times
    """
    if not hasattr(tracked_func, 'calls'):
        raise ValueError("Function must be decorated with retry_tracker")
    
    actual_attempts = len(tracked_func.calls)
    assert actual_attempts == expected_attempts, \
        f"Expected {expected_attempts} attempts, got {actual_attempts}"
    
    return True


def verify_backoff_pattern(tracked_func: Callable, 
                          initial_delay: Optional[float] = None, 
                          backoff_factor: Optional[float] = None,
                          tolerance: Optional[float] = 0.1) -> bool:
    """
    Verify that retry attempts followed an exponential backoff pattern.
    
    Args:
        tracked_func: Function decorated with retry_tracker
        initial_delay: Expected initial delay between retries
        backoff_factor: Expected backoff factor
        tolerance: Tolerance factor for timing variations
        
    Returns:
        True if the retry delays follow an exponential backoff pattern
    """
    if not hasattr(tracked_func, 'calls'):
        raise ValueError("Function must be decorated with retry_tracker")
    
    # Use default values if not provided
    initial_delay = initial_delay or DEFAULT_TEST_RETRY_DELAY
    backoff_factor = backoff_factor or DEFAULT_TEST_BACKOFF_FACTOR
    
    # Need at least 2 calls to verify pattern
    if len(tracked_func.calls) < 2:
        return True  # Not enough calls to verify pattern
    
    # Extract timestamps
    timestamps = [call['timestamp'] for call in tracked_func.calls]
    
    # Calculate time differences between consecutive calls
    time_diffs = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
    
    # Check if time differences follow exponential backoff pattern
    expected_delays = [initial_delay * (backoff_factor ** i) for i in range(len(time_diffs))]
    
    for i, (actual, expected) in enumerate(zip(time_diffs, expected_delays)):
        # Allow for some tolerance in timing due to execution variations
        min_expected = expected * (1 - tolerance)
        max_expected = expected * (1 + tolerance)
        
        assert min_expected <= actual <= max_expected, \
            f"Retry {i+1} delay was {actual:.4f}s, expected between {min_expected:.4f}s and {max_expected:.4f}s"
    
    return True


def mock_retry_function(success_after: int, 
                       exception_type: Exception, 
                       return_value: Any,
                       max_retries: Optional[int] = None,
                       delay: Optional[int] = None,
                       backoff_factor: Optional[float] = None) -> Tuple[Callable, Callable]:
    """
    Create a mock function with retry behavior for testing.
    
    Args:
        success_after: Number of failures before success
        exception_type: Type of exception to raise on failure
        return_value: Value to return after successful execution
        max_retries: Maximum number of retries
        delay: Initial delay between retries
        backoff_factor: Backoff factor for exponential delay
        
    Returns:
        Tuple of (retry-decorated function, original failing function)
    """
    # Create a function that fails a specific number of times then succeeds
    failing_func = create_failing_function(success_after, exception_type, return_value)
    
    # Track the function's calls
    tracked_func = retry_tracker(failing_func)
    
    # Apply retry decorator
    retry_args = {}
    if max_retries is not None:
        retry_args['max_retries'] = max_retries
    if delay is not None:
        retry_args['delay'] = delay
    if backoff_factor is not None:
        retry_args['backoff_factor'] = backoff_factor
    
    # Apply retry decorator
    retry_func = retry_with_backoff(exceptions=exception_type, **retry_args)(tracked_func)
    
    return retry_func, tracked_func


def patch_time_sleep():
    """
    Context manager that patches time.sleep for faster tests.
    
    Returns:
        Mock object for time.sleep
    """
    return patch('time.sleep')


def assert_retry_called_with_backoff(tracked_func: Callable, 
                                    expected_attempts: int,
                                    initial_delay: Optional[float] = None,
                                    backoff_factor: Optional[float] = None) -> None:
    """
    Assert that a function was retried with exponential backoff.
    
    Args:
        tracked_func: Function decorated with retry_tracker
        expected_attempts: Number of expected attempts
        initial_delay: Expected initial delay between retries
        backoff_factor: Expected backoff factor
        
    Returns:
        None, raises AssertionError if retry pattern doesn't match
    """
    # Verify the number of retry attempts
    success = verify_retry_attempts(tracked_func, expected_attempts)
    
    # Verify the backoff pattern
    if success and expected_attempts > 1:
        success = verify_backoff_pattern(tracked_func, initial_delay, backoff_factor)
    
    if not success:
        raise AssertionError(
            f"Function {tracked_func.__name__} was not retried with the expected pattern"
        )


def test_retry_behavior(func: Callable, 
                       exceptions: List[Exception], 
                       expected_retries: int,
                       should_succeed: bool) -> Tuple[bool, Any]:
    """
    Test helper to verify retry behavior of a function.
    
    Args:
        func: Function to test
        exceptions: List of exceptions to simulate
        expected_retries: Expected number of retry attempts
        should_succeed: Whether the function should eventually succeed
        
    Returns:
        Tuple of (success flag, result or exception)
    """
    # Track function calls
    tracked_func = retry_tracker(func)
    
    # Patch time.sleep to speed up tests
    with patch_time_sleep() as sleep_mock:
        try:
            # Call the function (which may raise an exception if it fails)
            result = tracked_func()
            
            # If we get here, the function succeeded
            if not should_succeed:
                assert False, "Function succeeded but was expected to fail"
            
            # Verify retry attempts
            verify_retry_attempts(tracked_func, expected_retries)
            
            return True, result
        
        except Exception as e:
            # If we get here, the function failed
            if should_succeed:
                assert False, f"Function failed but was expected to succeed. Error: {str(e)}"
            
            # Verify retry attempts
            verify_retry_attempts(tracked_func, expected_retries)
            
            return False, e


class RetryTestCase:
    """
    Base test case class with utilities for testing retry behavior.
    """
    
    def __init__(self):
        """Initialize the RetryTestCase with default retry settings."""
        self.default_max_retries = DEFAULT_TEST_RETRY_COUNT
        self.default_delay = DEFAULT_TEST_RETRY_DELAY
        self.default_backoff_factor = DEFAULT_TEST_BACKOFF_FACTOR
    
    def create_retriable_error(self, status_code: Optional[int] = None) -> Exception:
        """
        Create an error that should trigger a retry.
        
        Args:
            status_code: Optional HTTP status code for HTTPError
            
        Returns:
            An exception that should be retried
        """
        if status_code is not None:
            # Use a status code that's in the RETRIABLE_STATUS_CODES list
            if status_code not in RETRY_SETTINGS["RETRIABLE_STATUS_CODES"]:
                status_code = 503  # Default to a retriable status code
            return create_http_error(status_code)
        else:
            # Default to a connection error which is retriable
            return create_connection_error()
    
    def create_non_retriable_error(self, status_code: Optional[int] = None) -> Exception:
        """
        Create an error that should not trigger a retry.
        
        Args:
            status_code: Optional HTTP status code for HTTPError
            
        Returns:
            An exception that should not be retried
        """
        if status_code is not None:
            # Use a status code that's not in the RETRIABLE_STATUS_CODES list
            if status_code in RETRY_SETTINGS["RETRIABLE_STATUS_CODES"]:
                status_code = 400  # Default to a non-retriable status code
            return create_http_error(status_code)
        else:
            # Default to a ValueError which is not retriable
            return ValueError("Non-retriable error")
    
    def setup_retry_test(self, fail_count: int, 
                        exception_type: Optional[Exception] = None,
                        return_value: Any = None) -> Tuple[Callable, Callable]:
        """
        Set up a test for retry behavior.
        
        Args:
            fail_count: Number of failures before success
            exception_type: Type of exception to raise on failure
            return_value: Value to return after successful execution
            
        Returns:
            Tuple of (retry-decorated function, original tracked function)
        """
        if exception_type is None:
            exception_type = self.create_retriable_error()
        
        return mock_retry_function(
            fail_count, 
            exception_type, 
            return_value,
            max_retries=self.default_max_retries,
            delay=self.default_delay,
            backoff_factor=self.default_backoff_factor
        )
    
    def verify_retry_behavior(self, tracked_func: Callable, 
                             expected_attempts: int,
                             sleep_mock: Optional[MagicMock] = None) -> None:
        """
        Verify the retry behavior of a function.
        
        Args:
            tracked_func: Function decorated with retry_tracker
            expected_attempts: Number of expected attempts
            sleep_mock: Optional mock of time.sleep for more detailed verification
            
        Returns:
            None
        """
        # Verify number of attempts
        verify_retry_attempts(tracked_func, expected_attempts)
        
        # If sleep_mock provided, verify sleep was called with expected delays
        if sleep_mock and expected_attempts > 1:
            expected_calls = []
            for i in range(expected_attempts - 1):  # -1 because last attempt doesn't sleep
                delay = self.default_delay * (self.default_backoff_factor ** i)
                expected_calls.append(call(delay))
            
            sleep_mock.assert_has_calls(expected_calls)
        else:
            # Verify backoff pattern
            if expected_attempts > 1:
                verify_backoff_pattern(
                    tracked_func,
                    initial_delay=self.default_delay,
                    backoff_factor=self.default_backoff_factor
                )
    
    def run_with_patched_sleep(self, test_func: Callable) -> Tuple[Any, MagicMock]:
        """
        Run a test function with patched time.sleep.
        
        Args:
            test_func: Function to run with patched time.sleep
            
        Returns:
            Tuple of (test result, sleep mock)
        """
        with patch_time_sleep() as sleep_mock:
            result = test_func()
            return result, sleep_mock


class MockResponse:
    """
    Mock HTTP response for testing retry behavior with requests.
    """
    
    def __init__(self, status_code: int, text: Optional[str] = None, 
                headers: Optional[Dict[str, str]] = None):
        """
        Initialize a mock HTTP response.
        
        Args:
            status_code: HTTP status code
            text: Response text
            headers: Response headers
        """
        self.status_code = status_code
        self.text = text or ""
        self.headers = headers or {}
    
    def json(self) -> Dict[str, Any]:
        """
        Return JSON data from the response.
        
        Returns:
            JSON data
        """
        try:
            import json
            return json.loads(self.text)
        except Exception:
            return {}
    
    def raise_for_status(self) -> None:
        """
        Raise HTTPError if status code indicates an error.
        
        Returns:
            None or raises HTTPError
        """
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"HTTP Error: {self.status_code}",
                response=self
            )