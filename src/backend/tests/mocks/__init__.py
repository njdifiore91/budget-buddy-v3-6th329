"""
Initialization file for the mocks package that exports all mock client implementations for testing the Budget Management Application. This file makes the mock clients available for import directly from the mocks package, simplifying test imports.
"""

from .mock_capital_one_client import (  # src/backend/tests/mocks/mock_capital_one_client.py
    MockCapitalOneClient,
    MockAuthenticationService as CapitalOneAuthService,
    create_mock_transaction_response,
    create_mock_account_response,
    create_mock_transfer_response
)
from .mock_google_sheets_client import (  # src/backend/tests/mocks/mock_google_sheets_client.py
    MockGoogleSheetsClient,
    create_mock_sheet_response,
    create_mock_append_response,
    create_mock_update_response,
    create_mock_batch_update_response
)
from .mock_gmail_client import (  # src/backend/tests/mocks/mock_gmail_client.py
    MockGmailClient,
    MockAuthenticationService as GmailAuthService,
    create_message,
    add_attachment,
    load_email_confirmation,
    load_email_error_response
)
from .mock_gemini_client import (  # src/backend/tests/mocks/mock_gemini_client.py
    MockGeminiClient,
    MockAuthenticationService as GeminiAuthService,
    create_mock_completion_response,
    parse_mock_categorization_response
)

__all__ = [
    'MockCapitalOneClient',
    'CapitalOneAuthService',
    'create_mock_transaction_response',
    'create_mock_account_response',
    'create_mock_transfer_response',
    'MockGoogleSheetsClient',
    'create_mock_sheet_response',
    'create_mock_append_response',
    'create_mock_update_response',
    'create_mock_batch_update_response',
    'MockGmailClient',
    'GmailAuthService',
    'create_message',
    'add_attachment',
    'load_email_confirmation',
    'load_email_error_response',
    'MockGeminiClient',
    'GeminiAuthService',
    'create_mock_completion_response',
    'parse_mock_categorization_response'
]