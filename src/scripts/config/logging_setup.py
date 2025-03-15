"""
Configures the logging system for the Budget Management Application's utility scripts.

This module provides structured logging with JSON formatting, sensitive data masking,
and file-based logging. It serves as the central logging configuration for all utility scripts.

Classes:
    JsonFormatter: Custom log formatter that outputs logs as JSON strings
    SensitiveDataFilter: Log filter that masks sensitive data in log records
    ContextAdapter: Adapter for adding context and correlation ID to log records
    LoggingContext: Context manager for consistent logging with context information

Functions:
    setup_logging: Sets up the logging system for utility scripts
    get_logger: Gets a configured logger for a specific script component
    generate_correlation_id: Generates unique correlation IDs for request tracing
    mask_sensitive_data: Masks sensitive data in logs
"""

import logging
import json
import os
import datetime
import re
import uuid

from .script_settings import SCRIPT_SETTINGS
from .path_constants import LOGS_DIR, ensure_dir_exists

# Default logging level if not specified
DEFAULT_LOG_LEVEL = logging.INFO

# Patterns for sensitive data that should be masked
SENSITIVE_PATTERNS = [
    re.compile(pattern) for pattern in [
        r'password', r'token', r'key', r'secret', r'credential', 
        r'auth', r'account.*id', r'card.*number'
    ]
]

# Format for structured JSON logs
LOG_FORMAT = {
    'timestamp': '%(asctime)s',
    'level': '%(levelname)s',
    'component': '%(name)s',
    'correlation_id': '%(correlation_id)s',
    'message': '%(message)s',
    'context': '%(context)s'
}

# Flag to track if logging has been initialized
initialized = False


class JsonFormatter(logging.Formatter):
    """Custom log formatter that outputs logs as JSON strings."""
    
    def __init__(self, format_dict):
        """
        Initializes the JSON formatter.
        
        Args:
            format_dict: Dictionary defining the JSON log structure
        """
        super().__init__()
        self.format_dict = format_dict
    
    def format(self, record):
        """
        Formats the log record as a JSON string.
        
        Args:
            record: The log record to format
            
        Returns:
            JSON formatted log string
        """
        # Create a copy of the format dictionary
        output_dict = self.format_dict.copy()
        
        # Add correlation_id to record if not present
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = ''
            
        # Add context to record if not present
        if not hasattr(record, 'context'):
            record.context = {}
            
        # Replace format placeholders with record values
        for key, value in output_dict.items():
            try:
                output_dict[key] = value % record.__dict__
            except (KeyError, TypeError):
                # Keep the original value if formatting fails
                pass
        
        # If there's an exception, include it
        if record.exc_info:
            output_dict['exception'] = self.formatException(record.exc_info)
            
        # Convert to JSON string
        return json.dumps(output_dict)
    
    def formatException(self, exc_info):
        """
        Formats an exception for inclusion in a log record.
        
        Args:
            exc_info: Exception information tuple
            
        Returns:
            Formatted exception information
        """
        return super().formatException(exc_info)


class SensitiveDataFilter(logging.Filter):
    """Log filter that masks sensitive data in log records."""
    
    def __init__(self):
        """Initializes the sensitive data filter."""
        super().__init__()
    
    def filter(self, record):
        """
        Filters log records to mask sensitive data.
        
        Args:
            record: The log record to filter
            
        Returns:
            True to include the record in the log output
        """
        # Mask sensitive data in context
        if hasattr(record, 'context') and record.context:
            record.context = self.mask_sensitive_data(record.context)
            
        # Mask sensitive data in message
        if isinstance(record.msg, str):
            record.msg = self.mask_sensitive_data(record.msg)
        
        # Always include the record after filtering
        return True
    
    def mask_sensitive_data(self, data):
        """
        Masks sensitive data in a string or dictionary.
        
        Args:
            data: The data to mask sensitive information in
            
        Returns:
            Data with sensitive information masked
        """
        if isinstance(data, str):
            # Check if the string contains any sensitive patterns
            for pattern in SENSITIVE_PATTERNS:
                if pattern.search(data):
                    data = pattern.sub('[REDACTED]', data)
            return data
        elif isinstance(data, dict):
            # Recursively process dictionary values
            masked_data = {}
            for key, value in data.items():
                # Check if the key contains any sensitive patterns
                is_sensitive = False
                if isinstance(key, str):
                    is_sensitive = any(pattern.search(key.lower()) for pattern in SENSITIVE_PATTERNS)
                
                if is_sensitive and isinstance(value, (str, int, float)):
                    masked_data[key] = '[REDACTED]'
                else:
                    masked_data[key] = self.mask_sensitive_data(value)
            return masked_data
        elif isinstance(data, list):
            # Recursively process list items
            return [self.mask_sensitive_data(item) for item in data]
        else:
            # Return other types unchanged
            return data


