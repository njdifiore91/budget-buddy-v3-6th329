"""
data_transformation_service.py - Service module that provides data transformation functions for converting between different data formats in the Budget Management Application.

This module handles transformations between Capital One API data, Google Sheets data, and internal application models, ensuring consistent data representation across the system.
"""

import logging
from typing import List, Dict, Any, Optional, Union

import pandas
import numpy as np
from decimal import Decimal

from ..models.transaction import Transaction, create_transactions_from_capital_one, create_transactions_from_sheet_data, create_transaction
from ..models.category import Category, create_categories_from_sheet_data
from ..models.budget import Budget, create_budget_from_sheet_data
from ..utils.formatters import format_transactions_for_sheets, format_budget_analysis_for_ai, format_dict_for_sheets
from ..utils.validation import validate_transactions, filter_duplicates
from ..utils.error_handlers import ValidationError, handle_validation_error

# Set up logger
logger = logging.getLogger(__name__)


def capital_one_to_transactions(api_response: List[Dict[str, Any]]) -> List[Transaction]:
    """
    Transforms Capital One API response data into Transaction objects
    
    Args:
        api_response: API response containing transaction data
        
    Returns:
        List of Transaction objects
    """
    try:
        # Validate the API response structure
        if not isinstance(api_response, list):
            logger.error("Invalid Capital One API response: not a list")
            raise ValidationError("Invalid API response format", "api_response")
        
        # Use the create_transactions_from_capital_one function to convert to Transaction objects
        transactions = create_transactions_from_capital_one(api_response)
        
        # Filter out duplicate transactions using filter_duplicates
        unique_transactions = filter_duplicates([t.to_dict() for t in transactions])
        transactions = [create_transaction(t) for t in unique_transactions]
        
        logger.info(f"Transformed {len(transactions)} transactions from Capital One API response")
        return transactions
        
    except ValidationError as e:
        logger.error(f"Validation error during Capital One data transformation: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error transforming Capital One data: {str(e)}")
        raise ValidationError(f"Error transforming Capital One data: {str(e)}", "api_response")


def transactions_to_sheets_format(transactions: List[Transaction]) -> List[List[Any]]:
    """
    Transforms Transaction objects into a format suitable for Google Sheets
    
    Args:
        transactions: List of Transaction objects
        
    Returns:
        List of rows formatted for Google Sheets
    """
    try:
        # Validate the transactions list
        if not isinstance(transactions, list):
            logger.error("Invalid transactions input: not a list")
            raise ValidationError("Transactions must be a list", "transactions")
        
        # Use format_transactions_for_sheets to convert transactions to sheets format
        formatted_rows = format_transactions_for_sheets([t.to_dict() for t in transactions])
        
        logger.info(f"Formatted {len(formatted_rows)} transactions for Google Sheets")
        return formatted_rows
        
    except ValidationError as e:
        logger.error(f"Validation error during transaction formatting: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error formatting transactions for sheets: {str(e)}")
        raise ValidationError(f"Error formatting transactions for sheets: {str(e)}", "transactions")


def sheets_to_transactions(sheet_data: List[List[Any]]) -> List[Transaction]:
    """
    Transforms Google Sheets data into Transaction objects
    
    Args:
        sheet_data: Data from Google Sheets
        
    Returns:
        List of Transaction objects
    """
    try:
        # Validate the sheet data structure
        if not isinstance(sheet_data, list):
            logger.error("Invalid sheet data: not a list")
            raise ValidationError("Sheet data must be a list", "sheet_data")
        
        # Use create_transactions_from_sheet_data to convert to Transaction objects
        transactions = create_transactions_from_sheet_data(sheet_data)
        
        logger.info(f"Created {len(transactions)} transactions from sheet data")
        return transactions
        
    except ValidationError as e:
        logger.error(f"Validation error during sheet data transformation: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error transforming sheet data to transactions: {str(e)}")
        raise ValidationError(f"Error transforming sheet data: {str(e)}", "sheet_data")


def sheets_to_categories(sheet_data: List[List[Any]]) -> List[Category]:
    """
    Transforms Google Sheets data into Category objects
    
    Args:
        sheet_data: Data from Google Sheets
        
    Returns:
        List of Category objects
    """
    try:
        # Validate the sheet data structure
        if not isinstance(sheet_data, list):
            logger.error("Invalid sheet data: not a list")
            raise ValidationError("Sheet data must be a list", "sheet_data")
        
        # Use create_categories_from_sheet_data to convert to Category objects
        categories = create_categories_from_sheet_data(sheet_data)
        
        logger.info(f"Created {len(categories)} categories from sheet data")
        return categories
        
    except ValidationError as e:
        logger.error(f"Validation error during sheet data transformation: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error transforming sheet data to categories: {str(e)}")
        raise ValidationError(f"Error transforming sheet data: {str(e)}", "sheet_data")


