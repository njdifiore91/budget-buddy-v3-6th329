"""
logging_service.py - Advanced logging capabilities for the Budget Management Application

This module extends the base logging configuration with context-aware logging,
performance tracking, and structured log formatting. It provides a central logging
interface for all application components with features including:

- Structured JSON logs for machine readability
- Correlation IDs to track request flow across components
- Context enrichment for comprehensive logging
- Performance tracking and execution time measurement
- Sensitive data masking for secure logging
- Detailed exception formatting and error classification
- Decorators and context managers for consistent logging patterns

Usage:
    logger = get_component_logger("component_name")
    logger.info("Operation completed", context={"key": "value"})

    # With context manager
    with LoggingContext(logger, "operation_name", {"context": "data"}) as log_ctx:
        # Do something
        log_ctx.update_context({"additional": "context"})

    # With performance tracking
    perf_logger = PerformanceLogger(logger, "operation_name")
    perf_logger.start()
    # Do something
    perf_logger.checkpoint("step_1")
    # Do more
    total_time = perf_logger.stop()

    # With decorator
    @with_logging(logger, "operation_name")
    def some_function(arg1, arg2):
        return result
"""

import logging
import time
import functools
import traceback
import sys
from typing import Dict, List, Any, Optional, Callable, Union, TypeVar, cast

from ..config.logging_config import (
    setup_logging,
    generate_correlation_id,
    ContextAdapter,
    SensitiveDataFilter
)
from ..config.settings import APP_SETTINGS

# Global variables
_initialized = False
_sensitive_data_filter = SensitiveDataFilter()

# Type variables for function annotations
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


def initialize_logging(log_level: str = None, use_cloud_logging: bool = None) -> bool:
    """
    Initializes the logging system for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_cloud_logging: Whether to use Google Cloud Logging
        
    Returns:
        True if initialization was successful, False otherwise
    """
    global _initialized
    
    # Check if already initialized to prevent duplicate initialization
    if _initialized:
        return True
    
    # Use settings if parameters not provided
    if log_level is None:
        log_level = APP_SETTINGS.get('LOG_LEVEL', 'INFO')
    
    if use_cloud_logging is None:
        use_cloud_logging = APP_SETTINGS.get('USE_CLOUD_LOGGING', not APP_SETTINGS.get('DEBUG', False))
    
    # Initialize using the base setup_logging function
    success = setup_logging(log_level, use_cloud_logging)
    
    if success:
        _initialized = True
        
    return success


def get_component_logger(component_name: str) -> logging.Logger:
    """
    Gets a configured logger for a specific component with context support.
    
    Args:
        component_name: Name of the component requiring a logger
        
    Returns:
        Configured logger for the component
    """
    # Initialize logging if not already done
    if not _initialized:
        initialize_logging()
    
    # Get the logger for the component
    logger = logging.getLogger(component_name)
    return logger


def log_exception(
    logger: logging.Logger,
    exception: Exception,
    message: str = "An exception occurred",
    context: Dict[str, Any] = None,
    level: int = logging.ERROR
) -> None:
    """
    Logs an exception with detailed context information.
    
    Args:
        logger: Logger to use for logging the exception
        exception: The exception to log
        message: Custom message to include with the exception
        context: Additional context information
        level: Logging level (default: ERROR)
    """
    if context is None:
        context = {}
    
    # Format exception information
    exc_info = sys.exc_info()
    exc_details = format_exception(exception, include_traceback=True)
    
    # Mask sensitive data in context
    masked_context = mask_sensitive_data(context) if context else {}
    
    # Create log record with exception details
    log_context = {
        'exception_type': exc_details.get('exception_type'),
        'exception_message': exc_details.get('exception_message'),
        'traceback': exc_details.get('traceback'),
        **masked_context
    }
    
    # Log at the specified level
    logger.log(level, f"{message}: {str(exception)}", extra={
        'correlation_id': getattr(logger, 'correlation_id', generate_correlation_id()),
        'context': log_context
    }, exc_info=exc_info)


