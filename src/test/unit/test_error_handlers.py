"""
Unit tests for the error handling utilities in the Budget Management Application.
Tests the functionality of retry mechanisms, error classification, custom exceptions,
and error formatting to ensure robust error handling across all components.
"""

import pytest  # pytest 7.4.0+
from unittest.mock import MagicMock, patch, Mock, call  # standard library
import requests  # requests 2.31.0+
import time  # standard library

from src.backend.utils.error_handlers import retry_with_backoff, is_retriable_error, handle_api_error, \
    handle_validation_error, handle_auth_error, format_exception_for_log, safe_execute, APIError, \
    ValidationError, AuthenticationError  # Internal imports
from src.test.utils.test_helpers import load_test_fixture  # Internal imports
from src.test.fixtures.api_responses import get_error_response  # Internal imports


@pytest.mark.unit
def test_retry_with_backoff_successful_execution():
    """Test that retry_with_backoff allows successful function execution to pass through"""
    # Create a mock function that returns a success value
    mock_func = MagicMock(return_value="Success")

    # Decorate the mock function with retry_with_backoff
    decorated_func = retry_with_backoff()(mock_func)

    # Call the decorated function
    result = decorated_func()

    # Assert that the function was called exactly once
    mock_func.assert_called_once()

    # Assert that the return value matches the expected success value
    assert result == "Success"


@pytest.mark.unit
@patch('time.sleep')
def test_retry_with_backoff_retries_on_specified_exceptions(mock_sleep):
    """Test that retry_with_backoff retries the function when specified exceptions occur"""
    # Create a mock function that raises an exception on first calls then succeeds
    mock_func = MagicMock(side_effect=[ValueError("Test Exception"), "Success"])

    # Decorate the mock function with retry_with_backoff for the specific exception
    decorated_func = retry_with_backoff(exceptions=ValueError, max_retries=1)(mock_func)

    # Call the decorated function
    result = decorated_func()

    # Assert that the function was called multiple times
    assert mock_func.call_count == 2

    # Assert that time.sleep was called with increasing delays
    mock_sleep.assert_called_once()

    # Assert that the final return value matches the expected success value
    assert result == "Success"


@pytest.mark.unit
@patch('time.sleep')
def test_retry_with_backoff_max_retries_exceeded(mock_sleep):
    """Test that retry_with_backoff raises the exception after max retries are exceeded"""
    # Create a mock function that always raises an exception
    mock_func = MagicMock(side_effect=ValueError("Test Exception"))

    # Decorate the mock function with retry_with_backoff with a specific max_retries value
    decorated_func = retry_with_backoff(exceptions=ValueError, max_retries=2)(mock_func)

    # Call the decorated function and expect it to raise the exception
    with pytest.raises(ValueError):
        decorated_func()

    # Assert that the function was called exactly max_retries + 1 times
    assert mock_func.call_count == 3

    # Assert that time.sleep was called the expected number of times with correct delays
    assert mock_sleep.call_count == 2


@pytest.mark.unit
@patch('time.sleep')
def test_retry_with_backoff_ignores_unspecified_exceptions(mock_sleep):
    """Test that retry_with_backoff doesn't retry for exceptions not in the specified list"""
    # Create a mock function that raises an exception not in the retry list
    mock_func = MagicMock(side_effect=TypeError("Test Exception"))

    # Decorate the mock function with retry_with_backoff for a different exception type
    decorated_func = retry_with_backoff(exceptions=ValueError, max_retries=2)(mock_func)

    # Call the decorated function and expect it to raise the original exception
    with pytest.raises(TypeError):
        decorated_func()

    # Assert that the function was called exactly once
    mock_func.assert_called_once()

    # Assert that time.sleep was not called
    mock_sleep.assert_not_called()


@pytest.mark.unit
def test_is_retriable_error_with_http_errors():
    """Test that is_retriable_error correctly identifies retriable HTTP errors"""
    # Create mock requests.HTTPError with various status codes
    retriable_status_codes = [429, 500, 502, 503, 504]
    non_retriable_status_codes = [400, 401, 403, 404]

    for status_code in retriable_status_codes:
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_http_error = requests.HTTPError("Test HTTP Error", response=mock_response)
        assert is_retriable_error(mock_http_error)

    for status_code in non_retriable_status_codes:
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_http_error = requests.HTTPError("Test HTTP Error", response=mock_response)
        assert not is_retriable_error(mock_http_error)


