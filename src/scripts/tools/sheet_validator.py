#!/usr/bin/env python3
"""
A comprehensive tool for validating Google Sheets data structure and content for the Budget Management Application.

This tool provides a command-line interface and programmatic API for validating Master Budget and 
Weekly Spending sheets, ensuring they conform to expected formats, contain valid data, and maintain
consistency between related sheets.
"""

import os
import sys
import argparse
import json
from typing import List, Dict, Optional, Tuple, Any, Union

import pandas as pd
from colorama import Fore, Style, init as colorama_init

# Internal imports
from ..config.logging_setup import get_logger
from ..config.script_settings import SCRIPT_SETTINGS, API_TEST_SETTINGS, DEBUG, VERBOSE
from .sheet_operations import (
    get_sheets_service, read_sheet, validate_sheet_structure, get_sheet_as_dataframe
)
from ...backend.utils.validate_budget import (
    validate_master_budget, validate_weekly_spending, validate_budget_consistency
)
from ...backend.models.category import Category, create_categories_from_sheet_data
from ...backend.models.budget import Budget, create_budget_from_sheet_data

# Initialize colorama for colored terminal output
colorama_init()

# Set up logger
logger = get_logger(__name__)

# Constants
MASTER_BUDGET_EXPECTED_HEADERS = ['Spending Category', 'Weekly Amount']
WEEKLY_SPENDING_EXPECTED_HEADERS = ['Transaction Location', 'Transaction Amount', 'Transaction Time', 'Corresponding Category']
DEFAULT_MASTER_BUDGET_RANGE = 'Master Budget!A:B'
DEFAULT_WEEKLY_SPENDING_RANGE = 'Weekly Spending!A:D'

# Validation rules for each sheet type
VALIDATION_RULES = {
    "master_budget": {
        "category_name": {
            "required": True,
            "min_length": 2,
            "max_length": 50
        },
        "weekly_amount": {
            "required": True,
            "min_value": "0.00",
            "max_value": "10000.00"
        }
    },
    "weekly_spending": {
        "transaction_location": {
            "required": True,
            "min_length": 2,
            "max_length": 100
        },
        "transaction_amount": {
            "required": True,
            "min_value": "0.01",
            "max_value": "10000.00"
        },
        "transaction_time": {
            "required": True,
            "format": "datetime"
        },
        "corresponding_category": {
            "required": False
        }
    }
}


def validate_sheet_data(df: pd.DataFrame, rules: dict) -> Tuple[bool, List[str]]:
    """
    Validates sheet data against specified validation rules
    
    Args:
        df: DataFrame containing sheet data
        rules: Dictionary of validation rules for each column
        
    Returns:
        Validation result (success/failure) and list of validation errors
    """
    validation_errors = []
    
    # Validate each column according to its rules
    for column, column_rules in rules.items():
        if column not in df.columns:
            if column_rules.get('required', False):
                validation_errors.append(f"Required column '{column}' is missing")
            continue
        
        # Check required fields
        if column_rules.get('required', False):
            missing_values = df[df[column].isna() | (df[column] == '')]
            if not missing_values.empty:
                row_indexes = missing_values.index.tolist()
                validation_errors.append(f"Column '{column}' has missing values in rows: {row_indexes}")
        
        # Validate string length
        if 'min_length' in column_rules or 'max_length' in column_rules:
            # Only validate non-empty strings
            non_empty_values = df[df[column].notna() & (df[column] != '')]
            
            if 'min_length' in column_rules:
                min_length = column_rules['min_length']
                too_short = non_empty_values[non_empty_values[column].astype(str).str.len() < min_length]
                if not too_short.empty:
                    row_indexes = too_short.index.tolist()
                    validation_errors.append(
                        f"Column '{column}' has values shorter than {min_length} characters in rows: {row_indexes}"
                    )
            
            if 'max_length' in column_rules:
                max_length = column_rules['max_length']
                too_long = non_empty_values[non_empty_values[column].astype(str).str.len() > max_length]
                if not too_long.empty:
                    row_indexes = too_long.index.tolist()
                    validation_errors.append(
                        f"Column '{column}' has values longer than {max_length} characters in rows: {row_indexes}"
                    )
        
        # Validate numeric ranges
        if 'min_value' in column_rules or 'max_value' in column_rules:
            # Only validate non-empty values
            non_empty_values = df[df[column].notna() & (df[column] != '')]
            
            # Convert to numeric, coercing errors to NaN
            numeric_values = pd.to_numeric(non_empty_values[column], errors='coerce')
            invalid_numeric = non_empty_values[numeric_values.isna()]
            if not invalid_numeric.empty:
                row_indexes = invalid_numeric.index.tolist()
                validation_errors.append(
                    f"Column '{column}' has non-numeric values in rows: {row_indexes}"
                )
            
            # Check valid numeric values against min/max
            valid_numeric = non_empty_values[~numeric_values.isna()]
            
            if 'min_value' in column_rules:
                min_value = float(column_rules['min_value'])
                too_small = valid_numeric[numeric_values < min_value]
                if not too_small.empty:
                    row_indexes = too_small.index.tolist()
                    validation_errors.append(
                        f"Column '{column}' has values less than {min_value} in rows: {row_indexes}"
                    )
            
            if 'max_value' in column_rules:
                max_value = float(column_rules['max_value'])
                too_large = valid_numeric[numeric_values > max_value]
                if not too_large.empty:
                    row_indexes = too_large.index.tolist()
                    validation_errors.append(
                        f"Column '{column}' has values greater than {max_value} in rows: {row_indexes}"
                    )
        
        # Validate date/time format
        if column_rules.get('format') == 'datetime':
            # Try to convert to datetime, with errors coerced to NaN
            datetime_values = pd.to_datetime(df[column], errors='coerce')
            invalid_dates = df[datetime_values.isna() & df[column].notna()]
            if not invalid_dates.empty:
                row_indexes = invalid_dates.index.tolist()
                validation_errors.append(
                    f"Column '{column}' has invalid date/time format in rows: {row_indexes}"
                )
    
    # Return validation result (True if no errors, False otherwise) and list of errors
    return len(validation_errors) == 0, validation_errors


