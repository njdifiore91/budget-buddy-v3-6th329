"""
test_logging.py - Utility module providing testing helpers for logging functionality in the Budget Management Application.

This module contains mock loggers, log capture mechanisms, and assertion utilities for verifying
log messages and patterns during tests.
"""

import logging
import io
from io import StringIO
import json
import re
import contextlib
from typing import List, Dict, Any, Optional, Union, Pattern, Callable

import pytest

from ...backend.services.logging_service import (
    initialize_logging, get_component_logger, log_exception, with_logging,
    mask_sensitive_data, format_exception, LoggingContext, PerformanceLogger
)
from ...backend.config.logging_config import (
    SensitiveDataFilter, ContextAdapter, JsonFormatter, generate_correlation_id
)
from .assertion_helpers import assert_dict_subset

# Default format for testing logs
DEFAULT_LOG_FORMAT = {
    'timestamp': '%(asctime)s', 
    'level': '%(levelname)s', 
    'component': '%(name)s', 
    'correlation_id': '%(correlation_id)s', 
    'message': '%(message)s', 
    'context': '%(context)s'
}


def create_test_logger(name: str, level: Optional[int] = None) -> tuple:
    """
    Creates a logger configured for testing with a StringIO handler
    
    Args:
        name: Name for the logger
        level: Logging level to set (default: DEBUG)
        
    Returns:
        Tuple containing (logger, log_output) where log_output is a StringIO object
    """
    # Create a new logger with the specified name
    logger = logging.getLogger(name)
    
    # Set the level (default to DEBUG)
    if level is None:
        level = logging.DEBUG
    logger.setLevel(level)
    
    # Remove any existing handlers to prevent duplication
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create a StringIO to capture log output
    log_output = StringIO()
    
    # Create a handler that writes to the StringIO
    handler = logging.StreamHandler(log_output)
    
    # Add formatter (use JsonFormatter if available, otherwise basic formatter)
    try:
        formatter = JsonFormatter(DEFAULT_LOG_FORMAT)
    except:
        formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    
    handler.setFormatter(formatter)
    
    # Add the handler to the logger
    logger.addHandler(handler)
    
    return logger, log_output


def capture_logs(logger: Optional[logging.Logger] = None, 
                level: Optional[int] = None) -> contextlib.ContextManager:
    """
    Context manager that captures logs from a logger during execution
    
    Args:
        logger: Logger to capture logs from (default: root logger)
        level: Logging level to capture (default: DEBUG)
        
    Returns:
        Context manager that yields a StringIO object with captured logs
    """
    # If no logger specified, use the root logger
    if logger is None:
        logger = logging.getLogger()
    
    # Create StringIO for capturing output
    log_output = StringIO()
    
    # Create a handler for capturing logs
    handler = logging.StreamHandler(log_output)
    
    # Add formatter
    try:
        formatter = JsonFormatter(DEFAULT_LOG_FORMAT)
    except:
        formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    
    handler.setFormatter(formatter)
    
    # Set level (default to DEBUG)
    if level is None:
        level = logging.DEBUG
    handler.setLevel(level)
    
    # Define the context manager
    @contextlib.contextmanager
    def _capture_logs_context():
        # Add the handler before entering context
        logger.addHandler(handler)
        try:
            # Yield StringIO object to context
            yield log_output
        finally:
            # Remove handler after exiting context
            logger.removeHandler(handler)
    
    return _capture_logs_context()


