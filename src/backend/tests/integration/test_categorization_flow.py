import pytest  # pytest 7.4.0+

# Internal imports
from ..conftest import transaction_categorizer, mock_google_sheets_client, mock_gemini_client, uncategorized_transactions, categories  # src/backend/tests/conftest.py
from ..mocks.mock_google_sheets_client import MockGoogleSheetsClient  # src/backend/tests/mocks/mock_google_sheets_client.py
from ..mocks.mock_gemini_client import MockGeminiClient  # src/backend/tests/mocks/mock_gemini_client.py
from ...components.transaction_categorizer import TransactionCategorizer  # src/backend/components/transaction_categorizer.py


@pytest.mark.integration
def test_successful_categorization_flow(transaction_categorizer: TransactionCategorizer,
                                        mock_google_sheets_client: MockGoogleSheetsClient,
                                        mock_gemini_client: MockGeminiClient,
                                        uncategorized_transactions,
                                        categories):
    """Test the complete transaction categorization flow with successful execution"""
    # Step 1: Set up mock Google Sheets client with uncategorized transactions in Weekly Spending sheet
    mock_google_sheets_client.set_sheet_data("Weekly Spending", [tx.to_dict() for tx in uncategorized_transactions])

    # Step 2: Set up mock Google Sheets client with categories in Master Budget sheet
    mock_google_sheets_client.set_sheet_data("Master Budget", [cat.to_dict() for cat in categories])

    # Step 3: Set up mock Gemini client with successful categorization response
    mock_gemini_client.set_mock_categorization_response({"location1": "Category A", "location2": "Category B"})

    # Step 4: Execute the transaction categorization process
    result = transaction_categorizer.execute()

    # Step 5: Verify execution status is 'success'
    assert result["status"] == "success"

    # Step 6: Verify categorization metrics in the result
    assert "metrics" in result
    assert result["metrics"]["transactions_categorized"] == len(uncategorized_transactions)

    # Step 7: Verify Weekly Spending sheet has been updated with categories
    updated_transactions = mock_google_sheets_client.get_sheet_data("Weekly Spending")
    assert len(updated_transactions) == len(uncategorized_transactions)

    # Step 8: Verify the number of transactions categorized matches expected count
    categorized_count = sum(1 for tx in updated_transactions if tx.get("category"))
    assert categorized_count == len(uncategorized_transactions)


@pytest.mark.integration
def test_categorization_flow_with_api_error(transaction_categorizer: TransactionCategorizer,
                                            mock_google_sheets_client: MockGoogleSheetsClient,
                                            mock_gemini_client: MockGeminiClient,
                                            uncategorized_transactions,
                                            categories):
    """Test the transaction categorization flow when Gemini API returns an error"""
    # Step 1: Set up mock Google Sheets client with uncategorized transactions in Weekly Spending sheet
    mock_google_sheets_client.set_sheet_data("Weekly Spending", [tx.to_dict() for tx in uncategorized_transactions])

    # Step 2: Set up mock Google Sheets client with categories in Master Budget sheet
    mock_google_sheets_client.set_sheet_data("Master Budget", [cat.to_dict() for cat in categories])

    # Step 3: Set up mock Gemini client to simulate an API error
    mock_gemini_client.set_api_error(True)

    # Step 4: Execute the transaction categorization process
    result = transaction_categorizer.execute()

    # Step 5: Verify execution status is 'error'
    assert result["status"] == "error"

    # Step 6: Verify error message indicates Gemini API failure
    assert "Gemini" in result["error"]

    # Step 7: Verify Weekly Spending sheet has not been updated with categories
    updated_transactions = mock_google_sheets_client.get_sheet_data("Weekly Spending")
    assert len(updated_transactions) == len(uncategorized_transactions)
    categorized_count = sum(1 for tx in updated_transactions if tx.get("category"))
    assert categorized_count == 0


@pytest.mark.integration
def test_categorization_flow_with_sheets_error(transaction_categorizer: TransactionCategorizer,
                                               mock_google_sheets_client: MockGoogleSheetsClient,
                                               mock_gemini_client: MockGeminiClient,
                                               uncategorized_transactions,
                                               categories):
    """Test the transaction categorization flow when Google Sheets API returns an error"""
    # Step 1: Set up mock Google Sheets client with uncategorized transactions in Weekly Spending sheet
    mock_google_sheets_client.set_sheet_data("Weekly Spending", [tx.to_dict() for tx in uncategorized_transactions])

    # Step 2: Set up mock Google Sheets client with categories in Master Budget sheet
    mock_google_sheets_client.set_sheet_data("Master Budget", [cat.to_dict() for cat in categories])

    # Step 3: Set up mock Google Sheets client to simulate an API error during update
    mock_google_sheets_client.set_api_error(True)

    # Step 4: Set up mock Gemini client with successful categorization response
    mock_gemini_client.set_mock_categorization_response({"location1": "Category A", "location2": "Category B"})

    # Step 5: Execute the transaction categorization process
    result = transaction_categorizer.execute()

    # Step 6: Verify execution status is 'error'
    assert result["status"] == "error"

    # Step 7: Verify error message indicates Google Sheets API failure
    assert "Google Sheets" in result["error"]


