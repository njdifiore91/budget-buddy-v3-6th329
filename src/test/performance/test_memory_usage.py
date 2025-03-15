"""
Performance test module focused on measuring and validating memory usage across different components of the Budget Management Application.
This module contains tests to ensure the application operates within defined memory constraints, detects memory leaks, and handles various workloads efficiently.
"""

import pytest  # pytest 7.4.0+
import logging
import tracemalloc  # standard library
import gc  # standard library
from typing import List, Dict, Any

from memory_profiler import profile  # memory_profiler 0.60.0+
import psutil  # psutil 5.9.0+

from src.test.utils.fixture_loader import load_fixture  # Load test fixtures for memory testing
from src.test.performance import get_memory_usage  # Utility function for measuring current memory usage
from src.test.performance import measure_peak_memory  # Utility function for measuring peak memory during function execution
from src.test.performance import PERFORMANCE_THRESHOLDS  # Dictionary containing memory usage thresholds for different components
from src.test.utils.test_helpers import setup_test_environment  # Set up test environment with mock objects and test data
from src.backend.components.transaction_retriever import TransactionRetriever  # Component under test for transaction retrieval memory usage
from src.backend.components.transaction_categorizer import TransactionCategorizer  # Component under test for transaction categorization memory usage
from src.backend.components.budget_analyzer import BudgetAnalyzer  # Component under test for budget analysis memory usage
from src.backend.components.insight_generator import InsightGenerator  # Component under test for insight generation memory usage
from src.backend.components.report_distributor import ReportDistributor  # Component under test for report distribution memory usage
from src.backend.components.savings_automator import SavingsAutomator  # Component under test for savings automation memory usage

# Set up logger
logger = logging.getLogger(__name__)

# Define memory usage thresholds for different components (in MB)
MEMORY_THRESHOLDS = {
    "transaction_retriever": 100,  # MB
    "transaction_categorizer": 150,  # MB
    "budget_analyzer": 100,  # MB
    "insight_generator": 200,  # MB
    "report_distributor": 100,  # MB
    "savings_automator": 50,   # MB
    "end_to_end": 500  # MB
}

# Define transaction sizes for scaling tests
TRANSACTION_SIZES = [10, 50, 100, 200]

def setup_memory_test_environment(transaction_count: int) -> Dict[str, Any]:
    """
    Set up a test environment with configurable transaction volume for memory testing
    
    Args:
        transaction_count: Number of transactions to generate
        
    Returns:
        Dictionary containing mock clients and test data
    """
    # Set up base test environment using setup_test_environment()
    test_env = setup_test_environment()
    
    # Generate specified number of test transactions
    transactions = test_env['test_data']['transactions'][:transaction_count]
    
    # Configure mock clients to handle the test transaction volume
    test_env['mocks']['capital_one'].set_transactions({'transactions': transactions})
    
    # Return dictionary with configured environment
    return test_env

def run_garbage_collection():
    """
    Force garbage collection to ensure accurate memory measurements
    """
    # Disable automatic garbage collection
    gc.disable()
    
    # Run manual garbage collection multiple times
    for _ in range(3):
        gc.collect()
    
    # Re-enable automatic garbage collection
    gc.enable()

def measure_memory_usage_over_time(func: callable, args: list, kwargs: dict, iterations: int) -> List[float]:
    """
    Measure memory usage over multiple iterations to detect memory leaks
    
    Args:
        func: Function to measure
        args: List of positional arguments for the function
        kwargs: Dictionary of keyword arguments for the function
        iterations: Number of iterations to run
        
    Returns:
        List of memory usage measurements after each iteration
    """
    # Initialize empty list for memory measurements
    memory_measurements = []
    
    # Run garbage collection to establish baseline
    run_garbage_collection()
    
    # Record initial memory usage
    initial_memory = get_memory_usage()
    memory_measurements.append(initial_memory)
    
    # For each iteration:
    for _ in range(iterations):
        # Execute the function with provided args and kwargs
        func(*args, **kwargs)
        
        # Run garbage collection
        run_garbage_collection()
        
        # Record memory usage and append to list
        memory_usage = get_memory_usage()
        memory_measurements.append(memory_usage)
    
    # Return list of memory measurements
    return memory_measurements

