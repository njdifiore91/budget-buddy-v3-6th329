"""
End-to-end performance test module for the Budget Management Application.
Tests the overall system performance, memory usage, and scalability across the complete workflow from transaction retrieval to savings automation. Validates that the application meets performance requirements under various load conditions.
"""

import pytest  # pytest 7.4.0+
import time  # standard library
from typing import List, Dict, Any, Optional  # standard library
import logging  # standard library
import statistics  # standard library

from src.test.utils.fixture_loader import load_fixture  # src/test/utils/fixture_loader.py
from src.test.utils.test_helpers import create_test_transactions, setup_test_environment, teardown_test_environment, with_test_environment  # src/test/utils/test_helpers.py
from src.test.mocks.capital_one_client import MockCapitalOneClient  # src/test/mocks/capital_one_client.py
from src.test.mocks.google_sheets_client import MockGoogleSheetsClient  # src/test/mocks/google_sheets_client.py
from src.test.mocks.gemini_client import MockGeminiClient  # src/test/mocks/gemini_client.py
from src.test.mocks.gmail_client import MockGmailClient  # src/test/mocks/gmail_client.py
from src.backend.components.transaction_retriever import TransactionRetriever  # src/backend/components/transaction_retriever.py
from src.backend.components.budget_analyzer import BudgetAnalyzer  # src/backend/components/budget_analyzer.py
from src.test.performance.test_transaction_processing import measure_execution_time, get_memory_usage  # src/test/performance/test_transaction_processing.py

# Set up logger
logger = logging.getLogger(__name__)

# Performance thresholds for different operations
PERFORMANCE_THRESHOLDS = {"end_to_end": {"small_volume": {"max_time": 3.0, "max_memory_mb": 100}, "medium_volume": {"max_time": 4.0, "max_memory_mb": 150}, "large_volume": {"max_time": 5.0, "max_memory_mb": 200}}}
LARGE_TRANSACTION_FIXTURE = "json/transactions/large_volume_transactions.json"
TEST_ITERATIONS = 3


def setup_mock_clients_with_volume(volume: str) -> Dict[str, Any]:
    """Set up mock clients with transaction data of specified volume

    Args:
        volume: Volume of transaction data ('small', 'medium', 'large')

    Returns:
        Dictionary containing mock clients and test data
    """
    test_env = setup_test_environment()
    capital_one_client = test_env['mocks']['capital_one']

    if volume == 'small':
        transactions = create_test_transactions(10)
    elif volume == 'medium':
        transactions = create_test_transactions(50)
    elif volume == 'large':
        transactions = load_fixture(LARGE_TRANSACTION_FIXTURE)
    else:
        raise ValueError(f"Invalid volume: {volume}")

    capital_one_client.set_transactions(transactions)
    google_sheets_client = test_env['mocks']['google_sheets']
    google_sheets_client.set_sheet_data("Master Budget", load_fixture("json/budget/valid_categories.json"))

    return test_env


def run_end_to_end_workflow(test_env: Dict[str, Any]) -> Dict[str, Any]:
    """Run the complete budget management workflow from transaction retrieval to reporting

    Args:
        test_env: Dictionary containing mock clients

    Returns:
        Results of the workflow execution
    """
    capital_one_client = test_env['mocks']['capital_one']
    google_sheets_client = test_env['mocks']['google_sheets']
    gemini_client = test_env['mocks']['gemini']
    gmail_client = test_env['mocks']['gmail']

    transaction_retriever = TransactionRetriever(capital_one_client=capital_one_client, sheets_client=google_sheets_client)
    retriever_result = transaction_retriever.execute()

    budget_analyzer = BudgetAnalyzer(sheets_client=google_sheets_client)
    analyzer_result = budget_analyzer.execute(retriever_result)

    return {"retriever_result": retriever_result, "analyzer_result": analyzer_result}


def measure_workflow_performance(test_env: Dict[str, Any]) -> Dict[str, Any]:
    """Measure execution time and memory usage of the end-to-end workflow

    Args:
        test_env: Dictionary containing mock clients

    Returns:
        Performance metrics including execution time and memory usage
    """
    baseline_memory = get_memory_usage()
    start_time = time.time()
    workflow_results = run_end_to_end_workflow(test_env)
    end_time = time.time()
    peak_memory = get_memory_usage()

    execution_time = end_time - start_time
    memory_increase = peak_memory - baseline_memory

    return {"execution_time": execution_time, "memory_increase": memory_increase, "workflow_results": workflow_results}