def validate_master_budget_sheet(
    spreadsheet_id: str, 
    range_name: str = DEFAULT_MASTER_BUDGET_RANGE, 
    service = None
) -> Dict[str, Any]:
    """
    Validates the Master Budget sheet structure and content
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        range_name: Range to validate (defaults to DEFAULT_MASTER_BUDGET_RANGE)
        service: Google Sheets API service (will be created if None)
        
    Returns:
        Validation results with status and detailed errors
    """
    # Get Google Sheets service if not provided
    if service is None:
        service = get_sheets_service()
    
    # Initialize validation results
    validation_results = {
        "status": "pending",
        "sheet_name": "Master Budget",
        "validation_type": "structure_and_content",
        "errors": [],
        "warnings": []
    }
    
    try:
        # Get sheet data as DataFrame
        df = get_sheet_as_dataframe(spreadsheet_id, range_name, service)
        
        if df.empty:
            validation_results["status"] = "failed"
            validation_results["errors"].append("Master Budget sheet is empty")
            return validation_results
        
        # Rename columns to match validation rules
        if len(df.columns) >= 2:
            df.columns = ['category_name', 'weekly_amount'] + list(df.columns[2:])
        
        # Validate sheet structure (check for required columns)
        structure_valid = validate_sheet_structure(
            spreadsheet_id, 
            range_name, 
            MASTER_BUDGET_EXPECTED_HEADERS, 
            service
        )
        
        if not structure_valid:
            validation_results["status"] = "failed"
            validation_results["errors"].append(
                f"Master Budget sheet does not have the expected headers: {MASTER_BUDGET_EXPECTED_HEADERS}"
            )
            return validation_results
        
        # Validate data content using validation rules
        data_valid, data_errors = validate_sheet_data(df, VALIDATION_RULES["master_budget"])
        
        if not data_valid:
            validation_results["status"] = "failed"
            validation_results["errors"].extend(data_errors)
        
        # Check for duplicate category names
        duplicate_categories = df[df['category_name'].duplicated()]['category_name'].tolist()
        if duplicate_categories:
            validation_results["status"] = "failed"
            validation_results["errors"].append(
                f"Duplicate category names found: {duplicate_categories}"
            )
        
        # Verify all amounts are valid decimal values
        try:
            # Additional validation for weekly amounts
            df['weekly_amount'] = pd.to_numeric(df['weekly_amount'], errors='raise')
        except Exception as e:
            validation_results["status"] = "failed"
            validation_results["errors"].append(
                f"Error converting weekly amounts to numeric values: {str(e)}"
            )
        
        # Try to create Category objects to validate model constraints
        try:
            sheet_data = read_sheet(spreadsheet_id, range_name, service)
            categories = create_categories_from_sheet_data(sheet_data[1:])  # Skip header row
            if not categories:
                validation_results["status"] = "failed"
                validation_results["errors"].append("No valid categories could be created from sheet data")
        except Exception as e:
            validation_results["status"] = "failed"
            validation_results["errors"].append(f"Error creating category objects: {str(e)}")
        
        # Set status to success if no errors were found
        if validation_results["status"] == "pending":
            validation_results["status"] = "success"
        
        return validation_results
        
    except Exception as e:
        validation_results["status"] = "error"
        validation_results["errors"].append(f"Error validating Master Budget sheet: {str(e)}")
        logger.error(f"Error validating Master Budget sheet: {str(e)}", exc_info=True)
        return validation_results


