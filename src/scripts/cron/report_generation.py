"""
Script for generating and sending budget reports on a scheduled basis. This module provides
functionality to create budget insights and email reports using the core components of the
Budget Management Application without requiring the full application execution.
"""

import os  # standard library
import sys  # standard library
import argparse  # standard library
from datetime import datetime  # standard library
from typing import Dict, List, Optional, Any  # standard library

import pandas as pd  # pandas 2.1.0+

# Internal imports
from ..config.logging_setup import get_logger  # src/scripts/config/logging_setup.py
from ..config.script_settings import SCRIPT_SETTINGS, MAINTENANCE_SETTINGS  # src/scripts/config/script_settings.py
from ..utils.sheet_operations import read_sheet, get_sheets_service, get_sheet_as_dataframe  # src/scripts/utils/sheet_operations.py
from ...backend.components.insight_generator import InsightGenerator  # src/backend/components/insight_generator.py
from ...backend.components.report_distributor import ReportDistributor  # src/backend/components/report_distributor.py
from ...backend.api_clients.gmail_client import GmailClient  # src/backend/api_clients/gmail_client.py
from ...backend.services.authentication_service import AuthenticationService  # src/backend/services/authentication_service.py
from ...backend.models.report import create_report  # src/backend/models/report.py

# Initialize logger
logger = get_logger(__name__)

# Set default sheet IDs from environment variables
DEFAULT_WEEKLY_SPENDING_SHEET_ID = os.getenv('WEEKLY_SPENDING_SHEET_ID', '')
DEFAULT_MASTER_BUDGET_SHEET_ID = os.getenv('MASTER_BUDGET_SHEET_ID', '')

# Set default recipients from maintenance settings
DEFAULT_RECIPIENTS = [MAINTENANCE_SETTINGS.get('ALERT_EMAIL', 'njdifiore@gmail.com')]


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments for the report generation script.

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    # Create ArgumentParser with description
    parser = argparse.ArgumentParser(description='Generate and send budget reports.')

    # Add --weekly-spending-sheet-id argument with default from DEFAULT_WEEKLY_SPENDING_SHEET_ID
    parser.add_argument('--weekly-spending-sheet-id', type=str,
                        default=DEFAULT_WEEKLY_SPENDING_SHEET_ID,
                        help='Weekly Spending Google Sheet ID')

    # Add --master-budget-sheet-id argument with default from DEFAULT_MASTER_BUDGET_SHEET_ID
    parser.add_argument('--master-budget-sheet-id', type=str,
                        default=DEFAULT_MASTER_BUDGET_SHEET_ID,
                        help='Master Budget Google Sheet ID')

    # Add --recipients argument with default from DEFAULT_RECIPIENTS
    parser.add_argument('--recipients', type=str, nargs='+',
                        default=DEFAULT_RECIPIENTS,
                        help='Email recipients for the report')

    # Add --debug flag to enable debug mode
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode')

    # Add --dry-run flag to skip sending email
    parser.add_argument('--dry-run', action='store_true',
                        help='Skip sending email (dry run)')

    # Parse and return arguments
    return parser.parse_args()


def get_budget_data(master_budget_sheet_id: str) -> pd.DataFrame:
    """
    Retrieve budget data from Google Sheets.

    Args:
        master_budget_sheet_id (str): Master Budget Google Sheet ID

    Returns:
        pandas.DataFrame: Budget data as DataFrame
    """
    try:
        # Get authenticated Google Sheets service
        service = get_sheets_service()

        # Read Master Budget sheet data using get_sheet_as_dataframe
        budget_df = get_sheet_as_dataframe(master_budget_sheet_id, 'Master Budget', service)

        # Validate that required columns exist
        required_columns = ['Spending Category', 'Weekly Amount']
        if not all(col in budget_df.columns for col in required_columns):
            raise ValueError(f"Missing required columns in Master Budget sheet: {required_columns}")

        # Return budget data as DataFrame
        return budget_df

    except Exception as e:
        # Log any errors during data retrieval
        logger.error(f"Error retrieving budget data: {e}")
        raise


def get_transaction_data(weekly_spending_sheet_id: str) -> pd.DataFrame:
    """
    Retrieve transaction data from Google Sheets.

    Args:
        weekly_spending_sheet_id (str): Weekly Spending Google Sheet ID

    Returns:
        pandas.DataFrame: Transaction data as DataFrame
    """
    try:
        # Get authenticated Google Sheets service
        service = get_sheets_service()

        # Read Weekly Spending sheet data using get_sheet_as_dataframe
        transactions_df = get_sheet_as_dataframe(weekly_spending_sheet_id, 'Weekly Spending', service)

        # Validate that required columns exist
        required_columns = ['Transaction Location', 'Transaction Amount', 'Transaction Time', 'Corresponding Category']
        if not all(col in transactions_df.columns for col in required_columns):
            raise ValueError(f"Missing required columns in Weekly Spending sheet: {required_columns}")

        # Return transaction data as DataFrame
        return transactions_df

    except Exception as e:
        # Log any errors during data retrieval
        logger.error(f"Error retrieving transaction data: {e}")
        raise


