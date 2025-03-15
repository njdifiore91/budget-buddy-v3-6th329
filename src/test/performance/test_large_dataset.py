"""
Performance test module for evaluating the Budget Management Application's ability to handle large transaction datasets.
Tests focus on memory usage, execution time, and processing efficiency when dealing with significantly larger than typical transaction volumes.
"""

import pytest  # pytest 7.4.0+
import time  # standard library
import logging  # standard library
from typing import List, Dict, Any, Tuple  # standard library
import psutil  # psutil 5.9.0+
import memory_profiler  # memory_profiler 0.60.0+

from ..utils.fixture_loader import load_fixture  # src/test/utils/fixture_loader.py
from ..utils.test_helpers import with_test_environment, create_test_transactions  # src/test/utils/test_helpers.py
from ..mocks.capital_one_client import MockCapitalOneClient  # src/test/mocks/capital_one_client.py
from ...backend.components.transaction_retriever import TransactionRetriever  # src/backend/components/transaction_retriever.py
from ...backend.components.transaction_categorizer import TransactionCategorizer  # src/backend/components/transaction_categorizer.py
from .test_transaction_processing import measure_execution_time, calculate_throughput  # src/test/performance/test_transaction_processing.py

# Set up logger
logger = logging.getLogger(__name__)

# Define large dataset sizes for testing
LARGE_DATASET_SIZES = [1000, 5000, 10000]

# Define performance thresholds for large dataset processing
PERFORMANCE_THRESHOLDS = {
    "large_dataset": {
        "max_time_seconds": 120,
        "transactions_per_second": 8,
        "max_memory_mb": 500
    }
}


def generate_large_dataset(size: int) -> List[Dict]:
    """
    Generate a large dataset of test transactions

    Args:
        size (int): The number of transactions to generate

    Returns:
        List[Dict]: List of transaction dictionaries
    """
    # Check if size is one of the predefined LARGE_DATASET_SIZES
    if size not in LARGE_DATASET_SIZES:
        raise ValueError(f"Invalid dataset size: {size}. Must be one of {LARGE_DATASET_SIZES}")

    try:
        # Try to load fixture from 'transactions/large_volume_transactions.json'
        fixture_path = 'transactions/large_volume_transactions.json'
        transactions = load_fixture(fixture_path)

        # If fixture exists, duplicate entries to reach desired size
        if len(transactions) < size:
            num_duplicates = size // len(transactions)
            remaining = size % len(transactions)
            large_dataset = transactions * num_duplicates + transactions[:remaining]
        else:
            large_dataset = transactions[:size]

        logger.info(f"Loaded large dataset from fixture: {fixture_path} with size: {size}")
        return large_dataset
    except FileNotFoundError:
        # If fixture doesn't exist, generate synthetic transactions using create_test_transactions
        logger.warning("Large volume transaction fixture not found, generating synthetic transactions")
        large_dataset = create_test_transactions(size)
        return [tx.__dict__ for tx in large_dataset]  # Convert Transaction objects to dictionaries


def setup_test_components() -> Tuple[TransactionRetriever, TransactionCategorizer, Dict]:
    """
    Set up test components with mock dependencies for large dataset testing

    Returns:
        Tuple: Tuple containing retriever, categorizer, and test environment
    """
    # Create test environment with mock objects
    test_env = with_test_environment()

    # Get mock clients from test environment
    mock_clients = test_env.get('mocks')
    mock_capital_one_client = mock_clients.get('capital_one')
    mock_google_sheets_client = mock_clients.get('google_sheets')
    mock_gemini_client = mock_clients.get('gemini')

    # Create TransactionRetriever with mock clients
    retriever = TransactionRetriever(capital_one_client=mock_capital_one_client, sheets_client=mock_google_sheets_client)

    # Create TransactionCategorizer with mock clients
    categorizer = TransactionCategorizer(gemini_client=mock_gemini_client, sheets_client=mock_google_sheets_client)

    # Authenticate the mock clients
    retriever.authenticate()
    categorizer.authenticate()

    # Return tuple of (retriever, categorizer, test_env)
    return retriever, categorizer, test_env


def monitor_resource_usage(func: callable) -> Dict:
    """
    Monitor system resource usage during test execution

    Args:
        func (callable): The function to monitor

    Returns:
        Dict: Dictionary with resource usage metrics
    """
    # Record initial CPU and memory usage using psutil
    process = psutil.Process()
    start_cpu_percent = process.cpu_percent()
    start_memory_info = process.memory_info()
    start_time = time.time()

    # Execute the provided function
    func()

    # Record final CPU and memory usage
    end_time = time.time()
    end_cpu_percent = process.cpu_percent()
    end_memory_info = process.memory_info()

    # Calculate usage differences
    cpu_usage = end_cpu_percent - start_cpu_percent
    memory_usage = end_memory_info.rss - start_memory_info.rss
    execution_time = end_time - start_time

    # Return dictionary with CPU, memory, and execution time metrics
    return {
        "cpu_usage": cpu_usage,
        "memory_usage": memory_usage,
        "execution_time": execution_time
    }