def validate_weekly_spending_sheet(
    spreadsheet_id: str, 
    range_name: str = DEFAULT_WEEKLY_SPENDING_RANGE, 
    valid_categories: List[str] = None,
    service = None
) -> Dict[str, Any]:
    """
    Validates the Weekly Spending sheet structure and content
    
    Args:
        spreadsheet_id: ID of the spreadsheet
        range_name: Range to validate (defaults to DEFAULT_WEEKLY_SPENDING_RANGE)
        valid_categories: List of valid category names from Master Budget
        service: Google Sheets API service (will be created if None)
        
    Returns:
        Validation results with status and detailed errors
    """
    # Get Google Sheets service if not provided
    if service is None:
        service = get_sheets_service()
    
    # Initialize validation results
    validation_results = {
        "status": "pending",
        "sheet_name": "Weekly Spending",
        "validation_type": "structure_and_content",
        "errors": [],
        "warnings": []
    }
    
    try:
        # Get sheet data as DataFrame
        df = get_sheet_as_dataframe(spreadsheet_id, range_name, service)
        
        if df.empty:
            # Empty sheet is not necessarily an error for Weekly Spending
            validation_results["status"] = "success"
            validation_results["warnings"].append("Weekly Spending sheet is empty")
            return validation_results
        
        # Rename columns to match validation rules
        if len(df.columns) >= 4:
            df.columns = [
                'transaction_location', 
                'transaction_amount', 
                'transaction_time', 
                'corresponding_category'
            ] + list(df.columns[4:])
        
        # Validate sheet structure (check for required columns)
        structure_valid = validate_sheet_structure(
            spreadsheet_id, 
            range_name, 
            WEEKLY_SPENDING_EXPECTED_HEADERS, 
            service
        )
        
        if not structure_valid:
            validation_results["status"] = "failed"
            validation_results["errors"].append(
                f"Weekly Spending sheet does not have the expected headers: {WEEKLY_SPENDING_EXPECTED_HEADERS}"
            )
            return validation_results
        
        # Validate data content using validation rules
        data_valid, data_errors = validate_sheet_data(df, VALIDATION_RULES["weekly_spending"])
        
        if not data_valid:
            validation_results["status"] = "failed"
            validation_results["errors"].extend(data_errors)
        
        # If valid_categories provided, verify categories exist in the list
        if valid_categories and 'corresponding_category' in df.columns:
            # Filter out empty categories and check if any are invalid
            categories = df['corresponding_category'].dropna().unique().tolist()
            invalid_categories = [c for c in categories if c and c not in valid_categories]
            
            if invalid_categories:
                validation_results["status"] = "failed"
                validation_results["errors"].append(
                    f"Invalid categories found: {invalid_categories}"
                )
        
        # Verify transaction amounts are valid decimal values
        try:
            # Additional validation for transaction amounts
            df['transaction_amount'] = pd.to_numeric(df['transaction_amount'], errors='raise')
        except Exception as e:
            validation_results["status"] = "failed"
            validation_results["errors"].append(
                f"Error converting transaction amounts to numeric values: {str(e)}"
            )
        
        # Verify transaction timestamps are in valid format
        try:
            # Additional validation for timestamps
            df['transaction_time'] = pd.to_datetime(df['transaction_time'], errors='raise')
        except Exception as e:
            validation_results["status"] = "failed"
            validation_results["errors"].append(
                f"Error converting transaction times to datetime: {str(e)}"
            )
        
        # Set status to success if no errors were found
        if validation_results["status"] == "pending":
            validation_results["status"] = "success"
        
        return validation_results
        
    except Exception as e:
        validation_results["status"] = "error"
        validation_results["errors"].append(f"Error validating Weekly Spending sheet: {str(e)}")
        logger.error(f"Error validating Weekly Spending sheet: {str(e)}", exc_info=True)
        return validation_results


