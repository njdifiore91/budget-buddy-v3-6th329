"""
Performance test module for measuring and validating the transaction processing capabilities of the Budget Management Application.
Tests focus on throughput, memory usage, and execution time of transaction retrieval, storage, and categorization operations under various load conditions.
"""

import pytest  # pytest 7.4.0+
import time  # standard library
from datetime import datetime, timedelta  # standard library
from decimal import decimal, Decimal  # standard library
import statistics  # standard library
import functools  # standard library
from functools import wraps  # standard library
from typing import List, Dict, Any, Callable, Tuple, Optional  # standard library
import logging  # standard library
import memory_profiler  # memory_profiler 0.60.0+
from memory_profiler import profile  # memory_profiler 0.60.0+

from ..utils.fixture_loader import load_fixture  # src/test/utils/fixture_loader.py
from ..utils.test_helpers import create_test_transactions, with_test_environment  # src/test/utils/test_helpers.py
from ..mocks.capital_one_client import MockCapitalOneClient  # src/test/mocks/capital_one_client.py
from ...backend.components.transaction_retriever import TransactionRetriever  # src/backend/components/transaction_retriever.py
from ...backend.models.transaction import Transaction  # src/backend/models/transaction.py

# Set up logger
logger = logging.getLogger(__name__)

# Performance thresholds for different operations
PERFORMANCE_THRESHOLDS = {
    "transaction_retrieval": {
        "max_time_seconds": 30,
        "transactions_per_second": 10
    },
    "transaction_storage": {
        "max_time_seconds": 15,
        "transactions_per_second": 20
    },
    "transaction_processing": {
        "max_time_seconds": 60,
        "transactions_per_second": 5
    },
    "memory_usage": {
        "max_mb": 200
    }
}

# Test transaction volumes
TEST_TRANSACTION_VOLUMES = [10, 50, 100, 500]