@pytest.mark.unit
def test_is_retriable_error_with_connection_errors():
    """Test that is_retriable_error correctly identifies retriable connection errors"""
    # Create mock requests.ConnectionError
    mock_connection_error = requests.ConnectionError("Test Connection Error")
    assert is_retriable_error(mock_connection_error)

    # Create mock requests.Timeout
    mock_timeout = requests.Timeout("Test Timeout")
    assert is_retriable_error(mock_timeout)


@pytest.mark.unit
def test_is_retriable_error_with_non_retriable_errors():
    """Test that is_retriable_error correctly identifies non-retriable errors"""
    # Create various non-retriable exceptions (ValueError, KeyError, etc.)
    non_retriable_errors = [ValueError("Test Value Error"), KeyError("Test Key Error"), TypeError("Test Type Error")]

    for error in non_retriable_errors:
        assert not is_retriable_error(error)


@pytest.mark.unit
def test_handle_api_error_with_http_error():
    """Test that handle_api_error correctly formats HTTP errors"""
    # Create a mock requests.HTTPError with status code and response text
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Test Response Text"
    mock_http_error = requests.HTTPError("Test HTTP Error", response=mock_response)

    # Call handle_api_error with the exception and context information
    error_response = handle_api_error(mock_http_error, "Test API", "Test Operation")

    # Assert that the returned error response contains the correct fields
    assert error_response["status"] == "error"
    assert error_response["api_name"] == "Test API"
    assert error_response["operation"] == "Test Operation"
    assert error_response["error_message"] == "Test HTTP Error"

    # Assert that status code and response text are included in the error response
    assert error_response["status_code"] == 404
    assert error_response["response_text"] == "Test Response Text"

    # Assert that api_name and operation are included in the error response
    assert "api_name" in error_response
    assert "operation" in error_response


@pytest.mark.unit
def test_handle_api_error_with_generic_exception():
    """Test that handle_api_error correctly formats generic exceptions"""
    # Create a generic exception
    generic_exception = Exception("Test Generic Exception")

    # Call handle_api_error with the exception and context information
    error_response = handle_api_error(generic_exception, "Test API", "Test Operation")

    # Assert that the returned error response contains the correct fields
    assert error_response["status"] == "error"
    assert error_response["api_name"] == "Test API"
    assert error_response["operation"] == "Test Operation"
    assert error_response["error_message"] == "Test Generic Exception"

    # Assert that the error message is included in the error response
    assert "error_message" in error_response

    # Assert that api_name and operation are included in the error response
    assert "api_name" in error_response
    assert "operation" in error_response


@pytest.mark.unit
def test_handle_validation_error():
    """Test that handle_validation_error correctly formats validation errors"""
    # Create a ValidationError with validation_errors dictionary
    validation_errors = {"field1": "error1", "field2": "error2"}
    validation_error = ValidationError("Test Validation Error", "Test Data Type", validation_errors)

    # Call handle_validation_error with the exception and context information
    error_response = handle_validation_error(validation_error, "Test Data Type")

    # Assert that the returned error response contains the correct fields
    assert error_response["status"] == "error"
    assert error_response["error_type"] == "validation"
    assert error_response["data_type"] == "Test Data Type"
    assert error_response["error_message"] == "Test Validation Error"

    # Assert that data_type and validation_errors are included in the error response
    assert "data_type" in error_response
    assert "validation_errors" in error_response

    # Assert that the error message is included in the error response
    assert "error_message" in error_response


@pytest.mark.unit
def test_handle_auth_error_with_successful_refresh():
    """Test that handle_auth_error correctly handles successful token refresh"""
    # Create an AuthenticationError
    auth_error = AuthenticationError("Test Auth Error", "Test Service")

    # Create a mock refresh function that returns a new token
    mock_refresh_function = MagicMock(return_value="New Token")

    # Call handle_auth_error with the exception, service name, and refresh function
    success, result = handle_auth_error(auth_error, "Test Service", mock_refresh_function)

    # Assert that the returned tuple indicates success
    assert success is True

    # Assert that the new token is returned
    assert result == "New Token"