def with_logging(
    logger: logging.Logger,
    operation: str,
    context: Dict[str, Any] = None
) -> Callable[[F], F]:
    """
    Decorator that adds logging to a function.
    
    Args:
        logger: Logger to use
        operation: Name of the operation being performed
        context: Context information to include in logs
        
    Returns:
        Decorated function with logging
    """
    if context is None:
        context = {}
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            correlation_id = getattr(logger, 'correlation_id', generate_correlation_id())
            
            # Log entry with operation name and context
            logger.info(f"Starting {operation}", extra={
                'correlation_id': correlation_id,
                'context': mask_sensitive_data(context)
            })
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Log success with masked result
                masked_result = mask_sensitive_data(result) if result is not None else None
                logger.info(f"Completed {operation}", extra={
                    'correlation_id': correlation_id,
                    'context': {**mask_sensitive_data(context), 'result': masked_result}
                })
                
                return result
            except Exception as e:
                # Log exception with context
                log_exception(
                    logger,
                    e,
                    f"Error in {operation}",
                    context=context,
                    level=logging.ERROR
                )
                # Re-raise the exception
                raise
                
        return cast(F, wrapper)
    
    return decorator


def mask_sensitive_data(data: Any) -> Any:
    """
    Masks sensitive data in logs using the sensitive data filter.
    
    Args:
        data: Data to mask sensitive information from
        
    Returns:
        Data with sensitive information masked
    """
    return _sensitive_data_filter.mask_sensitive_data(data)


def format_exception(exception: Exception, include_traceback: bool = False) -> Dict[str, Any]:
    """
    Formats an exception for logging with detailed information.
    
    Args:
        exception: The exception to format
        include_traceback: Whether to include the traceback
        
    Returns:
        Formatted exception details as a dictionary
    """
    # Create base dictionary with exception type and message
    exception_details = {
        'exception_type': exception.__class__.__name__,
        'exception_message': str(exception)
    }
    
    # Add traceback if requested
    if include_traceback:
        tb_lines = traceback.format_exception(
            type(exception), 
            exception, 
            exception.__traceback__
        )
        exception_details['traceback'] = ''.join(tb_lines)
    
    # Include additional attributes if available
    if hasattr(exception, 'to_dict'):
        exception_details['details'] = exception.to_dict()
    
    # Mask any sensitive data
    return mask_sensitive_data(exception_details)


class LoggingContext:
    """
    Context manager for consistent logging with context information.
    
    Usage:
        with LoggingContext(logger, "operation_name", context_dict) as log_ctx:
            # Perform operations
            log_ctx.update_context({"additional": "context"})
    """
    
    def __init__(
        self,
        logger: logging.Logger,
        operation: str,
        context: Dict[str, Any] = None,
        correlation_id: str = None
    ):
        """
        Initializes the logging context.
        
        Args:
            logger: Logger to use
            operation: Name of the operation being performed
            context: Context information to include in logs
            correlation_id: Optional correlation ID (generated if not provided)
        """
        self.logger = logger
        self.operation = operation
        self.context = context or {}
        self.correlation_id = correlation_id or generate_correlation_id()
        
        # Create adapter with correlation ID and context
        self.adapter = ContextAdapter(logger, {
            'correlation_id': self.correlation_id,
            'context': self.context
        })
    
    def __enter__(self) -> 'LoggingContext':
        """
        Enters the logging context and logs the operation start.
        
        Returns:
            Self reference for context manager
        """
        # Log operation start with context
        self.adapter.info(f"Starting {self.operation}", context=self.context)
        return self
    
    def __exit__(
        self,
        exc_type: Any,
        exc_val: Optional[Exception],
        exc_tb: Any
    ) -> bool:
        """
        Exits the logging context and logs any exceptions.
        
        Args:
            exc_type: Exception type, if any
            exc_val: Exception value, if any
            exc_tb: Exception traceback, if any
            
        Returns:
            False to propagate exceptions
        """
        if exc_val is None:
            # Log successful completion
            self.adapter.info(f"Completed {self.operation}", context=self.context)
        else:
            # Log exception with context
            log_exception(
                self.logger,
                exc_val,
                f"Error in {self.operation}",
                context=self.context
            )
        
        # Return False to propagate the exception
        return False
    
    def update_context(self, additional_context: Dict[str, Any]) -> None:
        """
        Updates the context with additional information.
        
        Args:
            additional_context: Additional context to add
        """
        # Update the stored context
        self.context.update(additional_context)
        
        # Update the adapter's context
        self.adapter = ContextAdapter(self.logger, {
            'correlation_id': self.correlation_id,
            'context': self.context
        })


