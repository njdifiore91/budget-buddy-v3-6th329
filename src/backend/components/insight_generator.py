"""
insight_generator.py - Component for generating AI-powered spending insights and visualizations

This component is responsible for creating a comprehensive analysis of spending patterns
using Gemini AI. It transforms raw budget analysis data into actionable insights and
visualizations for the weekly budget report.
"""

import os  # standard library
import time  # standard library
import logging  # standard library
from typing import Dict, List, Optional, Any  # standard library

# Visualization libraries
import matplotlib.pyplot as plt  # matplotlib 3.7.0+
import seaborn as sns  # seaborn 0.12.0+

# Internal imports
from ..api_clients.gemini_client import GeminiClient
from ..models.report import Report, create_report, create_complete_report
from ..utils.formatters import format_budget_analysis_for_ai
from ..services.logging_service import get_component_logger
from ..services.error_handling_service import ErrorHandlingContext
from ..utils.error_handlers import retry_with_backoff, APIError, ValidationError
from ..services.authentication_service import AuthenticationService

# Set up logger for this component
logger = get_component_logger('insight_generator')

# Directory for storing chart images
CHART_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp', 'charts')


def ensure_chart_directory() -> str:
    """
    Ensures the chart directory exists for storing generated chart images.
    
    Returns:
        Path to the chart directory
    """
    try:
        if not os.path.exists(CHART_DIR):
            os.makedirs(CHART_DIR, exist_ok=True)
            logger.info(f"Created chart directory at {CHART_DIR}")
        
        return CHART_DIR
    except Exception as e:
        logger.error(f"Failed to create chart directory: {str(e)}")
        raise


def create_category_comparison_chart(budget_analysis: Dict) -> str:
    """
    Creates a horizontal bar chart comparing budget vs. actual spending by category.
    
    Args:
        budget_analysis: Dictionary containing budget analysis data
        
    Returns:
        Path to the saved chart file
    """
    try:
        # Extract category analysis data
        category_variances = budget_analysis.get('category_analysis', {})
        
        # Prepare data for chart
        categories = []
        budget_amounts = []
        actual_amounts = []
        
        # Sort categories by variance (optionally by variance percentage)
        sorted_categories = sorted(
            category_variances.items(),
            key=lambda x: x[1]['variance_amount']
        )
        
        # Extract data for the chart
        for category_name, details in sorted_categories:
            categories.append(category_name)
            budget_amounts.append(float(details['budget_amount']))
            actual_amounts.append(float(details['actual_amount']))
        
        # Set up the figure with appropriate size
        plt.figure(figsize=(10, max(6, len(categories) * 0.4)))
        
        # Create horizontal bar chart using seaborn
        sns.set_style("whitegrid")
        
        # Create DataFrame for seaborn
        import pandas as pd
        df = pd.DataFrame({
            'Category': categories,
            'Budget': budget_amounts,
            'Actual': actual_amounts
        })
        
        # Reshape the DataFrame for seaborn
        df_melted = df.melt(id_vars='Category', var_name='Type', value_name='Amount')
        
        # Create chart
        chart = sns.barplot(
            x='Amount',
            y='Category',
            hue='Type',
            data=df_melted,
            palette=['#2C82C9', '#EF6D3B']
        )
        
        # Customize chart
        plt.title('Weekly Spending by Category', fontsize=14)
        plt.xlabel('Amount ($)', fontsize=12)
        plt.ylabel('Category', fontsize=12)
        plt.tight_layout()
        
        # Ensure chart directory exists
        chart_dir = ensure_chart_directory()
        
        # Save chart to file with timestamp
        timestamp = int(time.time())
        chart_path = os.path.join(chart_dir, f"category_comparison_{timestamp}.png")
        plt.savefig(chart_path, dpi=100, bbox_inches='tight')
        
        # Close the figure to free memory
        plt.close()
        
        logger.info(f"Created category comparison chart at {chart_path}")
        return chart_path
    
    except Exception as e:
        logger.error(f"Failed to create category comparison chart: {str(e)}")
        raise


