import pytest
from unittest.mock import MagicMock, patch
from googleapiclient.errors import HttpError
from decimal import Decimal
import datetime

from ../../api_clients.google_sheets_client import (
    GoogleSheetsClient, build_sheets_service, parse_sheet_range, format_sheet_range
)
from ../../models.transaction import Transaction, create_transactions_from_sheet_data
from ../../models.budget import create_budget_from_sheet_data
from ../mocks.mock_google_sheets_client import MockGoogleSheetsClient
from ../../services.authentication_service import AuthenticationService
from ../../utils.error_handlers import APIError
from ../fixtures.api_responses import (
    load_google_sheets_budget_response, 
    load_google_sheets_transactions_response,
    load_google_sheets_error_response
)


def test_build_sheets_service():
    # Create mock credentials object
    mock_credentials = MagicMock()
    
    # Mock googleapiclient.discovery.build function
    with patch('googleapiclient.discovery.build') as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Call build_sheets_service with mock credentials
        service = build_sheets_service(mock_credentials)
        
        # Assert build was called with correct parameters
        mock_build.assert_called_once_with('sheets', 'v4', credentials=mock_credentials)
        
        # Assert service object is returned correctly
        assert service == mock_service


def test_parse_sheet_range():
    # Test with simple range 'Sheet1!A1:B10'
    sheet_name, start_cell, end_cell = parse_sheet_range('Sheet1!A1:B10')
    assert sheet_name == 'Sheet1'
    assert start_cell == 'A1'
    assert end_cell == 'B10'
    
    # Test with sheet name containing spaces 'My Sheet!A1:B10'
    sheet_name, start_cell, end_cell = parse_sheet_range("'My Sheet'!A1:B10")
    assert sheet_name == 'My Sheet'
    assert start_cell == 'A1'
    assert end_cell == 'B10'
    
    # Test with single cell range 'Sheet1!A1'
    sheet_name, start_cell, end_cell = parse_sheet_range('Sheet1!A1')
    assert sheet_name == 'Sheet1'
    assert start_cell == 'A1'
    assert end_cell is None


def test_format_sheet_range():
    # Test with simple sheet name and range
    sheet_range = format_sheet_range('Sheet1', 'A1', 'B10')
    assert sheet_range == 'Sheet1!A1:B10'
    
    # Test with sheet name containing spaces
    sheet_range = format_sheet_range('My Sheet', 'A1', 'B10')
    assert sheet_range == "'My Sheet'!A1:B10"
    
    # Test with single cell (no end_cell)
    sheet_range = format_sheet_range('Sheet1', 'A1')
    assert sheet_range == 'Sheet1!A1'


def test_google_sheets_client_init():
    # Create mock AuthenticationService
    mock_auth_service = MagicMock(spec=AuthenticationService)
    
    # Initialize GoogleSheetsClient with mock auth_service
    client = GoogleSheetsClient(auth_service=mock_auth_service)
    
    # Assert auth_service is set correctly
    assert client.auth_service == mock_auth_service
    
    # Assert service is initially None
    assert client.service is None
    
    # Assert weekly_spending_id and master_budget_id are set from APP_SETTINGS
    from ../../config.settings import APP_SETTINGS
    assert client.weekly_spending_id == APP_SETTINGS['WEEKLY_SPENDING_SHEET_ID']
    assert client.master_budget_id == APP_SETTINGS['MASTER_BUDGET_SHEET_ID']


def test_authenticate_success():
    # Create mock AuthenticationService with successful authentication
    mock_auth_service = MagicMock(spec=AuthenticationService)
    mock_credentials = MagicMock()
    mock_auth_service.authenticate_google_sheets.return_value = mock_credentials
    
    # Mock build_sheets_service to return mock service
    mock_service = MagicMock()
    with patch('../../api_clients.google_sheets_client.build_sheets_service') as mock_build:
        mock_build.return_value = mock_service
        
        # Initialize GoogleSheetsClient with mock auth_service
        client = GoogleSheetsClient(auth_service=mock_auth_service)
        
        # Call authenticate method
        result = client.authenticate()
        
        # Assert authenticate_google_sheets was called
        mock_auth_service.authenticate_google_sheets.assert_called_once()
        
        # Assert build_sheets_service was called with credentials
        mock_build.assert_called_once_with(mock_credentials)
        
        # Assert service is set to the mock service
        assert client.service == mock_service
        
        # Assert authenticate returns True
        assert result is True