def sheets_to_budget(budget_sheet_data: List[List[Any]], transactions: List[Transaction]) -> Budget:
    """
    Transforms Google Sheets budget and transaction data into a Budget object
    
    Args:
        budget_sheet_data: Budget data from Google Sheets
        transactions: List of Transaction objects
        
    Returns:
        Budget object with analysis
    """
    try:
        # Validate the budget sheet data structure
        if not isinstance(budget_sheet_data, list):
            logger.error("Invalid budget sheet data: not a list")
            raise ValidationError("Budget sheet data must be a list", "budget_sheet_data")
        
        # Convert transactions to a dictionary of actual spending by category
        actual_spending = aggregate_by_category(transactions)
        
        # Use create_budget_from_sheet_data to create a Budget object
        budget = create_budget_from_sheet_data(budget_sheet_data, actual_spending)
        
        # Call analyze() on the Budget object to perform budget analysis
        budget.analyze()
        
        logger.info("Created and analyzed budget from sheet data")
        return budget
        
    except ValidationError as e:
        logger.error(f"Validation error during budget creation: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error creating budget from sheet data: {str(e)}")
        raise ValidationError(f"Error creating budget: {str(e)}", "budget_data")


def transactions_to_dataframe(transactions: List[Transaction]) -> pandas.DataFrame:
    """
    Converts Transaction objects to a pandas DataFrame for analysis
    
    Args:
        transactions: List of Transaction objects
        
    Returns:
        DataFrame containing transaction data
    """
    try:
        # Convert each Transaction to a dictionary using to_dict()
        transaction_dicts = [transaction.to_dict() for transaction in transactions]
        
        # Create a pandas DataFrame from the list of dictionaries
        df = pandas.DataFrame(transaction_dicts)
        
        # Ensure proper column types (datetime for timestamp, etc.)
        if 'timestamp' in df.columns:
            df['timestamp'] = pandas.to_datetime(df['timestamp'])
        
        if 'amount' in df.columns:
            df['amount'] = df['amount'].astype(float)
        
        logger.info(f"Created DataFrame with {len(df)} transactions")
        return df
        
    except Exception as e:
        logger.error(f"Error converting transactions to DataFrame: {str(e)}")
        raise ValidationError(f"DataFrame conversion error: {str(e)}", "transactions")


def dataframe_to_transactions(df: pandas.DataFrame) -> List[Transaction]:
    """
    Converts a pandas DataFrame back to Transaction objects
    
    Args:
        df: DataFrame containing transaction data
        
    Returns:
        List of Transaction objects
    """
    try:
        # Validate the DataFrame has required columns
        required_columns = ['location', 'amount', 'timestamp']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.error(f"DataFrame missing required columns: {missing_columns}")
            raise ValidationError(f"DataFrame missing columns: {missing_columns}", "dataframe")
        
        # Convert each row to a dictionary
        transactions = []
        for _, row in df.iterrows():
            try:
                # Convert row to a dictionary
                transaction_dict = row.to_dict()
                
                # Create Transaction objects from the dictionaries
                transaction = create_transaction(transaction_dict)
                transactions.append(transaction)
            except Exception as e:
                logger.warning(f"Error creating transaction from DataFrame row: {str(e)}")
                continue
        
        logger.info(f"Converted DataFrame to {len(transactions)} transactions")
        return transactions
        
    except ValidationError as e:
        logger.error(f"Validation error during DataFrame conversion: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error converting DataFrame to transactions: {str(e)}")
        raise ValidationError(f"Transaction conversion error: {str(e)}", "dataframe")


def budget_to_ai_prompt(budget: Budget) -> str:
    """
    Transforms Budget analysis results into a format suitable for Gemini AI prompt
    
    Args:
        budget: Budget object with analysis results
        
    Returns:
        Formatted budget analysis for AI prompt
    """
    try:
        # Ensure the budget has been analyzed by calling analyze() if needed
        if not budget.is_analyzed:
            logger.info("Budget not yet analyzed, running analysis")
            budget.analyze()
        
        # Convert budget to dictionary using to_dict()
        budget_dict = budget.to_dict()
        
        # Use format_budget_analysis_for_ai to format the budget data for AI prompt
        formatted_prompt = format_budget_analysis_for_ai(budget_dict)
        
        logger.info("Formatted budget analysis for AI prompt")
        return formatted_prompt
        
    except Exception as e:
        logger.error(f"Error formatting budget for AI prompt: {str(e)}")
        raise ValidationError(f"AI prompt formatting error: {str(e)}", "budget")


