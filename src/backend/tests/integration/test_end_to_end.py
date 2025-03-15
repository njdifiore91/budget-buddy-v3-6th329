"""
End-to-end integration tests for the Budget Management Application. This file tests the complete workflow from transaction retrieval to savings transfer, ensuring all components work together correctly with mocked external dependencies.
"""

import pytest  # pytest 7.4.0+
from decimal import Decimal  # standard library
from typing import Dict, List, Any  # standard library

# Internal imports
from ..conftest import mock_capital_one_client, mock_google_sheets_client, mock_gemini_client, mock_gmail_client, transactions, categories, budget_with_surplus  # src/backend/tests/conftest.py
from ..conftest import budget_with_deficit  # src/backend/tests/conftest.py
from ..conftest import create_test_transactions, create_test_categories  # src/backend/tests/conftest.py
from ...components.transaction_retriever import TransactionRetriever  # src/backend/components/transaction_retriever.py
from ...components.transaction_categorizer import TransactionCategorizer  # src/backend/components/transaction_categorizer.py
from ...components.budget_analyzer import BudgetAnalyzer  # src/backend/components/budget_analyzer.py
from ...components.insight_generator import InsightGenerator  # src/backend/components/insight_generator.py
from ...components.report_distributor import ReportDistributor  # src/backend/components/report_distributor.py
from ...components.savings_automator import SavingsAutomator  # src/backend/components/savings_automator.py
from ...main import initialize_clients, initialize_components, execute_workflow  # src/backend/main.py


def setup_budget_management_app(
    mock_capital_one_client,
    mock_google_sheets_client,
    mock_gemini_client,
    mock_gmail_client
):
    """Set up a complete Budget Management Application with mock dependencies for testing"""
    transaction_retriever = TransactionRetriever(
        capital_one_client=mock_capital_one_client,
        sheets_client=mock_google_sheets_client
    )
    transaction_categorizer = TransactionCategorizer(
        gemini_client=mock_gemini_client,
        sheets_client=mock_google_sheets_client
    )
    budget_analyzer = BudgetAnalyzer(sheets_client=mock_google_sheets_client)
    insight_generator = InsightGenerator(gemini_client=mock_gemini_client)
    report_distributor = ReportDistributor(gmail_client=mock_gmail_client)
    savings_automator = SavingsAutomator(capital_one_client=mock_capital_one_client)

    return (
        transaction_retriever,
        transaction_categorizer,
        budget_analyzer,
        insight_generator,
        report_distributor,
        savings_automator
    )


class BudgetManagementApp:
    """Test wrapper for the Budget Management Application that orchestrates the complete workflow"""

    def __init__(
        self,
        mock_capital_one_client,
        mock_google_sheets_client,
        mock_gemini_client,
        mock_gmail_client
    ):
        """Initialize the Budget Management App with mock clients"""
        self.mock_capital_one_client = mock_capital_one_client
        self.mock_google_sheets_client = mock_google_sheets_client
        self.mock_gemini_client = mock_gemini_client
        self.mock_gmail_client = mock_gmail_client

        (
            self.transaction_retriever,
            self.transaction_categorizer,
            self.budget_analyzer,
            self.insight_generator,
            self.report_distributor,
            self.savings_automator
        ) = setup_budget_management_app(
            mock_capital_one_client,
            mock_google_sheets_client,
            mock_gemini_client,
            mock_gmail_client
        )

    def run_weekly_process(self) -> Dict[str, Any]:
        """Execute the complete weekly budget management process"""
        retriever_status = self.transaction_retriever.execute()
        categorizer_status = self.transaction_categorizer.execute(retriever_status)
        analyzer_status = self.budget_analyzer.execute(categorizer_status)
        insight_status = self.insight_generator.execute(analyzer_status)
        report_status = self.report_distributor.execute(insight_status)
        savings_status = self.savings_automator.execute(analyzer_status)

        final_status = {
            "retriever": retriever_status,
            "categorizer": categorizer_status,
            "analyzer": analyzer_status,
            "insight": insight_status,
            "report": report_status,
            "savings": savings_status
        }

        return final_status


@pytest.mark.integration
def test_end_to_end_workflow_with_surplus(
    mock_capital_one_client,
    mock_google_sheets_client,
    mock_gemini_client,
    mock_gmail_client,
    transactions,
    categories,
    budget_with_surplus
):
    """Test the complete budget management workflow with a budget surplus"""
    mock_capital_one_client.set_transactions(transactions)
    mock_google_sheets_client.set_sheet_data("Master Budget", categories)
    mock_google_sheets_client.set_sheet_data("Weekly Spending", transactions)
    mock_gemini_client.set_categorization_response({"location": "Category"})
    mock_gemini_client.set_insights_response("Insights")

    app = BudgetManagementApp(
        mock_capital_one_client,
        mock_google_sheets_client,
        mock_gemini_client,
        mock_gmail_client
    )
    final_status = app.run_weekly_process()

    assert final_status["retriever"]["status"] == "success"
    assert final_status["categorizer"]["status"] == "success"
    assert final_status["analyzer"]["status"] == "success"
    assert final_status["insight"]["status"] == "success"
    assert final_status["report"]["status"] == "success"
    assert mock_gmail_client.get_sent_emails() != []
    assert mock_capital_one_client.transfer_initiated
    assert mock_capital_one_client.transfer_amount == budget_with_surplus["total_variance"]