def assert_log_contains(log_output: Union[str, StringIO], 
                       expected: Union[str, Pattern], 
                       message: Optional[str] = None) -> None:
    """
    Assert that log output contains expected text or pattern
    
    Args:
        log_output: Captured log output or StringIO containing logs
        expected: String or regex pattern to look for in logs
        message: Custom error message
        
    Returns:
        None, raises AssertionError if log doesn't contain expected content
    """
    # Get log content as string
    if isinstance(log_output, StringIO):
        log_content = log_output.getvalue()
    else:
        log_content = log_output
    
    # If expected is a regex pattern, use re.search
    if isinstance(expected, Pattern):
        match_found = bool(re.search(expected, log_content))
    else:
        # Otherwise check if string is in content
        match_found = expected in log_content
    
    # Create error message if needed
    if not message:
        if isinstance(expected, Pattern):
            message = f"Log output does not match pattern: {expected.pattern}"
        else:
            message = f"Log output does not contain: {expected}"
    
    # Assert that the expected content is found
    assert match_found, message


def assert_log_matches_json(log_output: Union[str, StringIO], 
                           expected_fields: Dict[str, Any], 
                           message: Optional[str] = None) -> None:
    """
    Assert that a JSON log entry contains expected fields and values
    
    Args:
        log_output: Captured log output or StringIO containing logs
        expected_fields: Dictionary with fields and values to check for
        message: Custom error message
        
    Returns:
        None, raises AssertionError if log doesn't match expected JSON
    """
    # Get log content as string
    if isinstance(log_output, StringIO):
        log_content = log_output.getvalue()
    else:
        log_content = log_output
    
    # Split into lines and process each line
    lines = log_content.splitlines()
    
    for line in lines:
        if not line.strip():
            continue
            
        try:
            # Try to parse as JSON
            log_entry = json.loads(line)
            
            # Check if all expected fields are in this entry
            try:
                assert_dict_subset(log_entry, expected_fields)
                # If we reach here, this log entry matches
                return
            except AssertionError:
                # This entry doesn't match, try next one
                continue
                
        except json.JSONDecodeError:
            # Skip non-JSON lines
            continue
    
    # If we get here, no matching entry was found
    if not message:
        message = (f"No JSON log entry matches expected fields: {expected_fields}\n"
                  f"Log content:\n{log_content}")
    
    raise AssertionError(message)


def assert_logs_count(log_output: Union[str, StringIO], 
                     pattern: Union[str, Pattern], 
                     expected_count: int, 
                     message: Optional[str] = None) -> None:
    """
    Assert that log output contains a specific number of matching entries
    
    Args:
        log_output: Captured log output or StringIO containing logs
        pattern: String or regex pattern to match in log entries
        expected_count: Expected number of matches
        message: Custom error message
        
    Returns:
        None, raises AssertionError if count doesn't match
    """
    # Get log content as string
    if isinstance(log_output, StringIO):
        log_content = log_output.getvalue()
    else:
        log_content = log_output
    
    # Split into lines
    lines = log_content.splitlines()
    
    # Count matching lines
    match_count = 0
    for line in lines:
        if isinstance(pattern, Pattern):
            if re.search(pattern, line):
                match_count += 1
        else:
            if pattern in line:
                match_count += 1
    
    # Create error message if needed
    if not message:
        message = (f"Expected {expected_count} log entries matching {pattern}, "
                  f"but found {match_count}.\nLog content:\n{log_content}")
    
    # Assert that count matches
    assert match_count == expected_count, message


def assert_log_level(log_output: Union[str, StringIO], 
                    level: Union[int, str], 
                    min_count: Optional[int] = None, 
                    message: Optional[str] = None) -> None:
    """
    Assert that log output contains entries at a specific level
    
    Args:
        log_output: Captured log output or StringIO containing logs
        level: Log level to check for (e.g., logging.INFO or 'INFO')
        min_count: Minimum number of entries to expect (default: at least 1)
        message: Custom error message
        
    Returns:
        None, raises AssertionError if level check fails
    """
    # Get log content as string
    if isinstance(log_output, StringIO):
        log_content = log_output.getvalue()
    else:
        log_content = log_output
    
    # Convert level to string if it's an integer
    if isinstance(level, int):
        level_name = logging.getLevelName(level)
    else:
        level_name = level
    
    # Split into lines and process each line
    lines = log_content.splitlines()
    
    # Count entries with matching level
    level_count = 0
    for line in lines:
        try:
            # Try to parse as JSON
            log_entry = json.loads(line)
            
            # Check if level matches
            if log_entry.get('level') == level_name:
                level_count += 1
        except (json.JSONDecodeError, KeyError):
            # Skip non-JSON lines or lines without level
            continue
    
    # Determine if count is acceptable
    if min_count is not None:
        success = level_count >= min_count
        expected_desc = f"at least {min_count}"
    else:
        success = level_count > 0
        expected_desc = "at least one"
    
    # Create error message if needed
    if not message:
        message = (f"Expected {expected_desc} log entries with level {level_name}, "
                  f"but found {level_count}.\nLog content:\n{log_content}")
    
    # Assert based on criteria
    assert success, message


