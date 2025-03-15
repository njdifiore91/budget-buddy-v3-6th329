"""
Test module for verifying the security of API authentication mechanisms in the Budget Management Application.
Tests authentication flows, token handling, credential management, and error handling for all external API integrations (Capital One, Google Sheets, Gmail, and Gemini).
"""

import pytest  # pytest 7.0.0+
import os  # standard library
import json  # standard library
import time  # standard library
from unittest.mock import MagicMock, patch  # standard library
from requests import RequestException  # requests 2.31.0+
from google.auth.exceptions import GoogleAuthError  # google-auth 2.22.0+

from src.backend.services.authentication_service import AuthenticationService, is_token_expired, cache_token, clear_token_cache  # Internal import
from src.backend.utils.error_handlers import AuthenticationError, APIError  # Internal import
from src.test.utils.test_helpers import with_test_environment, set_environment_variables, create_temp_file  # Internal import
from src.test.utils.assertion_helpers import APIAssertions  # Internal import
from src.test.mocks.capital_one_client import MockCapitalOneClient  # Internal import

TEST_CREDENTIALS = {"capital_one": {"client_id": "test-client-id", "client_secret": "test-client-secret"}, "google_sheets": {"credentials_file": "test-credentials.json"}, "gmail": {"credentials_file": "test-credentials.json"}, "gemini": {"api_key": "test-api-key"}}

def setup_auth_service():
    """Helper function to set up an AuthenticationService instance with mocked dependencies"""
    return AuthenticationService()

class TestTokenExpiration:
    """Test class for token expiration functionality"""

    def test_is_token_expired_with_expired_token(self):
        """Test that is_token_expired correctly identifies expired tokens"""
        service_name = "test_service"
        cache_token(service_name, "test_token", -10)
        assert is_token_expired(service_name)
        clear_token_cache()

    def test_is_token_expired_with_valid_token(self):
        """Test that is_token_expired correctly identifies valid tokens"""
        service_name = "test_service"
        cache_token(service_name, "test_token", 3600)
        assert not is_token_expired(service_name)
        clear_token_cache()

    def test_is_token_expired_with_nonexistent_token(self):
        """Test that is_token_expired returns True for nonexistent tokens"""
        service_name = "nonexistent_service"
        assert is_token_expired(service_name)

class TestTokenCaching:
    """Test class for token caching functionality"""

    def test_cache_token(self):
        """Test that cache_token correctly stores tokens"""
        service_name = "test_service"
        token = "test_token"
        expires_in = 3600
        cache_token(service_name, token, expires_in)
        assert service_name in globals()['TOKEN_CACHE']
        assert globals()['TOKEN_CACHE'][service_name] == token
        assert service_name in globals()['TOKEN_EXPIRY']
        assert globals()['TOKEN_EXPIRY'][service_name] > time.time()
        clear_token_cache()

    def test_clear_token_cache_specific_service(self):
        """Test that clear_token_cache correctly clears tokens for a specific service"""
        service_name1 = "test_service1"
        token1 = "test_token1"
        expires_in1 = 3600
        service_name2 = "test_service2"
        token2 = "test_token2"
        expires_in2 = 3600
        cache_token(service_name1, token1, expires_in1)
        cache_token(service_name2, token2, expires_in2)
        clear_token_cache(service_name1)
        assert service_name1 not in globals()['TOKEN_CACHE']
        assert service_name2 in globals()['TOKEN_CACHE']
        clear_token_cache()

    def test_clear_token_cache_all_services(self):
        """Test that clear_token_cache correctly clears all tokens when no service is specified"""
        service_name1 = "test_service1"
        token1 = "test_token1"
        expires_in1 = 3600
        service_name2 = "test_service2"
        token2 = "test_token2"
        expires_in2 = 3600
        cache_token(service_name1, token1, expires_in1)
        cache_token(service_name2, token2, expires_in2)
        clear_token_cache()
        assert not globals()['TOKEN_CACHE']