class TestMemoryUsage:
    """Test class for measuring memory usage of individual components"""
    
    def test_transaction_retriever_memory(self):
        """Test memory usage of TransactionRetriever component"""
        # Set up test environment with standard transaction volume
        test_env = setup_test_environment()
        
        # Initialize TransactionRetriever with mock clients
        retriever = TransactionRetriever(
            capital_one_client=test_env['mocks']['capital_one'],
            sheets_client=test_env['mocks']['google_sheets']
        )
        
        # Measure peak memory usage during execute() method
        peak_memory = measure_peak_memory(retriever.execute)
        
        # Assert peak memory is below threshold for TransactionRetriever
        assert peak_memory < MEMORY_THRESHOLDS['transaction_retriever'], \
            f"TransactionRetriever memory usage ({peak_memory:.2f} MB) exceeded threshold ({MEMORY_THRESHOLDS['transaction_retriever']} MB)"
        
        # Log memory usage statistics
        logger.info(f"TransactionRetriever memory usage: {peak_memory:.2f} MB")
    
    def test_transaction_categorizer_memory(self):
        """Test memory usage of TransactionCategorizer component"""
        # Set up test environment with standard transaction volume
        test_env = setup_test_environment()
        
        # Initialize TransactionCategorizer with mock clients
        categorizer = TransactionCategorizer(
            gemini_client=test_env['mocks']['gemini'],
            sheets_client=test_env['mocks']['google_sheets']
        )
        
        # Measure peak memory usage during execute() method
        peak_memory = measure_peak_memory(categorizer.execute, previous_status={})
        
        # Assert peak memory is below threshold for TransactionCategorizer
        assert peak_memory < MEMORY_THRESHOLDS['transaction_categorizer'], \
            f"TransactionCategorizer memory usage ({peak_memory:.2f} MB) exceeded threshold ({MEMORY_THRESHOLDS['transaction_categorizer']} MB)"
        
        # Log memory usage statistics
        logger.info(f"TransactionCategorizer memory usage: {peak_memory:.2f} MB")
    
    def test_budget_analyzer_memory(self):
        """Test memory usage of BudgetAnalyzer component"""
        # Set up test environment with standard transaction volume
        test_env = setup_test_environment()
        
        # Initialize BudgetAnalyzer with mock clients
        analyzer = BudgetAnalyzer(
            sheets_client=test_env['mocks']['google_sheets']
        )
        
        # Measure peak memory usage during execute() method
        peak_memory = measure_peak_memory(analyzer.execute, previous_status={})
        
        # Assert peak memory is below threshold for BudgetAnalyzer
        assert peak_memory < MEMORY_THRESHOLDS['budget_analyzer'], \
            f"BudgetAnalyzer memory usage ({peak_memory:.2f} MB) exceeded threshold ({MEMORY_THRESHOLDS['budget_analyzer']} MB)"
        
        # Log memory usage statistics
        logger.info(f"BudgetAnalyzer memory usage: {peak_memory:.2f} MB")
    
    def test_insight_generator_memory(self):
        """Test memory usage of InsightGenerator component"""
        # Set up test environment with standard transaction volume
        test_env = setup_test_environment()
        
        # Initialize InsightGenerator with mock clients
        generator = InsightGenerator(
            gemini_client=test_env['mocks']['gemini']
        )
        
        # Measure peak memory usage during execute() method
        peak_memory = measure_peak_memory(generator.execute, previous_status={})
        
        # Assert peak memory is below threshold for InsightGenerator
        assert peak_memory < MEMORY_THRESHOLDS['insight_generator'], \
            f"InsightGenerator memory usage ({peak_memory:.2f} MB) exceeded threshold ({MEMORY_THRESHOLDS['insight_generator']} MB)"
        
        # Log memory usage statistics
        logger.info(f"InsightGenerator memory usage: {peak_memory:.2f} MB")
    
    def test_report_distributor_memory(self):
        """Test memory usage of ReportDistributor component"""
        # Set up test environment with standard transaction volume
        test_env = setup_test_environment()
        
        # Initialize ReportDistributor with mock clients
        distributor = ReportDistributor(
            gmail_client=test_env['mocks']['gmail']
        )
        
        # Measure peak memory usage during execute() method
        peak_memory = measure_peak_memory(distributor.execute, previous_status={})
        
        # Assert peak memory is below threshold for ReportDistributor
        assert peak_memory < MEMORY_THRESHOLDS['report_distributor'], \
            f"ReportDistributor memory usage ({peak_memory:.2f} MB) exceeded threshold ({MEMORY_THRESHOLDS['report_distributor']} MB)"
        
        # Log memory usage statistics
        logger.info(f"ReportDistributor memory usage: {peak_memory:.2f} MB")
    
    def test_savings_automator_memory(self):
        """Test memory usage of SavingsAutomator component"""
        # Set up test environment with standard transaction volume
        test_env = setup_test_environment()
        
        # Initialize SavingsAutomator with mock clients
        automator = SavingsAutomator(
            capital_one_client=test_env['mocks']['capital_one']
        )
        
        # Measure peak memory usage during execute() method
        peak_memory = measure_peak_memory(automator.execute, previous_status={})
        
        # Assert peak memory is below threshold for SavingsAutomator
        assert peak_memory < MEMORY_THRESHOLDS['savings_automator'], \
            f"SavingsAutomator memory usage ({peak_memory:.2f} MB) exceeded threshold ({MEMORY_THRESHOLDS['savings_automator']} MB)"
        
        # Log memory usage statistics
        logger.info(f"SavingsAutomator memory usage: {peak_memory:.2f} MB")
    
    def test_end_to_end_memory(self):
        """Test memory usage of complete end-to-end workflow"""
        # Set up test environment with standard transaction volume
        test_env = setup_test_environment()
        
        # Initialize all components with mock clients
        retriever = TransactionRetriever(
            capital_one_client=test_env['mocks']['capital_one'],
            sheets_client=test_env['mocks']['google_sheets']
        )
        categorizer = TransactionCategorizer(
            gemini_client=test_env['mocks']['gemini'],
            sheets_client=test_env['mocks']['google_sheets']
        )
        analyzer = BudgetAnalyzer(
            sheets_client=test_env['mocks']['google_sheets']
        )
        generator = InsightGenerator(
            gemini_client=test_env['mocks']['gemini']
        )
        distributor = ReportDistributor(
            gmail_client=test_env['mocks']['gmail']
        )
        automator = SavingsAutomator(
            capital_one_client=test_env['mocks']['capital_one']
        )
        
        # Measure peak memory usage during complete workflow execution
        def run_workflow():
            status = retriever.execute()
            status = categorizer.execute(status)
            status = analyzer.execute(status)
            status = generator.execute(status)
            status = distributor.execute(status)
            automator.execute(status)
        
        peak_memory = measure_peak_memory(run_workflow)
        
        # Assert peak memory is below threshold for end-to-end process
        assert peak_memory < MEMORY_THRESHOLDS['end_to_end'], \
            f"End-to-end memory usage ({peak_memory:.2f} MB) exceeded threshold ({MEMORY_THRESHOLDS['end_to_end']} MB)"
        
        # Log memory usage statistics
        logger.info(f"End-to-end memory usage: {peak_memory:.2f} MB")

