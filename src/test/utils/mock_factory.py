"""
Factory module for creating and managing mock objects used in testing the Budget Management Application.
Provides a centralized way to create consistent mock implementations of external API clients
(Capital One, Google Sheets, Gemini, Gmail) with configurable behaviors for different test scenarios.
"""

import logging
from typing import Dict, Any, Optional, Union, Callable, Type, TypeVar, Generic

from ..mocks.capital_one_client import MockCapitalOneClient
from ..mocks.google_sheets_client import MockGoogleSheetsClient
from ..mocks.gemini_client import MockGeminiClient, MockGeminiClientFactory
from ..mocks.gmail_client import MockGmailClient
from .fixture_loader import load_fixture

# Set up logger
logger = logging.getLogger(__name__)

# Define a TypeVar for GenericMockFactory
T = TypeVar('T')

# Default configuration for mock objects
DEFAULT_CONFIG = {
    'capital_one': {
        'client_id': 'test-client-id',
        'client_secret': 'test-client-secret',
        'checking_account_id': 'test-checking-account',
        'savings_account_id': 'test-savings-account'
    },
    'google_sheets': {
        'credentials_file': 'test-credentials.json',
        'weekly_spending_id': 'test-weekly-spending-id',
        'master_budget_id': 'test-master-budget-id'
    },
    'gemini': {
        'api_key': 'test-api-key',
        'authenticated': True
    },
    'gmail': {
        'auth_service': None,
        'sender_email': 'njdifiore@gmail.com',
        'user_id': 'me'
    }
}


def create_mock_capital_one_client(config: Optional[Dict[str, Any]] = None) -> MockCapitalOneClient:
    """
    Create a mock Capital One API client with optional configuration
    
    Args:
        config: Optional configuration for the mock client
        
    Returns:
        Configured mock Capital One client
    """
    # Extract Capital One configuration from config or use defaults
    if config is None:
        config = DEFAULT_CONFIG['capital_one']
    
    # Create a new MockCapitalOneClient with the extracted configuration
    mock_client = MockCapitalOneClient(
        client_id=config.get('client_id', 'test-client-id'),
        client_secret=config.get('client_secret', 'test-client-secret'),
        checking_account_id=config.get('checking_account_id', 'test-checking-account'),
        savings_account_id=config.get('savings_account_id', 'test-savings-account')
    )
    
    # Log creation of mock Capital One client
    logger.debug(f"Created mock Capital One client with checking_account_id={config.get('checking_account_id')}")
    
    # Return the configured mock client
    return mock_client


def create_mock_google_sheets_client(config: Optional[Dict[str, Any]] = None) -> MockGoogleSheetsClient:
    """
    Create a mock Google Sheets API client with optional configuration
    
    Args:
        config: Optional configuration for the mock client
        
    Returns:
        Configured mock Google Sheets client
    """
    # Extract Google Sheets configuration from config or use defaults
    if config is None:
        config = DEFAULT_CONFIG['google_sheets']
    
    # Create a new MockGoogleSheetsClient with the extracted configuration
    mock_client = MockGoogleSheetsClient(
        credentials_file=config.get('credentials_file', 'test-credentials.json'),
        weekly_spending_id=config.get('weekly_spending_id', 'test-weekly-spending-id'),
        master_budget_id=config.get('master_budget_id', 'test-master-budget-id')
    )
    
    # Log creation of mock Google Sheets client
    logger.debug(f"Created mock Google Sheets client with weekly_spending_id={config.get('weekly_spending_id')}")
    
    # Return the configured mock client
    return mock_client