def mock_logging_context(logger: Optional[logging.Logger] = None,
                       operation: Optional[str] = None,
                       context: Optional[Dict[str, Any]] = None,
                       correlation_id: Optional[str] = None) -> LoggingContext:
    """
    Creates a mock LoggingContext for testing
    
    Args:
        logger: Logger to use (created if not provided)
        operation: Operation name (default: 'test_operation')
        context: Context dictionary (default: empty dict)
        correlation_id: Correlation ID (generated if not provided)
        
    Returns:
        A LoggingContext instance configured for testing
    """
    # Create logger if not provided
    if logger is None:
        logger, _ = create_test_logger("test_logger")
    
    # Default operation name
    if operation is None:
        operation = "test_operation"
    
    # Default empty context
    if context is None:
        context = {}
    
    # Generate correlation ID if not provided
    if correlation_id is None:
        correlation_id = generate_correlation_id()
    
    # Create and return LoggingContext
    return LoggingContext(logger, operation, context, correlation_id)


def mock_performance_logger(logger: Optional[logging.Logger] = None,
                          operation: Optional[str] = None,
                          context: Optional[Dict[str, Any]] = None) -> PerformanceLogger:
    """
    Creates a mock PerformanceLogger for testing
    
    Args:
        logger: Logger to use (created if not provided)
        operation: Operation name (default: 'test_operation')
        context: Context dictionary (default: empty dict)
        
    Returns:
        A PerformanceLogger instance configured for testing
    """
    # Create logger if not provided
    if logger is None:
        logger, _ = create_test_logger("test_logger")
    
    # Default operation name
    if operation is None:
        operation = "test_operation"
    
    # Default empty context
    if context is None:
        context = {}
    
    # Create and return PerformanceLogger
    return PerformanceLogger(logger, operation, context)