class TestMemoryScaling:
    """Test class for measuring how memory usage scales with different transaction volumes"""
    
    @pytest.mark.performance
    @pytest.mark.parametrize("transaction_count", TRANSACTION_SIZES)
    def test_transaction_retriever_memory_scaling(self, transaction_count: int):
        """Test how TransactionRetriever memory usage scales with transaction volume"""
        # Set up test environment with specified transaction count
        test_env = setup_memory_test_environment(transaction_count)
        
        # Initialize TransactionRetriever with mock clients
        retriever = TransactionRetriever(
            capital_one_client=test_env['mocks']['capital_one'],
            sheets_client=test_env['mocks']['google_sheets']
        )
        
        # Measure peak memory usage during execute() method
        peak_memory = measure_peak_memory(retriever.execute)
        
        # Log memory usage for this transaction volume
        logger.info(f"TransactionRetriever memory usage for {transaction_count} transactions: {peak_memory:.2f} MB")
        
        # Assert memory usage scales sub-linearly with transaction count
        assert peak_memory < MEMORY_THRESHOLDS['transaction_retriever'] * (transaction_count / TRANSACTION_SIZES[0]), \
            f"TransactionRetriever memory usage ({peak_memory:.2f} MB) scaled linearly with {transaction_count} transactions"
    
    @pytest.mark.performance
    @pytest.mark.parametrize("transaction_count", TRANSACTION_SIZES)
    def test_transaction_categorizer_memory_scaling(self, transaction_count: int):
        """Test how TransactionCategorizer memory usage scales with transaction volume"""
        # Set up test environment with specified transaction count
        test_env = setup_memory_test_environment(transaction_count)
        
        # Initialize TransactionCategorizer with mock clients
        categorizer = TransactionCategorizer(
            gemini_client=test_env['mocks']['gemini'],
            sheets_client=test_env['mocks']['google_sheets']
        )
        
        # Measure peak memory usage during execute() method
        peak_memory = measure_peak_memory(categorizer.execute, previous_status={})
        
        # Log memory usage for this transaction volume
        logger.info(f"TransactionCategorizer memory usage for {transaction_count} transactions: {peak_memory:.2f} MB")
        
        # Assert memory usage scales sub-linearly with transaction count
        assert peak_memory < MEMORY_THRESHOLDS['transaction_categorizer'] * (transaction_count / TRANSACTION_SIZES[0]), \
            f"TransactionCategorizer memory usage ({peak_memory:.2f} MB) scaled linearly with {transaction_count} transactions"
    
    @pytest.mark.performance
    @pytest.mark.parametrize("transaction_count", TRANSACTION_SIZES)
    def test_budget_analyzer_memory_scaling(self, transaction_count: int):
        """Test how BudgetAnalyzer memory usage scales with transaction volume"""
        # Set up test environment with specified transaction count
        test_env = setup_memory_test_environment(transaction_count)
        
        # Initialize BudgetAnalyzer with mock clients
        analyzer = BudgetAnalyzer(
            sheets_client=test_env['mocks']['google_sheets']
        )
        
        # Measure peak memory usage during execute() method
        peak_memory = measure_peak_memory(analyzer.execute, previous_status={})
        
        # Log memory usage for this transaction volume
        logger.info(f"BudgetAnalyzer memory usage for {transaction_count} transactions: {peak_memory:.2f} MB")
        
        # Assert memory usage scales sub-linearly with transaction count
        assert peak_memory < MEMORY_THRESHOLDS['budget_analyzer'] * (transaction_count / TRANSACTION_SIZES[0]), \
            f"BudgetAnalyzer memory usage ({peak_memory:.2f} MB) scaled linearly with {transaction_count} transactions"
    
    @pytest.mark.performance
    @pytest.mark.parametrize("transaction_count", TRANSACTION_SIZES)
    def test_end_to_end_memory_scaling(self, transaction_count: int):
        """Test how end-to-end workflow memory usage scales with transaction volume"""
        # Set up test environment with specified transaction count
        test_env = setup_memory_test_environment(transaction_count)
        
        # Initialize all components with mock clients
        retriever = TransactionRetriever(
            capital_one_client=test_env['mocks']['capital_one'],
            sheets_client=test_env['mocks']['google_sheets']
        )
        categorizer = TransactionCategorizer(
            gemini_client=test_env['mocks']['gemini'],
            sheets_client=test_env['mocks']['google_sheets']
        )
        analyzer = BudgetAnalyzer(
            sheets_client=test_env['mocks']['google_sheets']
        )
        generator = InsightGenerator(
            gemini_client=test_env['mocks']['gemini']
        )
        distributor = ReportDistributor(
            gmail_client=test_env['mocks']['gmail']
        )
        automator = SavingsAutomator(
            capital_one_client=test_env['mocks']['capital_one']
        )
        
        # Measure peak memory usage during complete workflow execution
        def run_workflow():
            status = retriever.execute()
            status = categorizer.execute(status)
            status = analyzer.execute(status)
            status = generator.execute(status)
            status = distributor.execute(status)
            automator.execute(status)
        
        peak_memory = measure_peak_memory(run_workflow)
        
        # Log memory usage for this transaction volume
        logger.info(f"End-to-end memory usage for {transaction_count} transactions: {peak_memory:.2f} MB")
        
        # Assert memory usage scales sub-linearly with transaction count
        assert peak_memory < MEMORY_THRESHOLDS['end_to_end'] * (transaction_count / TRANSACTION_SIZES[0]), \
            f"End-to-end memory usage ({peak_memory:.2f} MB) scaled linearly with {transaction_count} transactions"