class TestEndToEndPerformance:
    """Test class for measuring end-to-end performance of the Budget Management Application"""

    @pytest.mark.e2e
    @pytest.mark.performance
    def test_end_to_end_performance_small_volume(self):
        """Test end-to-end performance with small transaction volume"""
        test_env = setup_mock_clients_with_volume('small')
        performance_metrics = measure_workflow_performance(test_env)

        assert performance_metrics["execution_time"] <= PERFORMANCE_THRESHOLDS["end_to_end"]["small_volume"]["max_time"]
        assert performance_metrics["memory_increase"] <= PERFORMANCE_THRESHOLDS["end_to_end"]["small_volume"]["max_memory_mb"]
        assert test_env["mocks"]["capital_one"].authenticated

    @pytest.mark.e2e
    @pytest.mark.performance
    def test_end_to_end_performance_medium_volume(self):
        """Test end-to-end performance with medium transaction volume"""
        test_env = setup_mock_clients_with_volume('medium')
        performance_metrics = measure_workflow_performance(test_env)

        assert performance_metrics["execution_time"] <= PERFORMANCE_THRESHOLDS["end_to_end"]["medium_volume"]["max_time"]
        assert performance_metrics["memory_increase"] <= PERFORMANCE_THRESHOLDS["end_to_end"]["medium_volume"]["max_memory_mb"]
        assert test_env["mocks"]["capital_one"].authenticated

    @pytest.mark.e2e
    @pytest.mark.performance
    def test_end_to_end_performance_large_volume(self):
        """Test end-to-end performance with large transaction volume"""
        test_env = setup_mock_clients_with_volume('large')
        performance_metrics = measure_workflow_performance(test_env)

        assert performance_metrics["execution_time"] <= PERFORMANCE_THRESHOLDS["end_to_end"]["large_volume"]["max_time"]
        assert performance_metrics["memory_increase"] <= PERFORMANCE_THRESHOLDS["end_to_end"]["large_volume"]["max_memory_mb"]
        assert test_env["mocks"]["capital_one"].authenticated

    @pytest.mark.e2e
    @pytest.mark.performance
    def test_performance_consistency(self):
        """Test consistency of performance across multiple executions"""
        test_env = setup_mock_clients_with_volume('medium')
        execution_times = []

        for _ in range(TEST_ITERATIONS):
            performance_metrics = measure_workflow_performance(test_env)
            execution_times.append(performance_metrics["execution_time"])

        stdev_execution_time = statistics.stdev(execution_times)
        assert stdev_execution_time <= 1.0  # Acceptable standard deviation
        assert all(test_env["mocks"]["capital_one"].authenticated for _ in range(TEST_ITERATIONS))

    @pytest.mark.e2e
    @pytest.mark.performance
    def test_memory_cleanup(self):
        """Test that memory is properly released after workflow execution"""
        baseline_memory = get_memory_usage()
        test_env = setup_mock_clients_with_volume('medium')
        performance_metrics = measure_workflow_performance(test_env)
        peak_memory = performance_metrics["memory_increase"]

        import gc
        gc.collect()
        memory_after_cleanup = get_memory_usage()

        assert memory_after_cleanup - baseline_memory <= 20  # Acceptable memory leak
        assert test_env["mocks"]["capital_one"].authenticated

    @pytest.mark.e2e
    @pytest.mark.performance
    @pytest.mark.parametrize("volume", ["small", "medium", "large"])
    def test_parametrized_volume_performance(self, volume: str):
        """Parametrized test for different transaction volumes"""
        test_env = setup_mock_clients_with_volume(volume)
        performance_metrics = measure_workflow_performance(test_env)

        assert performance_metrics["execution_time"] <= PERFORMANCE_THRESHOLDS["end_to_end"][volume]["max_time"]
        assert performance_metrics["memory_increase"] <= PERFORMANCE_THRESHOLDS["end_to_end"][volume]["max_memory_mb"]
        assert test_env["mocks"]["capital_one"].authenticated


class TestComponentPerformanceIntegration:
    """Test class for measuring performance of integrated components"""

    @pytest.mark.e2e
    @pytest.mark.performance
    def test_transaction_retrieval_to_budget_analysis(self):
        """Test performance of transaction retrieval followed by budget analysis"""
        test_env = setup_mock_clients_with_volume('medium')
        capital_one_client = test_env['mocks']['capital_one']
        google_sheets_client = test_env['mocks']['google_sheets']

        transaction_retriever = TransactionRetriever(capital_one_client=capital_one_client, sheets_client=google_sheets_client)
        budget_analyzer = BudgetAnalyzer(sheets_client=google_sheets_client)

        @measure_execution_time
        def retrieve_and_analyze():
            retriever_result = transaction_retriever.execute()
            return budget_analyzer.execute(retriever_result)

        result, execution_time = retrieve_and_analyze()

        assert execution_time <= 5.0  # Combined threshold
        assert test_env["mocks"]["capital_one"].authenticated
        assert result["status"] == "success"

    @pytest.mark.e2e
    @pytest.mark.performance
    def test_memory_profile_critical_path(self):
        """Test memory usage along the critical path of the application"""
        test_env = setup_mock_clients_with_volume('medium')
        capital_one_client = test_env['mocks']['capital_one']
        google_sheets_client = test_env['mocks']['google_sheets']

        transaction_retriever = TransactionRetriever(capital_one_client=capital_one_client, sheets_client=google_sheets_client)
        budget_analyzer = BudgetAnalyzer(sheets_client=google_sheets_client)

        def retrieve_and_analyze():
            retriever_result = transaction_retriever.execute()
            return budget_analyzer.execute(retriever_result)

        baseline_memory = get_memory_usage()
        result, peak_memory = measure_execution_time(retrieve_and_analyze)()
        memory_increase = peak_memory - baseline_memory

        assert memory_increase <= 150  # Combined memory threshold
        assert test_env["mocks"]["capital_one"].authenticated