@pytest.mark.integration
def test_end_to_end_workflow_with_deficit(
    mock_capital_one_client,
    mock_google_sheets_client,
    mock_gemini_client,
    mock_gmail_client,
    transactions,
    categories,
    budget_with_deficit
):
    """Test the complete budget management workflow with a budget deficit"""
    mock_capital_one_client.set_transactions(transactions)
    mock_google_sheets_client.set_sheet_data("Master Budget", categories)
    mock_google_sheets_client.set_sheet_data("Weekly Spending", transactions)
    mock_gemini_client.set_categorization_response({"location": "Category"})
    mock_gemini_client.set_insights_response("Insights")

    app = BudgetManagementApp(
        mock_capital_one_client,
        mock_google_sheets_client,
        mock_gemini_client,
        mock_gmail_client
    )
    final_status = app.run_weekly_process()

    assert final_status["retriever"]["status"] == "success"
    assert final_status["categorizer"]["status"] == "success"
    assert final_status["analyzer"]["status"] == "success"
    assert final_status["insight"]["status"] == "success"
    assert final_status["report"]["status"] == "success"
    assert mock_gmail_client.get_sent_emails() != []
    assert not mock_capital_one_client.transfer_initiated


@pytest.mark.integration
def test_end_to_end_error_recovery(
    mock_capital_one_client,
    mock_google_sheets_client,
    mock_gemini_client,
    mock_gmail_client,
    transactions,
    categories,
    budget_with_surplus
):
    """Test the application's ability to recover from errors during the workflow"""
    mock_capital_one_client.set_transactions(transactions)
    mock_google_sheets_client.set_sheet_data("Master Budget", categories)
    mock_google_sheets_client.set_sheet_data("Weekly Spending", transactions)
    mock_gemini_client.set_categorization_response({"location": "Category"})
    mock_gemini_client.set_insights_response("Insights")

    # Configure mock_gemini_client to fail on first categorization attempt but succeed on retry
    mock_gemini_client.api_error = True

    app = BudgetManagementApp(
        mock_capital_one_client,
        mock_google_sheets_client,
        mock_gemini_client,
        mock_gmail_client
    )
    final_status = app.run_weekly_process()

    assert final_status["retriever"]["status"] == "success"
    assert final_status["categorizer"]["status"] == "error"
    assert final_status["analyzer"]["status"] == "success"
    assert final_status["insight"]["status"] == "success"
    assert final_status["report"]["status"] == "success"
    assert mock_gmail_client.get_sent_emails() != []
    assert mock_capital_one_client.transfer_initiated
    assert mock_capital_one_client.transfer_amount == budget_with_surplus["total_variance"]


@pytest.mark.integration
def test_end_to_end_component_integration(
    mock_capital_one_client,
    mock_google_sheets_client,
    mock_gemini_client,
    mock_gmail_client,
    transactions,
    categories,
    budget_with_surplus
):
    """Test the integration between individual components in the workflow"""
    mock_capital_one_client.set_transactions(transactions)
    mock_google_sheets_client.set_sheet_data("Master Budget", categories)
    mock_google_sheets_client.set_sheet_data("Weekly Spending", transactions)
    mock_gemini_client.set_categorization_response({"location": "Category"})
    mock_gemini_client.set_insights_response("Insights")

    (
        transaction_retriever,
        transaction_categorizer,
        budget_analyzer,
        insight_generator,
        report_distributor,
        savings_automator
    ) = setup_budget_management_app(
        mock_capital_one_client,
        mock_google_sheets_client,
        mock_gemini_client,
        mock_gmail_client
    )

    retriever_status = transaction_retriever.execute()
    assert retriever_status["status"] == "success"

    categorizer_status = transaction_categorizer.execute(retriever_status)
    assert categorizer_status["status"] == "success"

    analyzer_status = budget_analyzer.execute(categorizer_status)
    assert analyzer_status["status"] == "success"

    insight_status = insight_generator.execute(analyzer_status)
    assert insight_status["status"] == "success"

    report_status = report_distributor.execute(insight_status)
    assert report_status["status"] == "success"

    savings_status = savings_automator.execute(analyzer_status)
    assert savings_status["status"] == "success"


@pytest.mark.integration
def test_end_to_end_with_main_functions(
    mock_capital_one_client,
    mock_google_sheets_client,
    mock_gemini_client,
    mock_gmail_client,
    transactions,
    categories,
    budget_with_surplus
):
    """Test the complete workflow using the main.py functions"""
    mock_capital_one_client.set_transactions(transactions)
    mock_google_sheets_client.set_sheet_data("Master Budget", categories)
    mock_google_sheets_client.set_sheet_data("Weekly Spending", transactions)
    mock_gemini_client.set_categorization_response({"location": "Category"})
    mock_gemini_client.set_insights_response("Insights")

    def mock_initialize_clients():
        return (
            mock_capital_one_client,
            mock_google_sheets_client,
            mock_gemini_client,
            mock_gmail_client,
        )

    (
        capital_one_client,
        sheets_client,
        gemini_client,
        gmail_client,
    ) = mock_initialize_clients()

    (
        transaction_retriever,
        transaction_categorizer,
        budget_analyzer,
        insight_generator,
        report_distributor,
        savings_automator
    ) = initialize_components(
        capital_one_client,
        sheets_client,
        gemini_client,
        gmail_client,
    )

    final_status = execute_workflow(
        transaction_retriever,
        transaction_categorizer,
        budget_analyzer,
        insight_generator,
        report_distributor,
        savings_automator
    )

    assert final_status["retriever"]["status"] == "success"
    assert final_status["categorizer"]["status"] == "success"
    assert final_status["analyzer"]["status"] == "success"
    assert final_status["insight"]["status"] == "success"
    assert final_status["report"]["status"] == "success"
    assert mock_gmail_client.get_sent_emails() != []
    assert mock_capital_one_client.transfer_initiated
    assert mock_capital_one_client.transfer_amount == budget_with_surplus["total_variance"]