class LogCapture:
    """
    Context manager class for capturing and testing log output
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None, level: Optional[int] = None):
        """
        Initialize the log capture context manager
        
        Args:
            logger: Logger to capture logs from (default: root logger)
            level: Logging level to capture (default: DEBUG)
        """
        # If no logger specified, use the root logger
        if logger is None:
            logger = logging.getLogger()
        
        self.logger = logger
        
        # Create StringIO for capturing output
        self.log_output = StringIO()
        
        # Create a handler for capturing logs
        self.handler = logging.StreamHandler(self.log_output)
        
        # Add formatter
        try:
            formatter = JsonFormatter(DEFAULT_LOG_FORMAT)
        except:
            formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
        
        self.handler.setFormatter(formatter)
        
        # Set level (default to DEBUG)
        if level is None:
            level = logging.DEBUG
        self.handler.setLevel(level)
        
        # Initialize empty json_logs list
        self.json_logs = []
    
    def __enter__(self):
        """
        Enter the context manager and start capturing logs
        
        Returns:
            Self reference for context manager
        """
        # Add handler to logger
        self.logger.addHandler(self.handler)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context manager and stop capturing logs
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
            
        Returns:
            False to propagate exceptions
        """
        # Remove handler from logger
        self.logger.removeHandler(self.handler)
        
        # Process logs to extract JSON if needed
        if not self.json_logs:
            self.get_json_logs()
        
        # Propagate exceptions
        return False
    
    def get_output(self):
        """
        Get the captured log output as a string
        
        Returns:
            Captured log output
        """
        return self.log_output.getvalue()
    
    def get_json_logs(self):
        """
        Get the captured logs as a list of parsed JSON objects
        
        Returns:
            List of parsed JSON log entries
        """
        if not self.json_logs:
            # Process log output
            output = self.log_output.getvalue()
            lines = output.splitlines()
            
            for line in lines:
                if not line.strip():
                    continue
                    
                try:
                    # Try to parse as JSON
                    log_entry = json.loads(line)
                    self.json_logs.append(log_entry)
                except json.JSONDecodeError:
                    # Skip non-JSON lines
                    continue
        
        return self.json_logs
    
    def assert_contains(self, expected: Union[str, Pattern], message: Optional[str] = None):
        """
        Assert that log output contains expected text or pattern
        
        Args:
            expected: String or regex pattern to look for in logs
            message: Custom error message
            
        Returns:
            Self reference for method chaining
        """
        assert_log_contains(self.log_output, expected, message)
        return self
    
    def assert_json_contains(self, expected_fields: Dict[str, Any], message: Optional[str] = None):
        """
        Assert that a JSON log entry contains expected fields and values
        
        Args:
            expected_fields: Dictionary with fields and values to check for
            message: Custom error message
            
        Returns:
            Self reference for method chaining
        """
        assert_log_matches_json(self.log_output, expected_fields, message)
        return self
    
    def assert_count(self, pattern: Union[str, Pattern], expected_count: int, message: Optional[str] = None):
        """
        Assert that log output contains a specific number of matching entries
        
        Args:
            pattern: String or regex pattern to match in log entries
            expected_count: Expected number of matches
            message: Custom error message
            
        Returns:
            Self reference for method chaining
        """
        assert_logs_count(self.log_output, pattern, expected_count, message)
        return self
    
    def assert_level(self, level: Union[int, str], min_count: Optional[int] = None, message: Optional[str] = None):
        """
        Assert that log output contains entries at a specific level
        
        Args:
            level: Log level to check for (e.g., logging.INFO or 'INFO')
            min_count: Minimum number of entries to expect (default: at least 1)
            message: Custom error message
            
        Returns:
            Self reference for method chaining
        """
        assert_log_level(self.log_output, level, min_count, message)
        return self


class MockLoggingHandler(logging.Handler):
    """
    Mock logging handler that stores log records for testing
    """
    
    def __init__(self, level: Optional[int] = None):
        """
        Initialize the mock logging handler
        
        Args:
            level: Logging level to set (default: DEBUG)
        """
        # Initialize parent class
        super().__init__(level or logging.DEBUG)
        
        # Initialize messages dictionary
        self.messages = {
            'debug': [],
            'info': [],
            'warning': [],
            'error': [],
            'critical': []
        }
    
    def emit(self, record: logging.LogRecord):
        """
        Store a log record in the appropriate level list
        
        Args:
            record: Log record to store
        """
        # Get level name in lowercase
        level = record.levelname.lower()
        
        # Store record in corresponding list
        self.messages[level].append(record)
    
    def reset(self):
        """
        Clear all stored log records
        """
        # Reset each list to empty
        for level in self.messages:
            self.messages[level] = []
    
    def get_messages(self, level: str):
        """
        Get all messages for a specific log level
        
        Args:
            level: Log level name in lowercase
            
        Returns:
            List of formatted log messages
        """
        # Get all records for the level
        records = self.messages.get(level.lower(), [])
        
        # Format each record using the handler's formatter
        if self.formatter:
            return [self.formatter.format(record) for record in records]
        else:
            return [record.getMessage() for record in records]
    
    def get_records(self, level: str):
        """
        Get all log records for a specific log level
        
        Args:
            level: Log level name in lowercase
            
        Returns:
            List of log records
        """
        return self.messages.get(level.lower(), [])


