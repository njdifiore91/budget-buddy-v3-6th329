"""
Budget Calculator - Utility tool for budget calculations and analysis

This script provides both a command-line interface and programmatic API for calculating
budget variances, analyzing spending patterns, and determining savings transfer amounts
based on budget data from Google Sheets.

Functions:
    calculate_budget_variance: Calculate variance between actual and budgeted amounts
    calculate_transfer_amount: Calculate amount to transfer to savings based on surplus
    project_future_spending: Project future spending based on current patterns
    generate_budget_summary: Generate a comprehensive budget summary with insights
    parse_arguments: Parse command-line arguments
    main: Main function to run the budget calculator

Classes:
    BudgetCalculator: Class for performing budget calculations and analysis

Usage:
    As a module:
        from scripts.tools.budget_calculator import BudgetCalculator
        calculator = BudgetCalculator()
        results = calculator.run_calculation('variance', master_budget_id, master_budget_range, 
                                             weekly_spending_id, weekly_spending_range)
    
    As a script:
        python budget_calculator.py variance --master-budget-id=SHEET_ID --weekly-spending-id=SHEET_ID
"""

import os
import sys
import argparse
import json
import decimal
from decimal import Decimal
import datetime
from typing import List, Dict, Optional, Tuple, Any, Union

# Third-party imports
import pandas as pd  # pandas 2.1.0+
import matplotlib.pyplot as plt  # matplotlib 3.7.0+
import numpy as np  # numpy 1.24.0+

# Internal imports
from ...config.logging_setup import get_logger
from ...config.script_settings import SCRIPT_SETTINGS, API_TEST_SETTINGS
from ...utils.sheet_operations import (
    get_sheets_service, 
    read_sheet, 
    get_sheet_as_dataframe, 
    write_dataframe_to_sheet
)
from ...backend.models.category import Category, create_categories_from_sheet_data
from ...backend.models.budget import Budget, create_budget_from_sheet_data

# Set up logger
logger = get_logger(__name__)

# Default values
DEFAULT_MASTER_BUDGET_RANGE = "Master Budget!A:B"
DEFAULT_WEEKLY_SPENDING_RANGE = "Weekly Spending!A:D"
DEFAULT_OUTPUT_FORMAT = "text"
CALCULATION_TYPES = ['variance', 'transfer', 'projection', 'summary']


def calculate_budget_variance(categories: List[Category], actual_spending: Dict[str, Decimal]) -> Dict[str, Dict[str, Decimal]]:
    """
    Calculates variance between budget and actual spending by category
    
    Args:
        categories: List of Category objects
        actual_spending: Dictionary mapping categories to actual spending amounts
        
    Returns:
        Dictionary with variance details by category
    """
    variance_results = {}
    
    # Calculate variance for each category
    for category in categories:
        category_name = category.name
        budget_amount = category.weekly_amount
        actual_amount = actual_spending.get(category_name, Decimal('0'))
        
        # Calculate variance (budget - actual)
        # Positive variance means under budget, negative means over budget
        variance = budget_amount - actual_amount
        
        # Calculate variance percentage
        if budget_amount > 0:
            variance_percentage = (variance / budget_amount) * 100
        else:
            variance_percentage = Decimal('0')
        
        # Store results for this category
        variance_results[category_name] = {
            'budget_amount': budget_amount,
            'actual_amount': actual_amount,
            'variance_amount': variance,
            'variance_percentage': variance_percentage
        }
    
    logger.debug(f"Calculated variance for {len(categories)} categories")
    return variance_results


def calculate_transfer_amount(variance_results: Dict[str, Dict[str, Decimal]]) -> Dict[str, Decimal]:
    """
    Calculates amount to transfer to savings based on budget surplus
    
    Args:
        variance_results: Dictionary with variance details by category
        
    Returns:
        Dictionary with transfer amount and related values
    """
    # Calculate total budget and total spent
    total_budget = sum(cat_data['budget_amount'] for cat_data in variance_results.values())
    total_spent = sum(cat_data['actual_amount'] for cat_data in variance_results.values())
    
    # Calculate total variance
    total_variance = total_budget - total_spent
    
    # Determine if there is a surplus
    is_surplus = total_variance > 0
    
    # Calculate transfer amount
    if is_surplus:
        transfer_amount = total_variance
    else:
        transfer_amount = Decimal('0')
    
    logger.debug(f"Calculated transfer amount: {transfer_amount}")
    
    # Return transfer details
    return {
        'total_budget': total_budget,
        'total_spent': total_spent,
        'total_variance': total_variance,
        'transfer_amount': transfer_amount,
        'is_surplus': is_surplus
    }


def project_future_spending(variance_results: Dict[str, Dict[str, Decimal]], weeks_ahead: int) -> Dict[str, Dict[str, Decimal]]:
    """
    Projects future spending based on current spending patterns
    
    Args:
        variance_results: Dictionary with variance details by category
        weeks_ahead: Number of weeks to project into the future
        
    Returns:
        Dictionary with projected spending by category
    """
    projection_results = {}
    
    # Calculate spending rate for each category
    for category, data in variance_results.items():
        budget_amount = data['budget_amount']
        actual_amount = data['actual_amount']
        
        # Calculate spending rate as a percentage of budget
        if budget_amount > 0:
            spending_rate = actual_amount / budget_amount
        else:
            spending_rate = Decimal('0')
        
        # Project future spending
        projected_spending = budget_amount * spending_rate * Decimal(str(weeks_ahead))
        projected_budget = budget_amount * Decimal(str(weeks_ahead))
        projected_variance = projected_budget - projected_spending
        
        # Store projection results
        projection_results[category] = {
            'weekly_budget': budget_amount,
            'spending_rate': spending_rate,
            'projected_spending': projected_spending,
            'projected_budget': projected_budget,
            'projected_variance': projected_variance
        }
    
    # Calculate projected totals
    projected_total_spent = sum(data['projected_spending'] for data in projection_results.values())
    projected_total_budget = sum(data['projected_budget'] for data in projection_results.values())
    projected_total_variance = projected_total_budget - projected_total_spent
    
    # Add totals to projection results
    projection_results['__totals__'] = {
        'projected_spending': projected_total_spent,
        'projected_budget': projected_total_budget,
        'projected_variance': projected_total_variance,
        'weeks_ahead': weeks_ahead
    }
    
    logger.debug(f"Projected spending for {weeks_ahead} weeks ahead")
    return projection_results