@pytest.mark.unit
def test_handle_auth_error_with_failed_refresh():
    """Test that handle_auth_error correctly handles failed token refresh"""
    # Create an AuthenticationError
    auth_error = AuthenticationError("Test Auth Error", "Test Service")

    # Create a mock refresh function that raises an exception
    mock_refresh_function = MagicMock(side_effect=Exception("Refresh Failed"))

    # Call handle_auth_error with the exception, service name, and refresh function
    success, result = handle_auth_error(auth_error, "Test Service", mock_refresh_function)

    # Assert that the returned tuple indicates failure
    assert success is False

    # Assert that the error response contains refresh failure information
    assert "error_message" in result
    assert "Failed to refresh token" in result["error_message"]


@pytest.mark.unit
def test_handle_auth_error_without_refresh_function():
    """Test that handle_auth_error works correctly without a refresh function"""
    # Create an AuthenticationError
    auth_error = AuthenticationError("Test Auth Error", "Test Service")

    # Call handle_auth_error with the exception and service name, but no refresh function
    success, result = handle_auth_error(auth_error, "Test Service")

    # Assert that the returned tuple indicates failure
    assert success is False

    # Assert that the error response contains the authentication error information
    assert "error_message" in result
    assert "Test Auth Error" in result["error_message"]


@pytest.mark.unit
def test_format_exception_for_log():
    """Test that format_exception_for_log correctly formats exceptions for logging"""
    # Create various types of exceptions (HTTPError, ValidationError, generic Exception)
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Test Response Text"
    http_error = requests.HTTPError("Test HTTP Error", response=mock_response)
    validation_error = ValidationError("Test Validation Error", "Test Data Type")
    generic_exception = Exception("Test Generic Exception")

    # Call format_exception_for_log with each exception
    http_error_details = format_exception_for_log(http_error)
    validation_error_details = format_exception_for_log(validation_error)
    generic_exception_details = format_exception_for_log(generic_exception)

    # Assert that the returned dictionary contains the correct fields for each exception type
    assert "type" in http_error_details
    assert "message" in http_error_details
    assert "status_code" in http_error_details
    assert "response_text" in http_error_details

    assert "type" in validation_error_details
    assert "message" in validation_error_details

    assert "type" in generic_exception_details
    assert "message" in generic_exception_details

    # Assert that exception type and message are always included
    assert http_error_details["type"] == "HTTPError"
    assert http_error_details["message"] == "Test HTTP Error"

    assert validation_error_details["type"] == "ValidationError"
    assert validation_error_details["message"] == "Test Validation Error"

    assert generic_exception_details["type"] == "Exception"
    assert generic_exception_details["message"] == "Test Generic Exception"

    # Assert that status_code is included for HTTPError
    assert http_error_details["status_code"] == 404

    # Assert that response text is included for HTTPError with response
    assert http_error_details["response_text"] == "Test Response Text"


@pytest.mark.unit
def test_safe_execute_with_successful_execution():
    """Test that safe_execute correctly handles successful function execution"""
    # Create a mock function that returns a success value
    mock_func = MagicMock(return_value="Success")

    # Call safe_execute with the function and arguments
    success, result = safe_execute(mock_func, 1, 2, arg1="value1")

    # Assert that the returned tuple indicates success
    assert success is True

    # Assert that the function result is returned
    assert result == "Success"


@pytest.mark.unit
def test_safe_execute_with_exception():
    """Test that safe_execute correctly handles exceptions"""
    # Create a mock function that raises an exception
    mock_func = MagicMock(side_effect=Exception("Test Exception"))

    # Call safe_execute with the function, arguments, and default value
    success, result = safe_execute(mock_func, 1, 2, default_value="Default")

    # Assert that the returned tuple indicates failure
    assert success is False

    # Assert that the default value is returned
    assert result == "Default"

    # Call safe_execute without a default value
    success, result = safe_execute(mock_func, 1, 2)

    # Assert that the formatted exception is returned
    assert success is False
    assert isinstance(result, dict)
    assert "type" in result
    assert "message" in result


