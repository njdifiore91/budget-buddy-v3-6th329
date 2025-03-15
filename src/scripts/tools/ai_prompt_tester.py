# src/scripts/tools/ai_prompt_tester.py
#!/usr/bin/env python3
"""
A utility tool for testing and optimizing AI prompts used in the Budget Management Application.
This script allows developers to experiment with different prompt variations for transaction categorization and insight generation,
evaluate their effectiveness, and compare results against baseline prompts.
"""

import argparse  # standard library
import os  # standard library
import json  # standard library
import time  # standard library
from typing import Dict, List, Optional, Any, Union  # standard library
import pandas  # pandas 2.1.0+
import matplotlib.pyplot as plt  # matplotlib 3.7.0+

# Internal imports
from ...backend.api_clients.gemini_client import GeminiClient, load_prompt_template  # src/backend/api_clients/gemini_client.py
from ...backend.services.authentication_service import AuthenticationService  # src/backend/services/authentication_service.py
from ..config.script_settings import SCRIPT_SETTINGS, API_TEST_SETTINGS  # src/scripts/config/script_settings.py
from ..config.logging_setup import get_logger, LoggingContext  # src/scripts/config/logging_setup.py
from .api_testing import test_gemini_api  # src/scripts/utils/api_testing.py
from .test_categorization import run_categorization_test  # src/scripts/utils/test_categorization.py

# Initialize global logger
logger = get_logger('ai_prompt_tester')

# Define default output directory for test results
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'prompt_tests')

# Define available prompt types and their corresponding template files
PROMPT_TYPES = {'categorization': 'categorization_prompt.txt', 'insight': 'insight_generation_prompt.txt', 'custom': None}


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments for the script

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(description='Test Gemini AI prompt performance')
    parser.add_argument('--type', type=str, required=True, choices=PROMPT_TYPES.keys(),
                        help='Type of prompt to test (categorization, insight, custom)')
    parser.add_argument('--prompt-file', type=str,
                        help='Path to prompt file (optional, overrides default template)')
    parser.add_argument('--prompt-text', type=str,
                        help='Prompt text to use directly (optional, overrides file and template)')
    parser.add_argument('--test-data', type=str,
                        help='Path to test data (JSON format, required for categorization and insight prompts)')
    parser.add_argument('--output-dir', type=str, default=DEFAULT_OUTPUT_DIR,
                        help=f'Output directory for results (default: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('--compare', action='store_true',
                        help='Compare performance against baseline prompt')
    parser.add_argument('--baseline', type=str,
                        help='Path to baseline prompt file for comparison')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--visualize', action='store_true',
                        help='Generate visualizations of results')
    return parser.parse_args()


def load_prompt(prompt_type: str, prompt_file: Optional[str] = None, prompt_text: Optional[str] = None) -> str:
    """
    Load a prompt template from file or use provided text

    Args:
        prompt_type (str): Type of prompt (categorization, insight, custom)
        prompt_file (Optional[str], optional): Path to prompt file. Defaults to None.
        prompt_text (Optional[str], optional): Prompt text to use directly. Defaults to None.

    Returns:
        str: Loaded prompt template
    """
    if prompt_text:
        return prompt_text

    if prompt_file:
        try:
            with open(prompt_file, 'r') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_file}")
            return None

    template_name = PROMPT_TYPES.get(prompt_type)
    if template_name:
        try:
            return load_prompt_template(template_name)
        except ValueError as e:
            logger.error(f"Error loading prompt template: {e}")
            return None

    logger.error("No valid prompt source provided")
    return None


def test_prompt(prompt: str, prompt_type: str, test_data: Optional[str] = None) -> Dict[str, Any]:
    """
    Test a prompt with Gemini AI and measure performance

    Args:
        prompt (str): The prompt to test
        prompt_type (str): Type of prompt (categorization, insight, custom)
        test_data (Optional[str], optional): Path to test data. Defaults to None.

    Returns:
        Dict[str, Any]: Test results including response, metrics, and timing
    """
    start_time = time.time()
    auth_service = AuthenticationService()
    gemini_client = GeminiClient(auth_service)
    gemini_client.authenticate()

    if prompt_type == 'categorization':
        # Load test data for categorization
        try:
            with open(test_data, 'r') as f:
                test_data_json = json.load(f)
                transactions = test_data_json.get('transactions', [])
                categories = test_data_json.get('categories', [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading test data: {e}")
            return {'error': str(e)}

        # Run categorization test
        results = run_categorization_test(transactions, categories, custom_prompt=prompt)
        execution_time = time.time() - start_time
        results['execution_time'] = execution_time
        return results

    elif prompt_type == 'insight':
        # Generate insights with test data
        pass  # Implement insight generation logic here

    elif prompt_type == 'custom':
        # Generate completion with prompt
        completion = gemini_client.generate_completion(prompt)
        execution_time = time.time() - start_time
        return {'response': completion, 'execution_time': execution_time}

    else:
        logger.error(f"Invalid prompt type: {prompt_type}")
        return {'error': f"Invalid prompt type: {prompt_type}"}


def compare_prompts(prompt_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compare performance of multiple prompts

    Args:
        prompt_results (List[Dict[str, Any]]): List of test results for each prompt

    Returns:
        Dict[str, Any]: Comparison results
    """
    # Extract metrics from each prompt result
    pass  # Implement prompt comparison logic here


def visualize_results(results: Dict[str, Any], comparison_mode: bool, output_dir: str) -> bool:
    """
    Create visualizations of prompt test results

    Args:
        results (Dict[str, Any]): Test results
        comparison_mode (bool): Whether to create comparison charts
        output_dir (str): Output directory for visualizations

    Returns:
        bool: True if visualization was successful
    """
    # Implement visualization logic here
    pass


def save_results(results: Dict[str, Any], output_dir: str, prompt_type: str) -> str:
    """
    Save test results to JSON file

    Args:
        results (Dict[str, Any]): Test results
        output_dir (str): Output directory for results
        prompt_type (str): Type of prompt being tested

    Returns:
        str: Path to saved results file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Generate timestamp-based filename
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"prompt_test_{prompt_type}_{timestamp}.json")

    # Add metadata to results (timestamp, prompt_type)
    results['timestamp'] = timestamp
    results['prompt_type'] = prompt_type

    # Write results to JSON file
    try:
        with open(filename, 'w') as f:
            json.dump(results, f, indent=4)
        logger.info(f"Saved results to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Error saving results to file: {e}")
        return None


def main() -> int:
    """
    Main function to run the prompt testing tool

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    args = parse_args()

    # Set up logging based on verbose flag
    if args.verbose:
        logger.setLevel('DEBUG')

    # Load prompt(s) based on arguments
    prompt = load_prompt(args.type, args.prompt_file, args.prompt_text)
    if not prompt:
        logger.error("Failed to load prompt, exiting")
        return 1

    # If comparison mode, test multiple prompts
    if args.compare:
        pass  # Implement comparison mode logic here
    else:
        # Test single prompt
        results = test_prompt(prompt, args.type, args.test_data)
        if not results or 'error' in results:
            logger.error(f"Test failed: {results.get('error', 'Unknown error')}")
            return 1

        # If visualization requested, create visualizations
        if args.visualize:
            pass  # Implement visualization logic here

        # Save results to output directory
        output_file = save_results(results, args.output_dir, args.type)
        if not output_file:
            logger.error("Failed to save results")
            return 1

        # Print summary of results
        logger.info(f"Test completed successfully. Results saved to {output_file}")

    return 0


if __name__ == "__main__":
    exit(main())