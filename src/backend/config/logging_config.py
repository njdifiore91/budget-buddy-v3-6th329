"""
logging_config.py - Logging configuration for the Budget Management Application

This module provides structured logging setup with JSON formatting, sensitive data
masking, and integration with Google Cloud Logging. It implements correlation IDs
for request tracing and context enrichment for comprehensive monitoring.
"""

import logging  # standard library
import json  # standard library
import uuid  # standard library
import os  # standard library
import re  # standard library
from google.cloud import logging as cloud_logging  # google-cloud-logging 3.5.0+

from .settings import APP_SETTINGS  # Internal import for app configuration

# Default logging configuration
DEFAULT_LOG_LEVEL = logging.INFO

# Patterns for sensitive data that should be masked in logs
SENSITIVE_PATTERNS = [
    re.compile(pattern) for pattern in [
        r'password', r'token', r'key', r'secret', r'credential', r'auth',
        r'account.*id', r'card.*number'
    ]
]

# JSON log format structure
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
    """
    Custom log formatter that outputs logs as JSON strings.
    
    This formatter converts log records to structured JSON format for better
    parsing and analysis in logging systems.
    """
    
    def __init__(self, format_dict):
        """
        Initialize the JSON formatter.
        
        Args:
            format_dict (dict): Dictionary defining the JSON log structure
        """
        super().__init__()
        self.format_dict = format_dict
    
    def format(self, record):
        """
        Format the log record as a JSON string.
        
        Args:
            record (logging.LogRecord): The log record to format
            
        Returns:
            str: JSON formatted log string
        """
        # Create a copy of the format dictionary
        output = self.format_dict.copy()
        
        # Ensure record has correlation_id and context attributes
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = 'unknown'
        
        if not hasattr(record, 'context'):
            record.context = {}
        
        # Replace format placeholders with record values
        for key, value in output.items():
            try:
                output[key] = value % record.__dict__
            except (KeyError, TypeError):
                # Keep the original placeholder if formatting fails
                pass
        
        # Add exception info if present
        if record.exc_info:
            output['exception'] = self.formatException(record.exc_info)
        
        # Convert to JSON string
        return json.dumps(output)
    
    def formatException(self, exc_info):
        """
        Format exception information for inclusion in a log record.
        
        Args:
            exc_info (tuple): Exception information tuple
            
        Returns:
            str: Formatted exception information
        """
        return super().formatException(exc_info)


class SensitiveDataFilter(logging.Filter):
    """
    Log filter that masks sensitive data in log records.
    
    This filter scans log messages and contexts for sensitive patterns
    like passwords, tokens, and account numbers and redacts them.
    """
    
    def __init__(self):
        """Initialize the sensitive data filter."""
        super().__init__()
    
    def filter(self, record):
        """
        Filter log records to mask sensitive data.
        
        Args:
            record (logging.LogRecord): The log record to filter
            
        Returns:
            bool: True to include the record in the log output
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
        Mask sensitive data in a string or dictionary.
        
        Args:
            data (object): String, dictionary, or list containing data to mask
            
        Returns:
            object: Data with sensitive information masked
        """
        # Handle string data
        if isinstance(data, str):
            for pattern in SENSITIVE_PATTERNS:
                # Use regex to find and replace sensitive data
                data = pattern.sub(
                    lambda m: m.group(0)[0:1] + '[REDACTED]', 
                    data
                )
            return data
        
        # Handle dictionary data
        elif isinstance(data, dict):
            result = {}
            for key, value in data.items():
                # Check if the key itself might be sensitive
                sensitive_key = any(pattern.search(key.lower()) for pattern in SENSITIVE_PATTERNS)
                
                if sensitive_key:
                    # Completely redact sensitive values
                    result[key] = '[REDACTED]'
                else:
                    # Recursively process the value
                    result[key] = self.mask_sensitive_data(value)
            return result
        
        # Handle list data
        elif isinstance(data, list):
            return [self.mask_sensitive_data(item) for item in data]
        
        # Return other types unchanged
        return data


