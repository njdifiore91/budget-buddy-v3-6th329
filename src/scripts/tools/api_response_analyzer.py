#!/usr/bin/env python3
"""
API Response Analyzer Tool for the Budget Management Application.

This utility tool helps analyze API responses from external services, validate
response structures, identify patterns, and generate statistics about API behavior.
It supports responses from Capital One, Google Sheets, Gemini, and Gmail APIs.
"""

import os
import sys
import json
import argparse
import datetime
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional, Union, Tuple

import tabulate  # tabulate 0.9.0+
import jsonschema  # jsonschema 4.17.0+

from ...config.path_constants import ROOT_DIR, LOGS_DIR
from ...config.script_settings import API_TEST_SETTINGS
from ...config.logging_setup import get_logger
from ...utils.api_testing import (
    test_capital_one_api,
    test_google_sheets_api,
    test_gemini_api,
    test_gmail_api,
    validate_api_response
)

# Set up logger
logger = get_logger('api_response_analyzer')

# Define supported API services
API_SERVICES = ['capital_one', 'google_sheets', 'gemini', 'gmail']

# Define response types for each API
RESPONSE_TYPES = {
    'capital_one': ['transactions', 'account', 'transfer', 'transfer_status'],
    'google_sheets': ['read', 'write', 'batch_update'],
    'gemini': ['completion', 'categorization'],
    'gmail': ['send', 'status']
}

# Define supported output formats
OUTPUT_FORMATS = ['json', 'table', 'summary', 'schema']


def load_response_file(file_path: str) -> Dict[str, Any]:
    """
    Loads an API response from a JSON file.
    
    Args:
        file_path: Path to the JSON file containing the API response
        
    Returns:
        Loaded response data or empty dict if file not found
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        else:
            logger.warning(f"Response file not found: {file_path}")
            return {}
    except Exception as e:
        logger.error(f"Error loading response file {file_path}: {str(e)}")
        return {}


def save_response_file(response: Dict[str, Any], file_path: str) -> bool:
    """
    Saves an API response to a JSON file.
    
    Args:
        response: API response data to save
        file_path: Path where to save the response
        
    Returns:
        True if save was successful, False otherwise
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Write the response with pretty formatting
        with open(file_path, 'w') as f:
            json.dump(response, f, indent=2, sort_keys=True)
        
        logger.info(f"Response saved to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving response to {file_path}: {str(e)}")
        return False