@pytest.mark.unit
def test_api_error_class():
    """Test the APIError custom exception class"""
    # Create an APIError with various parameters
    api_error = APIError(
        message="Test API Error",
        api_name="Test API",
        operation="Test Operation",
        status_code=500,
        response_text="Test Response",
        context={"key": "value"}
    )

    # Assert that all parameters are correctly stored in the exception
    assert api_error.message == "Test API Error"
    assert api_error.api_name == "Test API"
    assert api_error.operation == "Test Operation"
    assert api_error.status_code == 500
    assert api_error.response_text == "Test Response"
    assert api_error.context == {"key": "value"}

    # Call to_dict method and verify the returned dictionary
    error_dict = api_error.to_dict()

    # Assert that the dictionary contains all the expected fields
    assert error_dict["message"] == "Test API Error"
    assert error_dict["api_name"] == "Test API"
    assert error_dict["operation"] == "Test Operation"
    assert error_dict["status_code"] == 500
    assert error_dict["response_text"] == "Test Response"
    assert error_dict["context"] == {"key": "value"}


@pytest.mark.unit
def test_validation_error_class():
    """Test the ValidationError custom exception class"""
    # Create a ValidationError with various parameters
    validation_error = ValidationError(
        message="Test Validation Error",
        data_type="Test Data Type",
        validation_errors={"field1": "error1"},
        context={"key": "value"}
    )

    # Assert that all parameters are correctly stored in the exception
    assert validation_error.message == "Test Validation Error"
    assert validation_error.data_type == "Test Data Type"
    assert validation_error.validation_errors == {"field1": "error1"}
    assert validation_error.context == {"key": "value"}

    # Call to_dict method and verify the returned dictionary
    error_dict = validation_error.to_dict()

    # Assert that the dictionary contains all the expected fields
    assert error_dict["message"] == "Test Validation Error"
    assert error_dict["data_type"] == "Test Data Type"
    assert error_dict["validation_errors"] == {"field1": "error1"}
    assert error_dict["context"] == {"key": "value"}


@pytest.mark.unit
def test_authentication_error_class():
    """Test the AuthenticationError custom exception class"""
    # Create an AuthenticationError with various parameters
    auth_error = AuthenticationError(
        message="Test Auth Error",
        service_name="Test Service",
        auth_context={"token": "sensitive_token", "key": "sensitive_key", "other": "value"}
    )

    # Assert that all parameters are correctly stored in the exception
    assert auth_error.message == "Test Auth Error"
    assert auth_error.service_name == "Test Service"
    assert auth_error.auth_context == {"token": "sensitive_token", "key": "sensitive_key", "other": "value"}

    # Call to_dict method and verify the returned dictionary
    error_dict = auth_error.to_dict()

    # Assert that the dictionary contains all the expected fields
    assert error_dict["message"] == "Test Auth Error"
    assert error_dict["service_name"] == "Test Service"

    # Verify that sensitive data is masked in the dictionary
    assert error_dict["auth_context"] == {"token": "[REDACTED]", "key": "[REDACTED]", "other": "value"}