class TestMemoryLeaks:
    """Test class for detecting memory leaks in components"""
    
    @pytest.mark.performance
    def test_transaction_retriever_memory_leak(self):
        """Test for memory leaks in TransactionRetriever component"""
        # Set up test environment with standard transaction volume
        test_env = setup_test_environment()
        
        # Initialize TransactionRetriever with mock clients
        retriever = TransactionRetriever(
            capital_one_client=test_env['mocks']['capital_one'],
            sheets_client=test_env['mocks']['google_sheets']
        )
        
        # Measure memory usage over multiple executions
        memory_measurements = measure_memory_usage_over_time(
            func=retriever.execute,
            args=[],
            kwargs={},
            iterations=5
        )
        
        # Assert memory usage stabilizes and doesn't continuously increase
        memory_diffs = [memory_measurements[i+1] - memory_measurements[i] for i in range(len(memory_measurements)-1)]
        assert all(diff < 5 for diff in memory_diffs), "TransactionRetriever memory usage continuously increased"
        
        # Log memory usage trend
        logger.info(f"TransactionRetriever memory usage trend: {memory_measurements}")
    
    @pytest.mark.performance
    def test_transaction_categorizer_memory_leak(self):
        """Test for memory leaks in TransactionCategorizer component"""
        # Set up test environment with standard transaction volume
        test_env = setup_test_environment()
        
        # Initialize TransactionCategorizer with mock clients
        categorizer = TransactionCategorizer(
            gemini_client=test_env['mocks']['gemini'],
            sheets_client=test_env['mocks']['google_sheets']
        )
        
        # Measure memory usage over multiple executions
        memory_measurements = measure_memory_usage_over_time(
            func=categorizer.execute,
            args=[{}],
            kwargs={},
            iterations=5
        )
        
        # Assert memory usage stabilizes and doesn't continuously increase
        memory_diffs = [memory_measurements[i+1] - memory_measurements[i] for i in range(len(memory_measurements)-1)]
        assert all(diff < 5 for diff in memory_diffs), "TransactionCategorizer memory usage continuously increased"
        
        # Log memory usage trend
        logger.info(f"TransactionCategorizer memory usage trend: {memory_measurements}")
    
    @pytest.mark.performance
    def test_budget_analyzer_memory_leak(self):
        """Test for memory leaks in BudgetAnalyzer component"""
        # Set up test environment with standard transaction volume
        test_env = setup_test_environment()
        
        # Initialize BudgetAnalyzer with mock clients
        analyzer = BudgetAnalyzer(
            sheets_client=test_env['mocks']['google_sheets']
        )
        
        # Measure memory usage over multiple executions
        memory_measurements = measure_memory_usage_over_time(
            func=analyzer.execute,
            args=[{}],
            kwargs={},
            iterations=5
        )
        
        # Assert memory usage stabilizes and doesn't continuously increase
        memory_diffs = [memory_measurements[i+1] - memory_measurements[i] for i in range(len(memory_measurements)-1)]
        assert all(diff < 5 for diff in memory_diffs), "BudgetAnalyzer memory usage continuously increased"
        
        # Log memory usage trend
        logger.info(f"BudgetAnalyzer memory usage trend: {memory_measurements}")
    
    @pytest.mark.performance
    def test_end_to_end_memory_leak(self):
        """Test for memory leaks in complete end-to-end workflow"""
        # Set up test environment with standard transaction volume
        test_env = setup_test_environment()
        
        # Initialize all components with mock clients
        retriever = TransactionRetriever(
            capital_one_client=test_env['mocks']['capital_one'],
            sheets_client=test_env['mocks']['google_sheets']
        )
        categorizer = TransactionCategorizer(
            gemini_client=test_env['mocks']['gemini'],
            sheets_client=test_env['mocks']['google_sheets']
        )
        analyzer = BudgetAnalyzer(
            sheets_client=test_env['mocks']['google_sheets']
        )
        generator = InsightGenerator(
            gemini_client=test_env['mocks']['gemini']
        )
        distributor = ReportDistributor(
            gmail_client=test_env['mocks']['gmail']
        )
        automator = SavingsAutomator(
            capital_one_client=test_env['mocks']['capital_one']
        )
        
        # Measure memory usage over multiple end-to-end executions
        def run_workflow():
            status = retriever.execute()
            status = categorizer.execute(status)
            status = analyzer.execute(status)
            status = generator.execute(status)
            status = distributor.execute(status)
            automator.execute(status)
        
        memory_measurements = measure_memory_usage_over_time(
            func=run_workflow,
            args=[],
            kwargs={},
            iterations=3
        )
        
        # Assert memory usage stabilizes and doesn't continuously increase
        memory_diffs = [memory_measurements[i+1] - memory_measurements[i] for i in range(len(memory_measurements)-1)]
        assert all(diff < 10 for diff in memory_diffs), "End-to-end memory usage continuously increased"
        
        # Log memory usage trend
        logger.info(f"End-to-end memory usage trend: {memory_measurements}")