@pytest.mark.integration
def test_categorization_flow_with_empty_transactions(transaction_categorizer: TransactionCategorizer,
                                                     mock_google_sheets_client: MockGoogleSheetsClient,
                                                     mock_gemini_client: MockGeminiClient,
                                                     categories):
    """Test the transaction categorization flow when no transactions are available"""
    # Step 1: Set up mock Google Sheets client with empty Weekly Spending sheet
    mock_google_sheets_client.set_sheet_data("Weekly Spending", [])

    # Step 2: Set up mock Google Sheets client with categories in Master Budget sheet
    mock_google_sheets_client.set_sheet_data("Master Budget", [cat.to_dict() for cat in categories])

    # Step 3: Execute the transaction categorization process
    result = transaction_categorizer.execute()

    # Step 4: Verify execution status is 'success'
    assert result["status"] == "warning"

    # Step 5: Verify message indicates no transactions to categorize
    assert "No transactions to categorize" in result["message"]

    # Step 6: Verify categorized_count is 0
    assert result["metrics"]["transactions_categorized"] == 0


@pytest.mark.integration
def test_categorization_flow_with_empty_categories(transaction_categorizer: TransactionCategorizer,
                                                   mock_google_sheets_client: MockGoogleSheetsClient,
                                                   mock_gemini_client: MockGeminiClient,
                                                   uncategorized_transactions):
    """Test the transaction categorization flow when no categories are available"""
    # Step 1: Set up mock Google Sheets client with uncategorized transactions in Weekly Spending sheet
    mock_google_sheets_client.set_sheet_data("Weekly Spending", [tx.to_dict() for tx in uncategorized_transactions])

    # Step 2: Set up mock Google Sheets client with empty Master Budget sheet
    mock_google_sheets_client.set_sheet_data("Master Budget", [])

    # Step 3: Execute the transaction categorization process
    result = transaction_categorizer.execute()

    # Step 4: Verify execution status is 'error'
    assert result["status"] == "error"

    # Step 5: Verify error message indicates no categories available
    assert "No budget categories available" in result["error"]

    # Step 6: Verify Weekly Spending sheet has not been updated
    updated_transactions = mock_google_sheets_client.get_sheet_data("Weekly Spending")
    assert len(updated_transactions) == len(uncategorized_transactions)
    categorized_count = sum(1 for tx in updated_transactions if tx.get("category"))
    assert categorized_count == 0


@pytest.mark.integration
def test_categorization_flow_with_low_accuracy(transaction_categorizer: TransactionCategorizer,
                                               mock_google_sheets_client: MockGoogleSheetsClient,
                                               mock_gemini_client: MockGeminiClient,
                                               uncategorized_transactions,
                                               categories):
    """Test the transaction categorization flow when AI categorization accuracy is below threshold"""
    # Step 1: Set up mock Google Sheets client with uncategorized transactions in Weekly Spending sheet
    mock_google_sheets_client.set_sheet_data("Weekly Spending", [tx.to_dict() for tx in uncategorized_transactions])

    # Step 2: Set up mock Google Sheets client with categories in Master Budget sheet
    mock_google_sheets_client.set_sheet_data("Master Budget", [cat.to_dict() for cat in categories])

    # Step 3: Set up mock Gemini client with partial categorization response (below 95% threshold)
    mock_gemini_client.set_mock_categorization_response({"location1": "Category A"})

    # Step 4: Execute the transaction categorization process
    result = transaction_categorizer.execute()

    # Step 5: Verify execution status is 'warning'
    assert result["status"] == "warning"

    # Step 6: Verify warning message indicates low categorization accuracy
    assert "below threshold" in result["message"]

    # Step 7: Verify Weekly Spending sheet has been updated with available categories
    updated_transactions = mock_google_sheets_client.get_sheet_data("Weekly Spending")
    assert len(updated_transactions) == len(uncategorized_transactions)

    # Step 8: Verify categorization_accuracy is below threshold
    categorized_count = sum(1 for tx in updated_transactions if tx.get("category"))
    assert categorized_count < len(uncategorized_transactions)


@pytest.mark.integration
def test_categorization_flow_with_retry_success(transaction_categorizer: TransactionCategorizer,
                                               mock_google_sheets_client: MockGoogleSheetsClient,
                                               mock_gemini_client: MockGeminiClient,
                                               uncategorized_transactions,
                                               categories,
                                               monkeypatch):
    """Test the transaction categorization flow with successful retry after initial failure"""
    # Step 1: Set up mock Google Sheets client with uncategorized transactions in Weekly Spending sheet
    mock_google_sheets_client.set_sheet_data("Weekly Spending", [tx.to_dict() for tx in uncategorized_transactions])

    # Step 2: Set up mock Google Sheets client with categories in Master Budget sheet
    mock_google_sheets_client.set_sheet_data("Master Budget", [cat.to_dict() for cat in categories])

    # Step 3: Set up mock Gemini client to fail on first call then succeed on retry
    def mock_generate_completion(prompt):
        if mock_generate_completion.call_count == 0:
            mock_generate_completion.call_count += 1
            raise Exception("Simulated API failure")
        else:
            return "Location: location1 -> Category: Category A\nLocation: location2 -> Category: Category B"
    mock_generate_completion.call_count = 0
    monkeypatch.setattr(mock_gemini_client, "generate_completion", mock_generate_completion)

    # Step 4: Use monkeypatch to modify retry behavior for testing
    monkeypatch.setattr(transaction_categorizer, "max_retries", 1)

    # Step 5: Execute the transaction categorization process
    result = transaction_categorizer.execute()

    # Step 6: Verify execution status is 'success'
    assert result["status"] == "success"

    # Step 7: Verify retry count in the result
    assert result["metrics"]["transactions_categorized"] == len(uncategorized_transactions)

    # Step 8: Verify Weekly Spending sheet has been updated with categories
    updated_transactions = mock_google_sheets_client.get_sheet_data("Weekly Spending")
    assert len(updated_transactions) == len(uncategorized_transactions)
    categorized_count = sum(1 for tx in updated_transactions if tx.get("category"))
    assert categorized_count == len(uncategorized_transactions)