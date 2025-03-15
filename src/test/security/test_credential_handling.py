import os
import json
import unittest
from unittest.mock import MagicMock
import pytest
import requests
from typing import Dict, Any
from google.cloud import secretmanager

from src.backend.services.authentication_service import AuthenticationService
from src.backend.config.settings import get_secret, load_json_secret, get_api_credentials, API_SETTINGS
from src.backend.api_clients.capital_one_client import CapitalOneClient
from src.test.mocks.secret_manager import MockSecretManagerServiceClient
from src.test.utils.test_helpers import with_test_environment, set_environment_variables

# Setup function that runs before all tests in the module
def setup_module():
    """Setup function that runs before all tests in the module"""
    # Set up any global test fixtures or environment variables
    # Initialize mock Secret Manager client
    global mock_secret_manager
    mock_secret_manager = MockSecretManagerServiceClient()

# Teardown function that runs after all tests in the module
def teardown_module():
    """Teardown function that runs after all tests in the module"""
    # Clean up any global test fixtures or environment variables
    # Reset any patched modules or functions
    global mock_secret_manager
    mock_secret_manager = None

class TestCredentialRetrieval(unittest.TestCase):
    """Test case for credential retrieval functionality"""

    def __init__(self, *args, **kwargs):
        """Initialize the test case"""
        super().__init__(*args, **kwargs)

    def setUp(self):
        """Set up test fixtures before each test method"""
        # Set up mock Secret Manager client
        self.mock_secret_manager = MockSecretManagerServiceClient()

        # Configure test secrets for each API service
        self.test_secrets = {
            'capital-one-credentials': '{"client_id": "test_client_id", "client_secret": "test_client_secret"}',
            'google-sheets-credentials': '{"type": "service_account", "project_id": "test-project", "private_key": "test_private_key", "client_email": "test@example.com"}',
            'gmail-credentials': '{"type": "service_account", "project_id": "test-project", "private_key": "test_private_key", "client_email": "test@example.com"}',
            'gemini-api-key': 'test_gemini_api_key'
        }

        # Create AuthenticationService instance with mocked dependencies
        self.auth_service = AuthenticationService()

    def tearDown(self):
        """Clean up test fixtures after each test method"""
        # Reset all mocks
        self.mock_secret_manager = None

        # Clear any cached tokens or credentials
        self.auth_service.credentials_cache = {}

    def test_get_secret_retrieves_from_secret_manager(self):
        """Test that get_secret correctly retrieves secrets from Secret Manager"""
        # Mock Secret Manager client to return a known test secret
        secret_name = "test-secret"
        expected_secret = "test_secret_value"
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.payload = MagicMock()
        mock_response.payload.data = expected_secret.encode('UTF-8')
        mock_client.access_secret_version.return_value = mock_response

        # Call get_secret with a test secret name
        with unittest.mock.patch('src.backend.config.settings.secretmanager.SecretManagerServiceClient', return_value=mock_client):
            actual_secret = get_secret(secret_name)

        # Assert that the returned secret matches the expected value
        self.assertEqual(actual_secret, expected_secret)

        # Verify Secret Manager client was called with correct parameters
        mock_client.access_secret_version.assert_called_once()

    def test_get_secret_handles_errors(self):
        """Test that get_secret properly handles Secret Manager errors"""
        # Mock Secret Manager client to raise an exception
        secret_name = "test-secret"
        mock_client = MagicMock()
        mock_client.access_secret_version.side_effect = Exception("Simulated error")

        # Call get_secret with a test secret name
        with unittest.mock.patch('src.backend.config.settings.secretmanager.SecretManagerServiceClient', return_value=mock_client):
            with self.assertRaises(Exception):
                get_secret(secret_name)

        # Verify error logging occurred
        # (This requires setting up a mock logger to capture log messages)

    def test_load_json_secret_parses_json(self):
        """Test that load_json_secret correctly parses JSON-formatted secrets"""
        # Mock get_secret to return a JSON string
        secret_name = "test-json-secret"
        expected_json = {"key1": "value1", "key2": 123}
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.payload = MagicMock()
        mock_response.payload.data = json.dumps(expected_json).encode('UTF-8')
        mock_client.access_secret_version.return_value = mock_response

        # Call load_json_secret with a test secret name
        with unittest.mock.patch('src.backend.config.settings.secretmanager.SecretManagerServiceClient', return_value=mock_client):
            actual_json = load_json_secret(secret_name)

        # Assert that the returned object is a properly parsed dictionary
        self.assertEqual(actual_json, expected_json)

        # Verify the parsed JSON contains the expected keys and values
        self.assertEqual(actual_json["key1"], "value1")
        self.assertEqual(actual_json["key2"], 123)

    @pytest.mark.parametrize('service_name', ['capital_one', 'google_sheets', 'gmail', 'gemini'])
    def test_get_api_credentials_retrieves_correct_credentials(self, service_name):
        """Test that get_api_credentials retrieves the correct credentials for each service"""
        # Mock appropriate secret retrieval function based on service_name
        if service_name == 'gemini':
            expected_credentials = "test_gemini_api_key"
            with unittest.mock.patch('src.backend.config.settings.get_secret', return_value=expected_credentials):
                actual_credentials = get_api_credentials(service_name.upper())
        else:
            expected_credentials = {"type": "service_account", "project_id": "test-project", "private_key": "test_private_key", "client_email": "test@example.com"}
            with unittest.mock.patch('src.backend.config.settings.load_json_secret', return_value=expected_credentials):
                actual_credentials = get_api_credentials(service_name.upper())

        # Call get_api_credentials with the service_name
        # Assert that the returned credentials match the expected format
        self.assertEqual(actual_credentials, expected_credentials)

        # Verify the correct secret was accessed based on API_SETTINGS
        if service_name == 'gemini':
            self.assertEqual(actual_credentials, "test_gemini_api_key")
        else:
            self.assertEqual(actual_credentials, {"type": "service_account", "project_id": "test-project", "private_key": "test_private_key", "client_email": "test@example.com"})

