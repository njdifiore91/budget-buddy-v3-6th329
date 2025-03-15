"""
A utility script for generating realistic test data for the Budget Management Application.
This script creates various types of test data including transactions, categories, budgets, and API responses,
and saves them as fixture files for use in testing and development.
"""

import os  # standard library
import sys  # standard library
import argparse  # standard library
import json  # standard library
import logging  # standard library
from datetime import datetime  # standard library
from decimal import Decimal  # standard library
from typing import List, Dict, Any, Optional, Union  # standard library

from src.scripts.config.script_settings import DEVELOPMENT_SETTINGS  # Access development script settings including test data count
from src.scripts.config.path_constants import ROOT_DIR, ensure_dir_exists  # Access to project root directory path
from src.test.utils.test_data_generator import TestDataGenerator  # Generate test data for various models and scenarios
from src.test.utils.fixture_loader import save_fixture  # Save generated data to fixture files
from src.backend.models.transaction import Transaction  # Access Transaction model for test data generation
from src.backend.models.category import Category  # Access Category model for test data generation
from src.backend.models.budget import Budget  # Access Budget model for test data generation

# Set up logger
logger = logging.getLogger(__name__)

# Define default output directory for generated fixtures
DEFAULT_OUTPUT_DIR = os.path.join(ROOT_DIR, 'src', 'test', 'fixtures', 'json')

# Define valid scenario types
SCENARIO_TYPES = ['surplus', 'deficit', 'balanced', 'error', 'empty', 'large']


def setup_logging():
    """
    Configure logging for the script
    """
    # Configure logging format with timestamp, level, and message
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=log_format, level=logging.INFO)

    # Set logging level based on verbosity flag
    verbosity = args.verbosity
    if verbosity == 0:
        logger.setLevel(logging.WARNING)
    elif verbosity == 1:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)

    # Add console handler for log output
    handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(handler)


