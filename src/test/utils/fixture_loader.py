"""
fixture_loader.py - Utility module for loading, managing, and converting test fixtures for the Budget Management Application.

Provides functions to load JSON test data from fixture files, convert raw data to model objects, and manage fixture paths.
Includes caching capabilities to improve test performance.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Union, TypeVar, Generic
from functools import lru_cache

from ...backend.models.transaction import Transaction, create_transaction
from ...backend.models.category import Category, create_category

# Set up logger
logger = logging.getLogger(__name__)

# Define fixture directories
FIXTURE_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fixtures')
JSON_FIXTURE_DIR = os.path.join(FIXTURE_BASE_DIR, 'json')
TRANSACTION_FIXTURE_DIR = os.path.join(JSON_FIXTURE_DIR, 'transactions')
BUDGET_FIXTURE_DIR = os.path.join(JSON_FIXTURE_DIR, 'budget')
API_RESPONSE_FIXTURE_DIR = os.path.join(JSON_FIXTURE_DIR, 'api_responses')
EXPECTED_FIXTURE_DIR = os.path.join(JSON_FIXTURE_DIR, 'expected')


def get_fixture_path(fixture_path: str, base_dir: Optional[str] = None) -> str:
    """
    Get the full path to a fixture file
    
    Args:
        fixture_path: Relative path to the fixture file
        base_dir: Base directory for fixtures, defaults to JSON_FIXTURE_DIR
        
    Returns:
        Full path to the fixture file
    """
    if base_dir is None:
        base_dir = JSON_FIXTURE_DIR
    
    full_path = os.path.join(base_dir, fixture_path)
    
    # Add .json extension if not present
    if not full_path.endswith('.json'):
        full_path += '.json'
    
    return full_path


@lru_cache(maxsize=128)
def load_fixture(fixture_path: str, base_dir: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Load a fixture file and parse its JSON content
    
    Args:
        fixture_path: Relative path to the fixture file
        base_dir: Base directory for fixtures, defaults to JSON_FIXTURE_DIR
        
    Returns:
        Parsed JSON data from the fixture file
    """
    full_path = get_fixture_path(fixture_path, base_dir)
    
    try:
        with open(full_path, 'r') as file:
            data = json.load(file)
        logger.debug(f"Loaded fixture: {full_path}")
        return data
    except FileNotFoundError:
        logger.error(f"Fixture file not found: {full_path}")
        raise FileNotFoundError(f"Fixture file not found: {full_path}")
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON fixture {full_path}: {str(e)}")
        raise json.JSONDecodeError(f"Error parsing fixture {fixture_path}: {str(e)}", e.doc, e.pos)


