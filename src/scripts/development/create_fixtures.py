"""
A utility script for generating and saving test fixtures for the Budget Management Application.
This script creates realistic test data for transactions, budget categories, API responses,
and expected results, which are used in unit, integration, and end-to-end tests.
"""

import os  # File path operations and directory management
import json  # JSON serialization for fixture files
import argparse  # Command-line argument parsing
import logging  # Logging script execution and errors
from datetime import datetime  # Date and time handling for test data
from decimal import Decimal  # Precise decimal arithmetic for financial test data
from typing import List, Dict, Any, Optional  # Type hints for better code documentation

# Internal imports
from ...config.path_constants import ROOT_DIR, ensure_dir_exists  # Access to project root directory path
from ...config.script_settings import DEVELOPMENT_SETTINGS  # Access development script settings
from ...test.utils.test_data_generator import TestDataGenerator  # Generate test data for fixtures
from ...test.utils.fixture_loader import save_fixture, get_fixture_path  # Get the path to fixture files

# Set up logger
logger = logging.getLogger(__name__)

# Constants
FIXTURE_TYPES = ['transactions', 'budget', 'api_responses', 'expected']
SCENARIO_TYPES = ['surplus', 'deficit', 'balanced', 'error', 'empty', 'large']
DEFAULT_COUNT = DEVELOPMENT_SETTINGS.get('GENERATE_TEST_DATA_COUNT', 50)


def setup_logging() -> None:
    """Configure logging for the script"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for the script"""
    parser = argparse.ArgumentParser(description='Generate test fixtures for the Budget Management Application.')
    parser.add_argument(
        'fixture_type',
        choices=FIXTURE_TYPES,
        help='Type of fixture to generate'
    )
    parser.add_argument(
        '--scenario_type',
        choices=SCENARIO_TYPES,
        help='Type of scenario to generate (optional, only for scenario fixtures)'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=DEFAULT_COUNT,
        help='Number of transactions or categories to generate (default: {})'.format(DEFAULT_COUNT)
    )
    parser.add_argument(
        '--output_dir',
        type=str,
        default=None,
        help='Output directory for the generated fixtures (default: None)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing fixtures if they exist'
    )
    return parser.parse_args()


def create_transaction_fixtures(count: int, output_dir: str, force: bool) -> List[str]:
    """Create transaction fixture files"""
    generator = TestDataGenerator()
    transactions = generator.generate_transactions(count)
    fixture_path = os.path.join(output_dir, 'transactions.json')
    save_fixture(transactions, fixture_path)
    logger.info(f"Created transaction fixture: {fixture_path}")
    return [fixture_path]


def create_budget_fixtures(output_dir: str, force: bool) -> List[str]:
    """Create budget fixture files"""
    generator = TestDataGenerator()
    categories = generator.generate_categories(5)
    budget_data = generator.generate_budget(categories=categories)
    fixture_path = os.path.join(output_dir, 'budget.json')
    save_fixture(budget_data, fixture_path)
    logger.info(f"Created budget fixture: {fixture_path}")
    return [fixture_path]


def create_api_response_fixtures(output_dir: str, force: bool) -> List[str]:
    """Create API response fixture files"""
    generator = TestDataGenerator()
    api_responses = {
        'capital_one': generator.generate_capital_one_transactions(10),
        'gemini': generator.generate_gemini_response('insights')
    }
    fixture_paths = []
    for api, response in api_responses.items():
        fixture_path = os.path.join(output_dir, f'{api}_response.json')
        save_fixture(response, fixture_path)
        fixture_paths.append(fixture_path)
        logger.info(f"Created API response fixture: {fixture_path}")
    return fixture_paths


def create_expected_result_fixtures(output_dir: str, force: bool) -> List[str]:
    """Create expected result fixture files"""
    generator = TestDataGenerator()
    expected_results = {
        'categorized_transactions': [],
        'budget_analysis': {}
    }
    fixture_paths = []
    for result_type, result in expected_results.items():
        fixture_path = os.path.join(output_dir, f'{result_type}.json')
        save_fixture(result, fixture_path)
        fixture_paths.append(fixture_path)
        logger.info(f"Created expected result fixture: {fixture_path}")
    return fixture_paths


def create_scenario_fixtures(scenario_type: str, output_dir: str, force: bool) -> List[str]:
    """Create complete test scenario fixtures"""
    generator = TestDataGenerator()
    scenario_data = generator.generate_test_scenario(scenario_type)
    fixture_paths = []
    for data_type, data in scenario_data.items():
        fixture_path = os.path.join(output_dir, f'{data_type}.json')
        save_fixture(data, fixture_path)
        fixture_paths.append(fixture_path)
        logger.info(f"Created scenario fixture: {fixture_path}")
    return fixture_paths


def check_fixture_exists(fixture_path: str) -> bool:
    """Check if a fixture file already exists"""
    return os.path.exists(fixture_path)


def main() -> int:
    """Main function to execute the script"""
    try:
        setup_logging()
        args = parse_arguments()

        # Determine output directory
        output_dir = args.output_dir or os.path.join(ROOT_DIR, 'test', 'fixtures', 'json', args.fixture_type)
        ensure_dir_exists(output_dir)

        # Create fixtures based on fixture_type argument
        if args.fixture_type == 'transactions':
            create_transaction_fixtures(args.count, output_dir, args.force)
        elif args.fixture_type == 'budget':
            create_budget_fixtures(output_dir, args.force)
        elif args.fixture_type == 'api_responses':
            create_api_response_fixtures(output_dir, args.force)
        elif args.fixture_type == 'expected':
            create_expected_result_fixtures(output_dir, args.force)
        else:
            logger.error(f"Unknown fixture type: {args.fixture_type}")
            return 1

        return 0

    except Exception as e:
        logger.exception(f"An error occurred: {e}")
        return 1


# Run the main function if the script is executed
if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)