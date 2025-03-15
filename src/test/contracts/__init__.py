"""
Initializes the contracts package which defines protocol interfaces and response contracts for external API integrations.
This file exports all contract classes and validation functions from the individual contract modules,
providing a centralized import point for contract-based testing throughout the application.
"""

from .capital_one_contract import (
    CapitalOneClientProtocol,
    TransactionResponseContract,
    AccountResponseContract,
    TransferResponseContract,
    validate_transaction_response,
    validate_account_response,
    validate_transfer_response,
    validate_transfer_status_response
)
from .google_sheets_contract import (
    GoogleSheetsClientProtocol,
    SheetResponseContract,
    MasterBudgetContract,
    WeeklySpendingContract
)
from .gemini_contract import (
    GeminiClientProtocol,
    CategorizationResponseContract,
    InsightResponseContract,
    validate_categorization_response,
    validate_insight_response,
    validate_categorization_prompt,
    validate_insight_prompt
)
from .gmail_contract import (
    GmailClientProtocol,
    EmailResponseContract,
    DeliveryResponseContract,
    validate_email_response,
    validate_delivery_response
)

__all__ = [
    'CapitalOneClientProtocol',
    'TransactionResponseContract',
    'AccountResponseContract',
    'TransferResponseContract',
    'validate_transaction_response',
    'validate_account_response',
    'validate_transfer_response',
    'validate_transfer_status_response',
    'GoogleSheetsClientProtocol',
    'SheetResponseContract',
    'MasterBudgetContract',
    'WeeklySpendingContract',
    'GeminiClientProtocol',
    'CategorizationResponseContract',
    'InsightResponseContract',
    'validate_categorization_response',
    'validate_insight_response',
    'validate_categorization_prompt',
    'validate_insight_prompt',
    'GmailClientProtocol',
    'EmailResponseContract',
    'DeliveryResponseContract',
    'validate_email_response',
    'validate_delivery_response'
]