def categorize_transactions(transactions: List[Transaction], categorization_results: Dict[str, str]) -> List[Transaction]:
    """
    Applies category assignments from AI to Transaction objects
    
    Args:
        transactions: List of Transaction objects
        categorization_results: Mapping of transaction locations to categories
        
    Returns:
        Transactions with categories assigned
    """
    try:
        # Validate transactions and categorization_results
        if not isinstance(transactions, list):
            raise ValidationError("Transactions must be a list", "transactions")
        
        if not isinstance(categorization_results, dict):
            raise ValidationError("Categorization results must be a dictionary", "categorization_results")
        
        # For each transaction, find its location in categorization_results
        categorized_before = sum(1 for t in transactions if t.category is not None)
        
        # Assign the corresponding category to the transaction
        for transaction in transactions:
            if transaction.location in categorization_results:
                transaction.set_category(categorization_results[transaction.location])
        
        # Log the number of transactions categorized
        categorized_after = sum(1 for t in transactions if t.category is not None)
        newly_categorized = categorized_after - categorized_before
        
        logger.info(f"Applied categories to {newly_categorized} transactions")
        return transactions
        
    except ValidationError as e:
        logger.error(f"Validation error during categorization: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error categorizing transactions: {str(e)}")
        raise ValidationError(f"Categorization error: {str(e)}", "categorization")


def aggregate_by_category(transactions: List[Transaction]) -> Dict[str, float]:
    """
    Aggregates transaction amounts by category
    
    Args:
        transactions: List of Transaction objects
        
    Returns:
        Dictionary mapping categories to total amounts
    """
    try:
        # Validate the transactions list
        if not isinstance(transactions, list):
            logger.error("Invalid transactions input: not a list")
            raise ValidationError("Transactions must be a list", "transactions")
        
        # Initialize an empty dictionary for category totals
        category_totals = {}
        
        # Group transactions by category
        for transaction in transactions:
            if transaction.category is None:
                category = "Uncategorized"
            else:
                category = transaction.category
            
            # Sum the amounts for each category
            if category not in category_totals:
                category_totals[category] = Decimal('0')
            
            category_totals[category] += transaction.amount
        
        # Return the dictionary of category totals
        logger.info(f"Aggregated transactions into {len(category_totals)} categories")
        return category_totals
        
    except ValidationError as e:
        logger.error(f"Validation error during category aggregation: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error aggregating transactions by category: {str(e)}")
        raise ValidationError(f"Error in category aggregation: {str(e)}", "transactions")


def prepare_ai_categorization_prompt(transactions: List[Transaction], categories: List[Category]) -> str:
    """
    Prepares a prompt for Gemini AI to categorize transactions
    
    Args:
        transactions: List of Transaction objects to categorize
        categories: List of Category objects with valid categories
        
    Returns:
        Formatted prompt for AI categorization
    """
    try:
        # Extract transaction locations from transactions
        transaction_locations = [transaction.location for transaction in transactions]
        
        # Extract category names from categories
        category_names = [category.name for category in categories]
        
        # Format the prompt with transaction locations and valid categories
        prompt = (
            "You are a financial transaction categorizer. Your task is to match each transaction location "
            "to the most appropriate budget category from the provided list.\n\n"
            "TRANSACTION LOCATIONS:\n"
        )
        
        # Add transaction locations
        for location in transaction_locations:
            prompt += f"- {location}\n"
        
        prompt += "\nVALID BUDGET CATEGORIES:\n"
        
        # Add category names
        for category in category_names:
            prompt += f"- {category}\n"
        
        prompt += (
            "\nFor each transaction location, respond with the location followed by the best matching "
            "category in this format:\n"
            "\"Location: [transaction location] -> Category: [matching category]\"\n\n"
            "If you're unsure about a category, choose the most likely one based on the transaction "
            "location. Every transaction must be assigned to exactly one category from the provided list."
        )
        
        logger.info(f"Prepared AI categorization prompt for {len(transaction_locations)} transactions")
        return prompt
        
    except Exception as e:
        logger.error(f"Error preparing AI categorization prompt: {str(e)}")
        raise ValidationError(f"Prompt preparation error: {str(e)}", "categorization")