def analyze_budget(budget_df: pd.DataFrame, transactions_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze budget data and transactions to create budget analysis.

    Args:
        budget_df (pandas.DataFrame): Budget data as DataFrame
        transactions_df (pandas.DataFrame): Transaction data as DataFrame

    Returns:
        Dict[str, Any]: Budget analysis data
    """
    try:
        # Group transactions by category and sum amounts
        transactions_by_category = transactions_df.groupby('Corresponding Category')['Transaction Amount'].sum()

        # Merge budget and actual spending data
        budget_analysis = pd.merge(budget_df, transactions_by_category,
                                   left_on='Spending Category', right_index=True, how='left')

        # Calculate variances (budget - actual)
        budget_analysis['Variance'] = budget_analysis['Weekly Amount'] - budget_analysis['Transaction Amount']
        budget_analysis['Variance'] = budget_analysis['Variance'].fillna(budget_analysis['Weekly Amount'])

        # Calculate total budget, total spent, and total variance
        total_budget = budget_analysis['Weekly Amount'].sum()
        total_spent = budget_analysis['Transaction Amount'].sum()
        total_spent = total_spent if not pd.isna(total_spent) else 0
        total_variance = budget_analysis['Variance'].sum()

        # Create category_variances list with details for each category
        category_variances = []
        for index, row in budget_analysis.iterrows():
            category_variances.append({
                'category': row['Spending Category'],
                'budget': row['Weekly Amount'],
                'actual': row['Transaction Amount'] if not pd.isna(row['Transaction Amount']) else 0,
                'variance': row['Variance']
            })

        # Return complete budget analysis dictionary
        return {
            'total_budget': total_budget,
            'total_spent': total_spent,
            'total_variance': total_variance,
            'category_variances': category_variances
        }

    except Exception as e:
        # Handle any calculation errors and log them
        logger.error(f"Error analyzing budget: {e}")
        raise


def generate_report(budget_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate budget report with insights and visualizations.

    Args:
        budget_analysis (Dict[str, Any]): Budget analysis data

    Returns:
        Dict[str, Any]: Report data with insights and chart paths
    """
    try:
        # Initialize InsightGenerator
        insight_generator = InsightGenerator()

        # Authenticate with Gemini API
        insight_generator.authenticate()

        # Generate insights from budget analysis
        insights = insight_generator.generate_insights(budget_analysis)

        # Create visualizations (charts)
        charts = insight_generator.create_visualizations(budget_analysis)

        # Create report object with insights and charts
        report_data = create_report(budget_analysis, insights, charts)

        # Return report data dictionary
        return report_data

    except Exception as e:
        # Handle any errors during report generation and log them
        logger.error(f"Error generating report: {e}")
        raise


def send_report_email(report_data: Dict[str, Any], recipients: List[str], dry_run: bool) -> bool:
    """
    Send budget report via email.

    Args:
        report_data (Dict[str, Any]): Report data with insights and chart paths
        recipients (List[str]): List of email recipients
        dry_run (bool): If True, skip sending email

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # If dry_run is True, log that email would be sent and return True
        if dry_run:
            logger.info("Dry run: Email would be sent to %s", recipients)
            return True

        # Initialize AuthenticationService
        auth_service = AuthenticationService()

        # Initialize GmailClient
        gmail_client = GmailClient(auth_service)

        # Initialize ReportDistributor with GmailClient and recipients
        report_distributor = ReportDistributor(gmail_client=gmail_client, recipients=recipients)

        # Authenticate with Gmail API
        report_distributor.authenticate()

        # Send report using ReportDistributor
        report_distributor.send_report(report_data)

        # Return True if email sent successfully, False otherwise
        return True

    except Exception as e:
        # Handle any errors during email sending and log them
        logger.error(f"Error sending email: {e}")
        return False


def main() -> int:
    """
    Main function for the report generation script.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        # Parse command line arguments
        args = parse_arguments()

        # Configure logging based on debug flag
        if args.debug:
            logger.setLevel('DEBUG')
            logger.debug("Debug mode enabled")

        # Log script start with parameters
        logger.info("Starting report generation script with parameters: %s", args)

        # Get budget data from Master Budget sheet
        budget_df = get_budget_data(args.master_budget_sheet_id)

        # Get transaction data from Weekly Spending sheet
        transactions_df = get_transaction_data(args.weekly_spending_sheet_id)

        # Analyze budget and transaction data
        budget_analysis = analyze_budget(budget_df, transactions_df)

        # Generate report with insights and visualizations
        report_data = generate_report(budget_analysis)

        # Send report via email (unless dry_run is True)
        if not args.dry_run:
            send_report_email(report_data, args.recipients, args.dry_run)
        else:
            logger.info("Dry run: Skipping email sending")

        # Log script completion
        logger.info("Report generation script completed successfully")

        # Return 0 for success
        return 0

    except Exception as e:
        # Handle any exceptions and log them
        logger.error(f"Report generation script failed: {e}")

        # Return appropriate error code for failure
        return 1


if __name__ == "__main__":
    # Call main function and exit with its return code
    sys.exit(main())