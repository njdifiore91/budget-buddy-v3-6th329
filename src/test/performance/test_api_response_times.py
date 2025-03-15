"""
Performance test module for measuring and validating API response times across all external service integrations in the Budget Management Application.
Tests focus on latency, reliability, and timeout handling for Capital One, Google Sheets, Gemini, and Gmail APIs under various conditions.
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
from unittest.mock import patch

import requests  # requests 2.31.0+

from src.test.utils.fixture_loader import load_fixture  # src/test/utils/fixture_loader.py
from src.test.performance.test_transaction_processing import measure_execution_time  # ./test_transaction_processing.py
from src.test.utils.test_helpers import with_test_environment  # ../utils/test_helpers.py
from src.test.mocks.capital_one_client import MockCapitalOneClient  # ../mocks/capital_one_client.py
from src.test.mocks.google_sheets_client import MockGoogleSheetsClient  # ../mocks/google_sheets_client.py
from src.test.mocks.gemini_client import MockGeminiClient  # ../mocks/gemini_client.py
from src.test.mocks.gmail_client import MockGmailClient  # ../mocks/gmail_client.py
from src.backend.api_clients.capital_one_client import CapitalOneClient  # ../../backend/api_clients/capital_one_client.py
from src.backend.api_clients.google_sheets_client import GoogleSheetsClient  # ../../backend/api_clients/google_sheets_client.py
from src.backend.api_clients.gemini_client import GeminiClient  # ../../backend/api_clients/gemini_client.py
from src.backend.api_clients.gmail_client import GmailClient  # ../../backend/api_clients/gmail_client.py
from src.backend.services.authentication_service import AuthenticationService  # ../../backend/services/authentication_service.py

# Set up logger
logger = logging.getLogger(__name__)

# Performance thresholds for different operations
API_RESPONSE_TIME_THRESHOLDS = {
    "capital_one": {
        "get_transactions": 5.0,
        "get_account_details": 3.0,
        "initiate_transfer": 5.0
    },
    "google_sheets": {
        "read_sheet": 3.0,
        "append_rows": 3.0,
        "update_values": 3.0
    },
    "gemini": {
        "generate_completion": 10.0,
        "categorize_transactions": 15.0
    },
    "gmail": {
        "send_email": 5.0
    }
}

RETRY_TEST_CONFIGS = [
    {"max_retries": 0, "expected_time": 1.0},
    {"max_retries": 1, "expected_time": 3.0},
    {"max_retries": 3, "expected_time": 15.0}
]


def simulate_api_delay(delay_seconds: float) -> None:
    """Simulates API response delay for controlled testing"""
    time.sleep(delay_seconds)
    return None


def simulate_api_error(error_type: str, delay_seconds: Optional[float] = None) -> None:
    """Simulates API error response for testing error handling"""
    if delay_seconds:
        time.sleep(delay_seconds)

    if error_type == 'timeout':
        raise requests.Timeout
    elif error_type == 'connection':
        raise requests.ConnectionError
    elif error_type == 'server':
        raise requests.HTTPError("Server Error", response=requests.Response())
    elif error_type == 'auth':
        response = requests.Response()
        response.status_code = 401
        raise requests.HTTPError("Authentication Error", response=response)
    elif error_type == 'rate_limit':
        response = requests.Response()
        response.status_code = 429
        raise requests.HTTPError("Rate Limit Error", response=response)
    else:
        raise ValueError("Unknown error type")


def calculate_statistics(response_times: List[float]) -> Dict[str, float]:
    """Calculate statistical measures for a series of response times"""
    mean_response_time = statistics.mean(response_times)
    median_response_time = statistics.median(response_times)
    min_response_time = min(response_times)
    max_response_time = max(response_times)
    stdev_response_time = statistics.stdev(response_times) if len(response_times) > 1 else 0

    return {
        "mean": mean_response_time,
        "median": median_response_time,
        "min": min_response_time,
        "max": max_response_time,
        "stdev": stdev_response_time
    }


def setup_api_clients(use_mocks: bool) -> Dict[str, Any]:
    """Set up API clients for testing with optional mocking"""
    auth_service = AuthenticationService()

    if use_mocks:
        capital_one_client = MockCapitalOneClient()
        google_sheets_client = MockGoogleSheetsClient()
        gemini_client = MockGeminiClient()
        gmail_client = MockGmailClient()
    else:
        capital_one_client = CapitalOneClient(auth_service)
        google_sheets_client = GoogleSheetsClient(auth_service)
        gemini_client = GeminiClient(auth_service)
        gmail_client = GmailClient(auth_service)

    capital_one_client.authenticate()
    google_sheets_client.authenticate()
    # No explicit authentication for Gemini and Gmail

    return {
        "capital_one": capital_one_client,
        "google_sheets": google_sheets_client,
        "gemini": gemini_client,
        "gmail": gmail_client
    }


class TestAPIResponseTimes:
    """Test class for measuring API response times across all external services"""

    @pytest.mark.performance
    @pytest.mark.integration
    def test_capital_one_transaction_retrieval_response_time(self):
        """Test response time of Capital One transaction retrieval API"""
        api_clients = setup_api_clients(use_mocks=False)
        capital_one_client = api_clients["capital_one"]

        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        @measure_execution_time
        def retrieve_transactions():
            return capital_one_client.get_transactions(start_date, end_date)

        _, execution_time = retrieve_transactions()

        assert execution_time <= API_RESPONSE_TIME_THRESHOLDS["capital_one"]["get_transactions"]

        logger.info(f"Capital One Transaction Retrieval Response Time: {execution_time:.4f} seconds")

    @pytest.mark.performance
    @pytest.mark.integration
    def test_capital_one_account_details_response_time(self):
        """Test response time of Capital One account details API"""
        api_clients = setup_api_clients(use_mocks=False)
        capital_one_client = api_clients["capital_one"]

        @measure_execution_time
        def get_account_details():
            return capital_one_client.get_account_details(capital_one_client.checking_account_id)

        _, execution_time = get_account_details()

        assert execution_time <= API_RESPONSE_TIME_THRESHOLDS["capital_one"]["get_account_details"]

        logger.info(f"Capital One Account Details Response Time: {execution_time:.4f} seconds")

    @pytest.mark.performance
    @pytest.mark.integration
    def test_capital_one_transfer_response_time(self):
        """Test response time of Capital One transfer API"""
        api_clients = setup_api_clients(use_mocks=False)
        capital_one_client = api_clients["capital_one"]

        @measure_execution_time
        def initiate_transfer():
            return capital_one_client.initiate_transfer(
                amount=1.00,
                source_account_id=capital_one_client.checking_account_id,
                destination_account_id=capital_one_client.savings_account_id
            )

        _, execution_time = initiate_transfer()

        assert execution_time <= API_RESPONSE_TIME_THRESHOLDS["capital_one"]["initiate_transfer"]

        logger.info(f"Capital One Transfer Response Time: {execution_time:.4f} seconds")

    @pytest.mark.performance
    @pytest.mark.integration
    def test_google_sheets_read_response_time(self):
        """Test response time of Google Sheets read API"""
        api_clients = setup_api_clients(use_mocks=False)
        google_sheets_client = api_clients["google_sheets"]

        @measure_execution_time
        def read_sheet():
            return google_sheets_client.read_sheet(
                spreadsheet_id=google_sheets_client.weekly_spending_id,
                range_name="Sheet1!A1:B2"
            )

        _, execution_time = read_sheet()

        assert execution_time <= API_RESPONSE_TIME_THRESHOLDS["google_sheets"]["read_sheet"]

        logger.info(f"Google Sheets Read Response Time: {execution_time:.4f} seconds")

    @pytest.mark.performance
    @pytest.mark.integration
    def test_google_sheets_write_response_time(self):
        """Test response time of Google Sheets write API"""
        api_clients = setup_api_clients(use_mocks=False)
        google_sheets_client = api_clients["google_sheets"]

        @measure_execution_time
        def append_rows():
            return google_sheets_client.append_rows(
                spreadsheet_id=google_sheets_client.weekly_spending_id,
                range_name="Sheet1!A1:B2",
                values=[["Test", "123"]]
            )

        _, execution_time = append_rows()

        assert execution_time <= API_RESPONSE_TIME_THRESHOLDS["google_sheets"]["append_rows"]

        logger.info(f"Google Sheets Write Response Time: {execution_time:.4f} seconds")

    @pytest.mark.performance
    @pytest.mark.integration
    def test_gemini_completion_response_time(self):
        """Test response time of Gemini AI completion API"""
        api_clients = setup_api_clients(use_mocks=False)
        gemini_client = api_clients["gemini"]

        @measure_execution_time
        def generate_completion():
            return gemini_client.generate_completion("Write a short poem.")

        _, execution_time = generate_completion()

        assert execution_time <= API_RESPONSE_TIME_THRESHOLDS["gemini"]["generate_completion"]

        logger.info(f"Gemini Completion Response Time: {execution_time:.4f} seconds")

    @pytest.mark.performance
    @pytest.mark.integration
    def test_gemini_categorization_response_time(self):
        """Test response time of Gemini AI transaction categorization"""
        api_clients = setup_api_clients(use_mocks=False)
        gemini_client = api_clients["gemini"]

        @measure_execution_time
        def categorize_transactions():
            return gemini_client.categorize_transactions(
                transaction_locations=["Walmart", "McDonalds"],
                budget_categories=["Groceries", "Dining Out"]
            )

        _, execution_time = categorize_transactions()

        assert execution_time <= API_RESPONSE_TIME_THRESHOLDS["gemini"]["categorize_transactions"]

        logger.info(f"Gemini Categorization Response Time: {execution_time:.4f} seconds")

    @pytest.mark.performance
    @pytest.mark.integration
    def test_gmail_send_email_response_time(self):
        """Test response time of Gmail send email API"""
        api_clients = setup_api_clients(use_mocks=False)
        gmail_client = api_clients["gmail"]

        @measure_execution_time
        def send_email():
            return gmail_client.send_email(
                subject="Test Email",
                html_content="<p>This is a test email.</p>",
                recipients=["test@example.com"]
            )

        _, execution_time = send_email()

        assert execution_time <= API_RESPONSE_TIME_THRESHOLDS["gmail"]["send_email"]

        logger.info(f"Gmail Send Email Response Time: {execution_time:.4f} seconds")

    @pytest.mark.performance
    @pytest.mark.parametrize("retry_config", RETRY_TEST_CONFIGS)
    def test_retry_mechanism_impact_on_response_time(self, retry_config: Dict[str, Any]):
        """Test impact of retry mechanism on API response times"""
        max_retries = retry_config["max_retries"]
        expected_time = retry_config["expected_time"]

        api_clients = setup_api_clients(use_mocks=True)
        capital_one_client = api_clients["capital_one"]

        # Simulate API delay
        with patch.object(MockCapitalOneClient, 'get_transactions', side_effect=[Exception("Simulated Error")] * max_retries + [[]]) as mock_get_transactions:
            start_time = time.time()
            try:
                capital_one_client.get_transactions()
            except:
                pass
            end_time = time.time()
            actual_time = end_time - start_time

            assert actual_time <= expected_time

            logger.info(
                f"Retry Mechanism Impact: Max Retries={max_retries}, "
                f"Expected Time={expected_time:.4f}s, Actual Time={actual_time:.4f}s"
            )

    @pytest.mark.performance
    @pytest.mark.parametrize("concurrent_requests", [1, 5, 10])
    def test_api_response_time_under_load(self, concurrent_requests: int):
        """Test API response times under concurrent load"""
        api_clients = setup_api_clients(use_mocks=True)
        capital_one_client = api_clients["capital_one"]

        response_times = []

        def make_request():
            start_time = time.time()
            capital_one_client.get_transactions()
            end_time = time.time()
            response_times.append(end_time - start_time)

        import threading
        threads = []
        for _ in range(concurrent_requests):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        stats = calculate_statistics(response_times)
        mean_response_time = stats["mean"]

        # Allow for some extra time due to concurrency
        threshold = API_RESPONSE_TIME_THRESHOLDS["capital_one"]["get_transactions"] * concurrent_requests
        assert mean_response_time <= threshold

        logger.info(
            f"API Response Time Under Load: Concurrent Requests={concurrent_requests}, "
            f"Mean Response Time={mean_response_time:.4f}s"
        )

    @pytest.mark.performance
    @pytest.mark.parametrize("timeout_seconds", [5, 10, 30])
    def test_api_timeout_handling(self, timeout_seconds: int):
        """Test handling of API timeouts"""
        api_clients = setup_api_clients(use_mocks=True)
        capital_one_client = api_clients["capital_one"]

        # Simulate API timeout
        with patch.object(MockCapitalOneClient, 'get_transactions', side_effect=requests.Timeout):
            start_time = time.time()
            try:
                capital_one_client.get_transactions()
            except requests.Timeout:
                end_time = time.time()
                actual_time = end_time - start_time

                assert actual_time <= timeout_seconds + 1  # Allow for some overhead

                logger.info(
                    f"API Timeout Handling: Timeout Seconds={timeout_seconds}, "
                    f"Actual Time={actual_time:.4f}s"
                )
            except Exception as e:
                pytest.fail(f"Unexpected exception: {e}")
            else:
                pytest.fail("Expected requests.Timeout exception was not raised")

    @pytest.mark.performance
    def test_api_rate_limit_handling(self):
        """Test handling of API rate limiting"""
        api_clients = setup_api_clients(use_mocks=True)
        capital_one_client = api_clients["capital_one"]

        # Simulate API rate limiting
        with patch.object(MockCapitalOneClient, 'get_transactions', side_effect=requests.exceptions.HTTPError("Rate Limited")) as mock_get_transactions:
            start_time = time.time()
            try:
                capital_one_client.get_transactions()
            except requests.exceptions.HTTPError:
                end_time = time.time()
                actual_time = end_time - start_time

                # Add assertions to validate backoff implementation
                assert mock_get_transactions.call_count == 1

                logger.info(
                    f"API Rate Limit Handling: Actual Time={actual_time:.4f}s"
                )
            except Exception as e:
                pytest.fail(f"Unexpected exception: {e}")
            else:
                pytest.fail("Expected requests.exceptions.HTTPError exception was not raised")

    @pytest.mark.performance
    @pytest.mark.integration
    def test_end_to_end_api_response_time(self):
        """Test end-to-end API response time for complete workflow"""
        api_clients = setup_api_clients(use_mocks=False)
        capital_one_client = api_clients["capital_one"]
        google_sheets_client = api_clients["google_sheets"]
        gemini_client = api_clients["gemini"]
        gmail_client = api_clients["gmail"]

        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        total_api_time = 0

        @measure_execution_time
        def retrieve_transactions():
            return capital_one_client.get_transactions(start_date, end_date)

        _, execution_time = retrieve_transactions()
        total_api_time += execution_time

        @measure_execution_time
        def read_sheet():
            return google_sheets_client.read_sheet(
                spreadsheet_id=google_sheets_client.weekly_spending_id,
                range_name="Sheet1!A1:B2"
            )

        _, execution_time = read_sheet()
        total_api_time += execution_time

        @measure_execution_time
        def generate_completion():
            return gemini_client.generate_completion("Write a short poem.")

        _, execution_time = generate_completion()
        total_api_time += execution_time

        @measure_execution_time
        def send_email():
            return gmail_client.send_email(
                subject="Test Email",
                html_content="<p>This is a test email.</p>",
                recipients=["test@example.com"]
            )

        _, execution_time = send_email()
        total_api_time += execution_time

        acceptable_threshold = 25  # Acceptable threshold for total API time

        assert total_api_time <= acceptable_threshold

        logger.info(f"End-to-End API Response Time: {total_api_time:.4f} seconds")