def parse_arguments():
    """
    Parse command line arguments for the script

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    # Create ArgumentParser with script description
    parser = argparse.ArgumentParser(description='Generate test data for Budget Management Application')

    # Add argument for count (number of items to generate)
    parser.add_argument('--count', type=int, default=DEVELOPMENT_SETTINGS['GENERATE_TEST_DATA_COUNT'],
                        help='Number of items to generate (default: {})'.format(DEVELOPMENT_SETTINGS['GENERATE_TEST_DATA_COUNT']))

    # Add argument for output directory
    parser.add_argument('--output_dir', type=str, default=DEFAULT_OUTPUT_DIR,
                        help='Output directory for generated files (default: {})'.format(DEFAULT_OUTPUT_DIR))

    # Add argument for scenario type
    parser.add_argument('--scenario', type=str, choices=SCENARIO_TYPES,
                        help='Generate a specific test scenario (surplus, deficit, balanced, error, empty, large)')

    # Add argument for verbosity
    parser.add_argument('--verbosity', type=int, default=1, choices=[0, 1, 2],
                        help='Increase output verbosity (0=Error, 1=Info, 2=Debug)')

    # Parse and return command line arguments
    return parser.parse_args()


def generate_transaction_fixtures(generator: TestDataGenerator, count: int, output_dir: str) -> Dict[str, str]:
    """
    Generate transaction fixture files

    Args:
        generator: TestDataGenerator instance
        count: Number of transactions to generate
        output_dir: Output directory for generated files

    Returns:
        Dict[str, str]: Dictionary mapping fixture types to file paths
    """
    # Generate valid transactions with categories
    valid_transactions = generator.generate_transactions(count)
    valid_transactions_path = save_fixture([t.to_dict() for t in valid_transactions], os.path.join(output_dir, 'valid_transactions.json'))

    # Generate invalid transactions for error testing
    invalid_transactions = generator.generate_transactions(count, params={'location': None, 'amount': 'invalid'})
    invalid_transactions_path = save_fixture([t.to_dict() for t in invalid_transactions], os.path.join(output_dir, 'invalid_transactions.json'))

    # Generate large volume transactions for performance testing
    large_transactions = generator.generate_transactions(count * 10)
    large_transactions_path = save_fixture([t.to_dict() for t in large_transactions], os.path.join(output_dir, 'large_transactions.json'))

    # Generate transaction dictionaries in Capital One API format
    capital_one_transactions = generator.generate_capital_one_transactions(count)
    capital_one_transactions_path = save_fixture(capital_one_transactions, os.path.join(output_dir, 'capital_one_transactions.json'))

    # Save API format transactions to fixture file
    api_format_transactions_path = save_fixture(capital_one_transactions, os.path.join(output_dir, 'api_format_transactions.json'))

    # Return dictionary with paths to generated files
    return {
        'valid_transactions': valid_transactions_path,
        'invalid_transactions': invalid_transactions_path,
        'large_transactions': large_transactions_path,
        'api_format_transactions': api_format_transactions_path
    }


def generate_category_fixtures(generator: TestDataGenerator, output_dir: str) -> Dict[str, str]:
    """
    Generate category fixture files

    Args:
        generator: TestDataGenerator instance
        output_dir: Output directory for generated files

    Returns:
        Dict[str, str]: Dictionary mapping fixture types to file paths
    """
    # Generate standard budget categories
    standard_categories = generator.generate_categories(5)
    standard_categories_path = save_fixture([c.to_dict() for c in standard_categories], os.path.join(output_dir, 'standard_categories.json'))

    # Generate categories with zero budget for edge cases
    zero_budget_categories = generator.generate_categories(3, params={'min_amount': 0, 'max_amount': 0})
    zero_budget_categories_path = save_fixture([c.to_dict() for c in zero_budget_categories], os.path.join(output_dir, 'zero_budget_categories.json'))

    # Generate categories with very large budget for edge cases
    large_budget_categories = generator.generate_categories(2, params={'min_amount': 1000, 'max_amount': 5000})
    large_budget_categories_path = save_fixture([c.to_dict() for c in large_budget_categories], os.path.join(output_dir, 'large_budget_categories.json'))

    # Save each category set to a fixture file
    all_categories_path = save_fixture([c.to_dict() for c in standard_categories + zero_budget_categories + large_budget_categories], os.path.join(output_dir, 'all_categories.json'))

    # Generate category dictionaries in Google Sheets format
    sheets_format_categories = generator.generate_sheets_data('master_budget')
    sheets_format_categories_path = save_fixture(sheets_format_categories, os.path.join(output_dir, 'sheets_format_categories.json'))

    # Return dictionary with paths to generated files
    return {
        'standard_categories': standard_categories_path,
        'zero_budget_categories': zero_budget_categories_path,
        'large_budget_categories': large_budget_categories_path,
        'all_categories': all_categories_path,
        'sheets_format_categories': sheets_format_categories_path
    }


def generate_budget_fixtures(generator: TestDataGenerator, output_dir: str) -> Dict[str, str]:
    """
    Generate budget fixture files

    Args:
        generator: TestDataGenerator instance
        output_dir: Output directory for generated files

    Returns:
        Dict[str, str]: Dictionary mapping fixture types to file paths
    """
    # Generate budget with surplus (under budget)
    surplus_budget = generator.generate_test_scenario('surplus')
    surplus_budget_path = save_fixture(surplus_budget, os.path.join(output_dir, 'surplus_budget.json'))

    # Generate budget with deficit (over budget)
    deficit_budget = generator.generate_test_scenario('deficit')
    deficit_budget_path = save_fixture(deficit_budget, os.path.join(output_dir, 'deficit_budget.json'))

    # Generate balanced budget (exactly on budget)
    balanced_budget = generator.generate_test_scenario('balanced')
    balanced_budget_path = save_fixture(balanced_budget, os.path.join(output_dir, 'balanced_budget.json'))

    # Generate empty budget with no transactions
    empty_budget = generator.generate_test_scenario('empty')
    empty_budget_path = save_fixture(empty_budget, os.path.join(output_dir, 'empty_budget.json'))

    # Save each budget to a fixture file
    all_budgets_path = save_fixture([surplus_budget, deficit_budget, balanced_budget, empty_budget], os.path.join(output_dir, 'all_budgets.json'))

    # Generate budget analysis dictionaries
    budget_analysis_path = save_fixture(surplus_budget.get('budget'), os.path.join(output_dir, 'budget_analysis.json'))

    # Save budget analysis to fixture file
    budget_analysis_path = save_fixture(surplus_budget.get('budget'), os.path.join(output_dir, 'budget_analysis.json'))

    # Return dictionary with paths to generated files
    return {
        'surplus_budget': surplus_budget_path,
        'deficit_budget': deficit_budget_path,
        'balanced_budget': balanced_budget_path,
        'empty_budget': empty_budget_path,
        'all_budgets': all_budgets_path,
        'budget_analysis': budget_analysis_path
    }


def generate_api_response_fixtures(generator: TestDataGenerator, output_dir: str) -> Dict[str, str]:
    """
    Generate mock API response fixture files

    Args:
        generator: TestDataGenerator instance
        output_dir: Output directory for generated files

    Returns:
        Dict[str, str]: Dictionary mapping fixture types to file paths
    """
    # Generate Capital One API response fixtures (transactions, accounts, transfers)
    capital_one_transactions = generator.generate_capital_one_transactions(5)
    capital_one_transactions_path = save_fixture(capital_one_transactions, os.path.join(output_dir, 'capital_one_transactions.json'))

    # Generate Google Sheets API response fixtures (budget data, transaction data)
    google_sheets_budget_data = generator.generate_sheets_data('master_budget')
    google_sheets_budget_data_path = save_fixture(google_sheets_budget_data, os.path.join(output_dir, 'google_sheets_budget_data.json'))

    # Generate Gemini API response fixtures (categorization, insights)
    gemini_categorization = generator.generate_gemini_response('categorization')
    gemini_categorization_path = save_fixture(gemini_categorization, os.path.join(output_dir, 'gemini_categorization.json'))

    gemini_insights = generator.generate_gemini_response('insights')
    gemini_insights_path = save_fixture(gemini_insights, os.path.join(output_dir, 'gemini_insights.json'))

    # Generate Gmail API response fixtures (email confirmation)
    gmail_email_confirmation = {'status': 'success', 'message_id': '12345'}
    gmail_email_confirmation_path = save_fixture(gmail_email_confirmation, os.path.join(output_dir, 'gmail_email_confirmation.json'))

    # Generate error response fixtures for each API
    capital_one_error = {'status': 'error', 'message': 'Capital One API error'}
    capital_one_error_path = save_fixture(capital_one_error, os.path.join(output_dir, 'capital_one_error.json'))

    google_sheets_error = {'status': 'error', 'message': 'Google Sheets API error'}
    google_sheets_error_path = save_fixture(google_sheets_error, os.path.join(output_dir, 'google_sheets_error.json'))

    gemini_error = {'status': 'error', 'message': 'Gemini API error'}
    gemini_error_path = save_fixture(gemini_error, os.path.join(output_dir, 'gemini_error.json'))

    gmail_error = {'status': 'error', 'message': 'Gmail API error'}
    gmail_error_path = save_fixture(gmail_error, os.path.join(output_dir, 'gmail_error.json'))

    # Save each API response to appropriate fixture file
    api_responses = {
        'capital_one_transactions': capital_one_transactions_path,
        'google_sheets_budget_data': google_sheets_budget_data_path,
        'gemini_categorization': gemini_categorization_path,
        'gemini_insights': gemini_insights_path,
        'gmail_email_confirmation': gmail_email_confirmation_path,
        'capital_one_error': capital_one_error_path,
        'google_sheets_error': google_sheets_error_path,
        'gemini_error': gemini_error_path,
        'gmail_error': gmail_error_path
    }

    # Return dictionary with paths to generated files
    return api_responses


def generate_scenario_fixtures(generator: TestDataGenerator, scenario_type: str, output_dir: str) -> str:
    """
    Generate complete test scenario fixture files

    Args:
        generator: TestDataGenerator instance
        scenario_type: Type of scenario to generate (surplus, deficit, balanced, error, empty, large)
        output_dir: Output directory for generated files

    Returns:
        str: Path to the generated scenario fixture file
    """
    # Generate the specified scenario type using TestDataGenerator
    scenario_data = generator.generate_test_scenario(scenario_type)

    # Save the complete scenario to a fixture file
    scenario_path = save_fixture(scenario_data, os.path.join(output_dir, f'{scenario_type}_scenario.json'))

    # Return the path to the generated fixture file
    return scenario_path


def main():
    """
    Main function to execute the script
    """
    # Parse command line arguments
    global args
    args = parse_arguments()

    # Setup logging based on verbosity
    setup_logging()

    # Create output directory if it doesn't exist
    ensure_dir_exists(args.output_dir)

    # Initialize TestDataGenerator
    generator = TestDataGenerator()

    # Generate transaction fixtures
    transaction_fixtures = generate_transaction_fixtures(generator, args.count, args.output_dir)

    # Generate category fixtures
    category_fixtures = generate_category_fixtures(generator, args.output_dir)

    # Generate budget fixtures
    budget_fixtures = generate_budget_fixtures(generator, args.output_dir)

    # Generate API response fixtures
    api_response_fixtures = generate_api_response_fixtures(generator, args.output_dir)

    # Generate scenario fixtures if scenario type specified
    if args.scenario:
        scenario_path = generate_scenario_fixtures(generator, args.scenario, args.output_dir)
        logger.info(f"Generated scenario fixture: {scenario_path}")

    # Log summary of generated files
    logger.info(f"Generated transaction fixtures: {transaction_fixtures}")
    logger.info(f"Generated category fixtures: {category_fixtures}")
    logger.info(f"Generated budget fixtures: {budget_fixtures}")
    logger.info(f"Generated API response fixtures: {api_response_fixtures}")

    # Return success exit code
    return 0


if __name__ == "__main__":
    sys.exit(main())