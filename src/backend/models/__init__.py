"""
__init__.py - Initialization file for the models package that imports and exposes
all model classes and utility functions for the Budget Management Application.

This file serves as the central access point for all data models used throughout
the application, including Category, Transaction, Budget, Transfer, and Report models.
"""

import logging

# Import Category model for budget categories
from .category import Category, create_category, create_categories_from_sheet_data, get_category_names

# Import Transaction model for financial transactions
from .transaction import (
    Transaction, create_transaction, create_transactions_from_capital_one,
    create_transactions_from_sheet_data, get_transaction_locations,
    group_transactions_by_category, calculate_category_totals
)

# Import Budget model for budget analysis
from .budget import (
    Budget, create_budget, create_budget_from_sheet_data,
    calculate_category_variances, calculate_transfer_amount
)

# Import Transfer model for fund transfers
from .transfer import (
    Transfer, create_transfer, create_transfer_from_capital_one_response
)

# Import Report model for budget reports
from .report import (
    Report, create_report, create_report_with_insights,
    create_report_with_charts, create_complete_report
)

# Set up logger
logger = logging.getLogger(__name__)

# Define exports
__all__ = [
    "Category", "create_category", "create_categories_from_sheet_data", "get_category_names",
    "Transaction", "create_transaction", "create_transactions_from_capital_one",
    "create_transactions_from_sheet_data", "get_transaction_locations",
    "group_transactions_by_category", "calculate_category_totals",
    "Budget", "create_budget", "create_budget_from_sheet_data",
    "calculate_category_variances", "calculate_transfer_amount",
    "Transfer", "create_transfer", "create_transfer_from_capital_one_response",
    "Report", "create_report", "create_report_with_insights",
    "create_report_with_charts", "create_complete_report"
]