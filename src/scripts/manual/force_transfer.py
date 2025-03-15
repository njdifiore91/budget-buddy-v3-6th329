#!/usr/bin/env python
"""
force_transfer.py - Manual utility for forcing transfers from checking to savings account

This script allows administrators to manually initiate a transfer from a checking
to a savings account outside of the regular weekly budget process. Useful for
testing, recovery from failed transfers, or manual savings adjustments.
"""

import argparse
import decimal
from decimal import Decimal
import sys
import time

from ...backend.api_clients.capital_one_client import CapitalOneClient
from ...backend.services.authentication_service import AuthenticationService
from ...backend.utils.validation import is_valid_transfer_amount, parse_amount
from ...backend.config.logging_config import get_logger
from ...backend.config.settings import APP_SETTINGS

# Set up logger for this script
logger = get_logger('force_transfer')


def setup_argument_parser():
    """
    Sets up command-line argument parser for the script
    
    Returns:
        argparse.ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Force a transfer from checking to savings account"
    )
    
    # Required argument for transfer amount
    parser.add_argument(
        "--amount",
        required=True,
        help="Amount to transfer from checking to savings (e.g., '50.00')"
    )
    
    # Optional arguments
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass confirmation prompt"
    )
    
    parser.add_argument(
        "--wait-for-completion",
        action="store_true",
        help="Wait for transfer to complete"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds when waiting for completion (default: 60)"
    )
    
    return parser


def confirm_transfer(amount, checking_details, savings_details):
    """
    Asks for user confirmation before proceeding with transfer
    
    Args:
        amount (decimal.Decimal): Transfer amount
        checking_details (dict): Checking account details
        savings_details (dict): Savings account details
    
    Returns:
        bool: True if user confirms, False otherwise
    """
    # Extract account numbers but mask for security (show only last 4 digits)
    checking_account = checking_details.get('accountId', 'Unknown')
    savings_account = savings_details.get('accountId', 'Unknown')
    
    # Extract account balance
    checking_balance = checking_details.get('balance', 0)
    
    # Display transfer details
    print("\n=== TRANSFER CONFIRMATION ===")
    print(f"Amount: ${amount:.2f}")
    print(f"From: Checking Account (...{checking_account[-4:] if len(checking_account) > 4 else checking_account})")
    print(f"To: Savings Account (...{savings_account[-4:] if len(savings_account) > 4 else savings_account})")
    print(f"Current Checking Balance: ${checking_balance:.2f}")
    print("=============================\n")
    
    # Ask for confirmation
    confirm = input("Proceed with transfer? (y/n): ").lower().strip()
    return confirm == 'y' or confirm == 'yes'


def wait_for_transfer_completion(client, transfer_id, timeout):
    """
    Waits for transfer to complete with timeout
    
    Args:
        client (CapitalOneClient): Initialized Capital One client
        transfer_id (str): ID of the transfer to check
        timeout (int): Maximum time to wait in seconds
    
    Returns:
        bool: True if transfer completed successfully, False otherwise
    """
    end_time = time.time() + timeout
    check_interval = 2  # seconds between checks
    
    print(f"\nWaiting for transfer to complete (timeout: {timeout}s)...")
    
    while time.time() < end_time:
        # Check transfer status
        is_completed = client.verify_transfer_completion(transfer_id)
        
        if is_completed:
            print("Transfer completed successfully!")
            return True
        
        # Wait before checking again
        print("Transfer still in progress, waiting...")
        time.sleep(check_interval)
    
    print(f"Timeout reached after {timeout} seconds. Transfer may still complete.")
    return False


def main():
    """
    Main function that orchestrates the force transfer process
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    # Parse command-line arguments
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    try:
        # Parse and validate transfer amount
        try:
            amount = parse_amount(args.amount)
            
            # Check if amount is valid for transfer
            if not is_valid_transfer_amount(amount, APP_SETTINGS.get('MIN_TRANSFER_AMOUNT')):
                logger.error(f"Invalid transfer amount: {amount}")
                print(f"Error: Transfer amount must be positive and at least "
                      f"${APP_SETTINGS.get('MIN_TRANSFER_AMOUNT', Decimal('1.00')):.2f}")
                return 1
                
        except (ValueError, decimal.InvalidOperation) as e:
            logger.error(f"Error parsing transfer amount: {str(e)}")
            print(f"Error: Invalid amount format. Please use a valid number (e.g., '50.00').")
            return 1
        
        # Initialize services
        print("Initializing services...")
        auth_service = AuthenticationService()
        client = CapitalOneClient(auth_service)
        
        # Authenticate with Capital One
        print("Authenticating with Capital One...")
        if not client.authenticate():
            logger.error("Authentication with Capital One failed")
            print("Error: Authentication with Capital One failed. Please check your credentials.")
            return 1
        
        # Get account details
        print("Retrieving account details...")
        checking_details = client.get_checking_account_details()
        savings_details = client.get_savings_account_details()
        
        # Check if account details were successfully retrieved
        if 'status' in checking_details and checking_details.get('status') == 'error':
            logger.error("Failed to retrieve checking account details")
            print("Error: Could not retrieve checking account details.")
            return 1
        
        if 'status' in savings_details and savings_details.get('status') == 'error':
            logger.error("Failed to retrieve savings account details")
            print("Error: Could not retrieve savings account details.")
            return 1
        
        # Confirm transfer if not forced
        if not args.force:
            if not confirm_transfer(amount, checking_details, savings_details):
                print("Transfer cancelled by user.")
                return 0
        
        # Initiate transfer
        print(f"\nInitiating transfer of ${amount:.2f} from checking to savings...")
        transfer_result = client.transfer_to_savings(amount)
        
        # Check transfer result
        if 'status' in transfer_result and transfer_result.get('status') == 'error':
            logger.error(f"Transfer failed: {transfer_result.get('error_message', 'Unknown error')}")
            print(f"Error: Transfer failed - {transfer_result.get('error_message', 'Unknown error')}")
            return 1
        
        # Extract transfer ID
        transfer_id = transfer_result.get('transfer_id')
        if not transfer_id:
            logger.warning("Transfer initiated but no transfer ID returned")
            print("Warning: Transfer was initiated but no transfer ID was returned.")
            print("Cannot verify completion status.")
            return 0
        
        print(f"Transfer initiated successfully! Transfer ID: {transfer_id}")
        
        # Wait for transfer to complete if requested
        if args.wait_for_completion:
            transfer_completed = wait_for_transfer_completion(
                client, transfer_id, args.timeout
            )
            
            if not transfer_completed:
                print("Transfer is still processing. You can check its status later.")
                # Not considering this a failure as the transfer was initiated
        
        logger.info(f"Manual transfer of ${amount:.2f} initiated successfully")
        print(f"\nTransfer of ${amount:.2f} from checking to savings has been initiated.")
        return 0
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during transfer: {str(e)}")
        print(f"Error: An unexpected error occurred: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())