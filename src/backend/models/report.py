"""
report.py - Defines the Report model class and related utility functions for budget reporting in the Budget Management Application.

This model encapsulates budget analysis data, AI-generated insights, and chart visualizations,
providing methods for generating email content for the weekly budget report.
"""

import os  # standard library
import base64  # standard library
import logging  # standard library
from typing import List, Dict, Optional  # standard library

from .budget import Budget
from ..utils.formatters import format_currency, format_percentage
from ..config.settings import EMAIL_TEMPLATE_PATH
from ..utils.error_handlers import ValidationError

# Set up logger
logger = logging.getLogger(__name__)


class Report:
    """Represents a budget report with analysis data, insights, and visualizations"""
    
    def __init__(self, budget: Budget):
        """
        Initialize a new Report instance
        
        Args:
            budget (Budget): Budget object with analysis data
        """
        self.budget = budget
        self.insights = None
        self.chart_files = []
        self.email_body = None
        self.email_subject = None
        
        logger.debug(f"Created report for budget: {budget}")
    
    def __str__(self):
        """String representation of the Report"""
        status = "with" if self.insights else "without"
        charts = len(self.chart_files)
        return f"Budget Report {status} insights and {charts} charts"
    
    def __repr__(self):
        """Official string representation of the Report"""
        has_insights = self.insights is not None
        num_charts = len(self.chart_files)
        return f'Report(budget={self.budget}, insights={has_insights}, charts={num_charts})'
    
    def set_insights(self, insights_text: str):
        """
        Set AI-generated insights for the report
        
        Args:
            insights_text (str): AI-generated insights text
        """
        if not insights_text or not isinstance(insights_text, str):
            logger.warning("Invalid insights text provided")
            raise ValidationError("Insights text must be a non-empty string", "insights")
        
        self.insights = insights_text
        # Reset email body since content has changed
        self.email_body = None
        
        logger.debug(f"Set insights for report: {len(insights_text)} characters")
    
    def add_chart(self, chart_file_path: str):
        """
        Add a chart file to the report
        
        Args:
            chart_file_path (str): Path to chart image file
        """
        if not chart_file_path or not isinstance(chart_file_path, str):
            logger.warning("Invalid chart file path provided")
            raise ValidationError("Chart file path must be a non-empty string", "chart_file")
        
        if not os.path.exists(chart_file_path):
            logger.warning(f"Chart file not found: {chart_file_path}")
            raise ValidationError(f"Chart file not found: {chart_file_path}", "chart_file")
        
        self.chart_files.append(chart_file_path)
        # Reset email body since content has changed
        self.email_body = None
        
        logger.debug(f"Added chart to report: {chart_file_path}")
    
    def add_charts(self, chart_file_paths: List[str]):
        """
        Add multiple chart files to the report
        
        Args:
            chart_file_paths (list): List of paths to chart image files
        """
        if not isinstance(chart_file_paths, list):
            logger.warning("Invalid chart file paths provided")
            raise ValidationError("Chart file paths must be a list", "chart_files")
        
        for chart_path in chart_file_paths:
            self.add_chart(chart_path)
        
        logger.debug(f"Added {len(chart_file_paths)} charts to report")
    
    def encode_chart_for_email(self, chart_file_path: str) -> str:
        """
        Encode a chart image as base64 for embedding in HTML email
        
        Args:
            chart_file_path (str): Path to chart image file
            
        Returns:
            str: Base64 encoded image data
        """
        if not os.path.exists(chart_file_path):
            logger.warning(f"Chart file not found for encoding: {chart_file_path}")
            raise ValidationError(f"Chart file not found: {chart_file_path}", "chart_file")
        
        try:
            with open(chart_file_path, 'rb') as img_file:
                img_data = img_file.read()
                
            encoded = base64.b64encode(img_data).decode('utf-8')
            
            # Get file extension from path
            file_ext = os.path.splitext(chart_file_path)[1].lower().lstrip('.')
            if not file_ext or file_ext not in ['png', 'jpg', 'jpeg', 'gif']:
                file_ext = 'png'  # Default to PNG if extension not recognized
            
            return f"data:image/{file_ext};base64,{encoded}"
        
        except Exception as e:
            logger.error(f"Error encoding chart file {chart_file_path}: {str(e)}")
            raise ValidationError(f"Error encoding chart: {str(e)}", "chart_encoding")
    
    def format_budget_status(self) -> str:
        """
        Format the budget status for display in email
        
        Returns:
            str: Formatted budget status HTML
        """
        total_variance = self.budget.total_variance
        
        # Determine status class (surplus or deficit)
        status_class = "surplus" if total_variance >= 0 else "deficit"
        
        # Format variance amount
        formatted_variance = format_currency(abs(total_variance))
        
        # Create status text
        status_text = "under budget" if total_variance >= 0 else "over budget"
        
        # Return formatted HTML
        return f'<span class="{status_class}">{formatted_variance} {status_text}</span>'
    
    def format_category_details(self) -> str:
        """
        Format category breakdown for display in email
        
        Returns:
            str: Formatted category details HTML
        """
        budget_data = self.budget.to_dict()
        category_analysis = budget_data.get('category_analysis', {})
        
        html_content = ""
        
        for category, details in category_analysis.items():
            budget_amount = details.get('budget_amount', 0)
            actual_amount = details.get('actual_amount', 0)
            variance_amount = details.get('variance_amount', 0)
            variance_percentage = details.get('variance_percentage', 0)
            is_over_budget = details.get('is_over_budget', False)
            
            # Determine CSS class for category
            category_class = "over-budget" if is_over_budget else "under-budget"
            
            # Format amounts
            formatted_budget = format_currency(budget_amount)
            formatted_actual = format_currency(actual_amount)
            formatted_variance = format_currency(abs(variance_amount))
            formatted_percentage = format_percentage(abs(variance_percentage) / 100)
            
            # Add sign to variance
            if variance_amount >= 0:
                variance_sign = "+"
            else:
                variance_sign = "-"
            
            # Format status text
            status_text = "over budget" if is_over_budget else "under budget"
            
            # Add to HTML content
            html_content += f"""
            <div class="category {category_class}">
                <div class="category-name">{category}</div>
                <div class="category-details">
                    Budget: {formatted_budget} | 
                    Actual: {formatted_actual} | 
                    Variance: {variance_sign}{formatted_variance} ({formatted_percentage}) {status_text}
                </div>
            </div>
            """
        
        return html_content
    
    def generate_email_body(self) -> str:
        """
        Generate HTML email body from template
        
        Returns:
            str: Complete HTML email body
        """
        # If email body is already generated, return it
        if self.email_body:
            return self.email_body
        
        try:
            # Load email template
            if not os.path.exists(EMAIL_TEMPLATE_PATH):
                logger.error(f"Email template not found: {EMAIL_TEMPLATE_PATH}")
                raise ValidationError(f"Email template not found: {EMAIL_TEMPLATE_PATH}", "email_template")
            
            with open(EMAIL_TEMPLATE_PATH, 'r') as template_file:
                template = template_file.read()
            
            # Format budget status
            budget_status = self.format_budget_status()
            
            # Format category details
            category_details = self.format_category_details()
            
            # Format insights
            insights_content = self.insights if self.insights else "No insights available for this week."
            
            # Format charts
            charts_content = ""
            if self.chart_files:
                for i, chart_file in enumerate(self.chart_files):
                    try:
                        encoded_chart = self.encode_chart_for_email(chart_file)
                        chart_id = f"chart_{i}"
                        charts_content += f'<div class="chart-container"><img src="{encoded_chart}" id="{chart_id}" alt="Budget Chart" style="max-width: 100%;"></div>'
                    except Exception as e:
                        logger.warning(f"Error encoding chart {chart_file}: {str(e)}")
                        # Continue with other charts if one fails
            
            if not charts_content:
                charts_content = "<p>No charts available for this week.</p>"
            
            # Replace placeholders in template
            email_body = template.replace("{{budget_status}}", budget_status)
            email_body = email_body.replace("{{charts_content}}", charts_content)
            email_body = email_body.replace("{{insights_content}}", insights_content)
            email_body = email_body.replace("{{category_details}}", category_details)
            
            # Store for future use
            self.email_body = email_body
            
            return email_body
            
        except Exception as e:
            logger.error(f"Error generating email body: {str(e)}")
            # Provide a simple fallback
            budget_data = self.budget.to_dict()
            total_variance = budget_data.get('total_variance', 0)
            status = "under budget" if total_variance >= 0 else "over budget"
            fallback = f"""
            <html>
            <body>
                <h1>Weekly Budget Report</h1>
                <p>You are {format_currency(abs(total_variance))} {status} this week.</p>
                <p>Please check your budget details for more information.</p>
            </body>
            </html>
            """
            return fallback
    
    def generate_email_subject(self) -> str:
        """
        Generate email subject line with budget status
        
        Returns:
            str: Email subject line
        """
        # If email subject is already generated, return it
        if self.email_subject:
            return self.email_subject
        
        total_variance = self.budget.total_variance
        formatted_variance = format_currency(abs(total_variance))
        
        if total_variance >= 0:
            subject = f"Budget Update: {formatted_variance} under budget this week"
        else:
            subject = f"Budget Update: {formatted_variance} over budget this week"
        
        # Store for future use
        self.email_subject = subject
        
        return subject
    
    def get_email_content(self) -> tuple:
        """
        Get complete email content (subject and body)
        
        Returns:
            tuple: (subject, body)
        """
        subject = self.generate_email_subject()
        body = self.generate_email_body()
        
        logger.info(f"Retrieved email content: {len(body)} characters, subject: {subject}")
        
        return (subject, body)
    
    def is_complete(self) -> bool:
        """
        Check if report has all required components
        
        Returns:
            bool: True if report has insights and charts
        """
        return self.insights is not None and len(self.chart_files) > 0
    
    def to_dict(self) -> Dict:
        """
        Convert Report to dictionary representation
        
        Returns:
            dict: Dictionary with report data
        """
        budget_dict = self.budget.to_dict()
        
        report_dict = {
            'budget': budget_dict,
            'has_insights': self.insights is not None,
            'chart_count': len(self.chart_files),
            'is_complete': self.is_complete()
        }
        
        return report_dict