def load_transaction_fixture(fixture_name: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Load transaction fixture data from the transactions directory
    
    Args:
        fixture_name: Name of the fixture file without extension
        
    Returns:
        Transaction fixture data
    """
    return load_fixture(fixture_name, TRANSACTION_FIXTURE_DIR)


def load_budget_fixture(fixture_name: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Load budget fixture data from the budget directory
    
    Args:
        fixture_name: Name of the fixture file without extension
        
    Returns:
        Budget fixture data
    """
    return load_fixture(fixture_name, BUDGET_FIXTURE_DIR)


def load_category_fixture(fixture_name: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Load category fixture data from the budget directory
    
    Args:
        fixture_name: Name of the fixture file without extension
        
    Returns:
        Category fixture data
    """
    return load_fixture(fixture_name, BUDGET_FIXTURE_DIR)


def load_api_response_fixture(api_name: str, response_type: str) -> Dict[str, Any]:
    """
    Load API response fixture data from the api_responses directory
    
    Args:
        api_name: Name of the API (e.g., 'capital_one', 'gemini')
        response_type: Type of response (e.g., 'transactions', 'categorization')
        
    Returns:
        API response fixture data
    """
    fixture_path = f"{api_name}/{response_type}"
    return load_fixture(fixture_path, API_RESPONSE_FIXTURE_DIR)


def load_expected_result_fixture(fixture_name: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Load expected result fixture data from the expected directory
    
    Args:
        fixture_name: Name of the fixture file without extension
        
    Returns:
        Expected result fixture data
    """
    return load_fixture(fixture_name, EXPECTED_FIXTURE_DIR)


def convert_to_transaction_objects(transaction_dicts: List[Dict[str, Any]]) -> List[Transaction]:
    """
    Convert transaction dictionaries to Transaction objects
    
    Args:
        transaction_dicts: List of transaction dictionaries
        
    Returns:
        List of Transaction objects
    """
    transactions = []
    for transaction_dict in transaction_dicts:
        transaction = create_transaction(transaction_dict)
        transactions.append(transaction)
    return transactions


def convert_to_category_objects(category_dicts: List[Dict[str, Any]]) -> List[Category]:
    """
    Convert category dictionaries to Category objects
    
    Args:
        category_dicts: List of category dictionaries
        
    Returns:
        List of Category objects
    """
    categories = []
    for category_dict in category_dicts:
        category = create_category(category_dict)
        categories.append(category)
    return categories


def save_fixture(data: Union[Dict[str, Any], List[Dict[str, Any]]], fixture_path: str, 
                base_dir: Optional[str] = None) -> str:
    """
    Save data to a fixture file
    
    Args:
        data: Data to save as JSON
        fixture_path: Relative path to the fixture file
        base_dir: Base directory for fixtures, defaults to JSON_FIXTURE_DIR
        
    Returns:
        Path to the saved fixture file
    """
    full_path = get_fixture_path(fixture_path, base_dir)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    try:
        with open(full_path, 'w') as file:
            json.dump(data, file, indent=2)
        logger.debug(f"Saved fixture: {full_path}")
        return full_path
    except Exception as e:
        logger.error(f"Error saving fixture {full_path}: {str(e)}")
        raise


def create_fixture_from_model(model_object: Any, fixture_path: str, 
                            base_dir: Optional[str] = None) -> str:
    """
    Create a fixture file from a model object or list of model objects
    
    Args:
        model_object: Model object or list of model objects with to_dict() method
        fixture_path: Relative path to the fixture file
        base_dir: Base directory for fixtures, defaults to JSON_FIXTURE_DIR
        
    Returns:
        Path to the saved fixture file
    """
    if isinstance(model_object, list):
        data = [obj.to_dict() for obj in model_object]
    else:
        data = model_object.to_dict()
    
    return save_fixture(data, fixture_path, base_dir)


class FixtureLoader:
    """Class for loading and managing test fixtures with caching"""
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize the FixtureLoader with an optional base directory
        
        Args:
            base_dir: Base directory for fixtures, defaults to JSON_FIXTURE_DIR
        """
        self._cache = {}
        self.base_dir = base_dir or JSON_FIXTURE_DIR
    
    def load(self, fixture_path: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Load a fixture file with caching
        
        Args:
            fixture_path: Relative path to the fixture file
            
        Returns:
            Parsed JSON data from the fixture file
        """
        if fixture_path in self._cache:
            return self._cache[fixture_path]
        
        data = load_fixture(fixture_path, self.base_dir)
        self._cache[fixture_path] = data
        return data
    
    def load_transaction(self, fixture_name: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Load transaction fixture data with caching
        
        Args:
            fixture_name: Name of the fixture file without extension
            
        Returns:
            Transaction fixture data
        """
        fixture_path = os.path.join(os.path.relpath(TRANSACTION_FIXTURE_DIR, self.base_dir), fixture_name)
        return self.load(fixture_path)
    
    def load_budget(self, fixture_name: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Load budget fixture data with caching
        
        Args:
            fixture_name: Name of the fixture file without extension
            
        Returns:
            Budget fixture data
        """
        fixture_path = os.path.join(os.path.relpath(BUDGET_FIXTURE_DIR, self.base_dir), fixture_name)
        return self.load(fixture_path)
    
    def load_category(self, fixture_name: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Load category fixture data with caching
        
        Args:
            fixture_name: Name of the fixture file without extension
            
        Returns:
            Category fixture data
        """
        fixture_path = os.path.join(os.path.relpath(BUDGET_FIXTURE_DIR, self.base_dir), fixture_name)
        return self.load(fixture_path)
    
    def load_api_response(self, api_name: str, response_type: str) -> Dict[str, Any]:
        """
        Load API response fixture data with caching
        
        Args:
            api_name: Name of the API (e.g., 'capital_one', 'gemini')
            response_type: Type of response (e.g., 'transactions', 'categorization')
            
        Returns:
            API response fixture data
        """
        fixture_path = os.path.join(
            os.path.relpath(API_RESPONSE_FIXTURE_DIR, self.base_dir),
            f"{api_name}/{response_type}"
        )
        return self.load(fixture_path)
    
    def load_expected_result(self, fixture_name: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Load expected result fixture data with caching
        
        Args:
            fixture_name: Name of the fixture file without extension
            
        Returns:
            Expected result fixture data
        """
        fixture_path = os.path.join(os.path.relpath(EXPECTED_FIXTURE_DIR, self.base_dir), fixture_name)
        return self.load(fixture_path)
    
    def clear_cache(self) -> None:
        """Clear the fixture cache"""
        self._cache.clear()
        logger.debug("Fixture cache cleared")


# Define a generic type for the GenericFixtureLoader
T = TypeVar('T')

class GenericFixtureLoader(Generic[T]):
    """Generic class for loading fixtures of a specific type with type conversion"""
    
    def __init__(self, converter: callable, base_dir: Optional[str] = None):
        """
        Initialize the GenericFixtureLoader with a converter function
        
        Args:
            converter: Function to convert dictionary to model object
            base_dir: Base directory for fixtures, defaults to JSON_FIXTURE_DIR
        """
        self._loader = FixtureLoader(base_dir)
        self._converter = converter
    
    def load(self, fixture_path: str) -> Union[T, List[T]]:
        """
        Load a fixture and convert it to the target type
        
        Args:
            fixture_path: Relative path to the fixture file
            
        Returns:
            Converted fixture data
        """
        data = self._loader.load(fixture_path)
        
        if isinstance(data, list):
            return [self._converter(item) for item in data]
        else:
            return self._converter(data)