@pytest.mark.unit
class TestRetryWithBackoff:
    """Test class for the retry_with_backoff decorator"""

    def setup_method(self, method):
        """Set up method called before each test"""
        # Reset mocks and counters for each test
        pass

    def test_successful_execution(self):
        """Test successful execution passes through"""
        # Create a mock function that succeeds
        mock_func = Mock(return_value="Success")

        # Decorate with retry_with_backoff
        decorated_func = retry_with_backoff()(mock_func)

        # Call the function and verify it succeeds on first try
        result = decorated_func()
        assert result == "Success"
        mock_func.assert_called_once()

    @patch('time.sleep', return_value=None)
    def test_retry_on_exception(self, mock_sleep):
        """Test function is retried on specified exceptions"""
        # Create a mock function that fails then succeeds
        mock_func = Mock(side_effect=[ValueError, "Success"])

        # Decorate with retry_with_backoff
        decorated_func = retry_with_backoff(exceptions=ValueError, max_retries=2)(mock_func)

        # Call the function and verify it retries and eventually succeeds
        result = decorated_func()
        assert result == "Success"
        assert mock_func.call_count == 2

    @patch('time.sleep', return_value=None)
    def test_max_retries_exceeded(self, mock_sleep):
        """Test exception is raised after max retries"""
        # Create a mock function that always fails
        mock_func = Mock(side_effect=ValueError)

        # Decorate with retry_with_backoff with max_retries=3
        decorated_func = retry_with_backoff(exceptions=ValueError, max_retries=3)(mock_func)

        # Call the function and verify it fails after 4 attempts (1 + 3 retries)
        with pytest.raises(ValueError):
            decorated_func()
        assert mock_func.call_count == 4

    @patch('time.sleep', return_value=None)
    def test_backoff_timing(self, mock_sleep):
        """Test backoff timing with exponential delay"""
        # Mock time.sleep
        mock_sleep.return_value = None

        # Create a function that fails multiple times
        mock_func = Mock(side_effect=[ValueError] * 3 + ["Success"])

        # Decorate with retry_with_backoff
        decorated_func = retry_with_backoff(exceptions=ValueError, max_retries=3, delay=1, backoff_factor=2)(mock_func)

        # Call the function and verify sleep times follow exponential pattern
        result = decorated_func()
        assert result == "Success"
        assert mock_func.call_count == 4
        expected_calls = [call(1), call(2), call(4)]
        mock_sleep.assert_has_calls(expected_calls)

    @patch('time.sleep', return_value=None)
    @patch('random.uniform', return_value=0.5)
    def test_jitter_applied(self, mock_uniform, mock_sleep):
        """Test that jitter is applied to backoff times"""
        # Mock time.sleep and random.uniform
        mock_sleep.return_value = None
        mock_uniform.return_value = 0.5

        # Create a function that fails multiple times
        mock_func = Mock(side_effect=[ValueError] * 3 + ["Success"])

        # Decorate with retry_with_backoff with jitter
        decorated_func = retry_with_backoff(exceptions=ValueError, max_retries=3, delay=1, backoff_factor=2, jitter=0.1)(mock_func)

        # Call the function and verify jitter is applied to sleep times
        result = decorated_func()
        assert result == "Success"
        assert mock_func.call_count == 4
        # Verify that sleep was called with jitter applied
        expected_calls = [call(1.05), call(2.1), call(4.2)]
        mock_sleep.assert_has_calls(expected_calls)


@pytest.mark.unit
class TestErrorHandlers:
    """Test class for error handling utility functions"""

    def setup_method(self, method):
        """Set up method called before each test"""
        # Reset mocks for each test
        pass

    def test_is_retriable_error(self):
        """Test error classification for retries"""
        # Test various error types with is_retriable_error
        http_error_429 = requests.exceptions.HTTPError("Too Many Requests")
        http_error_429.response = Mock(status_code=429)
        assert is_retriable_error(http_error_429)

        http_error_500 = requests.exceptions.HTTPError("Internal Server Error")
        http_error_500.response = Mock(status_code=500)
        assert is_retriable_error(http_error_500)

        connection_error = requests.exceptions.ConnectionError("Connection Error")
        assert is_retriable_error(connection_error)

        timeout = requests.exceptions.Timeout("Timeout")
        assert is_retriable_error(timeout)

        # Verify retriable errors return True
        # Verify non-retriable errors return False
        value_error = ValueError("Value Error")
        assert not is_retriable_error(value_error)

    def test_handle_api_error(self):
        """Test API error handling"""
        # Create API errors with different parameters
        http_error = requests.exceptions.HTTPError("HTTP Error")
        http_error.response = Mock(status_code=500, text="Internal Server Error")
        api_name = "TestAPI"
        operation = "test_operation"

        # Call handle_api_error with each error
        error_response = handle_api_error(http_error, api_name, operation)

        # Verify error response format and content
        assert error_response["status"] == "error"
        assert error_response["api_name"] == api_name
        assert error_response["operation"] == operation
        assert "error_message" in error_response

    def test_handle_validation_error(self):
        """Test validation error handling"""
        # Create validation errors with different parameters
        validation_error = ValidationError("Validation Failed", "TestDataType")
        data_type = "TestDataType"

        # Call handle_validation_error with each error
        error_response = handle_validation_error(validation_error, data_type)

        # Verify error response format and content
        assert error_response["status"] == "error"
        assert error_response["error_type"] == "validation"
        assert error_response["data_type"] == data_type
        assert "error_message" in error_response

    def test_handle_auth_error(self):
        """Test authentication error handling"""
        # Create auth errors with different parameters
        auth_error = AuthenticationError("Authentication Failed", "TestService")
        service_name = "TestService"
        mock_refresh_function = Mock(return_value="new_token")

        # Call handle_auth_error with each error
        success, result = handle_auth_error(auth_error, service_name, mock_refresh_function)

        # Test with and without refresh functions
        assert success is True
        assert result == "new_token"

        # Verify error response format and content
        success, result = handle_auth_error(auth_error, service_name)
        assert success is False
        assert "error_message" in result

    def test_safe_execute(self):
        """Test safe execution with fallback"""
        # Test successful function execution
        mock_func = Mock(return_value="Success")
        success, result = safe_execute(mock_func)
        assert success is True
        assert result == "Success"

        # Test function that raises exceptions
        mock_func.side_effect = ValueError("Test Exception")
        success, result = safe_execute(mock_func, default_value="Default")
        assert success is False
        assert result == "Default"

        # Test with and without default values
        success, result = safe_execute(mock_func)
        assert success is False
        assert isinstance(result, dict)
        assert "type" in result
        assert "message" in result