def create_mock_gemini_client(
    config: Optional[Dict[str, Any]] = None,
    should_fail: bool = False,
    failure_mode: str = 'authentication'
) -> MockGeminiClient:
    """
    Create a mock Gemini AI client with optional configuration
    
    Args:
        config: Optional configuration for the mock client
        should_fail: Whether operations should fail (for testing error handling)
        failure_mode: Which operation should fail ('authentication', 'completion',
                     'categorization', 'insights', or 'connectivity')
        
    Returns:
        Configured mock Gemini client
    """
    # Extract Gemini configuration from config or use defaults
    if config is None:
        config = DEFAULT_CONFIG['gemini']
    
    # If should_fail is True, use MockGeminiClientFactory.create_failing_client with failure_mode
    if should_fail:
        mock_client = MockGeminiClientFactory.create_failing_client(failure_mode)
    # Otherwise, use MockGeminiClientFactory.create_default_client
    else:
        mock_client = MockGeminiClientFactory.create_default_client()
    
    # Configure the client with the extracted configuration
    # (Factory methods already handle the basic setup)
    
    # Log creation of mock Gemini client
    logger.debug(f"Created mock Gemini client with should_fail={should_fail}, failure_mode={failure_mode}")
    
    # Return the configured mock client
    return mock_client


def create_mock_gmail_client(config: Optional[Dict[str, Any]] = None) -> MockGmailClient:
    """
    Create a mock Gmail API client with optional configuration
    
    Args:
        config: Optional configuration for the mock client
        
    Returns:
        Configured mock Gmail client
    """
    # Extract Gmail configuration from config or use defaults
    if config is None:
        config = DEFAULT_CONFIG['gmail']
    
    # Create a new MockGmailClient with the extracted configuration
    mock_client = MockGmailClient(
        auth_service=config.get('auth_service'),
        sender_email=config.get('sender_email', 'njdifiore@gmail.com'),
        user_id=config.get('user_id', 'me')
    )
    
    # Log creation of mock Gmail client
    logger.debug(f"Created mock Gmail client with sender_email={config.get('sender_email')}")
    
    # Return the configured mock client
    return mock_client


def create_mock(mock_type: str, config: Optional[Dict[str, Any]] = None) -> Any:
    """
    Generic function to create a mock object of the specified type
    
    Args:
        mock_type: Type of mock to create ('capital_one', 'google_sheets', 'gemini', 'gmail')
        config: Optional configuration for the mock client
        
    Returns:
        Configured mock object of the specified type
    """
    # Check mock_type to determine which mock creation function to call
    if mock_type == 'capital_one':
        return create_mock_capital_one_client(config)
    elif mock_type == 'google_sheets':
        return create_mock_google_sheets_client(config)
    elif mock_type == 'gemini':
        return create_mock_gemini_client(config)
    elif mock_type == 'gmail':
        return create_mock_gmail_client(config)
    else:
        # Raise ValueError for unknown mock_type
        raise ValueError(f"Unknown mock type: {mock_type}")