def create_budget_overview_chart(budget_analysis: Dict) -> str:
    """
    Creates a pie chart showing overall budget allocation and spending.
    
    Args:
        budget_analysis: Dictionary containing budget analysis data
        
    Returns:
        Path to the saved chart file
    """
    try:
        # Extract total values
        total_budget = float(budget_analysis.get('total_budget', 0))
        total_spent = float(budget_analysis.get('total_spent', 0))
        total_variance = float(budget_analysis.get('total_variance', 0))
        
        # Set up the figure
        plt.figure(figsize=(8, 8))
        
        # Create data for pie chart
        if total_variance > 0:
            # Budget surplus case
            labels = ['Spent', 'Remaining']
            sizes = [total_spent, total_variance]
            colors = ['#3498db', '#2ecc71']  # Blue for spent, green for remaining
        else:
            # Budget deficit case
            labels = ['Budget', 'Overspent']
            sizes = [total_budget, abs(total_variance)]
            colors = ['#3498db', '#e74c3c']  # Blue for budget, red for overspent
        
        # Create pie chart
        plt.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            shadow=False,
            wedgeprops={'edgecolor': 'white', 'linewidth': 1}
        )
        
        # Equal aspect ratio ensures that pie is drawn as a circle
        plt.axis('equal')
        
        # Set title based on budget status
        if total_variance >= 0:
            plt.title(f'Weekly Budget Overview\n${total_variance:.2f} Under Budget', fontsize=14)
        else:
            plt.title(f'Weekly Budget Overview\n${abs(total_variance):.2f} Over Budget', fontsize=14)
        
        # Ensure chart directory exists
        chart_dir = ensure_chart_directory()
        
        # Save chart to file with timestamp
        timestamp = int(time.time())
        chart_path = os.path.join(chart_dir, f"budget_overview_{timestamp}.png")
        plt.savefig(chart_path, dpi=100, bbox_inches='tight')
        
        # Close the figure to free memory
        plt.close()
        
        logger.info(f"Created budget overview chart at {chart_path}")
        return chart_path
    
    except Exception as e:
        logger.error(f"Failed to create budget overview chart: {str(e)}")
        raise