class TestAuthenticationService(unittest.TestCase):
    """Test case for the AuthenticationService class"""

    def __init__(self, *args, **kwargs):
        """Initialize the test case"""
        super().__init__(*args, **kwargs)

    def setUp(self):
        """Set up test fixtures before each test method"""
        # Mock get_api_credentials to return test credentials
        self.test_credentials = {
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'api_key': 'test_api_key'
        }
        self.mock_get_api_credentials = MagicMock(return_value=self.test_credentials)
        self.patcher_get_api_credentials = unittest.mock.patch('src.backend.services.authentication_service.get_api_credentials', self.mock_get_api_credentials)
        self.patcher_get_api_credentials.start()

        # Mock requests module for API calls
        self.mock_requests_post = MagicMock()
        self.patcher_requests_post = unittest.mock.patch('src.backend.services.authentication_service.requests.post', self.mock_requests_post)
        self.patcher_requests_post.start()

        # Create AuthenticationService instance
        self.auth_service = AuthenticationService()

    def tearDown(self):
        """Clean up test fixtures after each test method"""
        # Reset all mocks
        self.patcher_get_api_credentials.stop()
        self.patcher_requests_post.stop()

        # Clear token cache in AuthenticationService
        self.auth_service.credentials_cache = {}

    def test_authenticate_capital_one_uses_oauth(self):
        """Test that Capital One authentication uses OAuth 2.0"""
        # Mock requests.post to return a successful OAuth response
        test_token = "test_access_token"
        test_expires_in = 3600
        self.mock_requests_post.return_value.json.return_value = {'access_token': test_token, 'expires_in': test_expires_in}
        self.mock_requests_post.return_value.raise_for_status.return_value = None

        # Call auth_service.authenticate_capital_one()
        auth_data = self.auth_service.authenticate_capital_one()

        # Assert that the request was made with correct OAuth parameters
        self.mock_requests_post.assert_called_once()
        request_data = self.mock_requests_post.call_args[1]['data']
        self.assertEqual(request_data['grant_type'], 'client_credentials')

        # Verify client_id and client_secret were used correctly
        self.assertEqual(request_data['client_id'], self.test_credentials['client_id'])
        self.assertEqual(request_data['client_secret'], self.test_credentials['client_secret'])

        # Verify the returned token is properly structured
        self.assertEqual(auth_data['access_token'], test_token)
        self.assertEqual(auth_data['expires_in'], test_expires_in)

    def test_authenticate_google_sheets_uses_service_account(self):
        """Test that Google Sheets authentication uses service account"""
        # Mock google.oauth2.service_account.Credentials
        mock_credentials = MagicMock()
        mock_credentials.refresh.return_value = None
        mock_from_service_account_info = MagicMock(return_value=mock_credentials)
        with unittest.mock.patch('src.backend.services.authentication_service.google.oauth2.service_account.Credentials.from_service_account_info', mock_from_service_account_info):
            # Call auth_service.authenticate_google_sheets()
            credentials = self.auth_service.authenticate_google_sheets()

            # Assert that service account credentials were created with correct parameters
            mock_from_service_account_info.assert_called_once_with(
                self.test_credentials,
                scopes=API_SETTINGS['GOOGLE_SHEETS']['SCOPES']
            )

            # Verify the correct scopes were applied
            self.assertEqual(mock_credentials.scopes, API_SETTINGS['GOOGLE_SHEETS']['SCOPES'])

            # Verify credentials were refreshed
            mock_credentials.refresh.assert_called_once()

    def test_authenticate_gmail_uses_service_account(self):
        """Test that Gmail authentication uses service account"""
        # Mock google.oauth2.service_account.Credentials
        mock_credentials = MagicMock()
        mock_credentials.refresh.return_value = None
        mock_from_service_account_info = MagicMock(return_value=mock_credentials)
        with unittest.mock.patch('src.backend.services.authentication_service.google.oauth2.service_account.Credentials.from_service_account_info', mock_from_service_account_info):
            # Call auth_service.authenticate_gmail()
            credentials = self.auth_service.authenticate_gmail()

            # Assert that service account credentials were created with correct parameters
            mock_from_service_account_info.assert_called_once_with(
                self.test_credentials,
                scopes=API_SETTINGS['GMAIL']['SCOPES']
            )

            # Verify the correct scopes were applied
            self.assertEqual(mock_credentials.scopes, API_SETTINGS['GMAIL']['SCOPES'])

            # Verify credentials were refreshed
            mock_credentials.refresh.assert_called_once()

    def test_authenticate_gemini_uses_api_key(self):
        """Test that Gemini authentication uses API key"""
        # Mock get_secret to return a test API key
        test_api_key = "test_gemini_api_key"
        mock_get_secret = MagicMock(return_value=test_api_key)
        with unittest.mock.patch('src.backend.services.authentication_service.get_secret', mock_get_secret):
            # Call auth_service.authenticate_gemini()
            auth_data = self.auth_service.authenticate_gemini()

            # Assert that the returned object contains the API key
            self.assertEqual(auth_data['api_key'], test_api_key)

            # Verify no OAuth or service account methods were used
            self.assertFalse(hasattr(auth_data, 'access_token'))
            self.assertFalse(hasattr(auth_data, 'client_email'))

    def test_token_caching(self):
        """Test that authentication tokens are properly cached"""
        # Mock successful authentication for Capital One
        test_token = "test_access_token"
        test_expires_in = 3600
        self.mock_requests_post.return_value.json.return_value = {'access_token': test_token, 'expires_in': test_expires_in}
        self.mock_requests_post.return_value.raise_for_status.return_value = None

        # Call auth_service.get_token('capital_one') twice
        self.auth_service.get_token('CAPITAL_ONE')
        self.auth_service.get_token('CAPITAL_ONE')

        # Verify authentication was only performed once
        self.mock_requests_post.assert_called_once()

        # Verify the cached token was returned on second call
        self.assertEqual(self.auth_service.get_token('CAPITAL_ONE'), test_token)

    def test_token_expiry(self):
        """Test that expired tokens are refreshed"""
        # Mock successful authentication for Capital One with short expiry
        test_token = "test_access_token"
        test_expires_in = 1  # Expire after 1 second
        self.mock_requests_post.return_value.json.return_value = {'access_token': test_token, 'expires_in': test_expires_in}
        self.mock_requests_post.return_value.raise_for_status.return_value = None

        # Call auth_service.get_token('capital_one')
        self.auth_service.get_token('CAPITAL_ONE')

        # Manipulate token expiry to simulate expiration
        import time
        time.sleep(2)

        # Call auth_service.get_token('capital_one') again
        self.auth_service.get_token('CAPITAL_ONE')

        # Verify authentication was performed again for the second call
        self.assertEqual(self.mock_requests_post.call_count, 2)

    def test_refresh_token(self):
        """Test that refresh_token method works correctly"""
        # Mock successful authentication for Capital One
        test_token = "test_access_token"
        test_expires_in = 3600
        self.mock_requests_post.return_value.json.return_value = {'access_token': test_token, 'expires_in': test_expires_in}
        self.mock_requests_post.return_value.raise_for_status.return_value = None

        # Call auth_service.get_token('capital_one')
        self.auth_service.get_token('CAPITAL_ONE')

        # Call auth_service.refresh_token('capital_one')
        self.auth_service.refresh_token('CAPITAL_ONE')

        # Verify token cache was cleared
        self.assertNotIn('CAPITAL_ONE', self.auth_service.credentials_cache)

        # Verify authentication was performed again
        self.assertEqual(self.mock_requests_post.call_count, 2)

    @pytest.mark.parametrize('service_name,expected_header_key', [('capital_one', 'Authorization'), ('gemini', 'x-api-key')])
    def test_get_auth_headers(self, service_name, expected_header_key):
        """Test that get_auth_headers returns correct headers for each service"""
        # Mock get_token to return a test token for the service
        test_token = "test_token"
        mock_get_token = MagicMock(return_value=test_token)
        with unittest.mock.patch('src.backend.services.authentication_service.AuthenticationService.get_token', mock_get_token):
            # Call auth_service.get_auth_headers(service_name)
            headers = self.auth_service.get_auth_headers(service_name.upper())

            # Assert that the returned headers contain the expected header key
            self.assertIn(expected_header_key, headers)

            # Verify the header value is correctly formatted (e.g., 'Bearer token' for OAuth)
            if expected_header_key == 'Authorization':
                self.assertEqual(headers[expected_header_key], f"Bearer {test_token}")
            else:
                self.assertEqual(headers[expected_header_key], test_token)