class MockFactory:
    """
    Factory class for creating and managing mock objects for testing
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the mock factory with optional configuration
        
        Args:
            config: Optional configuration for mock objects
        """
        # Store config or use DEFAULT_CONFIG if None
        self.config = config if config is not None else DEFAULT_CONFIG
        # Initialize empty dictionary for mocks
        self.mocks = {}
        # Log initialization of mock factory
        logger.debug("Initialized MockFactory")
    
    def create_capital_one_client(self, override_config: Optional[Dict[str, Any]] = None) -> MockCapitalOneClient:
        """
        Create a mock Capital One API client
        
        Args:
            override_config: Optional configuration to override defaults
            
        Returns:
            Configured mock Capital One client
        """
        # Merge self.config with override_config if provided
        config = self.config.get('capital_one', {}).copy()
        if override_config:
            config.update(override_config)
        
        # Call create_mock_capital_one_client with the merged config
        mock = create_mock_capital_one_client(config)
        
        # Store the created mock in self.mocks
        self.mocks['capital_one'] = mock
        
        # Return the mock client
        return mock
    
    def create_google_sheets_client(self, override_config: Optional[Dict[str, Any]] = None) -> MockGoogleSheetsClient:
        """
        Create a mock Google Sheets API client
        
        Args:
            override_config: Optional configuration to override defaults
            
        Returns:
            Configured mock Google Sheets client
        """
        # Merge self.config with override_config if provided
        config = self.config.get('google_sheets', {}).copy()
        if override_config:
            config.update(override_config)
        
        # Call create_mock_google_sheets_client with the merged config
        mock = create_mock_google_sheets_client(config)
        
        # Store the created mock in self.mocks
        self.mocks['google_sheets'] = mock
        
        # Return the mock client
        return mock
    
    def create_gemini_client(
        self, 
        override_config: Optional[Dict[str, Any]] = None,
        should_fail: bool = False,
        failure_mode: str = 'authentication'
    ) -> MockGeminiClient:
        """
        Create a mock Gemini AI client
        
        Args:
            override_config: Optional configuration to override defaults
            should_fail: Whether operations should fail (for testing error handling)
            failure_mode: Which operation should fail
            
        Returns:
            Configured mock Gemini client
        """
        # Merge self.config with override_config if provided
        config = self.config.get('gemini', {}).copy()
        if override_config:
            config.update(override_config)
        
        # Call create_mock_gemini_client with the merged config, should_fail, and failure_mode
        mock = create_mock_gemini_client(config, should_fail, failure_mode)
        
        # Store the created mock in self.mocks
        self.mocks['gemini'] = mock
        
        # Return the mock client
        return mock
    
    def create_gmail_client(self, override_config: Optional[Dict[str, Any]] = None) -> MockGmailClient:
        """
        Create a mock Gmail API client
        
        Args:
            override_config: Optional configuration to override defaults
            
        Returns:
            Configured mock Gmail client
        """
        # Merge self.config with override_config if provided
        config = self.config.get('gmail', {}).copy()
        if override_config:
            config.update(override_config)
        
        # Call create_mock_gmail_client with the merged config
        mock = create_mock_gmail_client(config)
        
        # Store the created mock in self.mocks
        self.mocks['gmail'] = mock
        
        # Return the mock client
        return mock
    
    def create_all_mocks(self) -> Dict[str, Any]:
        """
        Create all mock objects with default configuration
        
        Returns:
            Dictionary of all created mock objects
        """
        # Call create_capital_one_client
        self.create_capital_one_client()
        # Call create_google_sheets_client
        self.create_google_sheets_client()
        # Call create_gemini_client
        self.create_gemini_client()
        # Call create_gmail_client
        self.create_gmail_client()
        
        # Return self.mocks dictionary with all created mocks
        return self.mocks
    
    def get_mock(self, mock_type: str) -> Any:
        """
        Get a previously created mock object by type
        
        Args:
            mock_type: Type of mock to retrieve
            
        Returns:
            The requested mock object
        """
        # Check if mock_type exists in self.mocks
        if mock_type not in self.mocks:
            # If not, raise KeyError with informative message
            raise KeyError(f"Mock of type '{mock_type}' has not been created yet")
        
        # If it exists, return the mock object
        return self.mocks[mock_type]
    
    def get_all_mocks(self) -> Dict[str, Any]:
        """
        Get all created mock objects
        
        Returns:
            Dictionary of all created mock objects
        """
        # Return self.mocks dictionary
        return self.mocks
    
    def reset_all_mocks(self) -> None:
        """
        Reset all created mock objects to their initial state
        
        Returns:
            None
        """
        # For each mock in self.mocks
        for mock_type, mock in self.mocks.items():
            # Call reset() method if it exists
            if hasattr(mock, 'reset'):
                mock.reset()
                # Log reset of each mock
                logger.debug(f"Reset mock: {mock_type}")
    
    def configure_mock_failures(self, failure_config: Dict[str, str]) -> None:
        """
        Configure mock objects to simulate failures for testing error handling
        
        Args:
            failure_config: Dictionary mapping mock types to failure modes
            
        Returns:
            None
        """
        # For each entry in failure_config
        for mock_type, failure_mode in failure_config.items():
            # Get the corresponding mock object
            if mock_type not in self.mocks:
                logger.warning(f"Cannot configure failure for non-existent mock: {mock_type}")
                continue
            
            mock = self.mocks[mock_type]
            
            # Configure the mock to fail according to the specified failure mode
            if mock_type == 'capital_one':
                if failure_mode == 'authentication':
                    mock.set_should_fail_authentication(True)
                elif failure_mode == 'transactions':
                    mock.set_should_fail_transactions(True)
                elif failure_mode == 'accounts':
                    mock.set_should_fail_accounts(True)
                elif failure_mode == 'transfers':
                    mock.set_should_fail_transfers(True)
                
            elif mock_type == 'google_sheets':
                if failure_mode == 'authentication':
                    mock.set_authentication_failure(True)
                
            elif mock_type == 'gemini':
                mock.set_failure_mode(True, failure_mode)
                
            elif mock_type == 'gmail':
                if failure_mode == 'authentication':
                    mock.set_should_fail_authentication(True)
                elif failure_mode == 'sending':
                    mock.set_should_fail_sending(True)
                elif failure_mode == 'verification':
                    mock.set_should_fail_verification(True)
            
            # Log configuration of mock failures
            logger.debug(f"Configured {mock_type} mock to fail with mode: {failure_mode}")