def validate_budget_sheets(
    master_budget_id: str, 
    master_budget_range: str = DEFAULT_MASTER_BUDGET_RANGE,
    weekly_spending_id: str = None, 
    weekly_spending_range: str = DEFAULT_WEEKLY_SPENDING_RANGE,
    service = None
) -> Dict[str, Any]:
    """
    Validates both Master Budget and Weekly Spending sheets and their consistency
    
    Args:
        master_budget_id: ID of the Master Budget spreadsheet
        master_budget_range: Range for Master Budget data
        weekly_spending_id: ID of the Weekly Spending spreadsheet
        weekly_spending_range: Range for Weekly Spending data
        service: Google Sheets API service (will be created if None)
        
    Returns:
        Comprehensive validation results for both sheets
    """
    # Get Google Sheets service if not provided
    if service is None:
        service = get_sheets_service()
    
    # Initialize combined validation results
    validation_results = {
        "status": "pending",
        "validation_type": "comprehensive",
        "master_budget": None,
        "weekly_spending": None,
        "consistency": {
            "status": "pending",
            "errors": [],
            "warnings": []
        },
        "timestamp": pd.Timestamp.now().isoformat()
    }
    
    # Validate Master Budget sheet
    master_budget_results = validate_master_budget_sheet(
        master_budget_id, 
        master_budget_range, 
        service
    )
    validation_results["master_budget"] = master_budget_results
    
    # Extract valid categories if Master Budget validation was successful
    valid_categories = []
    if master_budget_results["status"] == "success":
        try:
            # Read Master Budget data to extract categories
            master_budget_data = read_sheet(master_budget_id, master_budget_range, service)
            # Skip header row and extract category names
            valid_categories = [row[0] for row in master_budget_data[1:] if row and len(row) > 0]
        except Exception as e:
            validation_results["consistency"]["status"] = "error"
            validation_results["consistency"]["errors"].append(
                f"Error extracting categories from Master Budget: {str(e)}"
            )
    
    # Only validate Weekly Spending if ID is provided
    if weekly_spending_id:
        # Validate Weekly Spending sheet with valid categories
        weekly_spending_results = validate_weekly_spending_sheet(
            weekly_spending_id, 
            weekly_spending_range, 
            valid_categories, 
            service
        )
        validation_results["weekly_spending"] = weekly_spending_results
        
        # Check consistency between sheets
        if (master_budget_results["status"] == "success" and 
            weekly_spending_results["status"] == "success"):
            # Both sheets are valid, check for consistency issues
            try:
                # Use the backend utility for consistency validation
                is_consistent, consistency_errors = validate_budget_consistency(
                    master_budget_id,
                    master_budget_range,
                    weekly_spending_id,
                    weekly_spending_range,
                    service
                )
                
                if is_consistent:
                    validation_results["consistency"]["status"] = "success"
                else:
                    validation_results["consistency"]["status"] = "failed"
                    validation_results["consistency"]["errors"].extend(consistency_errors)
            except Exception as e:
                validation_results["consistency"]["status"] = "error"
                validation_results["consistency"]["errors"].append(
                    f"Error checking consistency between sheets: {str(e)}"
                )
        else:
            # One or both sheets have validation errors
            validation_results["consistency"]["status"] = "skipped"
            validation_results["consistency"]["warnings"].append(
                "Consistency checks skipped due to validation errors in one or both sheets"
            )
    else:
        # No Weekly Spending ID provided
        validation_results["weekly_spending"] = None
        validation_results["consistency"]["status"] = "skipped"
        validation_results["consistency"]["warnings"].append(
            "Weekly Spending sheet not provided for validation"
        )
    
    # Determine overall status
    if (master_budget_results["status"] == "success" and 
        (weekly_spending_id is None or validation_results["weekly_spending"]["status"] == "success") and
        validation_results["consistency"]["status"] in ["success", "skipped"]):
        validation_results["status"] = "success"
    elif (master_budget_results["status"] == "error" or 
          (weekly_spending_id and validation_results["weekly_spending"]["status"] == "error") or
          validation_results["consistency"]["status"] == "error"):
        validation_results["status"] = "error"
    else:
        validation_results["status"] = "failed"
    
    return validation_results