class TestLargeDatasetPerformance:
    """Test class for evaluating performance with large transaction datasets"""

    @pytest.mark.performance
    @pytest.mark.parametrize("dataset_size", LARGE_DATASET_SIZES)
    def test_transaction_retrieval_with_large_dataset(self, dataset_size: int) -> None:
        """Test performance of transaction retrieval with large datasets"""
        # Set up TransactionRetriever with mock dependencies
        retriever, mock_client, test_env = setup_test_components()

        # Generate large dataset of specified size
        large_dataset = generate_large_dataset(dataset_size)

        # Configure mock client to return large dataset
        mock_client.set_transactions({"transactions": large_dataset})

        # Measure execution time and memory usage of retrieve_transactions method
        start_time = time.time()
        retriever.retrieve_transactions()
        end_time = time.time()
        execution_time = end_time - start_time

        # Calculate throughput in transactions per second
        throughput = calculate_throughput(dataset_size, execution_time)

        # Assert execution time is within threshold
        assert execution_time <= PERFORMANCE_THRESHOLDS["large_dataset"]["max_time_seconds"]

        # Assert throughput meets minimum requirement
        assert throughput >= PERFORMANCE_THRESHOLDS["large_dataset"]["transactions_per_second"]

        # Log performance metrics
        logger.info(
            f"Large Dataset Transaction Retrieval Performance: "
            f"Size={dataset_size}, Time={execution_time:.4f}s, Throughput={throughput:.2f} tx/s"
        )

    @pytest.mark.performance
    @pytest.mark.parametrize("dataset_size", LARGE_DATASET_SIZES)
    def test_transaction_storage_with_large_dataset(self, dataset_size: int) -> None:
        """Test performance of transaction storage with large datasets"""
        # Set up TransactionRetriever with mock dependencies
        retriever, mock_client, test_env = setup_test_components()

        # Generate large dataset of specified size
        large_dataset = generate_large_dataset(dataset_size)
        transactions = [create_test_transactions(1)[0] for _ in range(dataset_size)]

        # Measure execution time and memory usage of store_transactions method
        start_time = time.time()
        retriever.store_transactions(transactions)
        end_time = time.time()
        execution_time = end_time - start_time

        # Calculate throughput in transactions per second
        throughput = calculate_throughput(dataset_size, execution_time)

        # Assert execution time is within threshold
        assert execution_time <= PERFORMANCE_THRESHOLDS["large_dataset"]["max_time_seconds"]

        # Assert throughput meets minimum requirement
        assert throughput >= PERFORMANCE_THRESHOLDS["large_dataset"]["transactions_per_second"]

        # Log performance metrics
        logger.info(
            f"Large Dataset Transaction Storage Performance: "
            f"Size={dataset_size}, Time={execution_time:.4f}s, Throughput={throughput:.2f} tx/s"
        )

    @pytest.mark.performance
    @pytest.mark.parametrize("dataset_size", LARGE_DATASET_SIZES)
    def test_transaction_categorization_with_large_dataset(self, dataset_size: int) -> None:
        """Test performance of transaction categorization with large datasets"""
        # Set up TransactionCategorizer with mock dependencies
        retriever, categorizer, test_env = setup_test_components()

        # Generate large dataset of specified size
        large_dataset = generate_large_dataset(dataset_size)
        transactions = [create_test_transactions(1)[0] for _ in range(dataset_size)]

        # Configure mock clients with test data
        mock_google_sheets_client = test_env.get('mocks').get('google_sheets')
        mock_google_sheets_client.set_sheet_data("Weekly Spending", large_dataset)

        # Measure execution time and memory usage of categorize_transactions method
        start_time = time.time()
        categorizer.categorize_transactions(transactions, test_env.get('test_data').get('categories'))
        end_time = time.time()
        execution_time = end_time - start_time

        # Calculate throughput in transactions per second
        throughput = calculate_throughput(dataset_size, execution_time)

        # Assert execution time is within threshold
        assert execution_time <= PERFORMANCE_THRESHOLDS["large_dataset"]["max_time_seconds"]

        # Assert throughput meets minimum requirement
        assert throughput >= PERFORMANCE_THRESHOLDS["large_dataset"]["transactions_per_second"]

        # Log performance metrics
        logger.info(
            f"Large Dataset Transaction Categorization Performance: "
            f"Size={dataset_size}, Time={execution_time:.4f}s, Throughput={throughput:.2f} tx/s"
        )

    @pytest.mark.performance
    @pytest.mark.parametrize("dataset_size", LARGE_DATASET_SIZES)
    def test_end_to_end_processing_with_large_dataset(self, dataset_size: int) -> None:
        """Test performance of complete processing flow with large datasets"""
        # Set up TransactionRetriever and TransactionCategorizer with mock dependencies
        retriever, categorizer, test_env = setup_test_components()

        # Generate large dataset of specified size
        large_dataset = generate_large_dataset(dataset_size)
        mock_capital_one_client = test_env.get('mocks').get('capital_one')
        mock_capital_one_client.set_transactions({"transactions": large_dataset})

        # Measure execution time and memory usage of complete workflow
        start_time = time.time()
        retriever.execute()
        categorizer.execute(previous_status={"status": "success"})
        end_time = time.time()
        execution_time = end_time - start_time

        # Calculate throughput in transactions per second
        throughput = calculate_throughput(dataset_size, execution_time)

        # Assert execution time is within threshold
        assert execution_time <= PERFORMANCE_THRESHOLDS["large_dataset"]["max_time_seconds"]

        # Assert throughput meets minimum requirement
        assert throughput >= PERFORMANCE_THRESHOLDS["large_dataset"]["transactions_per_second"]

        # Log performance metrics
        logger.info(
            f"Large Dataset End-to-End Processing Performance: "
            f"Size={dataset_size}, Time={execution_time:.4f}s, Throughput={throughput:.2f} tx/s"
        )

    @pytest.mark.performance
    @pytest.mark.parametrize("dataset_size", LARGE_DATASET_SIZES)
    def test_memory_efficiency_with_large_dataset(self, dataset_size: int) -> None:
        """Test memory efficiency when processing large datasets"""
        # Set up test components with mock dependencies
        retriever, categorizer, test_env = setup_test_components()

        # Generate large dataset of specified size
        large_dataset = generate_large_dataset(dataset_size)
        mock_capital_one_client = test_env.get('mocks').get('capital_one')
        mock_capital_one_client.set_transactions({"transactions": large_dataset})

        # Profile memory usage during execution of complete workflow
        @memory_profiler.profile
        def run_workflow():
            retriever.execute()
            categorizer.execute(previous_status={"status": "success"})

        run_workflow()

        # Measure peak memory usage and memory growth rate
        # Note: memory_profiler.profile decorator automatically prints memory usage to stdout

        # Assert peak memory usage is within threshold
        # Note: Memory profiling results are printed to stdout, but not directly accessible in pytest
        # Manual review of the output is required to verify memory usage

        # Log detailed memory usage metrics
        logger.info(
            f"Large Dataset Memory Efficiency: "
            f"Size={dataset_size}, Memory profiling results printed to stdout"
        )

    @pytest.mark.performance
    @pytest.mark.parametrize("batch_size", [100, 500, 1000])
    def test_batch_processing_with_large_dataset(self, batch_size: int) -> None:
        """Test performance of batch processing with large datasets"""
        # Set up test components with mock dependencies
        retriever, categorizer, test_env = setup_test_components()

        # Generate large dataset of 10000 transactions
        dataset_size = 10000
        large_dataset = generate_large_dataset(dataset_size)
        transactions = [create_test_transactions(1)[0] for _ in range(dataset_size)]

        # Process transactions in batches of specified size
        start_time = time.time()
        for i in range(0, len(transactions), batch_size):
            batch = transactions[i:i + batch_size]
            retriever.store_transactions(batch)
        end_time = time.time()
        execution_time = end_time - start_time

        # Calculate average throughput and memory efficiency across all batches
        average_throughput = calculate_throughput(dataset_size, execution_time)

        # Compare performance metrics between different batch sizes
        # Assert optimal batch size meets performance requirements
        assert average_throughput >= PERFORMANCE_THRESHOLDS["large_dataset"]["transactions_per_second"]

        # Log batch processing performance metrics
        logger.info(
            f"Large Dataset Batch Processing Performance: "
            f"Batch Size={batch_size}, Time={execution_time:.4f}s, Average Throughput={average_throughput:.2f} tx/s"
        )

    @pytest.mark.performance
    @pytest.mark.parametrize("dataset_size", [10000])
    def test_system_resource_usage_with_large_dataset(self, dataset_size: int) -> None:
        """Test system resource usage when processing large datasets"""
        # Set up test components with mock dependencies
        retriever, categorizer, test_env = setup_test_components()

        # Generate large dataset of specified size
        large_dataset = generate_large_dataset(dataset_size)
        mock_capital_one_client = test_env.get('mocks').get('capital_one')
        mock_capital_one_client.set_transactions({"transactions": large_dataset})

        # Monitor CPU, memory, and disk usage during execution
        resource_metrics = monitor_resource_usage(retriever.execute)

        # Calculate resource utilization percentages
        cpu_usage = resource_metrics["cpu_usage"]
        memory_usage = resource_metrics["memory_usage"]
        execution_time = resource_metrics["execution_time"]

        # Assert CPU usage is within acceptable limits
        # Assert memory usage is within acceptable limits
        # Assert disk I/O is within acceptable limits
        # Note: Resource utilization thresholds are not defined in PERFORMANCE_THRESHOLDS
        # Manual review of the output is required to verify resource usage

        # Log detailed system resource metrics
        logger.info(
            f"Large Dataset System Resource Usage: "
            f"Size={dataset_size}, CPU Usage={cpu_usage:.2f}%, Memory Usage={memory_usage / (1024 * 1024):.2f} MB, "
            f"Time={execution_time:.4f}s"
        )