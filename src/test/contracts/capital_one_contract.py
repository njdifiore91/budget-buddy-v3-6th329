"""
Defines the contract for the Capital One API client interface, including protocol classes and JSON schemas for validating API responses.
This contract ensures that both the real implementation and mock versions of the Capital One client adhere to the same interface and data structures, enabling reliable testing of components that depend on Capital One API integration.
"""

import jsonschema  # version 4.17.0+
from typing import Protocol, List, Dict, Any, Optional, Union  # standard library
from decimal import Decimal  # standard library

from src.backend.models.transaction import Transaction  # Use Transaction model for contract validation
from src.backend.models.transfer import Transfer  # Use Transfer model for contract validation
from src.test.utils.test_helpers import load_test_fixture  # Load test fixtures for schema examples

# Define JSON schemas for validating API responses
TRANSACTION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "transactions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "transactionId": {"type": "string"},
                    "accountId": {"type": "string"},
                    "location": {"type": "string"},
                    "amount": {"type": "string"},
                    "timestamp": {"type": "string"},
                    "description": {"type": "string"},
                    "category": {"type": "string"},
                    "status": {"type": "string"}
                },
                "required": ["transactionId", "accountId", "location", "amount", "timestamp"]
            }
        }
    },
    "required": ["transactions"]
}

ACCOUNT_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "accountId": {"type": "string"},
        "accountType": {"type": "string"},
        "balance": {"type": "string"},
        "availableBalance": {"type": "string"},
        "currency": {"type": "string"},
        "status": {"type": "string"}
    },
    "required": ["accountId", "accountType", "balance", "status"]
}

TRANSFER_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "transferId": {"type": "string"},
        "sourceAccountId": {"type": "string"},
        "destinationAccountId": {"type": "string"},
        "amount": {"type": "string"},
        "currency": {"type": "string"},
        "timestamp": {"type": "string"},
        "status": {"type": "string"}
    },
    "required": ["transferId", "sourceAccountId", "destinationAccountId", "amount", "status"]
}

TRANSFER_STATUS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "transferId": {"type": "string"},
        "status": {"type": "string"},
        "timestamp": {"type": "string"},
        "completedAt": {"type": "string"}
    },
    "required": ["transferId", "status"]
}


class CapitalOneClientProtocol(Protocol):
    """Protocol defining the interface for the Capital One API client"""

    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None, checking_account_id: Optional[str] = None, savings_account_id: Optional[str] = None, base_url: Optional[str] = None, auth_url: Optional[str] = None):
        """Initialize the Capital One API client"""
        ...

    def authenticate(self) -> bool:
        """Authenticate with the Capital One API"""
        ...

    def get_transactions(self, account_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve transactions from the specified account for a date range"""
        ...

    def get_account_details(self, account_id: str) -> Dict[str, Any]:
        """Retrieve details for a specific account"""
        ...

    def get_checking_account_details(self) -> Dict[str, Any]:
        """Retrieve details for the checking account"""
        ...

    def get_savings_account_details(self) -> Dict[str, Any]:
        """Retrieve details for the savings account"""
        ...

    def initiate_transfer(self, amount: Decimal, source_account_id: str, destination_account_id: str) -> Dict[str, Any]:
        """Initiate a transfer between accounts"""
        ...

    def transfer_to_savings(self, amount: Decimal) -> Dict[str, Any]:
        """Transfer funds from checking to savings account"""
        ...

    def get_transfer_status(self, transfer_id: str) -> Dict[str, Any]:
        """Check the status of a transfer"""
        ...

    def verify_transfer_completion(self, transfer_id: str) -> bool:
        """Verify that a transfer has completed successfully"""
        ...

    def get_weekly_transactions(self) -> List[Transaction]:
        """Get transactions from the past week"""
        ...

    def test_connectivity(self) -> bool:
        """Test connectivity to the Capital One API"""
        ...


class TransactionResponseContract:
    """Contract class for Capital One transaction responses"""

    def __init__(self):
        """Initialize the transaction response contract"""
        self.schema: Dict[str, Any] = TRANSACTION_RESPONSE_SCHEMA
        self.example: Dict[str, Any] = load_test_fixture("api_responses/capital_one/transactions.json")

    def validate(self, response: Dict[str, Any]) -> bool:
        """Validate a transaction response against the schema"""
        validate_transaction_response(response)
        return True

    def get_example(self) -> Dict[str, Any]:
        """Get an example transaction response"""
        return self.example


class AccountResponseContract:
    """Contract class for Capital One account responses"""

    def __init__(self):
        """Initialize the account response contract"""
        self.schema: Dict[str, Any] = ACCOUNT_RESPONSE_SCHEMA
        self.example: Dict[str, Any] = load_test_fixture("api_responses/capital_one/accounts.json")

    def validate(self, response: Dict[str, Any]) -> bool:
        """Validate an account response against the schema"""
        validate_account_response(response)
        return True

    def get_example(self) -> Dict[str, Any]:
        """Get an example account response"""
        return self.example


class TransferResponseContract:
    """Contract class for Capital One transfer responses"""

    def __init__(self):
        """Initialize the transfer response contract"""
        self.schema: Dict[str, Any] = TRANSFER_RESPONSE_SCHEMA
        self.status_schema: Dict[str, Any] = TRANSFER_STATUS_RESPONSE_SCHEMA
        self.example: Dict[str, Any] = load_test_fixture("api_responses/capital_one/transfer.json")
        self.status_example: Dict[str, Any] = load_test_fixture("api_responses/capital_one/transfer_status.json")

    def validate(self, response: Dict[str, Any]) -> bool:
        """Validate a transfer response against the schema"""
        validate_transfer_response(response)
        return True

    def validate_status(self, response: Dict[str, Any]) -> bool:
        """Validate a transfer status response against the schema"""
        validate_transfer_status_response(response)
        return True

    def get_example(self) -> Dict[str, Any]:
        """Get an example transfer response"""
        return self.example

    def get_status_example(self) -> Dict[str, Any]:
        """Get an example transfer status response"""
        return self.status_example


def validate_transaction_response(response: Dict[str, Any]) -> bool:
    """Validates a Capital One transaction response against the schema"""
    jsonschema.validate(response, TRANSACTION_RESPONSE_SCHEMA)
    return True


def validate_account_response(response: Dict[str, Any]) -> bool:
    """Validates a Capital One account response against the schema"""
    jsonschema.validate(response, ACCOUNT_RESPONSE_SCHEMA)
    return True


def validate_transfer_response(response: Dict[str, Any]) -> bool:
    """Validates a Capital One transfer response against the schema"""
    jsonschema.validate(response, TRANSFER_RESPONSE_SCHEMA)
    return True


def validate_transfer_status_response(response: Dict[str, Any]) -> bool:
    """Validates a Capital One transfer status response against the schema"""
    jsonschema.validate(response, TRANSFER_STATUS_RESPONSE_SCHEMA)
    return True