def test_authenticate_failure():
    # Create mock AuthenticationService that returns None for credentials
    mock_auth_service = MagicMock(spec=AuthenticationService)
    mock_auth_service.authenticate_google_sheets.return_value = None
    
    # Initialize GoogleSheetsClient with mock auth_service
    client = GoogleSheetsClient(auth_service=mock_auth_service)
    
    # Call authenticate method
    result = client.authenticate()
    
    # Assert authenticate_google_sheets was called
    mock_auth_service.authenticate_google_sheets.assert_called_once()
    
    # Assert service remains None
    assert client.service is None
    
    # Assert authenticate returns False
    assert result is False


def test_ensure_authenticated_already_authenticated():
    # Create GoogleSheetsClient with mock service already set
    client = GoogleSheetsClient()
    client.service = MagicMock()  # Set service to indicate authenticated state
    
    # Mock authenticate method
    client.authenticate = MagicMock()
    
    # Call ensure_authenticated method
    result = client.ensure_authenticated()
    
    # Assert authenticate method is not called
    client.authenticate.assert_not_called()
    
    # Assert ensure_authenticated returns True
    assert result is True


def test_ensure_authenticated_needs_authentication_success():
    # Create GoogleSheetsClient with service as None
    client = GoogleSheetsClient()
    client.service = None
    
    # Mock authenticate method to return True
    client.authenticate = MagicMock(return_value=True)
    
    # Call ensure_authenticated method
    result = client.ensure_authenticated()
    
    # Assert authenticate method is called
    client.authenticate.assert_called_once()
    
    # Assert ensure_authenticated returns True
    assert result is True


def test_ensure_authenticated_needs_authentication_failure():
    # Create GoogleSheetsClient with service as None
    client = GoogleSheetsClient()
    client.service = None
    
    # Mock authenticate method to return False
    client.authenticate = MagicMock(return_value=False)
    
    # Call ensure_authenticated method
    result = client.ensure_authenticated()
    
    # Assert authenticate method is called
    client.authenticate.assert_called_once()
    
    # Assert ensure_authenticated returns False
    assert result is False


def test_read_sheet_success():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    client.service = MagicMock()
    
    # Mock ensure_authenticated to return True
    client.ensure_authenticated = MagicMock(return_value=True)
    
    # Mock service.spreadsheets().values().get().execute() to return mock response
    mock_values = [["A1", "B1"], ["A2", "B2"]]
    mock_response = {"values": mock_values}
    
    # Need to configure the nested mocks
    mock_get = MagicMock()
    mock_get.execute.return_value = mock_response
    mock_values_obj = MagicMock()
    mock_values_obj.get.return_value = mock_get
    mock_spreadsheets = MagicMock()
    mock_spreadsheets.values.return_value = mock_values_obj
    client.service.spreadsheets.return_value = mock_spreadsheets
    
    # Call read_sheet method with test parameters
    result = client.read_sheet("sheet_id", "Sheet1!A1:B2")
    
    # Assert ensure_authenticated was called
    client.ensure_authenticated.assert_called_once()
    
    # Assert service.spreadsheets().values().get() was called with correct parameters
    client.service.spreadsheets().values().get.assert_called_with(
        spreadsheetId="sheet_id",
        range="Sheet1!A1:B2",
        valueRenderOption="UNFORMATTED_VALUE"
    )
    
    # Assert read_sheet returns expected values from response
    assert result == mock_values


def test_read_sheet_no_values():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    client.service = MagicMock()
    
    # Mock ensure_authenticated to return True
    client.ensure_authenticated = MagicMock(return_value=True)
    
    # Mock service.spreadsheets().values().get().execute() to return response without 'values' key
    mock_response = {}
    
    # Need to configure the nested mocks
    mock_get = MagicMock()
    mock_get.execute.return_value = mock_response
    mock_values_obj = MagicMock()
    mock_values_obj.get.return_value = mock_get
    mock_spreadsheets = MagicMock()
    mock_spreadsheets.values.return_value = mock_values_obj
    client.service.spreadsheets.return_value = mock_spreadsheets
    
    # Call read_sheet method with test parameters
    result = client.read_sheet("sheet_id", "Sheet1!A1:B2")
    
    # Assert read_sheet returns empty list
    assert result == []


