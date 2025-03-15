"""
transfer.py - Model class and utilities for fund transfers between accounts

This module defines the Transfer model class for representing and tracking
transfers between accounts, along with factory functions to create Transfer
objects from different data sources.
"""

import decimal  # standard library
from decimal import Decimal  # standard library
import datetime  # standard library
import logging  # standard library
from typing import Dict, Optional  # standard library

from ..utils.validation import is_valid_transfer_amount, parse_amount
from ..utils.formatters import format_currency
from ..config.settings import APP_SETTINGS
from ..utils.error_handlers import ValidationError

# Set up logger
logger = logging.getLogger(__name__)


class Transfer:
    """Represents a fund transfer between accounts with status tracking"""
    
    def __init__(self, amount: Decimal, source_account_id: str, 
                 destination_account_id: str, transfer_id: Optional[str] = None, 
                 status: str = 'pending'):
        """
        Initialize a new Transfer instance
        
        Args:
            amount: Transfer amount as Decimal
            source_account_id: Source account identifier
            destination_account_id: Destination account identifier
            transfer_id: Unique identifier for the transfer (optional)
            status: Transfer status ('pending', 'completed', 'failed')
        """
        self.amount = amount
        self.source_account_id = source_account_id
        self.destination_account_id = destination_account_id
        self.transfer_id = transfer_id
        self.status = status
        self.timestamp = datetime.datetime.now()
        
        logger.debug(
            f"Created transfer of {format_currency(amount)} from {source_account_id} "
            f"to {destination_account_id}",
            extra={"transfer_amount": str(amount), "status": status}
        )
    
    def __str__(self) -> str:
        """String representation of the Transfer"""
        return (f"Transfer of {format_currency(self.amount)} from {self.source_account_id} "
                f"to {self.destination_account_id} - Status: {self.status}")
    
    def __repr__(self) -> str:
        """Official string representation of the Transfer"""
        return (f"Transfer(amount={self.amount}, source={self.source_account_id}, "
                f"destination={self.destination_account_id}, status={self.status})")
    
    def update_status(self, new_status: str) -> bool:
        """
        Update the status of the transfer
        
        Args:
            new_status: New status value ('pending', 'completed', 'failed')
            
        Returns:
            bool: True if status was updated, False otherwise
        """
        valid_statuses = ['pending', 'completed', 'failed']
        
        if new_status not in valid_statuses:
            logger.warning(
                f"Invalid transfer status: {new_status}. Must be one of {valid_statuses}",
                extra={"transfer_id": self.transfer_id, "invalid_status": new_status}
            )
            return False
        
        old_status = self.status
        self.status = new_status
        
        logger.info(
            f"Transfer status updated from '{old_status}' to '{new_status}'",
            extra={
                "transfer_id": self.transfer_id,
                "transfer_amount": str(self.amount),
                "old_status": old_status,
                "new_status": new_status
            }
        )
        
        return True
    
    def set_transfer_id(self, transfer_id: str) -> bool:
        """
        Set the transfer ID after initiation
        
        Args:
            transfer_id: Unique identifier for the transfer
            
        Returns:
            bool: True if transfer_id was set, False otherwise
        """
        if not isinstance(transfer_id, str) or not transfer_id.strip():
            logger.warning(
                f"Invalid transfer ID: {transfer_id}. Must be a non-empty string.",
                extra={"provided_id": str(transfer_id)}
            )
            return False
        
        self.transfer_id = transfer_id
        
        logger.info(
            f"Transfer ID set to {transfer_id}",
            extra={
                "transfer_id": transfer_id,
                "transfer_amount": str(self.amount)
            }
        )
        
        return True
    
    def is_completed(self) -> bool:
        """
        Check if the transfer has completed successfully
        
        Returns:
            bool: True if status is 'completed', False otherwise
        """
        return self.status == 'completed'
    
    def is_pending(self) -> bool:
        """
        Check if the transfer is still pending
        
        Returns:
            bool: True if status is 'pending', False otherwise
        """
        return self.status == 'pending'
    
    def is_failed(self) -> bool:
        """
        Check if the transfer has failed
        
        Returns:
            bool: True if status is 'failed', False otherwise
        """
        return self.status == 'failed'
    
    def to_dict(self) -> Dict:
        """
        Convert Transfer to dictionary representation
        
        Returns:
            dict: Dictionary with transfer data
        """
        return {
            'amount': format_currency(self.amount),
            'source_account_id': self.source_account_id,
            'destination_account_id': self.destination_account_id,
            'transfer_id': self.transfer_id,
            'status': self.status,
            'timestamp': self.timestamp.isoformat()
        }
    
    def to_api_format(self) -> Dict:
        """
        Convert Transfer to format expected by Capital One API
        
        Returns:
            dict: Dictionary formatted for API request
        """
        return {
            'sourceAccountId': self.source_account_id,
            'destinationAccountId': self.destination_account_id,
            'amount': f"{self.amount:.2f}"
        }


def create_transfer(amount: Decimal, 
                   source_account_id: str, 
                   destination_account_id: str,
                   transfer_id: Optional[str] = None,
                   status: str = 'pending') -> Optional['Transfer']:
    """
    Factory function to create a Transfer object from raw data
    
    Args:
        amount: Transfer amount
        source_account_id: Source account identifier
        destination_account_id: Destination account identifier
        transfer_id: Unique identifier for the transfer (optional)
        status: Transfer status (default: 'pending')
        
    Returns:
        Transfer: A new Transfer instance, or None if validation fails
    """
    try:
        # Validate transfer amount
        if not is_valid_transfer_amount(amount, APP_SETTINGS.get('MIN_TRANSFER_AMOUNT')):
            raise ValidationError(
                f"Invalid transfer amount: {amount}. Must be positive and meet minimum requirements.",
                "transfer_amount"
            )
        
        # Create and return new Transfer instance
        return Transfer(
            amount=amount,
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            transfer_id=transfer_id,
            status=status
        )
    
    except ValidationError as e:
        logger.error(
            f"Transfer creation failed: {str(e)}",
            extra={"error": e.to_dict()}
        )
        return None
    
    except Exception as e:
        logger.error(
            f"Unexpected error creating transfer: {str(e)}",
            extra={
                "amount": str(amount),
                "source_account_id": source_account_id,
                "destination_account_id": destination_account_id
            }
        )
        return None


def create_transfer_from_capital_one_response(response_data: Dict) -> Optional[Transfer]:
    """
    Creates a Transfer object from Capital One API response
    
    Args:
        response_data: Response data from Capital One API
        
    Returns:
        Transfer: A Transfer instance with data from API response
    """
    try:
        # Extract required fields from response
        transfer_id = response_data.get('transferId')
        amount = response_data.get('amount')
        source_account_id = response_data.get('sourceAccountId')
        destination_account_id = response_data.get('destinationAccountId')
        status = response_data.get('status', 'pending')
        
        # Validate required fields are present
        if not all([transfer_id, amount, source_account_id, destination_account_id]):
            logger.warning(
                "Missing required fields in Capital One response",
                extra={"response_data": response_data}
            )
            return None
        
        # Parse amount to Decimal
        decimal_amount = parse_amount(amount)
        
        # Create a Transfer instance
        return create_transfer(
            amount=decimal_amount,
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            transfer_id=transfer_id,
            status=status
        )
    
    except Exception as e:
        logger.error(
            f"Error creating transfer from Capital One response: {str(e)}",
            extra={"response_data": response_data}
        )
        return None