def create_report(budget):
    """
    Factory function to create a Report object from budget analysis data
    
    Args:
        budget (Budget): Budget object with analysis data
        
    Returns:
        Report: A new Report instance
    """
    try:
        # Validate that budget is a Budget instance
        if not isinstance(budget, Budget):
            logger.error("Invalid budget object provided to create_report")
            raise ValidationError("Budget must be a valid Budget instance", "budget")
        
        # Ensure budget has been analyzed
        if not budget.is_analyzed:
            logger.info("Budget not yet analyzed, calling analyze() method")
            budget.analyze()
        
        # Create and return a new Report instance
        return Report(budget)
    
    except Exception as e:
        logger.error(f"Error creating report: {str(e)}")
        raise


def create_report_with_insights(budget, insights_text):
    """
    Creates a Report object with budget analysis data and AI-generated insights
    
    Args:
        budget (Budget): Budget object with analysis data
        insights_text (str): AI-generated insights text
        
    Returns:
        Report: A Report instance with insights
    """
    # Create a basic report
    report = create_report(budget)
    
    # Set insights
    report.set_insights(insights_text)
    
    logger.info(f"Created report with {len(insights_text)} characters of insights")
    
    return report


def create_report_with_charts(budget, chart_files):
    """
    Creates a Report object with budget analysis data and chart visualizations
    
    Args:
        budget (Budget): Budget object with analysis data
        chart_files (list): List of paths to chart image files
        
    Returns:
        Report: A Report instance with charts
    """
    # Create a basic report
    report = create_report(budget)
    
    # Add charts
    report.add_charts(chart_files)
    
    logger.info(f"Created report with {len(chart_files)} charts")
    
    return report


def create_complete_report(budget, insights_text, chart_files):
    """
    Creates a complete Report object with budget analysis, insights, and charts
    
    Args:
        budget (Budget): Budget object with analysis data
        insights_text (str): AI-generated insights text
        chart_files (list): List of paths to chart image files
        
    Returns:
        Report: A complete Report instance
    """
    # Create a basic report
    report = create_report(budget)
    
    # Set insights
    report.set_insights(insights_text)
    
    # Add charts
    report.add_charts(chart_files)
    
    logger.info(f"Created complete report with insights and {len(chart_files)} charts")
    
    return report