def test_read_sheet_authentication_failure():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    client.service = MagicMock()
    
    # Mock ensure_authenticated to return False
    client.ensure_authenticated = MagicMock(return_value=False)
    
    # Call read_sheet method with test parameters
    with pytest.raises(APIError):
        client.read_sheet("sheet_id", "Sheet1!A1:B2")


def test_read_sheet_api_error():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    client.service = MagicMock()
    
    # Mock ensure_authenticated to return True
    client.ensure_authenticated = MagicMock(return_value=True)
    
    # Mock service.spreadsheets().values().get().execute() to raise HttpError
    mock_resp = MagicMock()
    mock_resp.status = 400
    mock_error = HttpError(resp=mock_resp, content=b'{"error": "API error"}')
    
    # Need to configure the nested mocks
    mock_get = MagicMock()
    mock_get.execute.side_effect = mock_error
    mock_values_obj = MagicMock()
    mock_values_obj.get.return_value = mock_get
    mock_spreadsheets = MagicMock()
    mock_spreadsheets.values.return_value = mock_values_obj
    client.service.spreadsheets.return_value = mock_spreadsheets
    
    # Call read_sheet method with test parameters
    with pytest.raises(HttpError) as excinfo:
        client.read_sheet("sheet_id", "Sheet1!A1:B2")
    
    # Assert APIError is raised with appropriate message
    assert isinstance(excinfo.value, HttpError)


def test_append_rows_success():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    client.service = MagicMock()
    
    # Mock ensure_authenticated to return True
    client.ensure_authenticated = MagicMock(return_value=True)
    
    # Mock service.spreadsheets().values().append().execute() to return mock response
    mock_response = {
        "updates": {
            "updatedRange": "Sheet1!A1:B2",
            "updatedRows": 2,
            "updatedColumns": 2,
            "updatedCells": 4
        }
    }
    
    # Need to configure the nested mocks
    mock_append = MagicMock()
    mock_append.execute.return_value = mock_response
    mock_values_obj = MagicMock()
    mock_values_obj.append.return_value = mock_append
    mock_spreadsheets = MagicMock()
    mock_spreadsheets.values.return_value = mock_values_obj
    client.service.spreadsheets.return_value = mock_spreadsheets
    
    # Prepare test data
    spreadsheet_id = "sheet_id"
    range_name = "Sheet1!A1:B2"
    values = [["A1", "B1"], ["A2", "B2"]]
    
    # Call append_rows method with test parameters
    result = client.append_rows(spreadsheet_id, range_name, values)
    
    # Assert ensure_authenticated was called
    client.ensure_authenticated.assert_called_once()
    
    # Assert service.spreadsheets().values().append() was called with correct parameters
    client.service.spreadsheets().values().append.assert_called_with(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values}
    )
    
    # Assert append_rows returns expected response
    assert result == mock_response


def test_append_rows_authentication_failure():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    client.service = MagicMock()
    
    # Mock ensure_authenticated to return False
    client.ensure_authenticated = MagicMock(return_value=False)
    
    # Call append_rows method with test parameters
    with pytest.raises(APIError):
        client.append_rows("sheet_id", "Sheet1!A1:B2", [["A1", "B1"]])


def test_append_rows_api_error():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    client.service = MagicMock()
    
    # Mock ensure_authenticated to return True
    client.ensure_authenticated = MagicMock(return_value=True)
    
    # Mock service.spreadsheets().values().append().execute() to raise HttpError
    mock_resp = MagicMock()
    mock_resp.status = 400
    mock_error = HttpError(resp=mock_resp, content=b'{"error": "API error"}')
    
    # Need to configure the nested mocks
    mock_append = MagicMock()
    mock_append.execute.side_effect = mock_error
    mock_values_obj = MagicMock()
    mock_values_obj.append.return_value = mock_append
    mock_spreadsheets = MagicMock()
    mock_spreadsheets.values.return_value = mock_values_obj
    client.service.spreadsheets.return_value = mock_spreadsheets
    
    # Call append_rows method with test parameters
    with pytest.raises(HttpError) as excinfo:
        client.append_rows("sheet_id", "Sheet1!A1:B2", [["A1", "B1"]])
    
    # Assert APIError is raised with appropriate message
    assert isinstance(excinfo.value, HttpError)