def generate_budget_summary(variance_results: Dict[str, Dict[str, Decimal]], 
                           transfer_results: Dict[str, Decimal],
                           projection_results: Optional[Dict[str, Dict[str, Decimal]]] = None) -> Dict[str, Any]:
    """
    Generates a comprehensive budget summary with variance and projection data
    
    Args:
        variance_results: Dictionary with variance details by category
        transfer_results: Dictionary with transfer amount and related values
        projection_results: Optional dictionary with projected spending by category
        
    Returns:
        Comprehensive budget summary
    """
    summary = {
        'budget_status': {},
        'categories': {},
        'insights': [],
        'transfer': {},
        'projection': {}
    }
    
    # Add budget status information
    summary['budget_status'] = {
        'total_budget': transfer_results['total_budget'],
        'total_spent': transfer_results['total_spent'],
        'total_variance': transfer_results['total_variance'],
        'is_surplus': transfer_results['is_surplus'],
        'budget_used_percentage': (transfer_results['total_spent'] / transfer_results['total_budget'] * 100) if transfer_results['total_budget'] > 0 else Decimal('0')
    }
    
    # Add transfer information
    summary['transfer'] = {
        'transfer_amount': transfer_results['transfer_amount'],
        'is_surplus': transfer_results['is_surplus']
    }
    
    # Add category details
    for category, data in variance_results.items():
        summary['categories'][category] = {
            'budget_amount': data['budget_amount'],
            'actual_amount': data['actual_amount'],
            'variance_amount': data['variance_amount'],
            'variance_percentage': data['variance_percentage'],
            'is_over_budget': data['variance_amount'] < 0,
            'usage_percentage': (data['actual_amount'] / data['budget_amount'] * 100) if data['budget_amount'] > 0 else Decimal('0')
        }
    
    # Add projection information if available
    if projection_results:
        summary['projection'] = {
            'weeks_ahead': projection_results['__totals__']['weeks_ahead'],
            'projected_spending': projection_results['__totals__']['projected_spending'],
            'projected_budget': projection_results['__totals__']['projected_budget'],
            'projected_variance': projection_results['__totals__']['projected_variance'],
            'categories': {}
        }
        
        for category, data in projection_results.items():
            if category != '__totals__':
                summary['projection']['categories'][category] = {
                    'projected_spending': data['projected_spending'],
                    'projected_budget': data['projected_budget'],
                    'projected_variance': data['projected_variance'],
                    'spending_rate': data['spending_rate']
                }
    
    # Generate insights
    insights = []
    
    # Overall budget status insight
    if summary['budget_status']['is_surplus']:
        insights.append(f"Overall: You are under budget by {summary['budget_status']['total_variance']:.2f}.")
    else:
        insights.append(f"Overall: You are over budget by {abs(summary['budget_status']['total_variance']):.2f}.")
    
    # Find categories with significant overspending
    over_budget_categories = [
        (cat, data) for cat, data in summary['categories'].items()
        if data['is_over_budget'] and data['budget_amount'] > 0
    ]
    
    if over_budget_categories:
        # Sort by variance amount (most overspent first)
        over_budget_categories.sort(key=lambda x: x[1]['variance_amount'])
        top_overspent = over_budget_categories[:3]
        
        overspent_insight = "Categories most over budget: "
        overspent_insight += ", ".join(
            f"{cat} ({abs(data['variance_amount']):.2f}, {abs(data['variance_percentage']):.1f}%)"
            for cat, data in top_overspent
        )
        insights.append(overspent_insight)
    
    # Find categories with significant underspending
    under_budget_categories = [
        (cat, data) for cat, data in summary['categories'].items()
        if not data['is_over_budget'] and data['budget_amount'] > 0
    ]
    
    if under_budget_categories:
        # Sort by variance amount (most underspent first)
        under_budget_categories.sort(key=lambda x: -x[1]['variance_amount'])
        top_underspent = under_budget_categories[:3]
        
        underspent_insight = "Categories most under budget: "
        underspent_insight += ", ".join(
            f"{cat} ({data['variance_amount']:.2f}, {data['variance_percentage']:.1f}%)"
            for cat, data in top_underspent
        )
        insights.append(underspent_insight)
    
    # Add transfer insight
    if summary['transfer']['transfer_amount'] > 0:
        insights.append(f"Savings: {summary['transfer']['transfer_amount']:.2f} available to transfer to savings.")
    
    # Add projection insight if available
    if projection_results:
        weeks = summary['projection']['weeks_ahead']
        projected_variance = summary['projection']['projected_variance']
        
        if projected_variance >= 0:
            insights.append(f"Projection: At current rates, you will be under budget by {projected_variance:.2f} in {weeks} weeks.")
        else:
            insights.append(f"Projection: At current rates, you will be over budget by {abs(projected_variance):.2f} in {weeks} weeks.")
    
    summary['insights'] = insights
    
    logger.debug("Generated comprehensive budget summary")
    return summary