class InsightGenerator:
    """Component responsible for generating spending insights and visualizations"""
    
    def __init__(self, gemini_client: Optional[GeminiClient] = None, 
                 auth_service: Optional[AuthenticationService] = None):
        """
        Initialize the InsightGenerator component.
        
        Args:
            gemini_client: Optional pre-configured Gemini API client
            auth_service: Optional authentication service for API access
        """
        # Initialize authentication service
        self.auth_service = auth_service if auth_service else AuthenticationService()
        
        # Initialize Gemini client
        self.gemini_client = gemini_client if gemini_client else GeminiClient(self.auth_service)
        
        # Initialize correlation ID
        self.correlation_id = None
        
        logger.info("InsightGenerator component initialized")
    
    def authenticate(self) -> bool:
        """
        Authenticate with Gemini AI API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        logger.info("Authenticating with Gemini AI API")
        
        try:
            result = self.gemini_client.authenticate()
            
            if result:
                logger.info("Successfully authenticated with Gemini AI API")
            else:
                logger.error("Failed to authenticate with Gemini AI API")
            
            return result
        
        except Exception as e:
            logger.error(f"Authentication with Gemini AI failed: {str(e)}")
            return False
    
    @retry_with_backoff(exceptions=(APIError,), max_retries=3)
    def generate_insights(self, budget_analysis: Dict) -> str:
        """
        Generate natural language insights using Gemini AI.
        
        Args:
            budget_analysis: Budget analysis data
            
        Returns:
            Generated insights text
        """
        logger.info("Generating spending insights with Gemini AI")
        
        try:
            # Format budget analysis data for AI prompt
            formatted_analysis = format_budget_analysis_for_ai(budget_analysis)
            
            # Call Gemini API to generate insights
            insights = self.gemini_client.generate_spending_insights(budget_analysis)
            
            logger.info(f"Successfully generated insights ({len(insights)} characters)")
            return insights
            
        except APIError as e:
            logger.error(f"Failed to generate insights with Gemini AI: {str(e)}")
            raise
        
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            raise APIError(
                f"Insight generation failed: {str(e)}",
                "Gemini",
                "generate_insights"
            )
    
    def create_visualizations(self, budget_analysis: Dict) -> List[str]:
        """
        Create chart visualizations for budget analysis.
        
        Args:
            budget_analysis: Budget analysis data
            
        Returns:
            List of paths to generated chart files
        """
        logger.info("Creating data visualizations for budget analysis")
        
        try:
            chart_files = []
            
            # Create category comparison chart
            category_chart = create_category_comparison_chart(budget_analysis)
            chart_files.append(category_chart)
            
            # Create budget overview chart
            overview_chart = create_budget_overview_chart(budget_analysis)
            chart_files.append(overview_chart)
            
            logger.info(f"Successfully created {len(chart_files)} visualizations")
            return chart_files
            
        except Exception as e:
            logger.error(f"Failed to create visualizations: {str(e)}")
            # Return empty list if chart creation fails
            return []
    
    def create_report(self, budget_analysis: Dict) -> Report:
        """
        Create a complete report with insights and visualizations.
        
        Args:
            budget_analysis: Budget analysis data
            
        Returns:
            Complete report object with insights and charts
        """
        logger.info("Creating complete budget report with insights and visualizations")
        
        try:
            # Extract budget from analysis
            budget = budget_analysis.get('budget', {})
            
            # Generate AI insights
            insights = self.generate_insights(budget_analysis)
            
            # Create chart visualizations
            chart_files = self.create_visualizations(budget_analysis)
            
            # Create complete report
            report = create_complete_report(budget, insights, chart_files)
            
            logger.info("Successfully created complete report")
            return report
            
        except Exception as e:
            logger.error(f"Failed to create report: {str(e)}")
            raise
    
    def execute(self, previous_status: Dict) -> Dict:
        """
        Execute the insight generation process.
        
        Args:
            previous_status: Status information from previous component
            
        Returns:
            Execution status and report
        """
        start_time = time.time()
        logger.info("Starting insight generation process")
        
        try:
            # Extract data from previous status
            self.correlation_id = previous_status.get('correlation_id')
            budget_analysis = previous_status.get('budget_analysis', {})
            
            with ErrorHandlingContext(logger, 'insight_generation', 
                                     {'correlation_id': self.correlation_id}):
                # Authenticate with Gemini API
                auth_success = self.authenticate()
                
                if not auth_success:
                    return {
                        'status': 'error',
                        'message': 'Failed to authenticate with Gemini AI API',
                        'correlation_id': self.correlation_id,
                        'component': 'insight_generator'
                    }
                
                # Create complete report with insights and visualizations
                report = self.create_report(budget_analysis)
                
                # Calculate execution time
                execution_time = time.time() - start_time
                
                # Return success status with report
                result = {
                    'status': 'success',
                    'report': report,
                    'correlation_id': self.correlation_id,
                    'execution_time': execution_time,
                    'component': 'insight_generator'
                }
                
                logger.info(f"Insight generation process completed in {execution_time:.2f} seconds")
                return result
                
        except Exception as e:
            logger.error(f"Error in insight generation process: {str(e)}")
            
            # Return error status
            execution_time = time.time() - start_time
            return {
                'status': 'error',
                'message': f"Insight generation failed: {str(e)}",
                'correlation_id': self.correlation_id,
                'execution_time': execution_time,
                'component': 'insight_generator'
            }
    
    def check_health(self) -> Dict:
        """
        Check health of API connections.
        
        Returns:
            Health status of each integration
        """
        health_status = {}
        
        try:
            # Check Gemini API
            gemini_status = self.authenticate()
            health_status['gemini_api'] = 'healthy' if gemini_status else 'unhealthy'
            
            logger.info(f"Health check completed: {health_status}")
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            health_status['gemini_api'] = f'unhealthy: {str(e)}'
            return health_status