class LogTestCase:
    """
    Base class for test cases that need to test logging functionality
    """
    
    def setup_logger(self, logger_name: Optional[str] = None, level: Optional[int] = None):
        """
        Set up a logger with a mock handler for testing
        
        Args:
            logger_name: Name for the logger (default: 'test')
            level: Logging level to set (default: DEBUG)
        """
        # Use default name if not provided
        if logger_name is None:
            logger_name = 'test'
        
        # Get or create a logger
        self.logger = logging.getLogger(logger_name)
        
        # Set level (default to DEBUG)
        if level is None:
            level = logging.DEBUG
        self.logger.setLevel(level)
        
        # Remove existing handlers to avoid duplication
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create and add the mock handler
        self.handler = MockLoggingHandler(level)
        self.logger.addHandler(self.handler)
    
    def reset_logs(self):
        """
        Reset the mock handler to clear all stored log records
        """
        if hasattr(self, 'handler') and isinstance(self.handler, MockLoggingHandler):
            self.handler.reset()
    
    def assert_log_contains(self, level: str, expected: str, message: Optional[str] = None):
        """
        Assert that logs at a specific level contain expected text
        
        Args:
            level: Log level name (debug, info, warning, error, critical)
            expected: Text to look for in log messages
            message: Custom error message
        """
        if not hasattr(self, 'handler') or not isinstance(self.handler, MockLoggingHandler):
            pytest.fail("Logger not properly set up. Call setup_logger() first.")
            
        # Get messages for the specified level
        messages = self.handler.get_messages(level)
        
        # Check if any message contains the expected text
        for msg in messages:
            if expected in msg:
                return
        
        # If we get here, the expected text wasn't found
        if not message:
            available = '\n'.join(messages)
            message = (f"No {level} message contains '{expected}'.\n"
                      f"Available {level} messages:\n{available}")
        
        pytest.fail(message)
    
    def assert_log_regex(self, level: str, pattern: Union[str, Pattern], message: Optional[str] = None):
        """
        Assert that logs at a specific level match a regex pattern
        
        Args:
            level: Log level name (debug, info, warning, error, critical)
            pattern: Regex pattern to match in log messages
            message: Custom error message
        """
        if not hasattr(self, 'handler') or not isinstance(self.handler, MockLoggingHandler):
            pytest.fail("Logger not properly set up. Call setup_logger() first.")
            
        # Get messages for the specified level
        messages = self.handler.get_messages(level)
        
        # Compile pattern if it's a string
        if isinstance(pattern, str):
            compiled_pattern = re.compile(pattern)
        else:
            compiled_pattern = pattern
            
        # Check if any message matches the pattern
        for msg in messages:
            if compiled_pattern.search(msg):
                return
        
        # If we get here, no message matched the pattern
        if not message:
            available = '\n'.join(messages)
            message = (f"No {level} message matches pattern '{compiled_pattern.pattern}'.\n"
                      f"Available {level} messages:\n{available}")
        
        pytest.fail(message)
    
    def assert_log_count(self, level: str, expected_count: int, message: Optional[str] = None):
        """
        Assert that a specific number of log messages exist at a level
        
        Args:
            level: Log level name (debug, info, warning, error, critical)
            expected_count: Expected number of messages
            message: Custom error message
        """
        if not hasattr(self, 'handler') or not isinstance(self.handler, MockLoggingHandler):
            pytest.fail("Logger not properly set up. Call setup_logger() first.")
            
        # Get records for the specified level
        records = self.handler.get_records(level)
        
        # Check count
        actual_count = len(records)
        
        # Assert count matches
        if actual_count != expected_count:
            if not message:
                message = f"Expected {expected_count} {level} messages, got {actual_count}"
            pytest.fail(message)