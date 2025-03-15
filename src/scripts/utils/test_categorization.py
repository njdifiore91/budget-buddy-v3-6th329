#!/usr/bin/env python3
"""
Utility script for testing the transaction categorization functionality of the Budget Management Application.

This script evaluates the accuracy of Gemini AI-powered categorization by comparing results against
expected categories and generating performance metrics.
"""

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Union, Tuple, Any

# Internal imports
from ...backend.components.transaction_categorizer import TransactionCategorizer
from ...backend.api_clients.gemini_client import GeminiClient, load_prompt_template
from ...backend.models.transaction import Transaction
from ...backend.models.category import Category
from .sheet_operations import get_sheets_client, get_budget_categories, get_transactions
from ..config.script_settings import SCRIPT_SETTINGS, API_TEST_SETTINGS
from ..config.logging_setup import get_logger

# Set up logger
logger = get_logger('test_categorization')

def parse_args():
    """
    Parse command line arguments for the script
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Test Gemini AI transaction categorization accuracy'
    )
    parser.add_argument(
        '--source', 
        choices=['sheet', 'file'], 
        default='sheet',
        help='Source for test data (Google Sheets or local file)'
    )
    parser.add_argument(
        '--data-file', 
        type=str,
        help='Path to test data file (JSON format)'
    )
    parser.add_argument(
        '--output', 
        choices=['console', 'file', 'both'], 
        default='console',
        help='Output format for results'
    )
    parser.add_argument(
        '--output-file', 
        type=str,
        help='Path to output file for results'
    )
    parser.add_argument(
        '--visualize', 
        action='store_true',
        help='Generate visualizations of results'
    )
    parser.add_argument(
        '--custom-prompt', 
        type=str,
        help='Custom prompt for categorization'
    )
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser.parse_args()

def load_test_data(source: str, data_file: str) -> Tuple[List[Transaction], List[Category]]:
    """
    Load transaction and category data for testing
    
    Args:
        source: Source of test data ('sheet' or 'file')
        data_file: Path to test data file (when source is 'file')
        
    Returns:
        tuple: Tuple containing lists of transactions and categories
    """
    if source == 'sheet':
        # Get data from Google Sheets
        sheets_client = get_sheets_client()
        categories = get_budget_categories(sheets_client)
        transactions = get_transactions(sheets_client)
        logger.info(f"Loaded {len(transactions)} transactions and {len(categories)} categories from Google Sheets")
        return transactions, categories
    else:
        # Load from local file
        if not data_file:
            raise ValueError("Data file path is required when source is 'file'")
        
        with open(data_file, 'r') as f:
            data = json.load(f)
        
        if not isinstance(data, dict) or 'transactions' not in data or 'categories' not in data:
            raise ValueError("Invalid test data format")
        
        # Convert to Transaction and Category objects
        transactions = [Transaction(
            location=t['location'],
            amount=t['amount'],
            timestamp=t['timestamp'],
            category=t.get('expected_category')  # Store expected category
        ) for t in data['transactions']]
        
        categories = [Category(
            name=c['name'],
            weekly_amount=c['weekly_amount']
        ) for c in data['categories']]
        
        logger.info(f"Loaded {len(transactions)} transactions and {len(categories)} categories from file")
        return transactions, categories

def run_categorization_test(transactions: List[Transaction], categories: List[Category], 
                           custom_prompt: str = None) -> Dict:
    """
    Run categorization test using Gemini AI
    
    Args:
        transactions: List of transactions to test
        categories: List of categories to use for categorization
        custom_prompt: Optional custom prompt for categorization
        
    Returns:
        dict: Test results including categorization mapping and metrics
    """
    # Initialize GeminiClient
    gemini_client = GeminiClient(None)  # Will use default auth service
    gemini_client.authenticate()
    
    # Extract transaction locations and category names
    transaction_locations = [t.location for t in transactions]
    category_names = [c.name for c in categories]
    
    # Use custom prompt if provided, otherwise use default
    if custom_prompt:
        logger.info("Using custom prompt for categorization")
        prompt = custom_prompt
    else:
        prompt = API_TEST_SETTINGS.get('GEMINI_TEST_PROMPT')
        if not prompt:
            logger.info("Using default categorization prompt")
            prompt = None  # Will use the default prompt in the GeminiClient
    
    # Get expected categories
    expected_categories = {t.location: t.category for t in transactions if t.category}
    
    # Run categorization
    categorization_map = gemini_client.categorize_transactions(transaction_locations, category_names)
    
    # Create transaction categorizer to apply categories
    categorizer = TransactionCategorizer(gemini_client=gemini_client)
    categorized_transactions = categorizer.apply_categories(transactions, categorization_map)
    
    # Calculate metrics
    metrics = calculate_metrics(transactions, categorization_map, expected_categories)
    
    # Return results
    return {
        'transactions': [t.to_dict() for t in categorized_transactions],
        'categorization_map': categorization_map,
        'expected_categories': expected_categories,
        'metrics': metrics
    }

def calculate_metrics(transactions: List[Transaction], categorization_map: Dict[str, str],
                     expected_categories: Dict[str, str]) -> Dict:
    """
    Calculate accuracy metrics for categorization results
    
    Args:
        transactions: List of transactions
        categorization_map: Mapping of transaction locations to assigned categories
        expected_categories: Mapping of transaction locations to expected categories
        
    Returns:
        dict: Dictionary of accuracy metrics
    """
    total_transactions = len(transactions)
    categorized_count = len(categorization_map)
    uncategorized_count = total_transactions - categorized_count
    
    # Count transactions with expected categories
    expected_count = len(expected_categories)
    
    if expected_count == 0:
        logger.warning("No expected categories found, cannot calculate accuracy")
        return {
            'total_transactions': total_transactions,
            'categorized_count': categorized_count,
            'uncategorized_count': uncategorized_count,
            'expected_count': expected_count,
            'accuracy': None,
            'coverage': categorized_count / total_transactions if total_transactions > 0 else 0
        }
    
    # Count correct categorizations
    correct_count = 0
    incorrect_count = 0
    
    for location, expected in expected_categories.items():
        assigned = categorization_map.get(location)
        if assigned and assigned == expected:
            correct_count += 1
        elif assigned:
            incorrect_count += 1
    
    # Calculate accuracy
    accuracy = correct_count / expected_count if expected_count > 0 else 0
    
    # Calculate category-specific accuracy
    category_accuracy = {}
    category_counts = {}
    
    for location, expected in expected_categories.items():
        if expected not in category_counts:
            category_counts[expected] = 0
            category_accuracy[expected] = {'correct': 0, 'total': 0}
        
        category_counts[expected] += 1
        category_accuracy[expected]['total'] += 1
        
        assigned = categorization_map.get(location)
        if assigned and assigned == expected:
            category_accuracy[expected]['correct'] += 1
    
    # Calculate percentage accuracy for each category
    for category, counts in category_accuracy.items():
        counts['accuracy'] = counts['correct'] / counts['total'] if counts['total'] > 0 else 0
    
    return {
        'total_transactions': total_transactions,
        'categorized_count': categorized_count,
        'uncategorized_count': uncategorized_count,
        'expected_count': expected_count,
        'correct_count': correct_count,
        'incorrect_count': incorrect_count,
        'accuracy': accuracy,
        'coverage': categorized_count / total_transactions if total_transactions > 0 else 0,
        'category_accuracy': category_accuracy
    }

def generate_report(results: Dict, output_format: str, output_file: str = None) -> str:
    """
    Generate a report of categorization test results
    
    Args:
        results: Test results from run_categorization_test
        output_format: Format for output ('console', 'file', or 'both')
        output_file: Path to output file (when output_format includes 'file')
        
    Returns:
        str: Report content
    """
    metrics = results['metrics']
    categorization_map = results['categorization_map']
    expected_categories = results['expected_categories']
    
    # Format metrics for report
    report = "========== CATEGORIZATION TEST RESULTS ==========\n\n"
    report += f"Total transactions: {metrics['total_transactions']}\n"
    report += f"Categorized: {metrics['categorized_count']} ({metrics['coverage']:.2%})\n"
    report += f"Uncategorized: {metrics['uncategorized_count']}\n"
    
    if metrics['accuracy'] is not None:
        report += f"Transactions with expected categories: {metrics['expected_count']}\n"
        report += f"Correctly categorized: {metrics['correct_count']}\n"
        report += f"Incorrectly categorized: {metrics['incorrect_count']}\n"
        report += f"Accuracy: {metrics['accuracy']:.2%}\n\n"
    else:
        report += "No expected categories provided, accuracy metrics not available.\n\n"
    
    # Add detailed category accuracy
    if metrics.get('category_accuracy'):
        report += "Category-specific accuracy:\n"
        for category, data in sorted(metrics['category_accuracy'].items()):
            report += f"  {category}: {data['accuracy']:.2%} ({data['correct']}/{data['total']})\n"
        report += "\n"
    
    # Add transaction-by-transaction results
    if expected_categories:
        report += "Transaction results:\n"
        for location, expected in sorted(expected_categories.items()):
            assigned = categorization_map.get(location, "UNCATEGORIZED")
            status = "✓" if assigned == expected else "✗"
            report += f"  {status} {location}: expected '{expected}', got '{assigned}'\n"
    
    # Output the report
    if output_format in ['console', 'both']:
        print(report)
    
    if output_format in ['file', 'both']:
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"categorization_test_{timestamp}.txt"
        
        with open(output_file, 'w') as f:
            f.write(report)
        logger.info(f"Report saved to {output_file}")
    
    return report

def visualize_results(metrics: Dict, output_file: str = None) -> bool:
    """
    Create visualizations of categorization test results
    
    Args:
        metrics: Metrics from calculate_metrics
        output_file: Base path for output files
        
    Returns:
        bool: True if visualization was successful
    """
    try:
        # Create a figure for the main metrics
        plt.figure(figsize=(10, 6))
        
        # Overall accuracy bar chart
        labels = ['Coverage', 'Accuracy']
        values = [metrics['coverage'], metrics.get('accuracy', 0) or 0]
        
        plt.bar(labels, values, color=['blue', 'green'])
        plt.axhline(y=0.95, color='r', linestyle='--', label='Target (95%)')
        
        # Add percentage labels on top of bars
        for i, v in enumerate(values):
            plt.text(i, v + 0.02, f"{v:.2%}", ha='center')
        
        plt.title('Categorization Performance')
        plt.ylabel('Percentage')
        plt.ylim(0, 1.1)
        plt.legend()
        
        # Save or show the figure
        if output_file:
            metrics_file = f"{os.path.splitext(output_file)[0]}_metrics.png"
            plt.savefig(metrics_file)
            logger.info(f"Metrics visualization saved to {metrics_file}")
        else:
            plt.show()
        
        # Create category-specific accuracy chart if available
        if metrics.get('category_accuracy'):
            plt.figure(figsize=(12, 6))
            
            categories = list(metrics['category_accuracy'].keys())
            accuracy_values = [data['accuracy'] for data in metrics['category_accuracy'].values()]
            
            # Sort by accuracy
            sorted_indices = np.argsort(accuracy_values)
            sorted_categories = [categories[i] for i in sorted_indices]
            sorted_values = [accuracy_values[i] for i in sorted_indices]
            
            # Create horizontal bar chart
            y_pos = np.arange(len(sorted_categories))
            plt.barh(y_pos, sorted_values, color='skyblue')
            plt.yticks(y_pos, sorted_categories)
            plt.axvline(x=0.95, color='r', linestyle='--', label='Target (95%)')
            
            # Add percentage labels on bars
            for i, v in enumerate(sorted_values):
                plt.text(max(v + 0.02, 0.1), i, f"{v:.2%}", va='center')
            
            plt.title('Categorization Accuracy by Category')
            plt.xlabel('Accuracy')
            plt.xlim(0, 1.1)
            plt.tight_layout()
            plt.legend()
            
            # Save or show the figure
            if output_file:
                categories_file = f"{os.path.splitext(output_file)[0]}_categories.png"
                plt.savefig(categories_file)
                logger.info(f"Category visualization saved to {categories_file}")
            else:
                plt.show()
        
        return True
    
    except Exception as e:
        logger.error(f"Failed to visualize results: {str(e)}")
        return False

def save_test_results(results: Dict, output_file: str) -> bool:
    """
    Save test results to a JSON file
    
    Args:
        results: Test results from run_categorization_test
        output_file: Path to output file
        
    Returns:
        bool: True if save was successful
    """
    try:
        # Add timestamp to results
        results['timestamp'] = datetime.now().isoformat()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        
        # Save as JSON
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Test results saved to {output_file}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to save test results: {str(e)}")
        return False

class CategorizationTester:
    """Class for testing and evaluating transaction categorization accuracy"""
    
    def __init__(self, verbose=False):
        """
        Initialize the categorization tester
        
        Args:
            verbose: Whether to enable verbose logging
        """
        self.gemini_client = None
        self.transactions = []
        self.categories = []
        self.results = {}
        self.metrics = {}
        self.verbose = verbose
        logger.info("CategorizationTester initialized")
    
    def load_data(self, source: str, data_file: str = None) -> bool:
        """
        Load transaction and category data for testing
        
        Args:
            source: Source of test data ('sheet' or 'file')
            data_file: Path to test data file (when source is 'file')
            
        Returns:
            bool: True if data loading was successful
        """
        try:
            self.transactions, self.categories = load_test_data(source, data_file)
            logger.info(f"Loaded {len(self.transactions)} transactions and {len(self.categories)} categories")
            return True
        except Exception as e:
            logger.error(f"Failed to load test data: {str(e)}")
            return False
    
    def run_test(self, custom_prompt: str = None) -> Dict:
        """
        Run categorization test using Gemini AI
        
        Args:
            custom_prompt: Optional custom prompt for categorization
            
        Returns:
            dict: Test results
        """
        if not self.transactions or not self.categories:
            logger.error("No data loaded, call load_data() first")
            return {}
        
        try:
            self.results = run_categorization_test(
                self.transactions, 
                self.categories,
                custom_prompt
            )
            self.metrics = self.results.get('metrics', {})
            logger.info(f"Test completed with accuracy: {self.metrics.get('accuracy', 'N/A')}")
            return self.results
        except Exception as e:
            logger.error(f"Failed to run test: {str(e)}")
            return {}
    
    def generate_report(self, output_format: str = 'console', output_file: str = None) -> str:
        """
        Generate a report of test results
        
        Args:
            output_format: Format for output ('console', 'file', or 'both')
            output_file: Path to output file (when output_format includes 'file')
            
        Returns:
            str: Report content
        """
        if not self.results:
            logger.error("No test results available, call run_test() first")
            return ""
        
        return generate_report(self.results, output_format, output_file)
    
    def visualize(self, output_file: str = None) -> bool:
        """
        Create visualizations of test results
        
        Args:
            output_file: Base path for output files
            
        Returns:
            bool: True if visualization was successful
        """
        if not self.metrics:
            logger.error("No metrics available, call run_test() first")
            return False
        
        return visualize_results(self.metrics, output_file)
    
    def save_results(self, output_file: str) -> bool:
        """
        Save test results to a JSON file
        
        Args:
            output_file: Path to output file
            
        Returns:
            bool: True if save was successful
        """
        if not self.results:
            logger.error("No test results available, call run_test() first")
            return False
        
        return save_test_results(self.results, output_file)
    
    def get_metrics(self) -> Dict:
        """
        Get the calculated metrics from the test
        
        Returns:
            dict: Metrics dictionary
        """
        return self.metrics
    
    def get_results(self) -> Dict:
        """
        Get the complete test results
        
        Returns:
            dict: Results dictionary
        """
        return self.results

def main() -> int:
    """
    Main function to run the categorization test script
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    args = parse_args()
    
    # Configure logging based on verbosity
    if args.verbose or SCRIPT_SETTINGS.get('VERBOSE'):
        logger.setLevel('DEBUG')
    
    # Create tester instance
    tester = CategorizationTester(verbose=args.verbose)
    
    try:
        # Load test data
        if not tester.load_data(args.source, args.data_file):
            logger.error("Failed to load test data, exiting")
            return 1
        
        # Run the test
        results = tester.run_test(args.custom_prompt)
        if not results:
            logger.error("Test failed, exiting")
            return 1
        
        # Generate report
        tester.generate_report(args.output, args.output_file)
        
        # Visualize results if requested
        if args.visualize:
            tester.visualize(args.output_file)
        
        # Save results to JSON if output format includes file
        if args.output in ['file', 'both'] and args.output_file:
            json_file = f"{os.path.splitext(args.output_file)[0]}.json"
            tester.save_results(json_file)
        
        logger.info("Test completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())