def test_update_values_success():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    client.service = MagicMock()
    
    # Mock ensure_authenticated to return True
    client.ensure_authenticated = MagicMock(return_value=True)
    
    # Mock service.spreadsheets().values().update().execute() to return mock response
    mock_response = {
        "updatedRange": "Sheet1!A1:B2",
        "updatedRows": 2,
        "updatedColumns": 2,
        "updatedCells": 4
    }
    
    # Need to configure the nested mocks
    mock_update = MagicMock()
    mock_update.execute.return_value = mock_response
    mock_values_obj = MagicMock()
    mock_values_obj.update.return_value = mock_update
    mock_spreadsheets = MagicMock()
    mock_spreadsheets.values.return_value = mock_values_obj
    client.service.spreadsheets.return_value = mock_spreadsheets
    
    # Prepare test data
    spreadsheet_id = "sheet_id"
    range_name = "Sheet1!A1:B2"
    values = [["A1", "B1"], ["A2", "B2"]]
    
    # Call update_values method with test parameters
    result = client.update_values(spreadsheet_id, range_name, values)
    
    # Assert ensure_authenticated was called
    client.ensure_authenticated.assert_called_once()
    
    # Assert service.spreadsheets().values().update() was called with correct parameters
    client.service.spreadsheets().values().update.assert_called_with(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="USER_ENTERED",
        body={"values": values}
    )
    
    # Assert update_values returns expected response
    assert result == mock_response


def test_update_values_authentication_failure():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    client.service = MagicMock()
    
    # Mock ensure_authenticated to return False
    client.ensure_authenticated = MagicMock(return_value=False)
    
    # Call update_values method with test parameters
    with pytest.raises(APIError):
        client.update_values("sheet_id", "Sheet1!A1:B2", [["A1", "B1"]])


def test_update_values_api_error():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    client.service = MagicMock()
    
    # Mock ensure_authenticated to return True
    client.ensure_authenticated = MagicMock(return_value=True)
    
    # Mock service.spreadsheets().values().update().execute() to raise HttpError
    mock_resp = MagicMock()
    mock_resp.status = 400
    mock_error = HttpError(resp=mock_resp, content=b'{"error": "API error"}')
    
    # Need to configure the nested mocks
    mock_update = MagicMock()
    mock_update.execute.side_effect = mock_error
    mock_values_obj = MagicMock()
    mock_values_obj.update.return_value = mock_update
    mock_spreadsheets = MagicMock()
    mock_spreadsheets.values.return_value = mock_values_obj
    client.service.spreadsheets.return_value = mock_spreadsheets
    
    # Call update_values method with test parameters
    with pytest.raises(HttpError) as excinfo:
        client.update_values("sheet_id", "Sheet1!A1:B2", [["A1", "B1"]])
    
    # Assert APIError is raised with appropriate message
    assert isinstance(excinfo.value, HttpError)


def test_batch_update_success():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    client.service = MagicMock()
    
    # Mock ensure_authenticated to return True
    client.ensure_authenticated = MagicMock(return_value=True)
    
    # Mock service.spreadsheets().batchUpdate().execute() to return mock response
    mock_response = {
        "spreadsheetId": "sheet_id",
        "replies": [{}]
    }
    
    # Need to configure the nested mocks
    mock_batch_update = MagicMock()
    mock_batch_update.execute.return_value = mock_response
    mock_spreadsheets = MagicMock()
    mock_spreadsheets.batchUpdate.return_value = mock_batch_update
    client.service.spreadsheets.return_value = mock_spreadsheets
    
    # Prepare test data
    spreadsheet_id = "sheet_id"
    requests = [{"updateCells": {"fields": "userEnteredValue"}}]
    
    # Call batch_update method with test parameters
    result = client.batch_update(spreadsheet_id, requests)
    
    # Assert ensure_authenticated was called
    client.ensure_authenticated.assert_called_once()
    
    # Assert service.spreadsheets().batchUpdate() was called with correct parameters
    client.service.spreadsheets().batchUpdate.assert_called_with(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests}
    )
    
    # Assert batch_update returns expected response
    assert result == mock_response


def test_batch_update_authentication_failure():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    client.service = MagicMock()
    
    # Mock ensure_authenticated to return False
    client.ensure_authenticated = MagicMock(return_value=False)
    
    # Call batch_update method with test parameters
    with pytest.raises(APIError):
        client.batch_update("sheet_id", [{"updateCells": {"fields": "userEnteredValue"}}])