class ContextAdapter:
    """
    Adapter for adding context and correlation ID to log records.
    
    This adapter enriches log records with contextual information and
    correlation IDs for request tracing across components.
    """
    
    def __init__(self, logger, extra=None):
        """
        Initialize the context adapter.
        
        Args:
            logger (logging.Logger): The logger to adapt
            extra (dict): Extra context to add to all log records
        """
        self.logger = logger
        self.extra = extra or {}
        
        # Ensure we have correlation_id and context
        if 'correlation_id' not in self.extra:
            self.extra['correlation_id'] = 'unknown'
        
        if 'context' not in self.extra:
            self.extra['context'] = {}
    
    def process(self, record):
        """
        Process a log record to add context and correlation ID.
        
        Args:
            record (logging.LogRecord): The log record to process
            
        Returns:
            logging.LogRecord: Processed log record
        """
        # Add extra context to record
        for key, value in self.extra.items():
            setattr(record, key, value)
        
        return record
    
    # Implement logging methods that add context
    def debug(self, msg, *args, **kwargs):
        """Log with debug level."""
        self._log(logging.DEBUG, msg, args, kwargs)
    
    def info(self, msg, *args, **kwargs):
        """Log with info level."""
        self._log(logging.INFO, msg, args, kwargs)
    
    def warning(self, msg, *args, **kwargs):
        """Log with warning level."""
        self._log(logging.WARNING, msg, args, kwargs)
    
    def error(self, msg, *args, **kwargs):
        """Log with error level."""
        self._log(logging.ERROR, msg, args, kwargs)
    
    def critical(self, msg, *args, **kwargs):
        """Log with critical level."""
        self._log(logging.CRITICAL, msg, args, kwargs)
    
    def _log(self, level, msg, args, kwargs):
        """Internal logging implementation with context."""
        # Extract and merge extra context
        extra = kwargs.pop('extra', {})
        context = kwargs.pop('context', {})
        
        # Create combined extra dict with context
        combined_extra = self.extra.copy()
        combined_extra.update(extra)
        
        # Merge contexts
        if context:
            combined_context = combined_extra.get('context', {}).copy()
            combined_context.update(context)
            combined_extra['context'] = combined_context
        
        # Log with combined context
        self.logger.log(level, msg, *args, extra=combined_extra, **kwargs)
    
    def with_context(self, **context):
        """
        Create a new logger with additional context.
        
        Args:
            **context: Keyword arguments to add to the context
            
        Returns:
            ContextAdapter: New adapter with merged context
        """
        new_extra = self.extra.copy()
        new_context = new_extra.get('context', {}).copy()
        new_context.update(context)
        new_extra['context'] = new_context
        
        return ContextAdapter(self.logger, new_extra)
    
    def with_correlation_id(self, correlation_id=None):
        """
        Create a new logger with specified correlation ID.
        
        Args:
            correlation_id (str): The correlation ID to use, or None to generate
            
        Returns:
            ContextAdapter: New adapter with the correlation ID
        """
        new_extra = self.extra.copy()
        new_extra['correlation_id'] = correlation_id or generate_correlation_id()
        
        return ContextAdapter(self.logger, new_extra)


def generate_correlation_id():
    """
    Generate a unique correlation ID for request tracing.
    
    Returns:
        str: Unique correlation ID
    """
    return str(uuid.uuid4())


def setup_logging(log_level=None, use_cloud_logging=None):
    """
    Set up the logging system with appropriate handlers and formatters.
    
    Args:
        log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_cloud_logging (bool): Whether to use Google Cloud Logging
        
    Returns:
        bool: True if setup was successful, False otherwise
    """
    global initialized
    
    try:
        # Set defaults from app settings if not specified
        if log_level is None:
            log_level = APP_SETTINGS.get('LOG_LEVEL', 'INFO')
        
        if use_cloud_logging is None:
            # Default to True in production, False in development
            use_cloud_logging = not APP_SETTINGS.get('DEBUG', False)
        
        # Convert string log level to logging constant
        numeric_level = getattr(logging, log_level.upper(), DEFAULT_LOG_LEVEL)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        # Remove any existing handlers to prevent duplication
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Create formatter for structured JSON logs
        formatter = JsonFormatter(LOG_FORMAT)
        
        # Create sensitive data filter
        sensitive_filter = SensitiveDataFilter()
        
        # Set up appropriate handler based on environment
        if use_cloud_logging:
            # Setup Google Cloud Logging
            cloud_client = cloud_logging.Client()
            handler = cloud_client.get_default_handler()
        else:
            # Setup console logging
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
        
        # Add filter to handler
        handler.addFilter(sensitive_filter)
        
        # Add handler to root logger
        root_logger.addHandler(handler)
        
        # Mark logging as initialized
        initialized = True
        
        # Log successful setup
        logger = logging.getLogger(__name__)
        logger.info("Logging system initialized", extra={
            'correlation_id': generate_correlation_id(),
            'context': {'log_level': log_level, 'use_cloud_logging': use_cloud_logging}
        })
        
        return True
        
    except Exception as e:
        # If we can't set up logging, print to stderr as fallback
        print(f"Error setting up logging: {str(e)}", file=os.sys.stderr)
        return False


def get_logger(name):
    """
    Get a configured logger for a specific component.
    
    Args:
        name (str): Name of the component requiring logging
        
    Returns:
        ContextAdapter: Configured logger for the component
    """
    global initialized
    
    # Initialize logging if not already done
    if not initialized:
        setup_logging()
    
    # Get the named logger
    logger = logging.getLogger(name)
    
    # Wrap with context adapter
    return ContextAdapter(logger, {
        'correlation_id': generate_correlation_id(),
        'context': {}
    })