def generate_validation_report(validation_results: Dict[str, Any], format: str = "text") -> str:
    """
    Generates a detailed validation report in specified format
    
    Args:
        validation_results: Validation results dictionary
        format: Output format (json, text, html, markdown)
        
    Returns:
        Formatted validation report
    """
    # Extract key information
    status = validation_results.get("status", "unknown")
    
    # Gather all errors and warnings
    all_errors = []
    all_warnings = []
    
    # Process Master Budget results
    master_budget = validation_results.get("master_budget", {})
    if master_budget:
        master_status = master_budget.get("status", "unknown")
        all_errors.extend([f"Master Budget: {err}" for err in master_budget.get("errors", [])])
        all_warnings.extend([f"Master Budget: {warn}" for warn in master_budget.get("warnings", [])])
    
    # Process Weekly Spending results
    weekly_spending = validation_results.get("weekly_spending", {})
    if weekly_spending:
        weekly_status = weekly_spending.get("status", "unknown")
        all_errors.extend([f"Weekly Spending: {err}" for err in weekly_spending.get("errors", [])])
        all_warnings.extend([f"Weekly Spending: {warn}" for warn in weekly_spending.get("warnings", [])])
    
    # Process consistency results
    consistency = validation_results.get("consistency", {})
    if consistency:
        consistency_status = consistency.get("status", "unknown")
        all_errors.extend([f"Consistency: {err}" for err in consistency.get("errors", [])])
        all_warnings.extend([f"Consistency: {warn}" for warn in consistency.get("warnings", [])])
    
    # Format the report based on specified format
    if format.lower() == "json":
        # Return the results as a JSON string
        return json.dumps(validation_results, indent=2)
    
    elif format.lower() == "text":
        # Create a human-readable text report
        report = []
        report.append("=" * 80)
        report.append(f"BUDGET SHEET VALIDATION REPORT")
        report.append("=" * 80)
        report.append("")
        report.append(f"Overall Status: {status.upper()}")
        report.append("")
        
        # Master Budget section
        if master_budget:
            report.append("-" * 40)
            report.append(f"Master Budget Status: {master_status.upper()}")
            report.append("-" * 40)
            if master_budget.get("errors", []):
                report.append("Errors:")
                for i, err in enumerate(master_budget.get("errors", []), 1):
                    report.append(f"  {i}. {err}")
            if master_budget.get("warnings", []):
                report.append("Warnings:")
                for i, warn in enumerate(master_budget.get("warnings", []), 1):
                    report.append(f"  {i}. {warn}")
            if not master_budget.get("errors", []) and not master_budget.get("warnings", []):
                report.append("No issues found.")
            report.append("")
        
        # Weekly Spending section
        if weekly_spending:
            report.append("-" * 40)
            report.append(f"Weekly Spending Status: {weekly_status.upper()}")
            report.append("-" * 40)
            if weekly_spending.get("errors", []):
                report.append("Errors:")
                for i, err in enumerate(weekly_spending.get("errors", []), 1):
                    report.append(f"  {i}. {err}")
            if weekly_spending.get("warnings", []):
                report.append("Warnings:")
                for i, warn in enumerate(weekly_spending.get("warnings", []), 1):
                    report.append(f"  {i}. {warn}")
            if not weekly_spending.get("errors", []) and not weekly_spending.get("warnings", []):
                report.append("No issues found.")
            report.append("")
        
        # Consistency section
        if consistency:
            report.append("-" * 40)
            report.append(f"Consistency Status: {consistency_status.upper()}")
            report.append("-" * 40)
            if consistency.get("errors", []):
                report.append("Errors:")
                for i, err in enumerate(consistency.get("errors", []), 1):
                    report.append(f"  {i}. {err}")
            if consistency.get("warnings", []):
                report.append("Warnings:")
                for i, warn in enumerate(consistency.get("warnings", []), 1):
                    report.append(f"  {i}. {warn}")
            if not consistency.get("errors", []) and not consistency.get("warnings", []):
                report.append("No issues found.")
        
        report.append("")
        report.append("=" * 80)
        report.append(f"End of Report - Generated at {validation_results.get('timestamp', '')}")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    elif format.lower() == "html":
        # Create an HTML report
        html = []
        html.append("<!DOCTYPE html>")
        html.append("<html lang='en'>")
        html.append("<head>")
        html.append("  <meta charset='UTF-8'>")
        html.append("  <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
        html.append("  <title>Budget Sheet Validation Report</title>")
        html.append("  <style>")
        html.append("    body { font-family: Arial, sans-serif; margin: 20px; }")
        html.append("    h1, h2 { color: #333; }")
        html.append("    .success { color: green; }")
        html.append("    .failed { color: red; }")
        html.append("    .error { color: #ff5722; }")
        html.append("    .pending { color: #ff9800; }")
        html.append("    .skipped { color: #9e9e9e; }")
        html.append("    .unknown { color: #9e9e9e; }")
        html.append("    .section { border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; }")
        html.append("    .error-list { color: #d32f2f; }")
        html.append("    .warning-list { color: #ff9800; }")
        html.append("  </style>")
        html.append("</head>")
        html.append("<body>")
        html.append("  <h1>Budget Sheet Validation Report</h1>")
        html.append(f"  <p>Overall Status: <span class='{status.lower()}'>{status.upper()}</span></p>")
        
        # Master Budget section
        if master_budget:
            html.append("  <div class='section'>")
            html.append(f"    <h2>Master Budget Status: <span class='{master_status.lower()}'>{master_status.upper()}</span></h2>")
            if master_budget.get("errors", []):
                html.append("    <h3>Errors:</h3>")
                html.append("    <ul class='error-list'>")
                for err in master_budget.get("errors", []):
                    html.append(f"      <li>{err}</li>")
                html.append("    </ul>")
            if master_budget.get("warnings", []):
                html.append("    <h3>Warnings:</h3>")
                html.append("    <ul class='warning-list'>")
                for warn in master_budget.get("warnings", []):
                    html.append(f"      <li>{warn}</li>")
                html.append("    </ul>")
            if not master_budget.get("errors", []) and not master_budget.get("warnings", []):
                html.append("    <p>No issues found.</p>")
            html.append("  </div>")
        
        # Weekly Spending section
        if weekly_spending:
            html.append("  <div class='section'>")
            html.append(f"    <h2>Weekly Spending Status: <span class='{weekly_status.lower()}'>{weekly_status.upper()}</span></h2>")
            if weekly_spending.get("errors", []):
                html.append("    <h3>Errors:</h3>")
                html.append("    <ul class='error-list'>")
                for err in weekly_spending.get("errors", []):
                    html.append(f"      <li>{err}</li>")
                html.append("    </ul>")
            if weekly_spending.get("warnings", []):
                html.append("    <h3>Warnings:</h3>")
                html.append("    <ul class='warning-list'>")
                for warn in weekly_spending.get("warnings", []):
                    html.append(f"      <li>{warn}</li>")
                html.append("    </ul>")
            if not weekly_spending.get("errors", []) and not weekly_spending.get("warnings", []):
                html.append("    <p>No issues found.</p>")
            html.append("  </div>")
        
        # Consistency section
        if consistency:
            html.append("  <div class='section'>")
            html.append(f"    <h2>Consistency Status: <span class='{consistency_status.lower()}'>{consistency_status.upper()}</span></h2>")
            if consistency.get("errors", []):
                html.append("    <h3>Errors:</h3>")
                html.append("    <ul class='error-list'>")
                for err in consistency.get("errors", []):
                    html.append(f"      <li>{err}</li>")
                html.append("    </ul>")
            if consistency.get("warnings", []):
                html.append("    <h3>Warnings:</h3>")
                html.append("    <ul class='warning-list'>")
                for warn in consistency.get("warnings", []):
                    html.append(f"      <li>{warn}</li>")
                html.append("    </ul>")
            if not consistency.get("errors", []) and not consistency.get("warnings", []):
                html.append("    <p>No issues found.</p>")
            html.append("  </div>")
        
        html.append(f"  <p><small>Generated at {validation_results.get('timestamp', '')}</small></p>")
        html.append("</body>")
        html.append("</html>")
        
        return "\n".join(html)
    
    elif format.lower() == "markdown":
        # Create a markdown report
        md = []
        md.append("# Budget Sheet Validation Report")
        md.append("")
        md.append(f"**Overall Status**: {status.upper()}")
        md.append("")
        
        # Master Budget section
        if master_budget:
            md.append("## Master Budget")
            md.append(f"**Status**: {master_status.upper()}")
            md.append("")
            if master_budget.get("errors", []):
                md.append("### Errors:")
                for err in master_budget.get("errors", []):
                    md.append(f"- {err}")
                md.append("")
            if master_budget.get("warnings", []):
                md.append("### Warnings:")
                for warn in master_budget.get("warnings", []):
                    md.append(f"- {warn}")
                md.append("")
            if not master_budget.get("errors", []) and not master_budget.get("warnings", []):
                md.append("*No issues found.*")
                md.append("")
        
        # Weekly Spending section
        if weekly_spending:
            md.append("## Weekly Spending")
            md.append(f"**Status**: {weekly_status.upper()}")
            md.append("")
            if weekly_spending.get("errors", []):
                md.append("### Errors:")
                for err in weekly_spending.get("errors", []):
                    md.append(f"- {err}")
                md.append("")
            if weekly_spending.get("warnings", []):
                md.append("### Warnings:")
                for warn in weekly_spending.get("warnings", []):
                    md.append(f"- {warn}")
                md.append("")
            if not weekly_spending.get("errors", []) and not weekly_spending.get("warnings", []):
                md.append("*No issues found.*")
                md.append("")
        
        # Consistency section
        if consistency:
            md.append("## Consistency Checks")
            md.append(f"**Status**: {consistency_status.upper()}")
            md.append("")
            if consistency.get("errors", []):
                md.append("### Errors:")
                for err in consistency.get("errors", []):
                    md.append(f"- {err}")
                md.append("")
            if consistency.get("warnings", []):
                md.append("### Warnings:")
                for warn in consistency.get("warnings", []):
                    md.append(f"- {warn}")
                md.append("")
            if not consistency.get("errors", []) and not consistency.get("warnings", []):
                md.append("*No issues found.*")
                md.append("")
        
        md.append("---")
        md.append(f"*Generated at {validation_results.get('timestamp', '')}*")
        
        return "\n".join(md)
    
    else:
        # Default to simple text if format is not recognized
        return f"Validation Status: {status}\nErrors: {len(all_errors)}\nWarnings: {len(all_warnings)}"


def save_validation_report(report: str, output_file: str) -> bool:
    """
    Saves validation report to a file
    
    Args:
        report: Validation report string
        output_file: Path to save the report
        
    Returns:
        True if save was successful
    """
    try:
        # Determine file extension based on output file name
        file_ext = os.path.splitext(output_file)[1].lower()
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        
        # Write the report to the file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Validation report saved to {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving validation report: {str(e)}")
        return False


class SheetValidator:
    """
    Class for validating Google Sheets data for the Budget Management Application
    """
    
    def __init__(self, service=None, validation_rules=None, verbose=False):
        """
        Initialize the SheetValidator with optional service and rules
        
        Args:
            service: Google Sheets API service (will be created if None)
            validation_rules: Custom validation rules (uses default if None)
            verbose: Whether to log detailed information
        """
        self.service = service
        self.validation_rules = validation_rules or VALIDATION_RULES
        self.verbose = verbose
        logger.info("SheetValidator initialized")
    
    def ensure_service(self, credentials_path=None):
        """
        Ensures Google Sheets service is available
        
        Args:
            credentials_path: Path to the service account credentials
            
        Returns:
            Google Sheets service
        """
        if self.service is None:
            self.service = get_sheets_service(credentials_path)
        return self.service
    
    def validate_master_budget(self, spreadsheet_id, range_name=None):
        """
        Validates Master Budget sheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: Range to validate (uses default if None)
            
        Returns:
            Validation results
        """
        # Ensure service is available
        self.ensure_service()
        
        # Use default range if not specified
        if range_name is None:
            range_name = DEFAULT_MASTER_BUDGET_RANGE
        
        # Validate the sheet
        results = validate_master_budget_sheet(spreadsheet_id, range_name, self.service)
        
        if self.verbose:
            status = results.get("status", "unknown")
            logger.info(f"Master Budget validation status: {status}")
            if results.get("errors", []):
                for error in results.get("errors", []):
                    logger.warning(f"Master Budget error: {error}")
            if results.get("warnings", []):
                for warning in results.get("warnings", []):
                    logger.info(f"Master Budget warning: {warning}")
        
        return results
    
    def validate_weekly_spending(self, spreadsheet_id, range_name=None, valid_categories=None):
        """
        Validates Weekly Spending sheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: Range to validate (uses default if None)
            valid_categories: List of valid category names
            
        Returns:
            Validation results
        """
        # Ensure service is available
        self.ensure_service()
        
        # Use default range if not specified
        if range_name is None:
            range_name = DEFAULT_WEEKLY_SPENDING_RANGE
        
        # Validate the sheet
        results = validate_weekly_spending_sheet(
            spreadsheet_id, 
            range_name, 
            valid_categories, 
            self.service
        )
        
        if self.verbose:
            status = results.get("status", "unknown")
            logger.info(f"Weekly Spending validation status: {status}")
            if results.get("errors", []):
                for error in results.get("errors", []):
                    logger.warning(f"Weekly Spending error: {error}")
            if results.get("warnings", []):
                for warning in results.get("warnings", []):
                    logger.info(f"Weekly Spending warning: {warning}")
        
        return results
    
    def validate_budget_sheets(self, master_budget_id, master_budget_range=None, 
                              weekly_spending_id=None, weekly_spending_range=None):
        """
        Validates both budget sheets and their consistency
        
        Args:
            master_budget_id: ID of the Master Budget spreadsheet
            master_budget_range: Range for Master Budget data
            weekly_spending_id: ID of the Weekly Spending spreadsheet
            weekly_spending_range: Range for Weekly Spending data
            
        Returns:
            Comprehensive validation results
        """
        # Ensure service is available
        self.ensure_service()
        
        # Use default ranges if not specified
        if master_budget_range is None:
            master_budget_range = DEFAULT_MASTER_BUDGET_RANGE
        
        if weekly_spending_range is None:
            weekly_spending_range = DEFAULT_WEEKLY_SPENDING_RANGE
        
        # Validate both sheets
        results = validate_budget_sheets(
            master_budget_id,
            master_budget_range,
            weekly_spending_id,
            weekly_spending_range,
            self.service
        )
        
        if self.verbose:
            status = results.get("status", "unknown")
            logger.info(f"Budget sheets validation status: {status}")
        
        return results
    
    def generate_report(self, validation_results, format="text"):
        """
        Generates validation report in specified format
        
        Args:
            validation_results: Validation results dictionary
            format: Output format (json, text, html, markdown)
            
        Returns:
            Formatted validation report
        """
        return generate_validation_report(validation_results, format)
    
    def save_report(self, report, output_file):
        """
        Saves validation report to file
        
        Args:
            report: Validation report string
            output_file: Path to save the report
            
        Returns:
            True if save was successful
        """
        success = save_validation_report(report, output_file)
        if self.verbose:
            if success:
                logger.info(f"Report saved to {output_file}")
            else:
                logger.error(f"Failed to save report to {output_file}")
        return success


def parse_arguments():
    """
    Parses command-line arguments for the script
    
    Returns:
        Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Validate Google Sheets data structure and content for the Budget Management Application"
    )
    
    # Master Budget arguments
    parser.add_argument(
        "--master-budget-id",
        help="Google Sheets ID for the Master Budget spreadsheet",
        default=API_TEST_SETTINGS.get('SHEETS_TEST_SPREADSHEET_ID')
    )
    
    parser.add_argument(
        "--master-budget-range",
        help="Range for Master Budget data (default: 'Master Budget!A:B')",
        default=DEFAULT_MASTER_BUDGET_RANGE
    )
    
    # Weekly Spending arguments
    parser.add_argument(
        "--weekly-spending-id",
        help="Google Sheets ID for the Weekly Spending spreadsheet (if different from Master Budget)",
        default=None
    )
    
    parser.add_argument(
        "--weekly-spending-range",
        help="Range for Weekly Spending data (default: 'Weekly Spending!A:D')",
        default=DEFAULT_WEEKLY_SPENDING_RANGE
    )
    
    # Output format and file
    parser.add_argument(
        "--format",
        choices=["json", "text", "html", "markdown"],
        default="text",
        help="Output format for the validation report"
    )
    
    parser.add_argument(
        "--output",
        help="File to save the validation report (if not specified, prints to console)",
        default=None
    )
    
    # Credentials
    parser.add_argument(
        "--credentials",
        help="Path to Google Sheets API credentials file",
        default=None
    )
    
    # Verbose output
    parser.add_argument(
        "--verbose",
        help="Enable verbose output",
        action="store_true"
    )
    
    return parser.parse_args()


def main():
    """
    Main function to run the sheet validator tool
    
    Returns:
        Exit code (0 for success, 1 for validation failure, 2 for errors)
    """
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Set verbose mode based on arguments and script settings
        verbose = args.verbose or VERBOSE
        
        # Create validator with appropriate verbosity
        validator = SheetValidator(verbose=verbose)
        
        # Ensure we have the Google Sheets service
        try:
            validator.ensure_service(args.credentials)
        except Exception as e:
            logger.error(f"Failed to create Google Sheets service: {str(e)}")
            print(f"Error: Failed to create Google Sheets service. {str(e)}")
            return 2
        
        # If Weekly Spending ID not provided, use Master Budget ID
        weekly_spending_id = args.weekly_spending_id or args.master_budget_id
        
        # Validate the sheets
        validation_results = validator.validate_budget_sheets(
            args.master_budget_id,
            args.master_budget_range,
            weekly_spending_id,
            args.weekly_spending_range
        )
        
        # Generate the report
        report = validator.generate_report(validation_results, args.format)
        
        # Save or print the report
        if args.output:
            if validator.save_report(report, args.output):
                print(f"Validation report saved to {args.output}")
            else:
                print(f"Error: Failed to save validation report to {args.output}")
                return 2
        else:
            # Print to console with color for text format
            if args.format.lower() == "text":
                # Add color to the status in the output
                status = validation_results.get("status", "unknown")
                colored_report = report
                if status.lower() == "success":
                    status_colored = f"{Fore.GREEN}{status.upper()}{Style.RESET_ALL}"
                    colored_report = report.replace(f"Overall Status: {status.upper()}", 
                                                  f"Overall Status: {status_colored}")
                elif status.lower() in ["failed", "error"]:
                    status_colored = f"{Fore.RED}{status.upper()}{Style.RESET_ALL}"
                    colored_report = report.replace(f"Overall Status: {status.upper()}", 
                                                  f"Overall Status: {status_colored}")
                print(colored_report)
            else:
                print(report)
        
        # Return appropriate exit code
        status = validation_results.get("status", "unknown")
        if status == "success":
            return 0
        elif status == "error":
            return 2
        else:
            return 1
            
    except Exception as e:
        logger.error(f"Error in sheet validator: {str(e)}", exc_info=True)
        print(f"Error: {str(e)}")
        return 2


if __name__ == "__main__":
    sys.exit(main())