class TestCapitalOneAuthentication:
    """Test class for Capital One API authentication"""

    @patch('src.backend.services.authentication_service.get_api_credentials')
    def test_authenticate_capital_one_success(self, mock_get_api_credentials):
        """Test successful authentication with Capital One API"""
        mock_get_api_credentials.return_value = TEST_CREDENTIALS['capital_one']
        mock_post = MagicMock()
        mock_post.json.return_value = {"access_token": "test_access_token", "expires_in": 3600}
        mock_post.raise_for_status.return_value = None
        with patch('requests.post', mock_post):
            auth_service = setup_auth_service()
            auth_data = auth_service.authenticate_capital_one()
            assert "access_token" in auth_data
            assert auth_data["access_token"] == "test_access_token"
            assert 'CAPITAL_ONE' in globals()['TOKEN_CACHE']
            clear_token_cache()

    @patch('src.backend.services.authentication_service.get_api_credentials')
    def test_authenticate_capital_one_failure(self, mock_get_api_credentials):
        """Test authentication failure with Capital One API"""
        mock_get_api_credentials.return_value = TEST_CREDENTIALS['capital_one']
        mock_post = MagicMock()
        mock_post.raise_for_status.side_effect = RequestException("Authentication failed")
        with patch('requests.post', mock_post):
            auth_service = setup_auth_service()
            with pytest.raises(AuthenticationError):
                auth_service.authenticate_capital_one()
            assert 'CAPITAL_ONE' not in globals()['TOKEN_CACHE']

    @patch('src.backend.services.authentication_service.get_api_credentials')
    def test_authenticate_capital_one_retry(self, mock_get_api_credentials):
        """Test retry behavior on transient errors during Capital One authentication"""
        mock_get_api_credentials.return_value = TEST_CREDENTIALS['capital_one']
        mock_post = MagicMock()
        mock_post.raise_for_status.side_effect = [RequestException("Transient error"), None]
        mock_post.json.return_value = {"access_token": "test_access_token", "expires_in": 3600}
        with patch('requests.post', mock_post):
            auth_service = setup_auth_service()
            auth_data = auth_service.authenticate_capital_one()
            assert "access_token" in auth_data
            assert mock_post.call_count > 1

    def test_get_token_capital_one(self):
        """Test getting a Capital One token through the get_token method"""
        auth_service = setup_auth_service()
        auth_service.authenticate_capital_one = MagicMock(return_value={"access_token": "test_access_token"})
        token = auth_service.get_token('CAPITAL_ONE')
        auth_service.authenticate_capital_one.assert_called_once()
        assert token == "test_access_token"

    def test_refresh_token_capital_one(self):
        """Test refreshing a Capital One token"""
        auth_service = setup_auth_service()
        auth_service.authenticate_capital_one = MagicMock(return_value={"access_token": "new_test_access_token"})
        cache_token('CAPITAL_ONE', 'expired_token', -10)
        auth_service.refresh_token('CAPITAL_ONE')
        auth_service.authenticate_capital_one.assert_called_once()
        assert globals()['TOKEN_CACHE']['CAPITAL_ONE'] == "new_test_access_token"