def test_batch_update_api_error():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    client.service = MagicMock()
    
    # Mock ensure_authenticated to return True
    client.ensure_authenticated = MagicMock(return_value=True)
    
    # Mock service.spreadsheets().batchUpdate().execute() to raise HttpError
    mock_resp = MagicMock()
    mock_resp.status = 400
    mock_error = HttpError(resp=mock_resp, content=b'{"error": "API error"}')
    
    # Need to configure the nested mocks
    mock_batch_update = MagicMock()
    mock_batch_update.execute.side_effect = mock_error
    mock_spreadsheets = MagicMock()
    mock_spreadsheets.batchUpdate.return_value = mock_batch_update
    client.service.spreadsheets.return_value = mock_spreadsheets
    
    # Call batch_update method with test parameters
    with pytest.raises(HttpError) as excinfo:
        client.batch_update("sheet_id", [{"updateCells": {"fields": "userEnteredValue"}}])
    
    # Assert APIError is raised with appropriate message
    assert isinstance(excinfo.value, HttpError)


def test_get_weekly_spending_data():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    
    # Mock read_sheet to return mock transaction data
    mock_transaction_data = [
        ["Store 1", "10.00", "2023-07-15", "Groceries"],
        ["Store 2", "20.00", "2023-07-16", "Dining Out"]
    ]
    client.read_sheet = MagicMock(return_value=mock_transaction_data)
    
    # Call get_weekly_spending_data method
    result = client.get_weekly_spending_data()
    
    # Assert read_sheet was called with correct parameters
    client.read_sheet.assert_called_with(
        client.weekly_spending_id,
        "Weekly Spending!A2:D"
    )
    
    # Assert get_weekly_spending_data returns expected data
    assert result == mock_transaction_data


def test_get_master_budget_data():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    
    # Mock read_sheet to return mock budget data
    mock_budget_data = [
        ["Groceries", "100.00"],
        ["Dining Out", "50.00"]
    ]
    client.read_sheet = MagicMock(return_value=mock_budget_data)
    
    # Call get_master_budget_data method
    result = client.get_master_budget_data()
    
    # Assert read_sheet was called with correct parameters
    client.read_sheet.assert_called_with(
        client.master_budget_id,
        "Master Budget!A2:B"
    )
    
    # Assert get_master_budget_data returns expected data
    assert result == mock_budget_data


def test_append_transactions():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    
    # Create test Transaction objects
    transaction1 = Transaction("Store 1", Decimal("10.00"), datetime.datetime.now(), "Groceries")
    transaction2 = Transaction("Store 2", Decimal("20.00"), datetime.datetime.now(), "Dining Out")
    transactions = [transaction1, transaction2]
    
    # Mock to_sheets_format for the transactions
    transaction1.to_sheets_format = MagicMock(return_value=["Store 1", "10.00", "2023-07-15 12:00:00", "Groceries"])
    transaction2.to_sheets_format = MagicMock(return_value=["Store 2", "20.00", "2023-07-16 12:00:00", "Dining Out"])
    
    # Mock append_rows to return success response
    mock_response = {
        "updates": {
            "updatedRange": "Weekly Spending!A1:D2",
            "updatedRows": 2,
            "updatedColumns": 4,
            "updatedCells": 8
        }
    }
    client.append_rows = MagicMock(return_value=mock_response)
    
    # Call append_transactions method with test transactions
    result = client.append_transactions(transactions)
    
    # Assert append_rows was called with correct parameters
    client.append_rows.assert_called_once()
    
    # Assert each Transaction.to_sheets_format was called
    transaction1.to_sheets_format.assert_called_once()
    transaction2.to_sheets_format.assert_called_once()
    
    # Assert append_transactions returns correct count
    assert result == 2


def test_update_transaction_categories():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    
    # Create test Transaction objects
    transaction1 = Transaction("Store 1", Decimal("10.00"), datetime.datetime.now())
    transaction2 = Transaction("Store 2", Decimal("20.00"), datetime.datetime.now())
    transactions = [transaction1, transaction2]
    
    # Create location_to_category_map dictionary
    location_to_category_map = {
        "Store 1": "Groceries",
        "Store 2": "Dining Out"
    }
    
    # Mock get_weekly_spending_data to return mock transaction data
    mock_transaction_data = [
        ["Store 1", "10.00", "2023-07-15", ""],
        ["Store 2", "20.00", "2023-07-16", ""]
    ]
    client.get_weekly_spending_data = MagicMock(return_value=mock_transaction_data)
    
    # Mock update_values to return success response
    mock_response = {
        "updatedRange": "Weekly Spending!D2:D3",
        "updatedRows": 2,
        "updatedColumns": 1,
        "updatedCells": 2
    }
    client.update_values = MagicMock(return_value=mock_response)
    
    # Call update_transaction_categories method with test parameters
    result = client.update_transaction_categories(transactions, location_to_category_map)
    
    # Assert get_weekly_spending_data was called
    client.get_weekly_spending_data.assert_called_once()
    
    # Assert update_values was called with correct parameters
    client.update_values.assert_called()
    
    # Assert update_transaction_categories returns correct count
    assert result == 2