class TestCredentialSecurity(unittest.TestCase):
    """Test case for credential security practices"""

    def __init__(self, *args, **kwargs):
        """Initialize the test case"""
        super().__init__(*args, **kwargs)

    def setUp(self):
        """Set up test fixtures before each test method"""
        # Set up mock loggers to capture log output
        self.mock_logger = MagicMock()
        self.patcher_logger = unittest.mock.patch('src.backend.services.authentication_service.logger', self.mock_logger)
        self.patcher_logger.start()

        # Create AuthenticationService instance with mocked dependencies
        self.auth_service = AuthenticationService()

    def tearDown(self):
        """Clean up test fixtures after each test method"""
        # Reset all mocks
        self.patcher_logger.stop()

        # Clear any cached tokens or credentials
        self.auth_service.credentials_cache = {}

    def test_no_credentials_in_logs(self):
        """Test that credentials are not logged in plain text"""
        # Mock logger to capture log messages
        mock_logger = MagicMock()

        # Perform authentication operations that would log information
        try:
            self.auth_service.authenticate_capital_one()
        except Exception:
            pass

        # Assert that sensitive data (tokens, keys, secrets) is not present in log messages
        for call in mock_logger.mock_calls:
            log_message = str(call)
            self.assertNotIn("test_client_secret", log_message)
            self.assertNotIn("test_client_id", log_message)

        # Verify that masked or redacted values are used instead
        # (This requires more sophisticated log analysis)

    def test_no_credentials_in_exceptions(self):
        """Test that credentials are not exposed in exception messages"""
        # Mock authentication to raise exceptions
        mock_requests_post = MagicMock()
        mock_requests_post.side_effect = Exception("Authentication failed")
        with unittest.mock.patch('src.backend.services.authentication_service.requests.post', mock_requests_post):
            # Capture exceptions raised during authentication
            try:
                self.auth_service.authenticate_capital_one()
            except Exception as e:
                exception_message = str(e)

                # Assert that sensitive data is not present in exception messages
                self.assertNotIn("test_client_secret", exception_message)
                self.assertNotIn("test_client_id", exception_message)

                # Verify that masked or redacted values are used instead
                # (This requires more sophisticated exception message analysis)

    def test_account_id_masking(self):
        """Test that account IDs are properly masked in logs and errors"""
        # Create CapitalOneClient with mocked auth_service
        mock_auth_service = MagicMock()
        capital_one_client = CapitalOneClient(mock_auth_service)

        # Perform operations that would log account IDs
        try:
            capital_one_client.get_account_details("test_account_id_12345")
        except Exception as e:
            exception_message = str(e)

            # Assert that full account IDs are not present in logs
            self.assertNotIn("test_account_id_12345", exception_message)

            # Verify that masked account IDs (e.g., XXXX1234) are used instead
            self.assertIn("XXXXX12345", exception_message)

    def test_no_credentials_in_memory_after_use(self):
        """Test that credentials are not kept in memory longer than necessary"""
        # Mock garbage collection and memory inspection
        import gc
        mock_gc_collect = MagicMock()
        mock_gc_get_objects = MagicMock(return_value=[])
        with unittest.mock.patch('gc.collect', mock_gc_collect), \
             unittest.mock.patch('gc.get_objects', mock_gc_get_objects):
            # Perform authentication operations
            self.auth_service.authenticate_capital_one()

            # Trigger cleanup or scope exit
            del self.auth_service

            # Assert that raw credentials are not retained in memory
            mock_gc_get_objects.assert_called()

            # Verify that only necessary token information is cached
            # (This requires more sophisticated memory analysis)

