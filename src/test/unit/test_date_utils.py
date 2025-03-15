"""
Unit tests for the date utility functions used in the Budget Management Application.
Tests date range calculations, parsing, formatting, and timezone conversions.
"""

import pytest
from datetime import datetime, date, timedelta, timezone
import pytz
from freezegun import freeze_time

from ...backend.utils.date_utils import (
    get_transaction_date_range, parse_capital_one_date, format_date_for_sheets,
    parse_sheets_date, get_current_week_start, get_current_week_end,
    is_date_in_current_week, format_iso_date, format_iso_datetime,
    convert_to_est, EST_TIMEZONE, UTC_TIMEZONE
)
from ...backend.config.settings import APP_SETTINGS
from ..utils.fixture_loader import load_fixture

# Test constants
TEST_DATE_ISO = "2023-07-23"
TEST_DATETIME_ISO = "2023-07-23T14:30:45+0000"
TEST_CAPITAL_ONE_DATE = "2023-07-23T14:30:45.123Z"
TEST_SHEETS_DATETIME = "2023-07-23 10:30:45"


@freeze_time("2023-07-23")
def test_get_transaction_date_range_default():
    """Test that get_transaction_date_range returns correct date range with default lookback period"""
    # Call get_transaction_date_range with default days_lookback
    start_date, end_date = get_transaction_date_range()
    
    # Assert that the returned start_date is 7 days before the current date
    expected_start_date = "2023-07-16"  # 7 days before 2023-07-23
    expected_end_date = "2023-07-23"    # Current date
    
    assert start_date == expected_start_date
    assert end_date == expected_end_date
    
    # Assert that both dates are in ISO format (YYYY-MM-DD)
    assert len(start_date) == 10
    assert start_date[4] == '-' and start_date[7] == '-'
    assert len(end_date) == 10
    assert end_date[4] == '-' and end_date[7] == '-'


@freeze_time("2023-07-23")
def test_get_transaction_date_range_custom():
    """Test that get_transaction_date_range returns correct date range with custom lookback period"""
    # Call get_transaction_date_range with days_lookback=14
    start_date, end_date = get_transaction_date_range(days_lookback=14)
    
    # Assert that the returned start_date is 14 days before the current date
    expected_start_date = "2023-07-09"  # 14 days before 2023-07-23
    expected_end_date = "2023-07-23"    # Current date
    
    assert start_date == expected_start_date
    assert end_date == expected_end_date
    
    # Assert that both dates are in ISO format (YYYY-MM-DD)
    assert len(start_date) == 10
    assert start_date[4] == '-' and start_date[7] == '-'
    assert len(end_date) == 10
    assert end_date[4] == '-' and end_date[7] == '-'


def test_parse_capital_one_date():
    """Test that parse_capital_one_date correctly parses Capital One API date format"""
    # Call parse_capital_one_date with TEST_CAPITAL_ONE_DATE
    result = parse_capital_one_date(TEST_CAPITAL_ONE_DATE)
    
    # Assert that the returned datetime has the correct year, month, day, hour, minute, second
    assert result.year == 2023
    assert result.month == 7
    assert result.day == 23
    
    # Assert that the returned datetime is in EST timezone
    assert result.tzinfo == EST_TIMEZONE
    
    # The time part needs to be adjusted for EST (UTC-4 or UTC-5 depending on DST)
    # Since TEST_CAPITAL_ONE_DATE is "2023-07-23T14:30:45.123Z" (UTC time)
    # and July is during DST in Eastern Time (UTC-4), the hour should be 10:30
    assert result.hour == 10  # 14 - 4 = 10 (during DST)
    assert result.minute == 30
    assert result.second == 45


def test_parse_capital_one_date_invalid():
    """Test that parse_capital_one_date handles invalid date formats gracefully"""
    # Call parse_capital_one_date with an invalid date string
    with pytest.raises(ValueError):
        parse_capital_one_date("invalid-date-format")


def test_format_date_for_sheets():
    """Test that format_date_for_sheets correctly formats datetime for Google Sheets"""
    # Create a datetime object with timezone info (UTC)
    dt = datetime(2023, 7, 23, 14, 30, 45, tzinfo=UTC_TIMEZONE)
    
    # Call format_date_for_sheets with the datetime object
    result = format_date_for_sheets(dt)
    
    # Assert that the returned string matches the expected Google Sheets format
    # Since the datetime is in UTC (2023-07-23 14:30:45)
    # and July is during DST in Eastern Time (UTC-4), the hour should be 10:30
    expected_format = "2023-07-23 10:30:45"
    assert result == expected_format
    
    # Assert that the timezone conversion to EST is correct by checking the time difference
    dt_est = dt.astimezone(EST_TIMEZONE)
    assert dt_est.hour == 10  # 14 - 4 = 10 (during DST)


def test_parse_sheets_date():
    """Test that parse_sheets_date correctly parses Google Sheets date format"""
    # Call parse_sheets_date with TEST_SHEETS_DATETIME
    result = parse_sheets_date(TEST_SHEETS_DATETIME)
    
    # Assert that the returned datetime has the correct year, month, day, hour, minute, second
    assert result.year == 2023
    assert result.month == 7
    assert result.day == 23
    assert result.hour == 10
    assert result.minute == 30
    assert result.second == 45
    
    # Assert that the returned datetime is in EST timezone
    assert result.tzinfo == EST_TIMEZONE


def test_parse_sheets_date_invalid():
    """Test that parse_sheets_date handles invalid date formats gracefully"""
    # Call parse_sheets_date with an invalid date string
    with pytest.raises(ValueError):
        parse_sheets_date("invalid-date-format")