def test_get_transactions():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    
    # Mock get_weekly_spending_data to return mock transaction data
    mock_transaction_data = [
        ["Store 1", "10.00", "2023-07-15", "Groceries"],
        ["Store 2", "20.00", "2023-07-16", "Dining Out"]
    ]
    client.get_weekly_spending_data = MagicMock(return_value=mock_transaction_data)
    
    # Mock create_transactions_from_sheet_data to return test Transaction objects
    test_transactions = [
        Transaction("Store 1", Decimal("10.00"), datetime.datetime(2023, 7, 15), "Groceries"),
        Transaction("Store 2", Decimal("20.00"), datetime.datetime(2023, 7, 16), "Dining Out")
    ]
    
    with patch('../../models.transaction.create_transactions_from_sheet_data') as mock_create:
        mock_create.return_value = test_transactions
        
        # Call get_transactions method
        result = client.get_transactions()
        
        # Assert get_weekly_spending_data was called
        client.get_weekly_spending_data.assert_called_once()
        
        # Assert create_transactions_from_sheet_data was called with correct data
        mock_create.assert_called_with(mock_transaction_data)
        
        # Assert get_transactions returns expected Transaction objects
        assert result == test_transactions


def test_get_budget():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    
    # Mock get_master_budget_data to return mock budget data
    mock_budget_data = [
        ["Groceries", "100.00"],
        ["Dining Out", "50.00"]
    ]
    client.get_master_budget_data = MagicMock(return_value=mock_budget_data)
    
    # Create test actual_spending dictionary
    actual_spending = {
        "Groceries": Decimal("75.00"),
        "Dining Out": Decimal("60.00")
    }
    
    # Mock create_budget_from_sheet_data to return test Budget object
    test_budget = MagicMock()
    
    with patch('../../models.budget.create_budget_from_sheet_data') as mock_create:
        mock_create.return_value = test_budget
        
        # Call get_budget method with actual_spending
        result = client.get_budget(actual_spending)
        
        # Assert get_master_budget_data was called
        client.get_master_budget_data.assert_called_once()
        
        # Assert create_budget_from_sheet_data was called with correct parameters
        mock_create.assert_called_with(mock_budget_data, actual_spending)
        
        # Assert get_budget returns expected Budget object
        assert result == test_budget


def test_retry_with_backoff_success_after_retry():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    
    # Create mock function that fails with HttpError twice then succeeds
    mock_func = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_error = HttpError(resp=mock_resp, content=b'{"error": "API error"}')
    mock_func.side_effect = [mock_error, mock_error, "success"]
    
    # Apply retry_with_backoff decorator to mock function
    from ../../utils.error_handlers import retry_with_backoff
    decorated_func = retry_with_backoff(exceptions=HttpError, max_retries=3)(mock_func)
    
    # Call decorated function
    result = decorated_func()
    
    # Assert function was called 3 times (2 failures + 1 success)
    assert mock_func.call_count == 3
    
    # Assert function returns expected result
    assert result == "success"


def test_retry_with_backoff_max_retries_exceeded():
    # Create GoogleSheetsClient with mock service
    client = GoogleSheetsClient()
    
    # Create mock function that always fails with HttpError
    mock_func = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_error = HttpError(resp=mock_resp, content=b'{"error": "API error"}')
    mock_func.side_effect = mock_error
    
    # Apply retry_with_backoff decorator to mock function with max_retries=3
    from ../../utils.error_handlers import retry_with_backoff
    decorated_func = retry_with_backoff(exceptions=HttpError, max_retries=3)(mock_func)
    
    # Call decorated function
    with pytest.raises(HttpError) as excinfo:
        decorated_func()
    
    # Assert function was called 4 times (initial + 3 retries)
    assert mock_func.call_count == 4
    
    # Assert APIError is raised after max retries
    assert isinstance(excinfo.value, HttpError)