def format_calculation_results(results: Dict[str, Any], format: str) -> str:
    """
    Formats calculation results into specified output format
    
    Args:
        results: Calculation results to format
        format: Output format (json, text, html, markdown, csv)
        
    Returns:
        Formatted calculation results
    """
    if format == 'json':
        # Need to handle Decimal objects for JSON serialization
        def decimal_default(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            raise TypeError
        
        return json.dumps(results, indent=2, default=decimal_default)
    
    elif format == 'text':
        # Create a text report
        report = []
        
        # Handle different result types
        if 'transfer_amount' in results:
            # Transfer results
            report.append("Budget Transfer Summary")
            report.append("=====================")
            report.append(f"Total Budget: ${results['total_budget']:.2f}")
            report.append(f"Total Spent: ${results['total_spent']:.2f}")
            report.append(f"Total Variance: ${results['total_variance']:.2f}")
            report.append(f"Transfer Amount: ${results['transfer_amount']:.2f}")
            report.append(f"Budget Status: {'Surplus' if results['is_surplus'] else 'Deficit'}")
        
        elif 'budget_status' in results:
            # Summary results
            report.append("Budget Summary")
            report.append("=============")
            
            # Budget status
            status = results['budget_status']
            report.append(f"Total Budget: ${status['total_budget']:.2f}")
            report.append(f"Total Spent: ${status['total_spent']:.2f}")
            report.append(f"Total Variance: ${status['total_variance']:.2f}")
            report.append(f"Budget Status: {'Surplus' if status['is_surplus'] else 'Deficit'}")
            report.append(f"Budget Used: {status['budget_used_percentage']:.1f}%")
            report.append("")
            
            # Insights
            report.append("Insights:")
            for insight in results['insights']:
                report.append(f"- {insight}")
            report.append("")
            
            # Categories
            report.append("Category Details:")
            for category, data in results['categories'].items():
                variance_sign = "+" if data['variance_amount'] >= 0 else ""
                report.append(f"{category}:")
                report.append(f"  Budget: ${data['budget_amount']:.2f}")
                report.append(f"  Spent: ${data['actual_amount']:.2f}")
                report.append(f"  Variance: {variance_sign}${data['variance_amount']:.2f} ({data['variance_percentage']:.1f}%)")
                report.append(f"  Status: {'Under Budget' if not data['is_over_budget'] else 'Over Budget'}")
                report.append("")
            
            # Transfer info
            if results['transfer']['transfer_amount'] > 0:
                report.append(f"Transfer to Savings: ${results['transfer']['transfer_amount']:.2f}")
                report.append("")
            
            # Projection info
            if results['projection']:
                proj = results['projection']
                report.append(f"Projection ({proj['weeks_ahead']} weeks ahead):")
                report.append(f"  Projected Budget: ${proj['projected_budget']:.2f}")
                report.append(f"  Projected Spending: ${proj['projected_spending']:.2f}")
                report.append(f"  Projected Variance: ${proj['projected_variance']:.2f}")
                report.append("")
        
        elif '__totals__' in results:
            # Projection results
            totals = results['__totals__']
            report.append("Spending Projection")
            report.append("==================")
            report.append(f"Weeks Ahead: {totals['weeks_ahead']}")
            report.append(f"Projected Total Budget: ${totals['projected_budget']:.2f}")
            report.append(f"Projected Total Spending: ${totals['projected_spending']:.2f}")
            report.append(f"Projected Total Variance: ${totals['projected_variance']:.2f}")
            report.append("")
            
            report.append("Category Projections:")
            for category, data in [(c, d) for c, d in results.items() if c != '__totals__']:
                report.append(f"{category}:")
                report.append(f"  Weekly Budget: ${data['weekly_budget']:.2f}")
                report.append(f"  Spending Rate: {data['spending_rate']:.2f} of budget")
                report.append(f"  Projected Spending: ${data['projected_spending']:.2f}")
                report.append(f"  Projected Budget: ${data['projected_budget']:.2f}")
                report.append(f"  Projected Variance: ${data['projected_variance']:.2f}")
                report.append("")
        
        else:
            # Variance results
            report.append("Budget Variance Analysis")
            report.append("=======================")
            
            # Calculate totals
            total_budget = sum(data['budget_amount'] for data in results.values())
            total_actual = sum(data['actual_amount'] for data in results.values())
            total_variance = sum(data['variance_amount'] for data in results.values())
            
            report.append(f"Total Budget: ${total_budget:.2f}")
            report.append(f"Total Spent: ${total_actual:.2f}")
            report.append(f"Total Variance: ${total_variance:.2f}")
            report.append("")
            
            report.append("Category Details:")
            for category, data in results.items():
                variance_sign = "+" if data['variance_amount'] >= 0 else ""
                report.append(f"{category}:")
                report.append(f"  Budget: ${data['budget_amount']:.2f}")
                report.append(f"  Spent: ${data['actual_amount']:.2f}")
                report.append(f"  Variance: {variance_sign}${data['variance_amount']:.2f} ({data['variance_percentage']:.1f}%)")
                report.append(f"  Status: {'Under Budget' if data['variance_amount'] >= 0 else 'Over Budget'}")
                report.append("")
        
        return "\n".join(report)
    
    elif format == 'html':
        # Create an HTML report
        html = ["<html><head><style>",
                "body { font-family: Arial, sans-serif; margin: 20px; }",
                "h1, h2 { color: #333; }",
                ".surplus { color: green; }",
                ".deficit { color: red; }",
                "table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }",
                "th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }",
                "th { background-color: #f2f2f2; }",
                ".summary { background-color: #f9f9f9; padding: 10px; border-radius: 5px; margin-bottom: 20px; }",
                "</style></head><body>"]
        
        # Handle different result types
        if 'transfer_amount' in results:
            # Transfer results
            html.append("<h1>Budget Transfer Summary</h1>")
            html.append("<div class='summary'>")
            html.append(f"<p>Total Budget: <strong>${results['total_budget']:.2f}</strong></p>")
            html.append(f"<p>Total Spent: <strong>${results['total_spent']:.2f}</strong></p>")
            
            # Format variance with color
            variance_class = "surplus" if results['total_variance'] >= 0 else "deficit"
            html.append(f"<p>Total Variance: <strong class='{variance_class}'>${results['total_variance']:.2f}</strong></p>")
            
            # Format transfer amount
            transfer_class = "surplus" if results['transfer_amount'] > 0 else ""
            html.append(f"<p>Transfer Amount: <strong class='{transfer_class}'>${results['transfer_amount']:.2f}</strong></p>")
            
            html.append(f"<p>Budget Status: <strong class='{variance_class}'>{'Surplus' if results['is_surplus'] else 'Deficit'}</strong></p>")
            html.append("</div>")
        
        elif 'budget_status' in results:
            # Summary results
            html.append("<h1>Budget Summary</h1>")
            
            # Budget status
            status = results['budget_status']
            variance_class = "surplus" if status['total_variance'] >= 0 else "deficit"
            
            html.append("<div class='summary'>")
            html.append(f"<p>Total Budget: <strong>${status['total_budget']:.2f}</strong></p>")
            html.append(f"<p>Total Spent: <strong>${status['total_spent']:.2f}</strong></p>")
            html.append(f"<p>Total Variance: <strong class='{variance_class}'>${status['total_variance']:.2f}</strong></p>")
            html.append(f"<p>Budget Status: <strong class='{variance_class}'>{'Surplus' if status['is_surplus'] else 'Deficit'}</strong></p>")
            html.append(f"<p>Budget Used: <strong>{status['budget_used_percentage']:.1f}%</strong></p>")
            html.append("</div>")
            
            # Insights
            html.append("<h2>Insights</h2>")
            html.append("<ul>")
            for insight in results['insights']:
                html.append(f"<li>{insight}</li>")
            html.append("</ul>")
            
            # Categories
            html.append("<h2>Category Details</h2>")
            html.append("<table>")
            html.append("<tr><th>Category</th><th>Budget</th><th>Spent</th><th>Variance</th><th>Status</th></tr>")
            
            for category, data in results['categories'].items():
                variance_class = "surplus" if data['variance_amount'] >= 0 else "deficit"
                variance_sign = "+" if data['variance_amount'] >= 0 else ""
                status_text = "Under Budget" if not data['is_over_budget'] else "Over Budget"
                
                html.append("<tr>")
                html.append(f"<td>{category}</td>")
                html.append(f"<td>${data['budget_amount']:.2f}</td>")
                html.append(f"<td>${data['actual_amount']:.2f}</td>")
                html.append(f"<td class='{variance_class}'>{variance_sign}${data['variance_amount']:.2f} ({data['variance_percentage']:.1f}%)</td>")
                html.append(f"<td class='{variance_class}'>{status_text}</td>")
                html.append("</tr>")
            
            html.append("</table>")
            
            # Transfer info
            if results['transfer']['transfer_amount'] > 0:
                html.append("<h2>Savings Transfer</h2>")
                html.append(f"<p>Amount to transfer to savings: <strong class='surplus'>${results['transfer']['transfer_amount']:.2f}</strong></p>")
            
            # Projection info
            if results['projection']:
                proj = results['projection']
                proj_class = "surplus" if proj['projected_variance'] >= 0 else "deficit"
                
                html.append(f"<h2>Projection ({proj['weeks_ahead']} weeks ahead)</h2>")
                html.append("<div class='summary'>")
                html.append(f"<p>Projected Budget: <strong>${proj['projected_budget']:.2f}</strong></p>")
                html.append(f"<p>Projected Spending: <strong>${proj['projected_spending']:.2f}</strong></p>")
                html.append(f"<p>Projected Variance: <strong class='{proj_class}'>${proj['projected_variance']:.2f}</strong></p>")
                html.append("</div>")
        
        elif '__totals__' in results:
            # Projection results
            totals = results['__totals__']
            proj_class = "surplus" if totals['projected_variance'] >= 0 else "deficit"
            
            html.append("<h1>Spending Projection</h1>")
            html.append("<div class='summary'>")
            html.append(f"<p>Weeks Ahead: <strong>{totals['weeks_ahead']}</strong></p>")
            html.append(f"<p>Projected Total Budget: <strong>${totals['projected_budget']:.2f}</strong></p>")
            html.append(f"<p>Projected Total Spending: <strong>${totals['projected_spending']:.2f}</strong></p>")
            html.append(f"<p>Projected Total Variance: <strong class='{proj_class}'>${totals['projected_variance']:.2f}</strong></p>")
            html.append("</div>")
            
            html.append("<h2>Category Projections</h2>")
            html.append("<table>")
            html.append("<tr><th>Category</th><th>Weekly Budget</th><th>Spending Rate</th><th>Projected Spending</th><th>Projected Variance</th></tr>")
            
            for category, data in [(c, d) for c, d in results.items() if c != '__totals__']:
                proj_class = "surplus" if data['projected_variance'] >= 0 else "deficit"
                
                html.append("<tr>")
                html.append(f"<td>{category}</td>")
                html.append(f"<td>${data['weekly_budget']:.2f}</td>")
                html.append(f"<td>{data['spending_rate']:.2f} of budget</td>")
                html.append(f"<td>${data['projected_spending']:.2f}</td>")
                html.append(f"<td class='{proj_class}'>${data['projected_variance']:.2f}</td>")
                html.append("</tr>")
            
            html.append("</table>")
        
        else:
            # Variance results
            html.append("<h1>Budget Variance Analysis</h1>")
            
            # Calculate totals
            total_budget = sum(data['budget_amount'] for data in results.values())
            total_actual = sum(data['actual_amount'] for data in results.values())
            total_variance = sum(data['variance_amount'] for data in results.values())
            
            variance_class = "surplus" if total_variance >= 0 else "deficit"
            
            html.append("<div class='summary'>")
            html.append(f"<p>Total Budget: <strong>${total_budget:.2f}</strong></p>")
            html.append(f"<p>Total Spent: <strong>${total_actual:.2f}</strong></p>")
            html.append(f"<p>Total Variance: <strong class='{variance_class}'>${total_variance:.2f}</strong></p>")
            html.append("</div>")
            
            html.append("<h2>Category Details</h2>")
            html.append("<table>")
            html.append("<tr><th>Category</th><th>Budget</th><th>Spent</th><th>Variance</th><th>Status</th></tr>")
            
            for category, data in results.items():
                variance_class = "surplus" if data['variance_amount'] >= 0 else "deficit"
                variance_sign = "+" if data['variance_amount'] >= 0 else ""
                status_text = "Under Budget" if data['variance_amount'] >= 0 else "Over Budget"
                
                html.append("<tr>")
                html.append(f"<td>{category}</td>")
                html.append(f"<td>${data['budget_amount']:.2f}</td>")
                html.append(f"<td>${data['actual_amount']:.2f}</td>")
                html.append(f"<td class='{variance_class}'>{variance_sign}${data['variance_amount']:.2f} ({data['variance_percentage']:.1f}%)</td>")
                html.append(f"<td class='{variance_class}'>{status_text}</td>")
                html.append("</tr>")
            
            html.append("</table>")
        
        html.append("</body></html>")
        return "\n".join(html)
    
    elif format == 'markdown':
        # Create a Markdown report
        md = []
        
        # Handle different result types
        if 'transfer_amount' in results:
            # Transfer results
            md.append("# Budget Transfer Summary")
            md.append("")
            md.append(f"**Total Budget:** ${results['total_budget']:.2f}")
            md.append(f"**Total Spent:** ${results['total_spent']:.2f}")
            md.append(f"**Total Variance:** ${results['total_variance']:.2f}")
            md.append(f"**Transfer Amount:** ${results['transfer_amount']:.2f}")
            md.append(f"**Budget Status:** {'Surplus' if results['is_surplus'] else 'Deficit'}")
        
        elif 'budget_status' in results:
            # Summary results
            md.append("# Budget Summary")
            md.append("")
            
            # Budget status
            status = results['budget_status']
            md.append("## Overall Status")
            md.append("")
            md.append(f"**Total Budget:** ${status['total_budget']:.2f}")
            md.append(f"**Total Spent:** ${status['total_spent']:.2f}")
            md.append(f"**Total Variance:** ${status['total_variance']:.2f}")
            md.append(f"**Budget Status:** {'Surplus' if status['is_surplus'] else 'Deficit'}")
            md.append(f"**Budget Used:** {status['budget_used_percentage']:.1f}%")
            md.append("")
            
            # Insights
            md.append("## Insights")
            md.append("")
            for insight in results['insights']:
                md.append(f"- {insight}")
            md.append("")
            
            # Categories
            md.append("## Category Details")
            md.append("")
            md.append("| Category | Budget | Spent | Variance | Status |")
            md.append("| -------- | ------ | ----- | -------- | ------ |")
            
            for category, data in results['categories'].items():
                variance_sign = "+" if data['variance_amount'] >= 0 else ""
                status_text = "Under Budget" if not data['is_over_budget'] else "Over Budget"
                
                md.append(f"| {category} | ${data['budget_amount']:.2f} | ${data['actual_amount']:.2f} | "
                         f"{variance_sign}${data['variance_amount']:.2f} ({data['variance_percentage']:.1f}%) | {status_text} |")
            
            md.append("")
            
            # Transfer info
            if results['transfer']['transfer_amount'] > 0:
                md.append("## Savings Transfer")
                md.append("")
                md.append(f"Amount to transfer to savings: **${results['transfer']['transfer_amount']:.2f}**")
                md.append("")
            
            # Projection info
            if results['projection']:
                proj = results['projection']
                md.append(f"## Projection ({proj['weeks_ahead']} weeks ahead)")
                md.append("")
                md.append(f"**Projected Budget:** ${proj['projected_budget']:.2f}")
                md.append(f"**Projected Spending:** ${proj['projected_spending']:.2f}")
                md.append(f"**Projected Variance:** ${proj['projected_variance']:.2f}")
                md.append("")
        
        elif '__totals__' in results:
            # Projection results
            totals = results['__totals__']
            md.append("# Spending Projection")
            md.append("")
            md.append(f"**Weeks Ahead:** {totals['weeks_ahead']}")
            md.append(f"**Projected Total Budget:** ${totals['projected_budget']:.2f}")
            md.append(f"**Projected Total Spending:** ${totals['projected_spending']:.2f}")
            md.append(f"**Projected Total Variance:** ${totals['projected_variance']:.2f}")
            md.append("")
            
            md.append("## Category Projections")
            md.append("")
            md.append("| Category | Weekly Budget | Spending Rate | Projected Spending | Projected Variance |")
            md.append("| -------- | ------------- | ------------- | ------------------ | ------------------ |")
            
            for category, data in [(c, d) for c, d in results.items() if c != '__totals__']:
                md.append(f"| {category} | ${data['weekly_budget']:.2f} | {data['spending_rate']:.2f} of budget | "
                         f"${data['projected_spending']:.2f} | ${data['projected_variance']:.2f} |")
            
            md.append("")
        
        else:
            # Variance results
            md.append("# Budget Variance Analysis")
            md.append("")
            
            # Calculate totals
            total_budget = sum(data['budget_amount'] for data in results.values())
            total_actual = sum(data['actual_amount'] for data in results.values())
            total_variance = sum(data['variance_amount'] for data in results.values())
            
            md.append(f"**Total Budget:** ${total_budget:.2f}")
            md.append(f"**Total Spent:** ${total_actual:.2f}")
            md.append(f"**Total Variance:** ${total_variance:.2f}")
            md.append("")
            
            md.append("## Category Details")
            md.append("")
            md.append("| Category | Budget | Spent | Variance | Status |")
            md.append("| -------- | ------ | ----- | -------- | ------ |")
            
            for category, data in results.items():
                variance_sign = "+" if data['variance_amount'] >= 0 else ""
                status_text = "Under Budget" if data['variance_amount'] >= 0 else "Over Budget"
                
                md.append(f"| {category} | ${data['budget_amount']:.2f} | ${data['actual_amount']:.2f} | "
                         f"{variance_sign}${data['variance_amount']:.2f} ({data['variance_percentage']:.1f}%) | {status_text} |")
        
        return "\n".join(md)
    
    elif format == 'csv':
        # Create CSV report
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Handle different result types
        if 'transfer_amount' in results:
            # Transfer results
            writer.writerow(['Total Budget', 'Total Spent', 'Total Variance', 'Transfer Amount', 'Budget Status'])
            writer.writerow([
                results['total_budget'],
                results['total_spent'],
                results['total_variance'],
                results['transfer_amount'],
                'Surplus' if results['is_surplus'] else 'Deficit'
            ])
        
        elif 'budget_status' in results:
            # Summary results - Overall status
            writer.writerow(['Overall Budget Status'])
            writer.writerow(['Total Budget', 'Total Spent', 'Total Variance', 'Budget Status', 'Budget Used %'])
            
            status = results['budget_status']
            writer.writerow([
                status['total_budget'],
                status['total_spent'],
                status['total_variance'],
                'Surplus' if status['is_surplus'] else 'Deficit',
                status['budget_used_percentage']
            ])
            
            # Categories
            writer.writerow([])
            writer.writerow(['Category Details'])
            writer.writerow(['Category', 'Budget', 'Spent', 'Variance', 'Variance %', 'Status'])
            
            for category, data in results['categories'].items():
                writer.writerow([
                    category,
                    data['budget_amount'],
                    data['actual_amount'],
                    data['variance_amount'],
                    data['variance_percentage'],
                    'Under Budget' if not data['is_over_budget'] else 'Over Budget'
                ])
            
            # Transfer info
            if results['transfer']['transfer_amount'] > 0:
                writer.writerow([])
                writer.writerow(['Savings Transfer'])
                writer.writerow(['Transfer Amount'])
                writer.writerow([results['transfer']['transfer_amount']])
            
            # Projection info
            if results['projection']:
                proj = results['projection']
                writer.writerow([])
                writer.writerow([f'Projection ({proj["weeks_ahead"]} weeks ahead)'])
                writer.writerow(['Projected Budget', 'Projected Spending', 'Projected Variance'])
                writer.writerow([
                    proj['projected_budget'],
                    proj['projected_spending'],
                    proj['projected_variance']
                ])
        
        elif '__totals__' in results:
            # Projection results
            totals = results['__totals__']
            writer.writerow(['Spending Projection'])
            writer.writerow(['Weeks Ahead', 'Projected Budget', 'Projected Spending', 'Projected Variance'])
            writer.writerow([
                totals['weeks_ahead'],
                totals['projected_budget'],
                totals['projected_spending'],
                totals['projected_variance']
            ])
            
            writer.writerow([])
            writer.writerow(['Category Projections'])
            writer.writerow(['Category', 'Weekly Budget', 'Spending Rate', 'Projected Spending', 'Projected Budget', 'Projected Variance'])
            
            for category, data in [(c, d) for c, d in results.items() if c != '__totals__']:
                writer.writerow([
                    category,
                    data['weekly_budget'],
                    data['spending_rate'],
                    data['projected_spending'],
                    data['projected_budget'],
                    data['projected_variance']
                ])
        
        else:
            # Variance results
            writer.writerow(['Budget Variance Analysis'])
            
            # Calculate totals
            total_budget = sum(data['budget_amount'] for data in results.values())
            total_actual = sum(data['actual_amount'] for data in results.values())
            total_variance = sum(data['variance_amount'] for data in results.values())
            
            writer.writerow(['Total Budget', 'Total Spent', 'Total Variance'])
            writer.writerow([total_budget, total_actual, total_variance])
            
            writer.writerow([])
            writer.writerow(['Category Details'])
            writer.writerow(['Category', 'Budget', 'Spent', 'Variance', 'Variance %', 'Status'])
            
            for category, data in results.items():
                writer.writerow([
                    category,
                    data['budget_amount'],
                    data['actual_amount'],
                    data['variance_amount'],
                    data['variance_percentage'],
                    'Under Budget' if data['variance_amount'] >= 0 else 'Over Budget'
                ])
        
        return output.getvalue()
    
    else:
        logger.warning(f"Unsupported output format: {format}, using text format instead")
        return format_calculation_results(results, 'text')


def save_calculation_results(formatted_results: str, output_file: str) -> bool:
    """
    Saves calculation results to a file
    
    Args:
        formatted_results: Formatted results string to save
        output_file: Path to output file
        
    Returns:
        True if save was successful, False otherwise
    """
    try:
        # Determine file extension based on content
        if formatted_results.startswith("<html>"):
            file_extension = ".html"
        elif formatted_results.startswith("{") or formatted_results.startswith("["):
            file_extension = ".json"
        elif formatted_results.startswith("#"):
            file_extension = ".md"
        elif "," in formatted_results.split("\n")[0]:
            file_extension = ".csv"
        else:
            file_extension = ".txt"
        
        # If output_file doesn't have an extension, add one
        if not output_file.endswith(file_extension):
            if "." not in os.path.basename(output_file):
                output_file += file_extension
        
        # Write to file
        with open(output_file, 'w') as f:
            f.write(formatted_results)
        
        logger.info(f"Results saved to {output_file}")
        return True
    
    except IOError as e:
        logger.error(f"Error saving results to file: {str(e)}")
        return False


def visualize_budget_data(results: Dict[str, Any], visualization_type: str, output_file: Optional[str] = None) -> bool:
    """
    Creates visualizations of budget data and analysis results
    
    Args:
        results: Budget data and analysis results
        visualization_type: Type of visualization to create (bar, pie, line, all)
        output_file: Optional path to save visualization to
        
    Returns:
        True if visualization was successful, False otherwise
    """
    try:
        # Set plot style
        plt.style.use('ggplot')
        
        # Determine what kind of results we have
        if 'budget_status' in results:
            # Summary results
            categories = results['categories']
            budget_status = results['budget_status']
            projection = results.get('projection', {})
        elif 'transfer_amount' in results:
            # Transfer results
            return False  # Not enough data for visualization
        elif '__totals__' in results:
            # Projection results
            categories = {cat: data for cat, data in results.items() if cat != '__totals__'}
            budget_status = None
            projection = {'totals': results['__totals__']}
        else:
            # Variance results
            categories = results
            budget_status = {
                'total_budget': sum(data['budget_amount'] for data in results.values()),
                'total_spent': sum(data['actual_amount'] for data in results.values()),
                'total_variance': sum(data['variance_amount'] for data in results.values())
            }
            projection = None
        
        # Choose visualization based on type
        if visualization_type == 'bar' or visualization_type == 'all':
            # Create bar chart of budget vs. actual by category
            plt.figure(figsize=(12, 8))
            
            # Extract categories and values
            cats = list(categories.keys())
            
            if 'budget_amount' in list(categories.values())[0]:
                # Variance results
                budget_amounts = [data['budget_amount'] for data in categories.values()]
                actual_amounts = [data['actual_amount'] for data in categories.values()]
                
                # Sort by budget amount
                sorted_data = sorted(zip(cats, budget_amounts, actual_amounts), key=lambda x: x[1], reverse=True)
                cats = [x[0] for x in sorted_data]
                budget_amounts = [x[1] for x in sorted_data]
                actual_amounts = [x[2] for x in sorted_data]
                
                # Create bar chart
                x = np.arange(len(cats))
                width = 0.35
                
                fig, ax = plt.subplots(figsize=(12, 8))
                rects1 = ax.bar(x - width/2, budget_amounts, width, label='Budget')
                rects2 = ax.bar(x + width/2, actual_amounts, width, label='Actual')
                
                # Add labels and title
                ax.set_xlabel('Categories')
                ax.set_ylabel('Amount ($)')
                ax.set_title('Budget vs. Actual Spending by Category')
                ax.set_xticks(x)
                ax.set_xticklabels(cats, rotation=45, ha='right')
                ax.legend()
                
                # Add grid
                ax.grid(True, linestyle='--', alpha=0.7)
                
                # Add value labels
                for rect in rects1:
                    height = rect.get_height()
                    ax.annotate(f'${height:.2f}',
                                xy=(rect.get_x() + rect.get_width()/2, height),
                                xytext=(0, 3),  # 3 points vertical offset
                                textcoords="offset points",
                                ha='center', va='bottom', fontsize=8)
                
                for rect in rects2:
                    height = rect.get_height()
                    ax.annotate(f'${height:.2f}',
                                xy=(rect.get_x() + rect.get_width()/2, height),
                                xytext=(0, 3),  # 3 points vertical offset
                                textcoords="offset points",
                                ha='center', va='bottom', fontsize=8)
                
                plt.tight_layout()
                
                # Save or display
                if output_file:
                    bar_output = f"{os.path.splitext(output_file)[0]}_bar.png"
                    plt.savefig(bar_output)
                    logger.info(f"Bar chart saved to {bar_output}")
                else:
                    plt.show()
            else:
                # Projection results
                plt.close()  # Close any existing plots
                return False  # Not implemented for this result type
        
        if visualization_type == 'pie' or visualization_type == 'all':
            # Create pie charts of budget and spending distribution
            if budget_status:
                # Budget distribution
                plt.figure(figsize=(12, 6))
                
                # Create subplot for budget distribution
                plt.subplot(1, 2, 1)
                
                if 'budget_amount' in list(categories.values())[0]:
                    # Get budget amounts and labels
                    budget_amounts = [data['budget_amount'] for data in categories.values()]
                    labels = categories.keys()
                    
                    # Filter out zero values
                    non_zero = [(label, amount) for label, amount in zip(labels, budget_amounts) if amount > 0]
                    labels = [x[0] for x in non_zero]
                    budget_amounts = [x[1] for x in non_zero]
                    
                    # Create pie chart
                    plt.pie(budget_amounts, labels=None, autopct='%1.1f%%', startangle=90)
                    plt.title('Budget Distribution by Category')
                    
                    # Add legend
                    plt.legend(labels, loc="center left", bbox_to_anchor=(1, 0.5))
                    
                    # Create subplot for actual spending distribution
                    plt.subplot(1, 2, 2)
                    
                    # Get actual amounts and labels
                    actual_amounts = [data['actual_amount'] for data in categories.values()]
                    labels = categories.keys()
                    
                    # Filter out zero values
                    non_zero = [(label, amount) for label, amount in zip(labels, actual_amounts) if amount > 0]
                    labels = [x[0] for x in non_zero]
                    actual_amounts = [x[1] for x in non_zero]
                    
                    # Create pie chart
                    plt.pie(actual_amounts, labels=None, autopct='%1.1f%%', startangle=90)
                    plt.title('Actual Spending Distribution by Category')
                    
                    # Add legend
                    plt.legend(labels, loc="center left", bbox_to_anchor=(1, 0.5))
                    
                    plt.tight_layout()
                    
                    # Save or display
                    if output_file:
                        pie_output = f"{os.path.splitext(output_file)[0]}_pie.png"
                        plt.savefig(pie_output)
                        logger.info(f"Pie charts saved to {pie_output}")
                    else:
                        plt.show()
                else:
                    # Projection results
                    plt.close()  # Close any existing plots
                    return False  # Not implemented for this result type
        
        if visualization_type == 'line' or visualization_type == 'all':
            # Currently not implemented - would need historical data for line charts
            pass
        
        return True
    
    except Exception as e:
        logger.error(f"Error creating visualization: {str(e)}")
        plt.close()  # Close any plots in case of error
        return False


def get_budget_data_from_sheets(master_budget_id: str, master_budget_range: str, 
                              weekly_spending_id: str, weekly_spending_range: str,
                              service=None) -> Tuple[List[Category], Dict[str, Decimal]]:
    """
    Retrieves budget data from Google Sheets
    
    Args:
        master_budget_id: ID of the Master Budget spreadsheet
        master_budget_range: Range to read from Master Budget sheet
        weekly_spending_id: ID of the Weekly Spending spreadsheet
        weekly_spending_range: Range to read from Weekly Spending sheet
        service: Google Sheets API service (will be created if None)
        
    Returns:
        Tuple of (categories, actual_spending)
    """
    try:
        # Get Google Sheets service if not provided
        if service is None:
            service = get_sheets_service()
        
        # Read Master Budget data
        logger.info(f"Reading Master Budget data from {master_budget_id}, range: {master_budget_range}")
        budget_data = read_sheet(master_budget_id, master_budget_range, service)
        
        # Check if we have data
        if not budget_data:
            logger.error("No data found in Master Budget sheet")
            raise ValueError("No data found in Master Budget sheet")
        
        # Create Category objects from budget data
        categories = create_categories_from_sheet_data(budget_data)
        
        # Read Weekly Spending data
        logger.info(f"Reading Weekly Spending data from {weekly_spending_id}, range: {weekly_spending_range}")
        spending_data = read_sheet(weekly_spending_id, weekly_spending_range, service)
        
        # Check if we have data
        if not spending_data:
            logger.warning("No data found in Weekly Spending sheet")
            # Continue with empty spending data
            spending_data = []
        
        # Extract spending by category
        actual_spending = {}
        
        # Skip header row
        for row in spending_data[1:] if len(spending_data) > 0 else []:
            # Each row should have: [Location, Amount, Timestamp, Category]
            if len(row) >= 4 and row[3]:  # If row has a category
                category = row[3]
                try:
                    # Get amount and convert to Decimal
                    amount = Decimal(str(row[1]))
                    
                    # Add to category total
                    if category in actual_spending:
                        actual_spending[category] += amount
                    else:
                        actual_spending[category] = amount
                except (decimal.InvalidOperation, ValueError, IndexError) as e:
                    logger.warning(f"Error processing spending data row: {e}")
                    continue
        
        logger.info(f"Retrieved {len(categories)} categories and {len(actual_spending)} spending entries")
        return categories, actual_spending
    
    except Exception as e:
        logger.error(f"Error retrieving budget data from sheets: {str(e)}")
        raise


class BudgetCalculator:
    """Class for performing budget calculations and analysis"""
    
    def __init__(self, service=None, verbose=False):
        """
        Initialize the BudgetCalculator with optional service
        
        Args:
            service: Google Sheets API service (will be created when needed if None)
            verbose: Whether to output verbose logging
        """
        self.service = service
        self.verbose = verbose
        logger.info("BudgetCalculator initialized")
    
    def ensure_service(self, credentials_path=None):
        """
        Ensures Google Sheets service is available
        
        Args:
            credentials_path: Path to credentials file
            
        Returns:
            Google Sheets service object
        """
        if self.service is None:
            logger.debug("Creating Google Sheets service")
            self.service = get_sheets_service(credentials_path)
        return self.service
    
    def get_budget_data(self, master_budget_id, master_budget_range, weekly_spending_id, weekly_spending_range):
        """
        Retrieves budget data from Google Sheets
        
        Args:
            master_budget_id: ID of the Master Budget spreadsheet
            master_budget_range: Range to read from Master Budget sheet
            weekly_spending_id: ID of the Weekly Spending spreadsheet
            weekly_spending_range: Range to read from Weekly Spending sheet
            
        Returns:
            Tuple of (categories, actual_spending)
        """
        # Ensure service is available
        self.ensure_service()
        
        return get_budget_data_from_sheets(
            master_budget_id,
            master_budget_range,
            weekly_spending_id,
            weekly_spending_range,
            self.service
        )
    
    def calculate_variance(self, categories, actual_spending):
        """
        Calculates budget variance
        
        Args:
            categories: List of Category objects
            actual_spending: Dictionary mapping categories to actual spending amounts
            
        Returns:
            Dictionary with variance results by category
        """
        variance_results = calculate_budget_variance(categories, actual_spending)
        
        if self.verbose:
            logger.info(f"Calculated variance for {len(categories)} categories")
        
        return variance_results
    
    def calculate_transfer(self, variance_results):
        """
        Calculates savings transfer amount
        
        Args:
            variance_results: Dictionary with variance details by category
            
        Returns:
            Dictionary with transfer amount and related values
        """
        transfer_results = calculate_transfer_amount(variance_results)
        
        if self.verbose:
            logger.info(f"Calculated transfer amount: {transfer_results['transfer_amount']}")
        
        return transfer_results
    
    def project_spending(self, variance_results, weeks_ahead):
        """
        Projects future spending
        
        Args:
            variance_results: Dictionary with variance details by category
            weeks_ahead: Number of weeks to project into the future
            
        Returns:
            Dictionary with projected spending by category
        """
        projection_results = project_future_spending(variance_results, weeks_ahead)
        
        if self.verbose:
            logger.info(f"Projected spending for {weeks_ahead} weeks ahead")
        
        return projection_results
    
    def generate_summary(self, variance_results, transfer_results, projection_results=None):
        """
        Generates comprehensive budget summary
        
        Args:
            variance_results: Dictionary with variance details by category
            transfer_results: Dictionary with transfer amount and related values
            projection_results: Optional dictionary with projected spending by category
            
        Returns:
            Comprehensive budget summary
        """
        summary = generate_budget_summary(variance_results, transfer_results, projection_results)
        
        if self.verbose:
            logger.info("Generated comprehensive budget summary")
        
        return summary
    
    def format_results(self, results, format):
        """
        Formats calculation results
        
        Args:
            results: Calculation results to format
            format: Output format
            
        Returns:
            Formatted results
        """
        return format_calculation_results(results, format)
    
    def save_results(self, formatted_results, output_file):
        """
        Saves calculation results to file
        
        Args:
            formatted_results: Formatted results to save
            output_file: Path to output file
            
        Returns:
            True if save was successful
        """
        success = save_calculation_results(formatted_results, output_file)
        
        if self.verbose:
            if success:
                logger.info(f"Results saved to {output_file}")
            else:
                logger.error(f"Failed to save results to {output_file}")
        
        return success
    
    def visualize(self, results, visualization_type, output_file=None):
        """
        Creates visualizations of budget data
        
        Args:
            results: Calculation results to visualize
            visualization_type: Type of visualization to create
            output_file: Optional path to save visualization to
            
        Returns:
            True if visualization was successful
        """
        success = visualize_budget_data(results, visualization_type, output_file)
        
        if self.verbose:
            if success:
                if output_file:
                    logger.info(f"Visualization saved to {output_file}")
                else:
                    logger.info("Visualization displayed")
            else:
                logger.warning("Visualization failed or not supported for this result type")
        
        return success
    
    def run_calculation(self, calculation_type, master_budget_id, master_budget_range,
                       weekly_spending_id, weekly_spending_range, weeks_ahead=None):
        """
        Runs a complete budget calculation workflow
        
        Args:
            calculation_type: Type of calculation to perform
            master_budget_id: ID of the Master Budget spreadsheet
            master_budget_range: Range to read from Master Budget sheet
            weekly_spending_id: ID of the Weekly Spending spreadsheet
            weekly_spending_range: Range to read from Weekly Spending sheet
            weeks_ahead: Number of weeks for projection calculation
            
        Returns:
            Calculation results
        """
        try:
            # Get budget data
            categories, actual_spending = self.get_budget_data(
                master_budget_id,
                master_budget_range,
                weekly_spending_id,
                weekly_spending_range
            )
            
            # Calculate variance
            variance_results = self.calculate_variance(categories, actual_spending)
            
            # Perform requested calculation
            if calculation_type == 'variance':
                return variance_results
            
            elif calculation_type == 'transfer':
                transfer_results = self.calculate_transfer(variance_results)
                return transfer_results
            
            elif calculation_type == 'projection':
                if weeks_ahead is None:
                    weeks_ahead = 4  # Default to 4 weeks
                
                projection_results = self.project_spending(variance_results, weeks_ahead)
                return projection_results
            
            elif calculation_type == 'summary':
                transfer_results = self.calculate_transfer(variance_results)
                
                if weeks_ahead is not None:
                    projection_results = self.project_spending(variance_results, weeks_ahead)
                else:
                    projection_results = None
                
                summary = self.generate_summary(variance_results, transfer_results, projection_results)
                return summary
            
            else:
                logger.error(f"Unknown calculation type: {calculation_type}")
                raise ValueError(f"Unknown calculation type: {calculation_type}")
        
        except Exception as e:
            logger.error(f"Error running calculation: {str(e)}")
            raise
        
        finally:
            if self.verbose:
                logger.info(f"Completed {calculation_type} calculation")


def parse_arguments():
    """
    Parses command-line arguments for the script
    
    Returns:
        Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description='Budget Calculator - Utility tool for budget calculations and analysis'
    )
    
    # Calculation type argument
    parser.add_argument(
        'calculation_type',
        choices=CALCULATION_TYPES,
        help='Type of calculation to perform'
    )
    
    # Google Sheets arguments
    parser.add_argument(
        '--master-budget-id',
        help='ID of the Master Budget spreadsheet',
        default=API_TEST_SETTINGS.get('SHEETS_TEST_SPREADSHEET_ID')
    )
    
    parser.add_argument(
        '--master-budget-range',
        help='Range to read from Master Budget sheet',
        default=DEFAULT_MASTER_BUDGET_RANGE
    )
    
    parser.add_argument(
        '--weekly-spending-id',
        help='ID of the Weekly Spending spreadsheet',
        default=API_TEST_SETTINGS.get('SHEETS_TEST_SPREADSHEET_ID')
    )
    
    parser.add_argument(
        '--weekly-spending-range',
        help='Range to read from Weekly Spending sheet',
        default=DEFAULT_WEEKLY_SPENDING_RANGE
    )
    
    # Output arguments
    parser.add_argument(
        '--output-format',
        choices=['json', 'text', 'html', 'markdown', 'csv'],
        default=DEFAULT_OUTPUT_FORMAT,
        help='Format for output results'
    )
    
    parser.add_argument(
        '--output-file',
        help='Path to save output to (if not specified, output is printed to console)'
    )
    
    # Visualization arguments
    parser.add_argument(
        '--visualization',
        choices=['bar', 'pie', 'line', 'all'],
        help='Type of visualization to create'
    )
    
    parser.add_argument(
        '--visualization-output',
        help='Path to save visualization to (if not specified, visualization is displayed)'
    )
    
    # Projection arguments
    parser.add_argument(
        '--weeks-ahead',
        type=int,
        help='Number of weeks for projection calculation'
    )
    
    # Credentials argument
    parser.add_argument(
        '--credentials',
        help='Path to Google API credentials file'
    )
    
    # Verbose flag
    parser.add_argument(
        '--verbose',
        action='store_true',
        default=SCRIPT_SETTINGS.get('VERBOSE', False),
        help='Enable verbose output'
    )
    
    return parser.parse_args()


def main():
    """
    Main function to run the budget calculator tool
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Parse command-line arguments
        args = parse_arguments()
        
        # Create BudgetCalculator with verbose flag from arguments
        calculator = BudgetCalculator(verbose=args.verbose or SCRIPT_SETTINGS.get('DEBUG', False))
        
        # Set up Google Sheets service with provided credentials
        if args.credentials:
            calculator.ensure_service(args.credentials)
        
        # Run the requested calculation
        results = calculator.run_calculation(
            args.calculation_type,
            args.master_budget_id,
            args.master_budget_range,
            args.weekly_spending_id,
            args.weekly_spending_range,
            args.weeks_ahead
        )
        
        # Format the results
        formatted_results = calculator.format_results(results, args.output_format)
        
        # Save or print the results
        if args.output_file:
            calculator.save_results(formatted_results, args.output_file)
        else:
            print(formatted_results)
        
        # Create visualization if requested
        if args.visualization:
            calculator.visualize(results, args.visualization, args.visualization_output)
        
        return 0  # Success
    
    except Exception as e:
        logger.error(f"Error in budget calculator: {str(e)}")
        if SCRIPT_SETTINGS.get('DEBUG', False):
            import traceback
            traceback.print_exc()
        return 1  # Error


if __name__ == "__main__":
    sys.exit(main())