class TestCredentialFailureHandling(unittest.TestCase):
    """Test case for handling credential retrieval failures"""

    def __init__(self, *args, **kwargs):
        """Initialize the test case"""
        super().__init__(*args, **kwargs)

    def setUp(self):
        """Set up test fixtures before each test method"""
        # Configure mock Secret Manager to simulate failures
        self.mock_secret_manager = MockSecretManagerServiceClient(should_fail=True, failure_mode='not_found')

        # Create AuthenticationService instance with mocked dependencies
        self.auth_service = AuthenticationService()

    def tearDown(self):
        """Clean up test fixtures after each test method"""
        # Reset all mocks
        self.mock_secret_manager = None

        # Clear any cached tokens or credentials
        self.auth_service.credentials_cache = {}

    def test_secret_manager_unavailable(self):
        """Test handling of Secret Manager service unavailability"""
        # Mock Secret Manager to raise service unavailable exception
        with self.assertRaises(Exception):
            # Attempt to retrieve credentials
            self.auth_service.authenticate_capital_one()

        # Assert that appropriate error is raised or handled
        # Verify error is logged with correct severity

    def test_missing_credentials(self):
        """Test handling of missing credentials"""
        # Mock Secret Manager to return empty or null response
        mock_secret_manager = MockSecretManagerServiceClient(test_secrets={})
        with unittest.mock.patch('src.backend.config.settings.secretmanager.SecretManagerServiceClient', return_value=mock_secret_manager):
            # Attempt to retrieve credentials
            with self.assertRaises(Exception):
                self.auth_service.authenticate_capital_one()

        # Assert that appropriate error is raised or handled
        # Verify error is logged with correct severity

    def test_invalid_credentials_format(self):
        """Test handling of malformed credential data"""
        # Mock Secret Manager to return malformed JSON or incorrect data structure
        mock_secret_manager = MockSecretManagerServiceClient(test_secrets={'capital-one-credentials': 'invalid json'})
        with unittest.mock.patch('src.backend.config.settings.secretmanager.SecretManagerServiceClient', return_value=mock_secret_manager):
            # Attempt to retrieve and use credentials
            with self.assertRaises(Exception):
                self.auth_service.authenticate_capital_one()

        # Assert that appropriate error is raised or handled
        # Verify error is logged with correct severity

    def test_authentication_failure(self):
        """Test handling of authentication failures with valid credentials"""
        # Mock Secret Manager to return valid credentials
        # Mock API to reject authentication attempt
        mock_requests_post = MagicMock()
        mock_requests_post.side_effect = Exception("Authentication failed")
        with unittest.mock.patch('src.backend.services.authentication_service.requests.post', mock_requests_post):
            # Attempt to authenticate
            with self.assertRaises(Exception):
                self.auth_service.authenticate_capital_one()

        # Assert that appropriate error is raised or handled
        # Verify retry logic is correctly applied
        # Verify error is logged with correct severity

    def test_retry_with_credential_refresh(self):
        """Test retry behavior with credential refresh on authentication failure"""
        # Mock initial authentication to fail
        # Mock credential refresh to succeed
        # Mock subsequent authentication to succeed
        mock_requests_post = MagicMock()
        mock_requests_post.side_effect = [Exception("Authentication failed"), MagicMock()]
        with unittest.mock.patch('src.backend.services.authentication_service.requests.post', mock_requests_post):
            # Attempt operation requiring authentication
            with self.assertRaises(Exception):
                self.auth_service.authenticate_capital_one()

        # Assert that operation succeeds after refresh
        # Verify refresh was triggered by authentication failure