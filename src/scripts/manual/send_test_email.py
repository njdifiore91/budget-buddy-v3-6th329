#!/usr/bin/env python3
"""
send_test_email.py - A utility script for manually sending test emails

This script allows developers and administrators to test the email delivery system
with sample budget reports without running the full weekly process.
"""

import os
import sys
import argparse
import logging
from decimal import Decimal
import dotenv

# Add src directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from backend.api_clients.gmail_client import GmailClient
from backend.services.authentication_service import AuthenticationService
from backend.models.budget import Budget
from backend.models.category import Category
from backend.models.report import Report, create_complete_report
from backend.components.insight_generator import InsightGenerator
from backend.config.settings import APP_SETTINGS

# Set up logger
logger = logging.getLogger(__name__)

def setup_logging():
    """Configure logging for the script"""
    # Get log level from environment variable or use INFO as default
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=numeric_level,
        stream=sys.stdout
    )
    
    logger.info(f"Logging initialized at level {log_level}")

def parse_arguments():
    """Parse command-line arguments for the script"""
    parser = argparse.ArgumentParser(
        description='Send a test email with budget report'
    )
    
    parser.add_argument(
        '--recipients', 
        type=str,
        help='Comma-separated list of email recipients'
    )
    
    parser.add_argument(
        '--subject', 
        type=str,
        help='Custom email subject'
    )
    
    parser.add_argument(
        '--use-sample-data', 
        action='store_true',
        help='Use sample budget data instead of real data'
    )
    
    parser.add_argument(
        '--skip-insights', 
        action='store_true',
        help='Skip AI insight generation and use sample insights'
    )
    
    parser.add_argument(
        '--skip-charts', 
        action='store_true',
        help='Skip chart generation'
    )
    
    return parser.parse_args()

def load_sample_budget_data():
    """Load sample budget data for testing"""
    # Create sample categories with weekly amounts
    categories = [
        Category("Groceries", Decimal("100.00")),
        Category("Dining Out", Decimal("75.00")),
        Category("Entertainment", Decimal("50.00")),
        Category("Transportation", Decimal("60.00")),
        Category("Shopping", Decimal("40.00"))
    ]
    
    # Create sample spending amounts
    actual_spending = {
        "Groceries": Decimal("85.75"),
        "Dining Out": Decimal("92.50"),
        "Entertainment": Decimal("25.00"),
        "Transportation": Decimal("45.30"),
        "Shopping": Decimal("65.25")
    }
    
    logger.debug(f"Created sample budget data with {len(categories)} categories")
    return categories, actual_spending

def create_sample_budget():
    """Create a sample Budget object for testing"""
    # Load sample budget data
    categories, actual_spending = load_sample_budget_data()
    
    # Create and analyze budget
    budget = Budget(categories, actual_spending)
    budget.analyze()
    
    logger.debug(f"Created sample budget: {budget}")
    return budget

def create_sample_insights(budget):
    """Create sample insights text for testing"""
    # Extract budget analysis data
    budget_data = budget.to_dict()
    
    # Extract key budget information
    total_budget = budget_data.get('total_budget', Decimal('0'))
    total_spent = budget_data.get('total_spent', Decimal('0'))
    total_variance = budget_data.get('total_variance', Decimal('0'))
    is_surplus = total_variance >= 0
    
    # Create sample insights text with budget status
    insights = f"""# Weekly Budget Report

## Budget Summary
You are {'under' if is_surplus else 'over'} budget by ${abs(total_variance):.2f} this week.

Total Budget: ${total_budget:.2f}
Total Spent: ${total_spent:.2f}
"""

    # Add category breakdown in insights
    insights += "\n## Category Breakdown\n"
    for category, details in budget_data.get('category_analysis', {}).items():
        budget_amount = details.get('budget_amount', 0)
        actual_amount = details.get('actual_amount', 0)
        variance_amount = details.get('variance_amount', 0)
        variance_percentage = details.get('variance_percentage', 0)
        status = "under budget" if variance_amount >= 0 else "over budget"
        
        insights += f"\n### {category}\n"
        insights += f"Budget: ${budget_amount:.2f}\n"
        insights += f"Actual: ${actual_amount:.2f}\n"
        insights += f"Variance: ${abs(variance_amount):.2f} ({abs(variance_percentage):.1f}%) {status}\n"
    
    # Add recommendations based on budget status
    insights += "\n## Recommendations\n"
    if is_surplus:
        insights += "- You're doing well staying under budget this week!\n"
        insights += "- Consider allocating the surplus to savings or investments.\n"
    else:
        insights += "- You've exceeded your budget this week. Consider reviewing your spending habits.\n"
        insights += "- Focus on reducing expenses in over-budget categories next week.\n"
    
    logger.debug(f"Created sample insights text ({len(insights)} characters)")
    return insights