@pytest.mark.unit
class TestCustomExceptions:
    """Test class for custom exception classes"""

    def setup_method(self, method):
        """Set up test fixtures for custom exception tests"""
        pass

    def test_api_error(self):
        """Test APIError class"""
        # Create APIError with various parameters
        api_error = APIError("Test Message", "Test API", "Test Operation", 500, "Test Response", {"key": "value"})

        # Verify all attributes are set correctly
        assert api_error.message == "Test Message"
        assert api_error.api_name == "Test API"
        assert api_error.operation == "Test Operation"
        assert api_error.status_code == 500
        assert api_error.response_text == "Test Response"
        assert api_error.context == {"key": "value"}

        # Test to_dict method returns correct dictionary
        error_dict = api_error.to_dict()
        assert error_dict["message"] == "Test Message"
        assert error_dict["api_name"] == "Test API"
        assert error_dict["operation"] == "Test Operation"
        assert error_dict["status_code"] == 500
        assert error_dict["response_text"] == "Test Response"
        assert error_dict["context"] == {"key": "value"}

    def test_validation_error(self):
        """Test ValidationError class"""
        # Create ValidationError with various parameters
        validation_error = ValidationError("Test Message", "Test Data Type", {"field": "error"}, {"key": "value"})

        # Verify all attributes are set correctly
        assert validation_error.message == "Test Message"
        assert validation_error.data_type == "Test Data Type"
        assert validation_error.validation_errors == {"field": "error"}
        assert validation_error.context == {"key": "value"}

        # Test to_dict method returns correct dictionary
        error_dict = validation_error.to_dict()
        assert error_dict["message"] == "Test Message"
        assert error_dict["data_type"] == "Test Data Type"
        assert error_dict["validation_errors"] == {"field": "error"}
        assert error_dict["context"] == {"key": "value"}

    def test_authentication_error(self):
        """Test AuthenticationError class"""
        # Create AuthenticationError with various parameters
        auth_error = AuthenticationError("Test Message", "Test Service", {"token": "sensitive_token", "key": "value"})

        # Verify all attributes are set correctly
        assert auth_error.message == "Test Message"
        assert auth_error.service_name == "Test Service"
        assert auth_error.auth_context == {"token": "sensitive_token", "key": "value"}

        # Test to_dict method returns correct dictionary
        error_dict = auth_error.to_dict()
        assert error_dict["message"] == "Test Message"
        assert error_dict["service_name"] == "Test Service"

        # Verify that sensitive data is masked in dictionary
        assert error_dict["auth_context"] == {"token": "[REDACTED]", "key": "[REDACTED]"}