def measure_execution_time(func: Callable) -> Callable:
    """Decorator to measure and log the execution time of a function"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """Wrapped function that measures execution time"""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"Execution time for {func.__name__}: {execution_time:.4f} seconds")
        return result, execution_time
    return wrapper


def calculate_throughput(transaction_count: int, execution_time_seconds: float) -> float:
    """Calculate throughput in transactions per second"""
    if execution_time_seconds == 0:
        return 0
    throughput = transaction_count / execution_time_seconds
    return throughput


def generate_test_transactions(count: int) -> List[Transaction]:
    """Generate a specified number of test transactions"""
    transactions = create_test_transactions(count)
    return transactions


def setup_transaction_retriever() -> Tuple[TransactionRetriever, MockCapitalOneClient, Dict]:
    """Set up a TransactionRetriever with mock dependencies for testing"""
    test_env = with_test_environment()
    mock_client = test_env.get('mocks').get('capital_one')
    retriever = TransactionRetriever(capital_one_client=mock_client)
    retriever.authenticate()
    return retriever, mock_client, test_env


def profile_memory_usage(func: Callable, args: List, kwargs: Dict) -> Tuple[Any, float]:
    """Profile memory usage of a function"""
    mprof = memory_profiler.LineProfiler()
    wrapped_func = mprof(func)
    result = wrapped_func(*args, **kwargs)
    peak_memory_usage = mprof.max_mem_usage
    return result, peak_memory_usage


class TestTransactionProcessingPerformance:
    """Test class for measuring transaction processing performance"""

    @pytest.mark.performance
    @pytest.mark.parametrize("transaction_count", TEST_TRANSACTION_VOLUMES)
    def test_transaction_retrieval_performance(self, transaction_count: int):
        """Test performance of transaction retrieval operation"""
        retriever, mock_client, test_env = setup_transaction_retriever()
        transactions = generate_test_transactions(transaction_count)
        mock_client.set_transactions(transactions)

        @measure_execution_time
        def retrieve_transactions():
            return retriever.retrieve_transactions()

        retrieved_transactions, execution_time = retrieve_transactions()
        throughput = calculate_throughput(transaction_count, execution_time)

        assert execution_time <= PERFORMANCE_THRESHOLDS["transaction_retrieval"]["max_time_seconds"]
        assert throughput >= PERFORMANCE_THRESHOLDS["transaction_retrieval"]["transactions_per_second"]

        logger.info(
            f"Transaction Retrieval Performance: "
            f"Count={transaction_count}, Time={execution_time:.4f}s, Throughput={throughput:.2f} tx/s"
        )

    @pytest.mark.performance
    @pytest.mark.parametrize("transaction_count", TEST_TRANSACTION_VOLUMES)
    def test_transaction_storage_performance(self, transaction_count: int):
        """Test performance of transaction storage operation"""
        retriever, mock_client, test_env = setup_transaction_retriever()
        transactions = generate_test_transactions(transaction_count)

        @measure_execution_time
        def store_transactions():
            return retriever.store_transactions(transactions)

        stored_count, execution_time = store_transactions()
        throughput = calculate_throughput(transaction_count, execution_time)

        assert execution_time <= PERFORMANCE_THRESHOLDS["transaction_storage"]["max_time_seconds"]
        assert throughput >= PERFORMANCE_THRESHOLDS["transaction_storage"]["transactions_per_second"]

        logger.info(
            f"Transaction Storage Performance: "
            f"Count={transaction_count}, Time={execution_time:.4f}s, Throughput={throughput:.2f} tx/s"
        )

    @pytest.mark.performance
    @pytest.mark.parametrize("transaction_count", TEST_TRANSACTION_VOLUMES)
    def test_end_to_end_transaction_processing_performance(self, transaction_count: int):
        """Test performance of complete transaction processing flow"""
        retriever, mock_client, test_env = setup_transaction_retriever()
        transactions = generate_test_transactions(transaction_count)
        mock_client.set_transactions(transactions)

        @measure_execution_time
        def execute_transaction_processing():
            return retriever.execute()

        result, execution_time = execute_transaction_processing()
        throughput = calculate_throughput(transaction_count, execution_time)

        assert execution_time <= PERFORMANCE_THRESHOLDS["transaction_processing"]["max_time_seconds"]
        assert throughput >= PERFORMANCE_THRESHOLDS["transaction_processing"]["transactions_per_second"]

        logger.info(
            f"End-to-End Transaction Processing Performance: "
            f"Count={transaction_count}, Time={execution_time:.4f}s, Throughput={throughput:.2f} tx/s"
        )

    @pytest.mark.performance
    @pytest.mark.parametrize("transaction_count", TEST_TRANSACTION_VOLUMES)
    def test_transaction_processing_memory_usage(self, transaction_count: int):
        """Test memory usage during transaction processing"""
        retriever, mock_client, test_env = setup_transaction_retriever()
        transactions = generate_test_transactions(transaction_count)
        mock_client.set_transactions(transactions)

        def execute_transaction_processing():
            return retriever.execute()

        result, peak_memory_usage = profile_memory_usage(execute_transaction_processing, [], {})

        assert peak_memory_usage <= PERFORMANCE_THRESHOLDS["memory_usage"]["max_mb"]

        logger.info(
            f"Transaction Processing Memory Usage: "
            f"Count={transaction_count}, Peak Memory={peak_memory_usage:.2f} MB"
        )

    @pytest.mark.performance
    @pytest.mark.parametrize("transaction_count", [100])
    @pytest.mark.parametrize("iterations", [5])
    def test_transaction_processing_under_load(self, transaction_count: int, iterations: int):
        """Test transaction processing performance under repeated load"""
        retriever, mock_client, test_env = setup_transaction_retriever()
        transactions = generate_test_transactions(transaction_count)
        mock_client.set_transactions(transactions)

        execution_times = []
        for i in range(iterations):
            start_time = time.time()
            retriever.execute()
            end_time = time.time()
            execution_time = end_time - start_time
            execution_times.append(execution_time)

        mean_execution_time = statistics.mean(execution_times)
        median_execution_time = statistics.median(execution_times)
        min_execution_time = min(execution_times)
        max_execution_time = max(execution_times)
        stdev_execution_time = statistics.stdev(execution_times)

        assert mean_execution_time <= PERFORMANCE_THRESHOLDS["transaction_processing"]["max_time_seconds"]
        assert stdev_execution_time <= 10  # Acceptable standard deviation

        logger.info(
            f"Transaction Processing Under Load: "
            f"Count={transaction_count}, Iterations={iterations}, "
            f"Mean={mean_execution_time:.4f}s, Median={median_execution_time:.4f}s, "
            f"Min={min_execution_time:.4f}s, Max={max_execution_time:.4f}s, "
            f"Stdev={stdev_execution_time:.4f}s"
        )

    @pytest.mark.performance
    @pytest.mark.parametrize("batch_size", [10, 25, 50, 100])
    def test_transaction_batch_size_impact(self, batch_size: int):
        """Test impact of different batch sizes on transaction processing performance"""
        retriever, mock_client, test_env = setup_transaction_retriever()
        transactions = generate_test_transactions(100)
        mock_client.set_transactions(transactions)

        total_execution_time = 0
        for i in range(0, len(transactions), batch_size):
            batch = transactions[i:i + batch_size]
            start_time = time.time()
            retriever.store_transactions(batch)
            end_time = time.time()
            total_execution_time += (end_time - start_time)

        average_throughput = calculate_throughput(len(transactions), total_execution_time)

        assert average_throughput >= PERFORMANCE_THRESHOLDS["transaction_storage"]["transactions_per_second"]

        logger.info(
            f"Transaction Batch Size Impact: "
            f"Batch Size={batch_size}, Time={total_execution_time:.4f}s, "
            f"Average Throughput={average_throughput:.2f} tx/s"
        )