def parse_ai_categorization_response(ai_response: str, transaction_locations: List[str], valid_categories: List[str]) -> Dict[str, str]:
    """
    Parses the Gemini AI response for transaction categorization
    
    Args:
        ai_response: AI response text
        transaction_locations: List of transaction locations
        valid_categories: List of valid category names
        
    Returns:
        Mapping of transaction locations to categories
    """
    try:
        # Parse the AI response text to extract location-category pairs
        categorization_results = {}
        lines = ai_response.strip().split('\n')
        
        for line in lines:
            # Look for the pattern "Location: X -> Category: Y"
            if '->' in line and 'Location:' in line and 'Category:' in line:
                try:
                    # Extract location and category
                    location_part = line.split('->')[0].strip()
                    category_part = line.split('->')[1].strip()
                    
                    location = location_part.replace('Location:', '').strip()
                    category = category_part.replace('Category:', '').strip()
                    
                    # Validate that each assigned category exists in valid_categories
                    if category in valid_categories:
                        categorization_results[location] = category
                    else:
                        logger.warning(f"Invalid category in AI response: {category}")
                except Exception as e:
                    logger.warning(f"Error parsing line from AI response: {line}, error: {str(e)}")
        
        # Log any locations that couldn't be categorized
        locations_found = set(categorization_results.keys())
        locations_missing = set(transaction_locations) - locations_found
        
        if locations_missing:
            logger.warning(f"Missing categorization for {len(locations_missing)} transaction locations")
        
        # Return the categorization dictionary
        logger.info(f"Parsed AI response: categorized {len(categorization_results)}/{len(transaction_locations)} transactions")
        return categorization_results
        
    except Exception as e:
        logger.error(f"Error parsing AI categorization response: {str(e)}")
        raise ValidationError(f"Response parsing error: {str(e)}", "ai_response")


class DataTransformationService:
    """
    Service class that provides methods for transforming data between different formats
    in the Budget Management Application
    """
    
    def __init__(self):
        """Initialize the DataTransformationService"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initialized DataTransformationService")
    
    def transform_capital_one_to_transactions(self, api_response: List[Dict[str, Any]]) -> List[Transaction]:
        """
        Transform Capital One API response to Transaction objects
        
        Args:
            api_response: API response from Capital One
            
        Returns:
            List of Transaction objects
        """
        return capital_one_to_transactions(api_response)
    
    def transform_transactions_to_sheets(self, transactions: List[Transaction]) -> List[List[Any]]:
        """
        Transform Transaction objects to Google Sheets format
        
        Args:
            transactions: List of Transaction objects
            
        Returns:
            Data formatted for Google Sheets
        """
        return transactions_to_sheets_format(transactions)
    
    def transform_sheets_to_transactions(self, sheet_data: List[List[Any]]) -> List[Transaction]:
        """
        Transform Google Sheets data to Transaction objects
        
        Args:
            sheet_data: Data from Google Sheets
            
        Returns:
            List of Transaction objects
        """
        return sheets_to_transactions(sheet_data)
    
    def transform_sheets_to_categories(self, sheet_data: List[List[Any]]) -> List[Category]:
        """
        Transform Google Sheets data to Category objects
        
        Args:
            sheet_data: Data from Google Sheets
            
        Returns:
            List of Category objects
        """
        return sheets_to_categories(sheet_data)
    
    def transform_sheets_to_budget(self, budget_sheet_data: List[List[Any]], transactions: List[Transaction]) -> Budget:
        """
        Transform Google Sheets data to a Budget object
        
        Args:
            budget_sheet_data: Budget data from Google Sheets
            transactions: List of Transaction objects
            
        Returns:
            Budget object with analysis
        """
        return sheets_to_budget(budget_sheet_data, transactions)
    
    def transform_budget_to_ai_prompt(self, budget: Budget) -> str:
        """
        Transform Budget analysis to AI prompt format
        
        Args:
            budget: Budget object with analysis
            
        Returns:
            Formatted budget analysis for AI prompt
        """
        return budget_to_ai_prompt(budget)
    
    def prepare_categorization_prompt(self, transactions: List[Transaction], categories: List[Category]) -> str:
        """
        Prepare prompt for AI transaction categorization
        
        Args:
            transactions: List of Transaction objects
            categories: List of Category objects
            
        Returns:
            Formatted prompt for AI categorization
        """
        return prepare_ai_categorization_prompt(transactions, categories)
    
    def parse_categorization_response(self, ai_response: str, transaction_locations: List[str], valid_categories: List[str]) -> Dict[str, str]:
        """
        Parse AI response for transaction categorization
        
        Args:
            ai_response: AI response text
            transaction_locations: List of transaction locations
            valid_categories: List of valid category names
            
        Returns:
            Mapping of transaction locations to categories
        """
        return parse_ai_categorization_response(ai_response, transaction_locations, valid_categories)
    
    def apply_categorization(self, transactions: List[Transaction], categorization_results: Dict[str, str]) -> List[Transaction]:
        """
        Apply category assignments to Transaction objects
        
        Args:
            transactions: List of Transaction objects
            categorization_results: Mapping of locations to categories
            
        Returns:
            Transactions with categories assigned
        """
        return categorize_transactions(transactions, categorization_results)