class TestGoogleSheetsAuthentication:
    """Test class for Google Sheets API authentication"""

    @patch('src.backend.services.authentication_service.get_api_credentials')
    @patch('google.oauth2.service_account.Credentials.from_service_account_info')
    def test_authenticate_google_sheets_success(self, mock_from_service_account_info, mock_get_api_credentials):
        """Test successful authentication with Google Sheets API"""
        mock_get_api_credentials.return_value = TEST_CREDENTIALS['google_sheets']
        mock_creds = MagicMock()
        mock_from_service_account_info.return_value = mock_creds
        auth_service = setup_auth_service()
        creds = auth_service.authenticate_google_sheets()
        assert creds is not None
        assert 'GOOGLE_SHEETS' in auth_service.credentials_cache

    @patch('src.backend.services.authentication_service.get_api_credentials')
    @patch('google.oauth2.service_account.Credentials.from_service_account_info')
    def test_authenticate_google_sheets_failure(self, mock_from_service_account_info, mock_get_api_credentials):
        """Test authentication failure with Google Sheets API"""
        mock_get_api_credentials.return_value = TEST_CREDENTIALS['google_sheets']
        mock_from_service_account_info.side_effect = GoogleAuthError("Authentication failed")
        auth_service = setup_auth_service()
        with pytest.raises(AuthenticationError):
            auth_service.authenticate_google_sheets()
        assert 'GOOGLE_SHEETS' not in auth_service.credentials_cache

    @patch('src.backend.services.authentication_service.get_api_credentials')
    @patch('google.oauth2.service_account.Credentials.from_service_account_info')
    def test_authenticate_google_sheets_retry(self, mock_from_service_account_info, mock_get_api_credentials):
        """Test retry behavior on transient errors during Google Sheets authentication"""
        mock_get_api_credentials.return_value = TEST_CREDENTIALS['google_sheets']
        mock_from_service_account_info.side_effect = [GoogleAuthError("Transient error"), MagicMock()]
        auth_service = setup_auth_service()
        creds = auth_service.authenticate_google_sheets()
        assert creds is not None
        assert mock_from_service_account_info.call_count > 1

class TestGmailAuthentication:
    """Test class for Gmail API authentication"""

    @patch('src.backend.services.authentication_service.get_api_credentials')
    @patch('google.oauth2.service_account.Credentials.from_service_account_info')
    def test_authenticate_gmail_success(self, mock_from_service_account_info, mock_get_api_credentials):
        """Test successful authentication with Gmail API"""
        mock_get_api_credentials.return_value = TEST_CREDENTIALS['gmail']
        mock_creds = MagicMock()
        mock_from_service_account_info.return_value = mock_creds
        auth_service = setup_auth_service()
        creds = auth_service.authenticate_gmail()
        assert creds is not None
        assert 'GMAIL' in auth_service.credentials_cache

    @patch('src.backend.services.authentication_service.get_api_credentials')
    @patch('google.oauth2.service_account.Credentials.from_service_account_info')
    def test_authenticate_gmail_failure(self, mock_from_service_account_info, mock_get_api_credentials):
        """Test authentication failure with Gmail API"""
        mock_get_api_credentials.return_value = TEST_CREDENTIALS['gmail']
        mock_from_service_account_info.side_effect = GoogleAuthError("Authentication failed")
        auth_service = setup_auth_service()
        with pytest.raises(AuthenticationError):
            auth_service.authenticate_gmail()
        assert 'GMAIL' not in auth_service.credentials_cache

class TestGeminiAuthentication:
    """Test class for Gemini API authentication"""

    @patch('src.backend.services.authentication_service.get_secret')
    def test_authenticate_gemini_success(self, mock_get_secret):
        """Test successful authentication with Gemini API"""
        mock_get_secret.return_value = "test_api_key"
        auth_service = setup_auth_service()
        auth_data = auth_service.authenticate_gemini()
        assert "api_key" in auth_data
        assert auth_data["api_key"] == "test_api_key"
        assert 'GEMINI' not in globals()['TOKEN_CACHE']

    @patch('src.backend.services.authentication_service.get_secret')
    def test_authenticate_gemini_failure(self, mock_get_secret):
        """Test authentication failure with Gemini API"""
        mock_get_secret.return_value = None
        auth_service = setup_auth_service()
        with pytest.raises(AuthenticationError):
            auth_service.authenticate_gemini()

    def test_get_token_gemini(self):
        """Test getting a Gemini token through the get_token method"""
        auth_service = setup_auth_service()
        auth_service.authenticate_gemini = MagicMock(return_value={"api_key": "test_api_key"})
        token = auth_service.get_token('GEMINI')
        auth_service.authenticate_gemini.assert_called_once()
        assert token == "test_api_key"