class ContextAdapter(logging.LoggerAdapter):
    """Adapter for adding context and correlation ID to log records."""
    
    def __init__(self, logger, extra=None):
        """
        Initializes the context adapter.
        
        Args:
            logger: The logger to adapt
            extra: Extra context information to add to log records
        """
        if extra is None:
            extra = {}
        
        # Ensure extra contains correlation_id and context keys
        if 'correlation_id' not in extra:
            extra['correlation_id'] = generate_correlation_id()
        if 'context' not in extra:
            extra['context'] = {}
            
        super().__init__(logger, extra)
    
    def process(self, msg, kwargs):
        """
        Processes a log record to add context and correlation ID.
        
        Args:
            msg: The log message
            kwargs: Additional keyword arguments
            
        Returns:
            Processed message and kwargs
        """
        # Add extra context to kwargs
        kwargs = kwargs.copy() if kwargs else {}
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        # Update extra with adapter's extra
        kwargs['extra'].update(self.extra)
        
        return msg, kwargs


class LoggingContext:
    """Context manager for consistent logging with context information."""
    
    def __init__(self, logger, operation, context=None, correlation_id=None):
        """
        Initializes the logging context.
        
        Args:
            logger: The logger to use
            operation: The operation being performed
            context: Context information to include in logs
            correlation_id: Unique ID to correlate log entries
        """
        self.logger = logger
        self.operation = operation
        self.context = context or {}
        
        # Generate a correlation ID if not provided
        self.correlation_id = correlation_id or generate_correlation_id()
        
        # Create a context adapter for the logger
        extra = {
            'correlation_id': self.correlation_id,
            'context': self.context
        }
        self.logger = ContextAdapter(logger, extra)
    
    def __enter__(self):
        """
        Enters the logging context and logs the operation start.
        
        Returns:
            Self reference for context manager
        """
        self.logger.info(f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exits the logging context and logs any exceptions.
        
        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
            
        Returns:
            False to propagate exceptions
        """
        if exc_val:
            self.logger.error(f"Error during {self.operation}: {exc_val}", exc_info=(exc_type, exc_val, exc_tb))
        else:
            self.logger.info(f"Completed {self.operation}")
        
        # Don't suppress exceptions
        return False


def generate_correlation_id():
    """
    Generates a unique correlation ID for request tracing.
    
    Returns:
        Unique correlation ID
    """
    return str(uuid.uuid4())


def mask_sensitive_data(data):
    """
    Masks sensitive data in logs using the sensitive data filter.
    
    Args:
        data: The data to mask sensitive information in
        
    Returns:
        Data with sensitive information masked
    """
    # Create a filter instance to use its masking method
    filter_instance = SensitiveDataFilter()
    return filter_instance.mask_sensitive_data(data)


def setup_logging(log_level=None, use_json_logs=None, log_file=None):
    """
    Sets up the logging system for utility scripts with appropriate handlers and formatters.
    
    Args:
        log_level: Logging level as a string (e.g., 'INFO', 'DEBUG')
        use_json_logs: Whether to use JSON formatting for logs
        log_file: Name of the log file to write to
        
    Returns:
        True if setup was successful, False otherwise
    """
    global initialized
    
    try:
        # Use provided values or defaults from SCRIPT_SETTINGS
        log_level = log_level or SCRIPT_SETTINGS.get('LOG_LEVEL', 'INFO')
        use_json_logs = use_json_logs if use_json_logs is not None else SCRIPT_SETTINGS.get('USE_JSON_LOGS', False)
        
        # Convert log_level string to logging level constant
        numeric_level = getattr(logging, log_level.upper(), DEFAULT_LOG_LEVEL)
        
        # Get the root logger and set its level
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        # Remove any existing handlers to prevent duplication
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Ensure logs directory exists
        ensure_dir_exists(LOGS_DIR)
        
        # Generate default log file name with timestamp if not provided
        if log_file is None:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = f"budget_script_{timestamp}.log"
        
        log_file_path = os.path.join(LOGS_DIR, log_file)
        
        # Create formatters based on configuration
        if use_json_logs:
            formatter = JsonFormatter(LOG_FORMAT)
        else:
            # Create a standard formatter for non-JSON logs
            format_string = ' - '.join([f'{k}: {v}' for k, v in LOG_FORMAT.items()])
            formatter = logging.Formatter(format_string)
        
        # Create a filter to mask sensitive data
        sensitive_filter = SensitiveDataFilter()
        
        # Set up file handler
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sensitive_filter)
        root_logger.addHandler(file_handler)
        
        # Set up console handler with the same formatter
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.addFilter(sensitive_filter)
        root_logger.addHandler(console_handler)
        
        initialized = True
        
        # Log successful setup (but only after handlers are configured)
        root_logger.info(f"Logging setup complete. Log file: {log_file_path}")
        
        return True
    
    except Exception as e:
        print(f"Error setting up logging: {e}")
        return False


def get_logger(name):
    """
    Gets a configured logger for a specific script component.
    
    Args:
        name: Name of the component requesting the logger
        
    Returns:
        Configured logger for the component
    """
    global initialized
    
    # Set up logging if not already initialized
    if not initialized:
        setup_logging(
            log_level=SCRIPT_SETTINGS.get('LOG_LEVEL', 'INFO'),
            use_json_logs=SCRIPT_SETTINGS.get('USE_JSON_LOGS', False)
        )
    
    # Return a logger with the specified name
    return logging.getLogger(name)