@freeze_time("2023-07-23")  # Sunday
def test_get_current_week_start():
    """Test that get_current_week_start returns the correct Sunday date"""
    # Call get_current_week_start()
    result = get_current_week_start()
    
    # Assert that the returned date is Sunday (2023-07-23)
    assert result.year == 2023
    assert result.month == 7
    assert result.day == 23
    
    # Assert that the time is set to midnight (00:00:00)
    assert result.hour == 0
    assert result.minute == 0
    assert result.second == 0
    
    # Assert that the timezone is EST
    assert result.tzinfo == EST_TIMEZONE


@freeze_time("2023-07-26")  # Wednesday
def test_get_current_week_start_midweek():
    """Test that get_current_week_start returns the correct Sunday date when called midweek"""
    # Call get_current_week_start() on a Wednesday
    result = get_current_week_start()
    
    # Assert that the returned date is the previous Sunday (2023-07-23)
    assert result.year == 2023
    assert result.month == 7
    assert result.day == 23  # Sunday
    
    # Assert that the time is set to midnight (00:00:00)
    assert result.hour == 0
    assert result.minute == 0
    assert result.second == 0
    
    # Assert that the timezone is EST
    assert result.tzinfo == EST_TIMEZONE


@freeze_time("2023-07-23")  # Sunday
def test_get_current_week_end():
    """Test that get_current_week_end returns the correct Saturday date"""
    # Call get_current_week_end()
    result = get_current_week_end()
    
    # Assert that the returned date is Saturday (2023-07-29)
    assert result.year == 2023
    assert result.month == 7
    assert result.day == 29  # Saturday
    
    # Assert that the time is set to 23:59:59
    assert result.hour == 23
    assert result.minute == 59
    assert result.second == 59
    
    # Assert that the timezone is EST
    assert result.tzinfo == EST_TIMEZONE


@freeze_time("2023-07-23")  # Sunday
def test_is_date_in_current_week():
    """Test that is_date_in_current_week correctly identifies dates in the current week"""
    # Create datetime objects for Sunday, Wednesday, and Saturday of the current week
    sunday = datetime(2023, 7, 23, 12, 0, 0, tzinfo=EST_TIMEZONE)
    wednesday = datetime(2023, 7, 26, 12, 0, 0, tzinfo=EST_TIMEZONE)
    saturday = datetime(2023, 7, 29, 12, 0, 0, tzinfo=EST_TIMEZONE)
    
    # Create datetime objects for dates outside the current week
    prev_saturday = datetime(2023, 7, 22, 12, 0, 0, tzinfo=EST_TIMEZONE)
    next_sunday = datetime(2023, 7, 30, 12, 0, 0, tzinfo=EST_TIMEZONE)
    
    # Call is_date_in_current_week for each date
    # Assert that dates in the current week return True
    assert is_date_in_current_week(sunday) is True
    assert is_date_in_current_week(wednesday) is True
    assert is_date_in_current_week(saturday) is True
    
    # Assert that dates outside the current week return False
    assert is_date_in_current_week(prev_saturday) is False
    assert is_date_in_current_week(next_sunday) is False


def test_format_iso_date():
    """Test that format_iso_date correctly formats a datetime as ISO date"""
    # Create a datetime object
    dt = datetime(2023, 7, 23, 14, 30, 45, tzinfo=UTC_TIMEZONE)
    
    # Call format_iso_date with the datetime object
    result = format_iso_date(dt)
    
    # Assert that the returned string is in ISO date format (YYYY-MM-DD)
    expected_format = "2023-07-23"
    assert result == expected_format


def test_format_iso_datetime():
    """Test that format_iso_datetime correctly formats a datetime as ISO datetime with timezone"""
    # Create a datetime object with timezone info (UTC)
    dt = datetime(2023, 7, 23, 14, 30, 45, tzinfo=UTC_TIMEZONE)
    
    # Call format_iso_datetime with the datetime object
    result = format_iso_datetime(dt)
    
    # The format is based on ISO_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
    # For UTC timezone, this would be like "2023-07-23T14:30:45+0000"
    # The exact format might vary by Python version for the timezone part
    assert result.startswith("2023-07-23T14:30:45")
    
    # Check timezone indication (should have +0000 or equivalent for UTC)
    timezone_part = result[19:]  # Everything after the seconds
    assert timezone_part.startswith("+") or timezone_part.startswith("-")
    assert len(timezone_part) >= 5  # Should at least have +HHMM format


def test_convert_to_est():
    """Test that convert_to_est correctly converts datetimes to EST timezone"""
    # Create a datetime object in UTC timezone
    dt_utc = datetime(2023, 7, 23, 14, 30, 45, tzinfo=UTC_TIMEZONE)
    
    # Call convert_to_est with the datetime object
    result = convert_to_est(dt_utc)
    
    # Assert that the returned datetime is in EST timezone
    assert result.tzinfo == EST_TIMEZONE
    
    # Assert that the hour is adjusted correctly for EST timezone
    # Since July is during DST in Eastern Time (UTC-4), the hour should be 10:30
    assert result.hour == 10  # 14 - 4 = 10 (during DST)
    assert result.minute == 30
    assert result.second == 45


def test_convert_to_est_naive():
    """Test that convert_to_est correctly handles naive datetime objects"""
    # Create a naive datetime object (no timezone)
    dt_naive = datetime(2023, 7, 23, 14, 30, 45)
    
    # Call convert_to_est with the naive datetime object
    result = convert_to_est(dt_naive)
    
    # Assert that the returned datetime is in EST timezone
    assert result.tzinfo == EST_TIMEZONE
    
    # Assert that the datetime was interpreted as UTC and converted correctly
    # Since July is during DST in Eastern Time (UTC-4), the hour should be 10:30
    assert result.hour == 10  # 14 - 4 = 10 (during DST)
    assert result.minute == 30
    assert result.second == 45