class GenericMockFactory(Generic[T]):
    """
    Generic factory class for creating mock objects of a specific type
    """
    
    def __init__(self, mock_class: Type[T], default_config: Dict[str, Any]):
        """
        Initialize the generic mock factory
        
        Args:
            mock_class: Class type to create instances of
            default_config: Default configuration for created instances
        """
        # Store mock_class for creating instances
        self.mock_class = mock_class
        # Store default_config for configuration
        self.default_config = default_config
        # Initialize empty dictionary for instances
        self.instances = {}
    
    def create(self, instance_id: str, config: Optional[Dict[str, Any]] = None) -> T:
        """
        Create a mock object with the specified configuration
        
        Args:
            instance_id: Identifier for the created instance
            config: Configuration for the instance
            
        Returns:
            Created mock object
        """
        # Merge default_config with provided config
        merged_config = self.default_config.copy()
        if config:
            merged_config.update(config)
        
        # Create instance of mock_class with merged config
        instance = self.mock_class(**merged_config)
        
        # Store instance in instances dictionary with instance_id as key
        self.instances[instance_id] = instance
        
        # Return the created instance
        return instance
    
    def get(self, instance_id: str) -> T:
        """
        Get a previously created mock object by ID
        
        Args:
            instance_id: ID of the instance to retrieve
            
        Returns:
            The requested mock object
        """
        # Check if instance_id exists in instances
        if instance_id not in self.instances:
            # If it doesn't exist, raise KeyError with informative message
            raise KeyError(f"No instance found with ID: {instance_id}")
        
        # If it exists, return the instance
        return self.instances[instance_id]
    
    def reset(self, instance_id: str) -> None:
        """
        Reset a mock object to its initial state
        
        Args:
            instance_id: ID of the instance to reset
            
        Returns:
            None
        """
        # Get the instance with the specified instance_id
        instance = self.get(instance_id)
        
        # Call reset() method on the instance
        if hasattr(instance, 'reset'):
            instance.reset()
            # Log reset of the instance
            logger.debug(f"Reset instance: {instance_id}")
    
    def reset_all(self) -> None:
        """
        Reset all created mock objects to their initial state
        
        Returns:
            None
        """
        # For each instance in instances
        for instance_id, instance in self.instances.items():
            # Call reset() method on the instance
            if hasattr(instance, 'reset'):
                instance.reset()
                # Log reset of all instances
                logger.debug(f"Reset instance: {instance_id}")