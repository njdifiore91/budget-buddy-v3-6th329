# Budget Management Application Testing Framework

This directory contains the comprehensive testing framework for the Budget Management Application, a serverless system designed to automate personal budget tracking, analysis, and savings allocation. The testing framework follows industry best practices and is designed to ensure the reliability, correctness, and robustness of the application.

## Testing Structure

The testing framework is organized into the following directories:

- `unit/`: Unit tests for individual components and functions
- `integration/`: Integration tests for component interactions
- `e2e/`: End-to-end tests for complete workflows
- `performance/`: Performance tests for critical operations
- `security/`: Security tests for credential handling and data protection
- `fixtures/`: Test data and fixtures
- `mocks/`: Mock implementations of external services
- `utils/`: Utility functions for testing
- `contracts/`: Contract tests for API integrations
- `docker/`: Docker configuration for test environments
- `ci/`: CI/CD pipeline test configurations

## Test Configuration

The testing framework uses the following configuration files:

- `pytest.ini`: Configuration for pytest including test discovery, markers, and plugins
- `.coveragerc`: Configuration for code coverage measurement
- `conftest.py`: Global pytest fixtures and test setup
- `.env.test.example`: Example environment variables for testing

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest

# Run unit tests only
pytest unit/

# Run integration tests only
pytest integration/

# Run with coverage report
pytest --cov=src/backend
```

### Using Test Markers

```bash
# Run tests marked as unit tests
pytest -m unit

# Run tests for Capital One API integration
pytest -m capital_one

# Run tests excluding slow tests
pytest -m "not slow"
```

### Test Environment Setup

```bash
# Set up test environment
source scripts/development/setup_local_env.sh

# Run tests with specific configuration
ENV=test pytest
```

## Writing Tests

### Test Naming Conventions

Tests should follow the naming convention:

```
test_[unit_under_test]_[scenario_being_tested]_[expected_behavior]
```

Examples:
- `test_calculate_transfer_amount_with_surplus_returns_correct_amount`
- `test_categorize_transactions_with_invalid_data_raises_validation_error`

### Using Test Fixtures

The testing framework provides fixtures for common test scenarios:

```python
def test_transaction_retrieval(capital_one_client, google_sheets_client):
    # Test using the provided mock clients
    retriever = TransactionRetriever(capital_one_client, google_sheets_client)
    result = retriever.execute()
    assert result['status'] == 'success'
```

### Using Test Helpers

Utility functions are available to simplify test implementation:

```python
from utils.test_helpers import create_test_transactions

def test_budget_analysis():
    # Create test data
    transactions = create_test_transactions(10)
    # Test with the created transactions
```

### Using Mock Clients

Mock implementations of external services are provided:

```python
from mocks.capital_one_client import MockCapitalOneClient

def test_custom_scenario():
    # Create and configure mock client
    client = MockCapitalOneClient()
    client.set_transactions(custom_transactions)
    # Test with the configured mock client
```

## Test Data Management

### Fixture Files

Test fixtures are stored in JSON format in the `fixtures/json/` directory:

- `transactions/`: Transaction data fixtures
- `budget/`: Budget and category data fixtures
- `api_responses/`: Mock API response fixtures
- `expected/`: Expected result fixtures

### Loading Fixtures

```python
from utils.fixture_loader import load_fixture, load_transaction_fixture

# Load any fixture by path
data = load_fixture('json/transactions/valid_transactions.json')

# Load a transaction fixture
transactions = load_transaction_fixture('valid_transactions')
```

### Creating Test Data

```python
from utils.test_helpers import create_test_transaction, create_test_transactions

# Create a single test transaction
transaction = create_test_transaction(location="Grocery Store", amount=Decimal("45.67"))

# Create multiple test transactions
transactions = create_test_transactions(5)
```

## Mocking Strategy

The testing framework uses a comprehensive mocking approach to isolate components and test without external dependencies:

### API Mocking

Mock implementations are provided for all external APIs:

- `MockCapitalOneClient`: Simulates Capital One API responses
- `MockGoogleSheetsClient`: Simulates Google Sheets API interactions
- `MockGeminiClient`: Simulates Gemini AI API responses
- `MockGmailClient`: Simulates Gmail API for email sending

### Mock Configuration

Mocks can be configured for different test scenarios:

```python
# Configure mock to simulate errors
capital_one_client.set_should_fail_transactions(True)