class TestAuthHeaders:
    """Test class for authentication headers generation"""

    def test_get_auth_headers_capital_one(self):
        """Test getting authentication headers for Capital One API"""
        auth_service = setup_auth_service()
        auth_service.get_token = MagicMock(return_value="test_token")
        headers = auth_service.get_auth_headers('CAPITAL_ONE')
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_token"

    def test_get_auth_headers_gemini(self):
        """Test getting authentication headers for Gemini API"""
        auth_service = setup_auth_service()
        auth_service.get_token = MagicMock(return_value="test_api_key")
        headers = auth_service.get_auth_headers('GEMINI')
        assert "x-api-key" in headers
        assert headers["x-api-key"] == "test_api_key"

    def test_get_auth_headers_google_services(self):
        """Test getting authentication headers for Google services"""
        auth_service = setup_auth_service()
        headers = auth_service.get_auth_headers('GOOGLE_SHEETS')
        assert headers == {}
        headers = auth_service.get_auth_headers('GMAIL')
        assert headers == {}

class TestCredentialValidation:
    """Test class for credential validation functionality"""

    def test_validate_credentials_all_valid(self):
        """Test validation when all credentials are valid"""
        auth_service = setup_auth_service()
        auth_service.authenticate_capital_one = MagicMock(return_value=True)
        auth_service.authenticate_google_sheets = MagicMock(return_value=True)
        auth_service.authenticate_gmail = MagicMock(return_value=True)
        auth_service.authenticate_gemini = MagicMock(return_value=True)
        result = auth_service.validate_credentials()
        assert result is True
        auth_service.authenticate_capital_one.assert_called_once()
        auth_service.authenticate_google_sheets.assert_called_once()
        auth_service.authenticate_gmail.assert_called_once()
        auth_service.authenticate_gemini.assert_called_once()

    def test_validate_credentials_with_failures(self):
        """Test validation when some credentials are invalid"""
        auth_service = setup_auth_service()
        auth_service.authenticate_capital_one = MagicMock(return_value=True)
        auth_service.authenticate_google_sheets = MagicMock(side_effect=Exception("Sheets auth failed"))
        auth_service.authenticate_gmail = MagicMock(return_value=True)
        auth_service.authenticate_gemini = MagicMock(side_effect=Exception("Gemini auth failed"))
        result = auth_service.validate_credentials()
        assert result is False
        auth_service.authenticate_capital_one.assert_called_once()
        auth_service.authenticate_google_sheets.assert_called_once()
        auth_service.authenticate_gmail.assert_called_once()
        auth_service.authenticate_gemini.assert_called_once()

class TestIntegrationWithMocks:
    """Integration tests for authentication service using mocks"""

    def test_capital_one_authentication_flow(self):
        """Test the complete Capital One authentication flow with mocks"""
        with with_test_environment() as test_env:
            mock_capital_one = test_env['mocks']['capital_one']
            auth_service = setup_auth_service()
            auth_data = auth_service.authenticate_capital_one()
            assert auth_data is not None
            assert mock_capital_one.authenticated
            assert 'CAPITAL_ONE' in globals()['TOKEN_CACHE']

            mock_capital_one.set_should_fail_authentication(True)
            clear_token_cache()
            with pytest.raises(AuthenticationError):
                auth_service.authenticate_capital_one()

    def test_token_refresh_flow(self):
        """Test the token refresh flow with mocks"""
        with with_test_environment() as test_env:
            auth_service = setup_auth_service()
            cache_token('CAPITAL_ONE', 'expired_token', -10)
            auth_service.authenticate_capital_one = MagicMock(return_value={"access_token": "new_test_access_token"})
            auth_service.get_token('CAPITAL_ONE')
            assert globals()['TOKEN_CACHE']['CAPITAL_ONE'] == "new_test_access_token"

    def test_authentication_error_handling(self):
        """Test error handling during authentication"""
        with with_test_environment() as test_env:
            mock_capital_one = test_env['mocks']['capital_one']
            mock_capital_one.set_should_fail_authentication(True)
            auth_service = setup_auth_service()
            with pytest.raises(AuthenticationError):
                auth_service.authenticate_capital_one()
            assert 'CAPITAL_ONE' not in globals()['TOKEN_CACHE']