def generate_response_schema(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates a JSON schema from an API response.
    
    Args:
        response: API response to generate schema for
        
    Returns:
        Generated JSON schema
    """
    def _infer_type(value: Any) -> Dict[str, Any]:
        """Helper function to infer the JSON Schema type of a value"""
        if value is None:
            return {"type": "null"}
        elif isinstance(value, bool):
            return {"type": "boolean"}
        elif isinstance(value, int):
            return {"type": "integer"}
        elif isinstance(value, float):
            return {"type": "number"}
        elif isinstance(value, str):
            return {"type": "string"}
        elif isinstance(value, list):
            if not value:
                return {"type": "array", "items": {}}
            # Sample the first few items to determine array item types
            samples = value[:min(10, len(value))]
            item_types = [_infer_type(item) for item in samples]
            # If all items are the same type, use that
            if all(t == item_types[0] for t in item_types):
                return {"type": "array", "items": item_types[0]}
            # Otherwise, allow multiple types
            return {"type": "array", "items": {"oneOf": item_types}}
        elif isinstance(value, dict):
            return {
                "type": "object",
                "properties": {k: _infer_type(v) for k, v in value.items()},
                "required": list(value.keys())
            }
        else:
            return {"type": "string", "description": f"Unknown type: {type(value).__name__}"}
    
    # Start with basic schema structure
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {},
        "required": []
    }
    
    # Only process dictionary responses
    if not isinstance(response, dict):
        logger.warning("Cannot generate schema for non-dictionary response")
        return schema
    
    # Generate properties and required fields
    for key, value in response.items():
        schema["properties"][key] = _infer_type(value)
        schema["required"].append(key)
    
    return schema


def extract_response_patterns(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts common patterns from an API response.
    
    Args:
        response: API response to analyze
        
    Returns:
        Extracted patterns and statistics
    """
    patterns = {
        "structure": {
            "keys": [],
            "depth": 0,
            "array_keys": [],
            "object_keys": []
        },
        "data_types": defaultdict(int),
        "patterns": {
            "date_fields": [],
            "id_fields": [],
            "status_fields": [],
            "numeric_fields": []
        },
        "error_patterns": {
            "has_error": False,
            "error_keys": [],
            "error_messages": []
        }
    }
    
    def _analyze_value(value, path="", depth=0):
        """Recursively analyze values in the response"""
        # Track maximum depth
        if depth > patterns["structure"]["depth"]:
            patterns["structure"]["depth"] = depth
        
        # Count data types
        value_type = type(value).__name__
        patterns["data_types"][value_type] += 1
        
        # Analyze based on data type
        if isinstance(value, dict):
            # Add object keys
            if path:
                patterns["structure"]["object_keys"].append(path)
            
            # Check for error patterns
            if "error" in value or "errorMessage" in value or "errors" in value:
                patterns["error_patterns"]["has_error"] = True
                
                # Extract error information
                for err_key in ["error", "errorMessage", "errorType", "errorCode", "message"]:
                    if err_key in value:
                        patterns["error_patterns"]["error_keys"].append(err_key)
                        if isinstance(value[err_key], str):
                            patterns["error_patterns"]["error_messages"].append(value[err_key])
            
            # Recursively analyze dictionary values
            for k, v in value.items():
                new_path = f"{path}.{k}" if path else k
                
                # Collect all keys
                if new_path not in patterns["structure"]["keys"]:
                    patterns["structure"]["keys"].append(new_path)
                
                # Check for specific field patterns
                lower_k = k.lower()
                if "date" in lower_k or "time" in lower_k:
                    patterns["patterns"]["date_fields"].append(new_path)
                elif "id" in lower_k and isinstance(v, (str, int)):
                    patterns["patterns"]["id_fields"].append(new_path)
                elif "status" in lower_k:
                    patterns["patterns"]["status_fields"].append(new_path)
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    patterns["patterns"]["numeric_fields"].append(new_path)
                
                # Continue recursion
                _analyze_value(v, new_path, depth + 1)
        
        elif isinstance(value, list):
            # Add array keys
            if path:
                patterns["structure"]["array_keys"].append(path)
            
            # Analyze array items (limit to first 10 for performance)
            for i, item in enumerate(value[:10]):
                item_path = f"{path}[{i}]"
                _analyze_value(item, item_path, depth + 1)
    
    # Start the recursive analysis if response is a dictionary
    if isinstance(response, dict):
        _analyze_value(response)
    
    # Convert defaultdict to regular dict for serialization
    patterns["data_types"] = dict(patterns["data_types"])
    
    return patterns


def compare_responses(response1: Dict[str, Any], response2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compares two API responses and identifies differences.
    
    Args:
        response1: First API response
        response2: Second API response
        
    Returns:
        Comparison results with differences
    """
    comparison = {
        "identical": False,
        "structural_differences": {
            "keys_only_in_first": [],
            "keys_only_in_second": [],
            "keys_in_both": []
        },
        "value_differences": {},
        "type_differences": {},
        "similarity_score": 0.0
    }
    
    # Only compare dictionaries
    if not isinstance(response1, dict) or not isinstance(response2, dict):
        comparison["identical"] = False
        comparison["error"] = "Cannot compare non-dictionary responses"
        return comparison
    
    # Get all keys from both responses
    keys1 = set(response1.keys())
    keys2 = set(response2.keys())
    
    # Find keys that are only in one response
    comparison["structural_differences"]["keys_only_in_first"] = list(keys1 - keys2)
    comparison["structural_differences"]["keys_only_in_second"] = list(keys2 - keys1)
    comparison["structural_differences"]["keys_in_both"] = list(keys1.intersection(keys2))
    
    # Compare values for common keys
    common_keys = keys1.intersection(keys2)
    different_values = 0
    type_differences = 0
    
    for key in common_keys:
        value1 = response1[key]
        value2 = response2[key]
        
        # Check for type differences
        if type(value1) != type(value2):
            comparison["type_differences"][key] = {
                "first_type": type(value1).__name__,
                "second_type": type(value2).__name__
            }
            type_differences += 1
        
        # Check for value differences (simple equality check)
        if value1 != value2:
            different_values += 1
            comparison["value_differences"][key] = {
                "first": value1 if not isinstance(value1, (dict, list)) else "...",
                "second": value2 if not isinstance(value2, (dict, list)) else "..."
            }
    
    # Calculate similarity score
    total_keys = len(keys1.union(keys2))
    if total_keys > 0:
        # Score based on common keys and matching values
        key_score = len(common_keys) / total_keys
        value_score = 1.0 if not common_keys else (len(common_keys) - different_values) / len(common_keys)
        comparison["similarity_score"] = round((key_score + value_score) / 2 * 100, 2)
    
    # Set identical flag
    comparison["identical"] = comparison["similarity_score"] == 100.0
    
    return comparison


def generate_response_statistics(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates statistics about an API response.
    
    Args:
        response: API response to analyze
        
    Returns:
        Response statistics
    """
    statistics = {
        "size": {
            "bytes": len(json.dumps(response)),
            "keys": 0,
            "total_items": 0
        },
        "data_types": {
            "strings": 0,
            "numbers": 0,
            "booleans": 0,
            "arrays": 0,
            "objects": 0,
            "nulls": 0
        },
        "structure": {
            "depth": 0,
            "max_array_length": 0,
            "arrays_count": 0,
            "objects_count": 0
        }
    }
    
    def _analyze_stats(value, depth=0):
        """Recursively analyze the response to generate statistics"""
        nonlocal statistics
        
        # Update depth
        if depth > statistics["structure"]["depth"]:
            statistics["structure"]["depth"] = depth
        
        # Count by data type
        if value is None:
            statistics["data_types"]["nulls"] += 1
        elif isinstance(value, str):
            statistics["data_types"]["strings"] += 1
        elif isinstance(value, bool):
            statistics["data_types"]["booleans"] += 1
        elif isinstance(value, (int, float)):
            statistics["data_types"]["numbers"] += 1
        elif isinstance(value, list):
            statistics["data_types"]["arrays"] += 1
            statistics["structure"]["arrays_count"] += 1
            if len(value) > statistics["structure"]["max_array_length"]:
                statistics["structure"]["max_array_length"] = len(value)
            for item in value:
                _analyze_stats(item, depth + 1)
        elif isinstance(value, dict):
            statistics["data_types"]["objects"] += 1
            statistics["structure"]["objects_count"] += 1
            statistics["size"]["keys"] += len(value)
            for k, v in value.items():
                _analyze_stats(v, depth + 1)
    
    # Only analyze dictionary responses
    if isinstance(response, dict):
        _analyze_stats(response)
        statistics["size"]["keys"] = statistics["size"]["keys"]
        statistics["size"]["total_items"] = sum(statistics["data_types"].values())
    
    return statistics


def format_output(results: Dict[str, Any], format_type: str) -> str:
    """
    Formats analysis results according to specified format.
    
    Args:
        results: Analysis results to format
        format_type: Output format (json, table, summary, schema)
        
    Returns:
        Formatted output string
    """
    if format_type not in OUTPUT_FORMATS:
        logger.warning(f"Invalid format type: {format_type}. Using 'json' format.")
        format_type = 'json'
    
    if format_type == 'json':
        return json.dumps(results, indent=2, sort_keys=True)
    
    elif format_type == 'table':
        output = []
        
        # Handle different result types
        if "schema" in results:
            # Format schema
            output.append("JSON Schema:")
            output.append(json.dumps(results["schema"], indent=2))
        
        if "statistics" in results:
            # Format statistics as tables
            output.append("\nResponse Statistics:")
            
            # Size statistics
            size_data = [
                ["Bytes", results["statistics"]["size"]["bytes"]],
                ["Keys", results["statistics"]["size"]["keys"]],
                ["Total Items", results["statistics"]["size"]["total_items"]]
            ]
            output.append("\nSize Statistics:")
            output.append(tabulate.tabulate(size_data, headers=["Metric", "Value"]))
            
            # Data type statistics
            type_data = [[k, v] for k, v in results["statistics"]["data_types"].items()]
            output.append("\nData Type Statistics:")
            output.append(tabulate.tabulate(type_data, headers=["Type", "Count"]))
            
            # Structure statistics
            structure_data = [[k, v] for k, v in results["statistics"]["structure"].items()]
            output.append("\nStructure Statistics:")
            output.append(tabulate.tabulate(structure_data, headers=["Metric", "Value"]))
        
        if "patterns" in results:
            # Format patterns
            output.append("\nResponse Patterns:")
            
            # Data field patterns
            if "patterns" in results["patterns"]:
                for pattern_type, fields in results["patterns"]["patterns"].items():
                    if fields:
                        output.append(f"\n{pattern_type.replace('_', ' ').title()}:")
                        output.append(tabulate.tabulate([[field] for field in fields], headers=["Field"]))
            
            # Error patterns
            if "error_patterns" in results["patterns"] and results["patterns"]["error_patterns"]["has_error"]:
                output.append("\nError Patterns:")
                if results["patterns"]["error_patterns"]["error_keys"]:
                    output.append("Error Keys: " + ", ".join(results["patterns"]["error_patterns"]["error_keys"]))
                if results["patterns"]["error_patterns"]["error_messages"]:
                    output.append("Error Messages:")
                    for msg in results["patterns"]["error_patterns"]["error_messages"]:
                        output.append(f"- {msg}")
        
        if "comparison" in results:
            # Format comparison results
            output.append("\nResponse Comparison:")
            output.append(f"Similarity Score: {results['comparison']['similarity_score']}%")
            output.append(f"Identical: {results['comparison']['identical']}")
            
            if results["comparison"]["structural_differences"]["keys_only_in_first"]:
                output.append("\nKeys only in first response:")
                output.append(tabulate.tabulate([[k] for k in results["comparison"]["structural_differences"]["keys_only_in_first"]], headers=["Key"]))
            
            if results["comparison"]["structural_differences"]["keys_only_in_second"]:
                output.append("\nKeys only in second response:")
                output.append(tabulate.tabulate([[k] for k in results["comparison"]["structural_differences"]["keys_only_in_second"]], headers=["Key"]))
            
            if results["comparison"]["type_differences"]:
                diff_data = [[k, v["first_type"], v["second_type"]] for k, v in results["comparison"]["type_differences"].items()]
                output.append("\nType Differences:")
                output.append(tabulate.tabulate(diff_data, headers=["Field", "First Type", "Second Type"]))
        
        return "\n".join(output)
    
    elif format_type == 'summary':
        # Create a concise summary of the analysis
        summary = []
        
        if "api_name" in results:
            summary.append(f"API: {results['api_name']}")
        if "operation" in results and results["operation"]:
            summary.append(f"Operation: {results['operation']}")
        if "timestamp" in results:
            summary.append(f"Analysis Time: {results['timestamp']}")
        
        # Add statistics summary
        if "statistics" in results:
            stats = results["statistics"]
            summary.append("\nResponse Overview:")
            summary.append(f"- Size: {stats['size']['bytes']} bytes, {stats['size']['keys']} keys")
            summary.append(f"- Structure: Depth {stats['structure']['depth']}, {stats['structure']['objects_count']} objects, "
                          f"{stats['structure']['arrays_count']} arrays")
            summary.append(f"- Data Types: {stats['data_types']['strings']} strings, {stats['data_types']['numbers']} numbers, "
                          f"{stats['data_types']['booleans']} booleans, {stats['data_types']['nulls']} nulls")
        
        # Add pattern summary
        if "patterns" in results:
            patterns = results["patterns"]
            summary.append("\nKey Patterns:")
            
            if "patterns" in patterns:
                pattern_counts = {
                    "Date Fields": len(patterns["patterns"].get("date_fields", [])),
                    "ID Fields": len(patterns["patterns"].get("id_fields", [])),
                    "Status Fields": len(patterns["patterns"].get("status_fields", [])),
                    "Numeric Fields": len(patterns["patterns"].get("numeric_fields", []))
                }
                for pattern, count in pattern_counts.items():
                    if count > 0:
                        summary.append(f"- {pattern}: {count}")
            
            # Add error summary
            if "error_patterns" in patterns and patterns["error_patterns"]["has_error"]:
                summary.append("\nError Information:")
                if patterns["error_patterns"]["error_messages"]:
                    summary.append(f"- Error Message: {patterns['error_patterns']['error_messages'][0]}")
        
        # Add comparison summary
        if "comparison" in results:
            comp = results["comparison"]
            summary.append("\nComparison Results:")
            summary.append(f"- Similarity: {comp['similarity_score']}%")
            summary.append(f"- Unique Keys in First: {len(comp['structural_differences']['keys_only_in_first'])}")
            summary.append(f"- Unique Keys in Second: {len(comp['structural_differences']['keys_only_in_second'])}")
            summary.append(f"- Value Differences: {len(comp['value_differences'])}")
            summary.append(f"- Type Differences: {len(comp['type_differences'])}")
        
        return "\n".join(summary)
    
    elif format_type == 'schema':
        # Return just the schema if it exists
        if "schema" in results:
            return json.dumps(results["schema"], indent=2)
        else:
            return "Schema not available in results"
    
    return "Unsupported format type"


def get_sample_response(api_name: str, operation: Optional[str] = None) -> Dict[str, Any]:
    """
    Gets a sample response from the specified API.
    
    Args:
        api_name: Name of the API (capital_one, google_sheets, gemini, gmail)
        operation: Optional operation to get specific response type
        
    Returns:
        Sample API response
    """
    # Validate API name
    if api_name not in API_SERVICES:
        logger.error(f"Invalid API name: {api_name}")
        return {"error": f"Invalid API name: {api_name}"}
    
    # Check if using mock responses
    if API_TEST_SETTINGS['USE_MOCK_RESPONSES']:
        logger.info(f"Using mock response for {api_name}")
        # Construct mock response file path
        file_path = os.path.join(
            API_TEST_SETTINGS['MOCK_RESPONSE_DIR'],
            api_name,
            f"{operation or 'test'}.json"
        )
        response = load_response_file(file_path)
        if response:
            return response
        else:
            logger.warning(f"Mock response not found for {api_name}/{operation or 'test'}")
    
    try:
        # Call appropriate API test function
        if api_name == 'capital_one':
            response = test_capital_one_api()
        elif api_name == 'google_sheets':
            response = test_google_sheets_api()
        elif api_name == 'gemini':
            response = test_gemini_api()
        elif api_name == 'gmail':
            response = test_gmail_api()
        else:
            logger.error(f"Unsupported API: {api_name}")
            return {"error": f"Unsupported API: {api_name}"}
        
        # If specific operation requested, extract that part of the response
        if operation and response and "details" in response:
            if operation in response["details"]:
                return response["details"][operation]
            else:
                logger.warning(f"Operation {operation} not found in {api_name} response")
        
        return response
    except Exception as e:
        logger.error(f"Error getting sample response for {api_name}: {str(e)}")
        return {"error": f"Failed to get sample response: {str(e)}"}


def analyze_response(response: Dict[str, Any], api_name: str, operation: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyzes an API response and generates comprehensive analysis.
    
    Args:
        response: API response to analyze
        api_name: Name of the API the response is from
        operation: Optional operation name for context
        
    Returns:
        Analysis results
    """
    # Initialize analysis results
    results = {
        "api_name": api_name,
        "operation": operation,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "is_error_response": False
    }
    
    # Check if the response is an error response
    if isinstance(response, dict) and (
        "error" in response or 
        "errorMessage" in response or 
        "errors" in response or
        (response.get("status") == "error") or
        (response.get("status") == "failed")
    ):
        results["is_error_response"] = True
        
        # Add error details
        results["error_details"] = {}
        for error_key in ["error", "errorMessage", "errorType", "errorCode", "message", "error_message"]:
            if error_key in response:
                results["error_details"][error_key] = response[error_key]
    
    # Generate schema
    results["schema"] = generate_response_schema(response)
    
    # Extract patterns
    results["patterns"] = extract_response_patterns(response)
    
    # Generate statistics
    results["statistics"] = generate_response_statistics(response)
    
    return results


def parse_args():
    """
    Parses command line arguments for the tool.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="API Response Analyzer Tool for the Budget Management Application"
    )
    
    parser.add_argument(
        "--api", 
        choices=API_SERVICES, 
        help="API to analyze (capital_one, google_sheets, gemini, gmail)"
    )
    
    parser.add_argument(
        "--operation", 
        help="Specific API operation to analyze"
    )
    
    parser.add_argument(
        "--input", 
        help="Input file containing API response to analyze"
    )
    
    parser.add_argument(
        "--output", 
        help="Output file to write the analysis results to"
    )
    
    parser.add_argument(
        "--format", 
        choices=OUTPUT_FORMATS, 
        default="json", 
        help="Output format (json, table, summary, schema)"
    )
    
    parser.add_argument(
        "--compare", 
        help="Compare with another response file"
    )
    
    return parser.parse_args()


def main() -> int:
    """
    Main function to run the API response analyzer.
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    # Parse command line arguments
    args = parse_args()
    
    # Load API response
    response = None
    if args.input:
        logger.info(f"Loading response from file: {args.input}")
        response = load_response_file(args.input)
        if not response:
            logger.error(f"Failed to load response from {args.input}")
            return 1
    elif args.api:
        logger.info(f"Getting sample response for {args.api}")
        response = get_sample_response(args.api, args.operation)
    else:
        logger.error("Either --api or --input must be specified")
        return 1
    
    # Analyze the response
    logger.info("Analyzing API response")
    analysis_results = analyze_response(response, args.api if args.api else "unknown", args.operation)
    
    # Compare with another response if requested
    if args.compare:
        logger.info(f"Comparing with response from file: {args.compare}")
        comparison_response = load_response_file(args.compare)
        if comparison_response:
            analysis_results["comparison"] = compare_responses(response, comparison_response)
        else:
            logger.error(f"Failed to load comparison response from {args.compare}")
    
    # Format the output
    logger.info(f"Formatting output as {args.format}")
    formatted_output = format_output(analysis_results, args.format)
    
    # Output the results
    if args.output:
        logger.info(f"Writing results to {args.output}")
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            f.write(formatted_output)
    else:
        print(formatted_output)
    
    logger.info("Analysis completed successfully")
    return 0


class ResponseAnalyzer:
    """
    Class for analyzing API responses with advanced features.
    """
    
    def __init__(self):
        """
        Initialize the ResponseAnalyzer.
        """
        self._responses = {}
        self._schemas = {}
        self._patterns = {}
        self._statistics = {}
        logger.info("ResponseAnalyzer initialized")
    
    def add_response(self, response: Dict[str, Any], api_name: str, operation: Optional[str] = None) -> None:
        """
        Add a response to the analyzer.
        
        Args:
            response: API response to add
            api_name: Name of the API the response is from
            operation: Optional operation name for context
        """
        # Create a key from api_name and operation
        key = f"{api_name}/{operation}" if operation else api_name
        
        # Store the response
        self._responses[key] = response
        
        # Generate and store analysis
        self._schemas[key] = generate_response_schema(response)
        self._patterns[key] = extract_response_patterns(response)
        self._statistics[key] = generate_response_statistics(response)
        
        logger.info(f"Added response for {key}")
    
    def load_response_from_file(self, file_path: str, api_name: str, operation: Optional[str] = None) -> bool:
        """
        Load a response from a file.
        
        Args:
            file_path: Path to the response file
            api_name: Name of the API the response is from
            operation: Optional operation name for context
            
        Returns:
            True if loading was successful
        """
        response = load_response_file(file_path)
        if response:
            self.add_response(response, api_name, operation)
            logger.info(f"Loaded response from {file_path}")
            return True
        else:
            logger.error(f"Failed to load response from {file_path}")
            return False
    
    def get_sample_response(self, api_name: str, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a sample response from an API.
        
        Args:
            api_name: Name of the API
            operation: Optional operation name
            
        Returns:
            Sample response
        """
        response = get_sample_response(api_name, operation)
        if response:
            self.add_response(response, api_name, operation)
        
        logger.info(f"Got sample response for {api_name}/{operation or ''}")
        return response
    
    def get_schema(self, api_name: str, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the schema for a response.
        
        Args:
            api_name: Name of the API
            operation: Optional operation name
            
        Returns:
            Schema for the response
        """
        key = f"{api_name}/{operation}" if operation else api_name
        schema = self._schemas.get(key, {})
        logger.info(f"Retrieved schema for {key}")
        return schema
    
    def get_patterns(self, api_name: str, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the patterns for a response.
        
        Args:
            api_name: Name of the API
            operation: Optional operation name
            
        Returns:
            Patterns for the response
        """
        key = f"{api_name}/{operation}" if operation else api_name
        patterns = self._patterns.get(key, {})
        logger.info(f"Retrieved patterns for {key}")
        return patterns
    
    def get_statistics(self, api_name: str, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the statistics for a response.
        
        Args:
            api_name: Name of the API
            operation: Optional operation name
            
        Returns:
            Statistics for the response
        """
        key = f"{api_name}/{operation}" if operation else api_name
        statistics = self._statistics.get(key, {})
        logger.info(f"Retrieved statistics for {key}")
        return statistics
    
    def compare_responses(self, api_name1: str, operation1: Optional[str], 
                         api_name2: str, operation2: Optional[str]) -> Dict[str, Any]:
        """
        Compare two responses.
        
        Args:
            api_name1: Name of the first API
            operation1: Optional operation name for first API
            api_name2: Name of the second API
            operation2: Optional operation name for second API
            
        Returns:
            Comparison results
        """
        key1 = f"{api_name1}/{operation1}" if operation1 else api_name1
        key2 = f"{api_name2}/{operation2}" if operation2 else api_name2
        
        if key1 not in self._responses or key2 not in self._responses:
            logger.error(f"One or both responses not found: {key1}, {key2}")
            return {"error": "One or both responses not found"}
        
        comparison = compare_responses(self._responses[key1], self._responses[key2])
        logger.info(f"Compared responses: {key1} vs {key2}")
        return comparison
    
    def generate_report(self, api_name: str, operation: Optional[str] = None, format_type: str = "json") -> str:
        """
        Generate a comprehensive report for a response.
        
        Args:
            api_name: Name of the API
            operation: Optional operation name
            format_type: Output format
            
        Returns:
            Formatted report
        """
        key = f"{api_name}/{operation}" if operation else api_name
        
        if key not in self._responses:
            logger.error(f"Response not found: {key}")
            return f"Response not found: {key}"
        
        # Compile report data
        report_data = {
            "api_name": api_name,
            "operation": operation,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "schema": self._schemas.get(key, {}),
            "patterns": self._patterns.get(key, {}),
            "statistics": self._statistics.get(key, {})
        }
        
        # Format the report
        formatted_report = format_output(report_data, format_type)
        logger.info(f"Generated report for {key} in {format_type} format")
        return formatted_report
    
    def save_report(self, api_name: str, operation: Optional[str] = None, 
                   file_path: str, format_type: str = "json") -> bool:
        """
        Save a report to a file.
        
        Args:
            api_name: Name of the API
            operation: Optional operation name
            file_path: Path to save the report
            format_type: Output format
            
        Returns:
            True if save was successful
        """
        report = self.generate_report(api_name, operation, format_type)
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            # Write report to file
            with open(file_path, "w") as f:
                f.write(report)
            
            logger.info(f"Saved report to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving report to {file_path}: {str(e)}")
            return False


if __name__ == "__main__":
    sys.exit(main())