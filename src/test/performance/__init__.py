"""
Initialization file for the performance testing module. Provides common utilities, fixtures,
and configuration for performance tests that measure the efficiency and resource usage of the
Budget Management Application.
"""

import time  # standard library
import pytest  # pytest 7.4.0+

from ..utils.test_helpers import setup_performance_test
from ..utils.fixture_loader import load_large_fixtures

# Performance thresholds for different metrics (in seconds, MB, transactions/sec)
PERFORMANCE_THRESHOLDS = {
    'EXECUTION_TIME_THRESHOLD': 300,  # 5 minutes
    'API_RESPONSE_TIME_THRESHOLD': 30,  # 30 seconds
    'MEMORY_USAGE_THRESHOLD': 1024,  # 1GB
    'TRANSACTION_PROCESSING_RATE': 10  # 10 transactions per second
}

# Configuration settings for performance tests
PERFORMANCE_TEST_CONFIG = {
    'REPEAT_COUNT': 3,  # Run each test multiple times to get average performance
    'WARMUP_ITERATIONS': 1,  # Initial iterations to ignore (warmup)
    'INCLUDE_SETUP_TIME': False,  # Whether to include setup time in measurements
    'LOG_MEMORY_USAGE': True  # Whether to log memory usage
}

def measure_execution_time(func):
    """
    Decorator function to measure and log the execution time of test functions
    
    Args:
        func: Function to measure
        
    Returns:
        Wrapped function that measures execution time
    """
    def wrapper(*args, **kwargs):
        # Record start time before executing the function
        start_time = time.time()
        
        # Execute the wrapped function
        result = func(*args, **kwargs)
        
        # Record end time after execution
        end_time = time.time()
        
        # Calculate execution time
        execution_time = end_time - start_time
        
        # Log the execution time
        print(f"PERFORMANCE: {func.__name__} executed in {execution_time:.2f} seconds")
        
        # Assert that execution time is below threshold
        assert execution_time < PERFORMANCE_THRESHOLDS['EXECUTION_TIME_THRESHOLD'], \
            f"Execution time ({execution_time:.2f}s) exceeded threshold " \
            f"({PERFORMANCE_THRESHOLDS['EXECUTION_TIME_THRESHOLD']}s)"
        
        # Return the result of the wrapped function
        return result
    
    return wrapper

def measure_memory_usage(func):
    """
    Decorator function to measure and log the memory usage of test functions
    
    Args:
        func: Function to measure
        
    Returns:
        Wrapped function that measures memory usage
    """
    def wrapper(*args, **kwargs):
        try:
            # Import psutil for memory measurements
            import psutil
            process = psutil.Process()
            
            # Record memory usage before executing the function
            memory_before = process.memory_info().rss / (1024 * 1024)  # Convert to MB
            
            # Execute the wrapped function
            result = func(*args, **kwargs)
            
            # Record memory usage after execution
            memory_after = process.memory_info().rss / (1024 * 1024)  # Convert to MB
            
            # Calculate memory consumption
            memory_used = memory_after - memory_before
            
            # Log the memory usage
            print(f"PERFORMANCE: {func.__name__} used {memory_used:.2f} MB of memory")
            
            # Assert that memory usage is below threshold
            assert memory_used < PERFORMANCE_THRESHOLDS['MEMORY_USAGE_THRESHOLD'], \
                f"Memory usage ({memory_used:.2f} MB) exceeded threshold " \
                f"({PERFORMANCE_THRESHOLDS['MEMORY_USAGE_THRESHOLD']} MB)"
            
        except ImportError:
            # If psutil is not available, log a warning and continue
            print(f"WARNING: psutil not available, memory usage measurement skipped for {func.__name__}")
        
        # Return the result of the wrapped function
        return result
    
    return wrapper