class PerformanceLogger:
    """
    Utility for logging performance metrics and execution times.
    
    Usage:
        perf_logger = PerformanceLogger(logger, "operation_name")
        perf_logger.start()
        # Do something
        perf_logger.checkpoint("step_1")
        # Do more
        total_time = perf_logger.stop()
    """
    
    def __init__(
        self,
        logger: logging.Logger,
        operation: str,
        context: Dict[str, Any] = None
    ):
        """
        Initializes the performance logger.
        
        Args:
            logger: Logger to use
            operation: Name of the operation being measured
            context: Context information to include in logs
        """
        self.logger = logger
        self.operation = operation
        self.context = context or {}
        self.start_time = None
        self.checkpoints = {}
    
    def start(self) -> None:
        """
        Starts the performance timer.
        """
        self.start_time = time.time()
        self.checkpoints = {}
        
        # Log operation start
        self.logger.info(f"Starting performance measurement for {self.operation}", extra={
            'correlation_id': getattr(self.logger, 'correlation_id', generate_correlation_id()),
            'context': mask_sensitive_data(self.context)
        })
    
    def checkpoint(self, checkpoint_name: str) -> float:
        """
        Records a checkpoint with elapsed time.
        
        Args:
            checkpoint_name: Name of the checkpoint
            
        Returns:
            Elapsed time since start in seconds
        """
        if self.start_time is None:
            raise RuntimeError("Performance timer not started. Call start() first.")
        
        # Calculate elapsed time
        elapsed = time.time() - self.start_time
        self.checkpoints[checkpoint_name] = elapsed
        
        # Log checkpoint
        self.logger.info(f"Checkpoint '{checkpoint_name}' reached in {elapsed:.4f}s", extra={
            'correlation_id': getattr(self.logger, 'correlation_id', generate_correlation_id()),
            'context': {
                **mask_sensitive_data(self.context),
                'checkpoint': checkpoint_name,
                'elapsed_seconds': elapsed
            }
        })
        
        return elapsed
    
    def stop(self) -> float:
        """
        Stops the timer and logs total execution time.
        
        Returns:
            Total execution time in seconds
        """
        if self.start_time is None:
            raise RuntimeError("Performance timer not started. Call start() first.")
        
        # Calculate total execution time
        total_time = time.time() - self.start_time
        
        # Log operation completion with total time
        self.logger.info(f"Completed {self.operation} in {total_time:.4f}s", extra={
            'correlation_id': getattr(self.logger, 'correlation_id', generate_correlation_id()),
            'context': {
                **mask_sensitive_data(self.context),
                'total_seconds': total_time,
                'checkpoints': self.checkpoints
            }
        })
        
        return total_time


class LogPerformance:
    """
    Decorator class for logging function performance.
    
    Usage:
        @LogPerformance(logger, "operation_name")
        def some_function(arg1, arg2):
            return result
    """
    
    def __init__(
        self,
        logger: logging.Logger,
        operation: str,
        context: Dict[str, Any] = None
    ):
        """
        Initializes the performance logging decorator.
        
        Args:
            logger: Logger to use
            operation: Name of the operation being measured
            context: Context information to include in logs
        """
        self.logger = logger
        self.operation = operation
        self.context = context or {}
    
    def __call__(self, func: F) -> F:
        """
        Decorates a function with performance logging.
        
        Args:
            func: Function to decorate
            
        Returns:
            Wrapped function with performance logging
        """
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create performance logger
            perf_logger = PerformanceLogger(
                self.logger,
                f"{self.operation} ({func.__name__})",
                self.context
            )
            
            # Start performance timer
            perf_logger.start()
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Stop timer and get execution time
                execution_time = perf_logger.stop()
                
                return result
            except Exception as e:
                # Stop timer even if an exception occurs
                perf_logger.stop()
                
                # Re-raise the exception
                raise
                
        return cast(F, wrapper)


# Convenience function for the LogPerformance decorator
def log_performance(
    logger: logging.Logger,
    operation: str,
    context: Dict[str, Any] = None
) -> Callable[[F], F]:
    """
    Decorator for measuring and logging function performance.
    
    Args:
        logger: Logger to use
        operation: Name of the operation being measured
        context: Context information to include in logs
        
    Returns:
        Decorator function
    """
    return LogPerformance(logger, operation, context)