# Configure mock with custom data
capital_one_client.set_transactions(custom_transaction_data)
```

### Mock Factory

A factory is provided to create and configure multiple mocks:

```python
from utils.mock_factory import MockFactory

# Create all required mocks
mocks = MockFactory().get_all_mocks()
```

## Test Environment Management

### Environment Setup

The `TestEnvironment` class provides a consistent way to set up test environments:

```python
from utils.test_helpers import TestEnvironment

# Create and set up test environment
env = TestEnvironment()
env.setup()

# Use the environment
mocks = env.get_mock('capital_one_client')

# Clean up
env.teardown()
```

### Context Manager

A context manager is available for automatic setup and teardown:

```python
from utils.test_helpers import with_test_environment

def test_with_environment():
    with with_test_environment() as env:
        # Test using the environment
        pass  # Environment is automatically cleaned up
```

### Environment Variables

Temporary environment variables can be set for tests:

```python
from utils.test_helpers import set_environment_variables

def test_with_env_vars():
    with set_environment_variables({'API_KEY': 'test-key'}):
        # Test with environment variables
        pass  # Original environment is restored
```

## Code Coverage

The testing framework measures code coverage using pytest-cov with the following targets:

- Overall coverage: 85%+
- Core logic: 90%+
- API clients: 85%+
- Utility functions: 80%+

### Coverage Reports

Coverage reports are generated in multiple formats:

```bash
# Generate HTML coverage report
pytest --cov=src/backend --cov-report=html

# Generate XML coverage report for CI integration
pytest --cov=src/backend --cov-report=xml
```

### Coverage Configuration

Coverage settings are defined in `.coveragerc`, including:

- Source directories to measure
- Files to exclude
- Branch coverage measurement
- Minimum coverage thresholds

## CI/CD Integration

The testing framework is integrated with GitHub Actions for continuous integration:

- Tests run automatically on pull requests
- Tests run on merge to main branch
- Weekly scheduled test runs
- Test reports published as artifacts
- Coverage reports published to dashboard

See `.github/workflows/ci.yml` for the CI configuration.

## Test Types

### Unit Tests

Unit tests focus on individual components and functions:

- Located in `unit/` directory
- Use extensive mocking to isolate components
- Fast execution for quick feedback
- Examples: `test_transaction_retriever.py`, `test_budget_analyzer.py`

### Integration Tests

Integration tests verify component interactions:

- Located in `integration/` directory
- Test multiple components together
- Use mock external services
- Examples: `test_transaction_flow.py`, `test_analysis_flow.py`

### End-to-End Tests

E2E tests verify complete workflows:

- Located in `e2e/` directory
- Test the entire application process
- Use mock external services
- Examples: `test_weekly_process.py`

### Performance Tests

Performance tests verify system efficiency:

- Located in `performance/` directory
- Measure execution time and resource usage
- Examples: `test_transaction_processing.py`

### Security Tests

Security tests verify data protection:

- Located in `security/` directory
- Test credential handling and secure communications
- Examples: `test_credential_handling.py`

## Troubleshooting

### Common Issues

- **Missing dependencies**: Run `pip install -r requirements.txt` to install all test dependencies
- **Environment setup**: Ensure `.env.test` file is properly configured
- **Test discovery issues**: Check `pytest.ini` for correct test path configuration
- **Mock configuration**: Verify mock objects are properly configured for your test scenario

### Debugging Tests

```bash
# Run tests with verbose output
pytest -v

# Run tests with debug logging
pytest --log-cli-level=DEBUG

# Run a specific test with debugging
pytest unit/test_transaction_retriever.py::test_execute_success -v
```

### Getting Help

For additional help with the testing framework, refer to:

- Documentation in `docs/testing.md`
- Pytest documentation: https://docs.pytest.org/
- Example tests in each test directory

## Contributing

When contributing new tests or modifying existing ones:

1. Follow the established naming conventions
2. Ensure tests are isolated and don't depend on external services
3. Use appropriate fixtures and mock objects
4. Include both positive and negative test cases
5. Verify code coverage for your changes
6. Update this documentation if adding new test patterns or utilities