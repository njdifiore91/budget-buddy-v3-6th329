"""
date_utils.py - Date and time manipulation utilities for Budget Management Application

This module provides functions for handling date calculations, parsing, formatting,
and timezone conversions specifically for transaction data processing and budget analysis.
"""

import logging
from datetime import datetime, date, timedelta, timezone
import pytz  # pytz 2023.3+

from ..config.settings import APP_SETTINGS

# Set up logger
logger = logging.getLogger(__name__)

# Timezone constants
EST_TIMEZONE = pytz.timezone('US/Eastern')
UTC_TIMEZONE = pytz.UTC

# Date format constants
ISO_DATE_FORMAT = "%Y-%m-%d"
ISO_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
CAPITAL_ONE_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
SHEETS_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_transaction_date_range(days_lookback=None):
    """
    Calculate the start and end dates for transaction retrieval based on the configured lookback period.
    
    Args:
        days_lookback (int, optional): Number of days to look back. If None, uses the value from 
                                       APP_SETTINGS.TRANSACTION_DAYS_LOOKBACK or defaults to 7.
    
    Returns:
        tuple: (start_date, end_date) as ISO format strings (YYYY-MM-DD)
    """
    # Get current date in EST timezone
    current_date = datetime.now(timezone.utc).astimezone(EST_TIMEZONE).date()
    
    # Use configured lookback period or default to 7 days
    if days_lookback is None:
        days_lookback = APP_SETTINGS.get('TRANSACTION_DAYS_LOOKBACK', 7)
    
    # Calculate start date (current date - lookback period)
    start_date = current_date - timedelta(days=days_lookback)
    
    # Format dates as ISO strings
    start_date_str = start_date.strftime(ISO_DATE_FORMAT)
    end_date_str = current_date.strftime(ISO_DATE_FORMAT)
    
    logger.debug(f"Calculated transaction date range: {start_date_str} to {end_date_str}")
    
    return (start_date_str, end_date_str)


def parse_capital_one_date(date_string):
    """
    Parse a date string from Capital One API format to a datetime object in EST timezone.
    
    Args:
        date_string (str): Date string in Capital One API format (e.g., "2023-07-15T14:30:45.123Z")
    
    Returns:
        datetime: Datetime object in EST timezone
    
    Raises:
        ValueError: If the date string cannot be parsed
    """
    try:
        # Parse the date string
        dt = datetime.strptime(date_string, CAPITAL_ONE_DATE_FORMAT)
        
        # Capital One dates are in UTC, but might not have timezone info
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC_TIMEZONE)
        
        # Convert to EST timezone
        est_dt = dt.astimezone(EST_TIMEZONE)
        
        return est_dt
    
    except ValueError as e:
        logger.error(f"Error parsing Capital One date '{date_string}': {str(e)}")
        raise ValueError(f"Invalid Capital One date format: {date_string}") from e


def format_date_for_sheets(dt):
    """
    Format a datetime object for Google Sheets storage.
    
    Args:
        dt (datetime): Datetime object to format
    
    Returns:
        str: Formatted date string for Google Sheets
    """
    # Ensure datetime is in EST timezone
    est_dt = convert_to_est(dt)
    
    # Format using Sheets datetime format
    return est_dt.strftime(SHEETS_DATETIME_FORMAT)


def parse_sheets_date(date_string):
    """
    Parse a date string from Google Sheets format to a datetime object.
    
    Args:
        date_string (str): Date string in Google Sheets format (e.g., "2023-07-15 14:30:45")
    
    Returns:
        datetime: Datetime object in EST timezone
    
    Raises:
        ValueError: If the date string cannot be parsed
    """
    try:
        # Parse the date string (Sheets dates have no timezone info)
        dt = datetime.strptime(date_string, SHEETS_DATETIME_FORMAT)
        
        # Set timezone to EST
        est_dt = EST_TIMEZONE.localize(dt)
        
        return est_dt
    
    except ValueError as e:
        logger.error(f"Error parsing Sheets date '{date_string}': {str(e)}")
        raise ValueError(f"Invalid Sheets date format: {date_string}") from e


def get_current_week_start():
    """
    Get the start date (Sunday) of the current week in EST timezone.
    
    Returns:
        datetime: Datetime object for Sunday of current week at 00:00:00
    """
    # Get current date in EST timezone
    now = datetime.now(timezone.utc).astimezone(EST_TIMEZONE)
    
    # Calculate days since Sunday (weekday 6 is Sunday in Python)
    days_since_sunday = (now.weekday() + 1) % 7
    
    # Subtract days to get to Sunday
    sunday = now - timedelta(days=days_since_sunday)
    
    # Set time to midnight
    sunday = sunday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    return sunday


def get_current_week_end():
    """
    Get the end date (Saturday) of the current week in EST timezone.
    
    Returns:
        datetime: Datetime object for Saturday of current week at 23:59:59
    """
    # Get Sunday of current week
    sunday = get_current_week_start()
    
    # Add 6 days to get to Saturday
    saturday = sunday + timedelta(days=6)
    
    # Set time to end of day
    saturday = saturday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return saturday


def is_date_in_current_week(dt):
    """
    Check if a given date falls within the current week.
    
    Args:
        dt (datetime): Datetime object to check
    
    Returns:
        bool: True if date is in current week, False otherwise
    """
    # Ensure datetime is in EST timezone
    est_dt = convert_to_est(dt)
    
    # Get current week boundaries
    week_start = get_current_week_start()
    week_end = get_current_week_end()
    
    # Check if date is within current week
    return week_start <= est_dt <= week_end


def format_iso_date(dt):
    """
    Format a datetime object as an ISO format date string.
    
    Args:
        dt (datetime): Datetime object to format
    
    Returns:
        str: ISO formatted date string (YYYY-MM-DD)
    """
    return dt.strftime(ISO_DATE_FORMAT)


def format_iso_datetime(dt):
    """
    Format a datetime object as an ISO format datetime string with timezone.
    
    Args:
        dt (datetime): Datetime object to format
    
    Returns:
        str: ISO formatted datetime string
    """
    # Ensure datetime has timezone info
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TIMEZONE)
        logger.warning("Datetime object had no timezone info, assuming UTC")
    
    return dt.strftime(ISO_DATETIME_FORMAT)


def convert_to_est(dt):
    """
    Convert a datetime object to EST timezone.
    
    Args:
        dt (datetime): Datetime object to convert
    
    Returns:
        datetime: Datetime object in EST timezone
    """
    # Check if datetime has timezone info
    if dt.tzinfo is None:
        # If no timezone, assume UTC
        dt = dt.replace(tzinfo=UTC_TIMEZONE)
        logger.debug("Datetime object had no timezone info, assuming UTC")
    
    # Convert to EST timezone
    return dt.astimezone(EST_TIMEZONE)