def main():
    """Main function to execute the script"""
    # Set up logging
    setup_logging()
    logger.info("Starting send_test_email script")
    
    # Parse command-line arguments
    args = parse_arguments()
    
    # Load environment variables from .env if present
    dotenv.load_dotenv()
    
    try:
        # Create authentication service
        auth_service = AuthenticationService()
        
        # Create Gmail client
        gmail_client = GmailClient(auth_service)
        
        # Authenticate with Gmail API
        logger.info("Authenticating with Gmail API")
        if not gmail_client.authenticate():
            logger.error("Failed to authenticate with Gmail API")
            return 1
        
        # Create sample budget or load real budget data
        if args.use_sample_data:
            logger.info("Using sample budget data")
            budget = create_sample_budget()
        else:
            logger.error("Real budget data loading not implemented. Please use --use-sample-data flag")
            return 1
        
        # Generate insights (real or sample based on flags)
        if args.skip_insights:
            logger.info("Skipping AI insight generation, using sample insights")
            insights = create_sample_insights(budget)
        else:
            logger.info("Generating insights with Gemini AI")
            insight_generator = InsightGenerator(auth_service=auth_service)
            if not insight_generator.authenticate():
                logger.error("Failed to authenticate with Gemini AI")
                logger.info("Falling back to sample insights")
                insights = create_sample_insights(budget)
            else:
                insights = insight_generator.generate_insights(budget.to_dict())
        
        # Generate charts if not skipped
        chart_files = []
        if not args.skip_charts:
            logger.info("Generating charts")
            try:
                # Use the insight_generator if it was created above, otherwise create a new one
                if 'insight_generator' not in locals():
                    insight_generator = InsightGenerator(auth_service=auth_service)
                    if not insight_generator.authenticate():
                        logger.error("Failed to authenticate with Gemini AI for chart generation")
                        logger.info("Continuing without charts")
                    else:
                        chart_files = insight_generator.create_visualizations(budget.to_dict())
                else:
                    chart_files = insight_generator.create_visualizations(budget.to_dict())
                    
                logger.info(f"Generated {len(chart_files)} charts")
            except Exception as e:
                logger.error(f"Failed to generate charts: {e}")
                logger.info("Continuing without charts")
        
        # Create complete report with budget, insights, and charts
        logger.info("Creating complete report")
        report = create_complete_report(budget, insights, chart_files)
        
        # Get email content (subject and body) from report
        subject, body = report.get_email_content()
        
        # Override subject if provided in arguments
        if args.subject:
            logger.info(f"Using custom subject: {args.subject}")
            subject = args.subject
        
        # Get recipients from arguments or default settings
        if args.recipients:
            recipients = [r.strip() for r in args.recipients.split(',')]
            logger.info(f"Using custom recipients: {', '.join(recipients)}")
        else:
            recipients = APP_SETTINGS.get('EMAIL_RECIPIENTS', [])
            logger.info(f"Using default recipients: {', '.join(recipients)}")
        
        # Send email using GmailClient
        logger.info(f"Sending email to {len(recipients)} recipients")
        response = gmail_client.send_email(
            subject=subject,
            html_content=body,
            recipients=recipients,
            attachment_paths=chart_files
        )
        
        # Check if email was sent successfully
        if response.get('status') == 'success':
            message_id = response.get('message_id', '')
            logger.info(f"Email sent successfully with message ID: {message_id}")
            
            # Verify email delivery
            if message_id:
                verification = gmail_client.verify_delivery(message_id)
                logger.info(f"Delivery verification: {verification.get('status', 'unknown')}")
            
            return 0
        else:
            logger.error(f"Failed to send email: {response}")
            return 1
            
    except Exception as e:
        logger.exception(f"Error sending test email: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())