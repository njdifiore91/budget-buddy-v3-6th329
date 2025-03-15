# Development Guide for Budget Management Application

This document provides comprehensive guidance for developing the Budget Management Application. It covers environment setup, codebase structure, development workflows, testing, and deployment.

## 1. Development Environment Setup

This section covers the setup of your local development environment for the Budget Management Application.

### 1.1 Prerequisites

Before setting up the development environment, ensure you have the following prerequisites installed:

- **Python 3.11+**: The application is built using Python 3.11 or higher
- **Git**: For version control
- **Docker**: For containerized development and testing (optional but recommended)
- **Google Cloud SDK**: For interacting with Google Cloud services
- **API Access**:
  - Capital One API credentials
  - Google Workspace (for Sheets and Gmail)
  - Gemini API access

For macOS users:
```bash
# Install with Homebrew
brew install python@3.11 git docker google-cloud-sdk
```

For Ubuntu/Debian users:
```bash
# Install Python 3.11
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.11 python3.11-venv python3.11-dev

# Install Git and Docker
sudo apt install git docker.io

# Install Google Cloud SDK
# Follow instructions at https://cloud.google.com/sdk/docs/install#deb
```

For Windows users:
- Install Python 3.11 from [python.org](https://www.python.org/downloads/)
- Install Git from [git-scm.com](https://git-scm.com/download/win)
- Install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop)
- Install Google Cloud SDK from [cloud.google.com/sdk](https://cloud.google.com/sdk/docs/install#windows)

### 1.2 Repository Setup

Clone the repository and navigate to the project directory:

```bash
# Clone the repository
git clone <repository-url>
cd budget-management-app
```

### 1.3 Python Environment Setup

Set up a Python virtual environment and install dependencies:

```bash
# Navigate to the backend directory
cd src/backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

The `requirements.txt` file includes the following key dependencies:
- `requests`: HTTP library for API communication
- `google-api-python-client`: Google API client for Google Sheets and Gmail integration
- `google-auth`: Authentication for Google APIs
- `google-generativeai`: Google Generative AI client for Gemini integration
- `pandas`: Data manipulation and analysis
- `matplotlib`: Chart generation for budget reports
- `python-dotenv`: Environment variable management
- `pytest`: Testing framework

See the full `requirements.txt` file for all dependencies.

### 1.4 Environment Configuration

Create a `.env` file for environment variables:

```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your API credentials and configuration
vim .env  # or use any text editor
```

The `.env` file contains configuration for:
- Application settings (debug mode, logging level)
- Execution schedule settings
- Transaction processing settings
- API credentials and configuration for:
  - Capital One API
  - Google Sheets API
  - Gemini API
  - Gmail API
- Google Cloud settings

For development, ensure the following settings are set:
```
DEBUG=True
TESTING=True
```

For security reasons, never commit the `.env` file to version control. It's already included in `.gitignore`.

### 1.5 Automated Setup Script

For convenience, you can use the provided setup script to automate the development environment setup:

```bash
# Navigate to the project root
cd <project-root>

# Run the setup script
bash src/scripts/development/setup_local_env.sh
```

This script will:
1. Create necessary directory structure
2. Set up Python virtual environment
3. Install required dependencies
4. Configure environment variables for development
5. Set up mock API servers for local testing
6. Generate test data for development

After running the script, follow the displayed instructions to activate the virtual environment and start development.

### 1.6 API Credentials Setup

For development, you'll need to set up API credentials for the external services:

#### Capital One API
1. Register for a Capital One developer account at their developer portal
2. Create a new application to get client ID and client secret
3. Configure the required scopes: `transactions:read`, `accounts:read`, `transfers:write`
4. Add the credentials to your `.env` file

#### Google APIs (Sheets and Gmail)
1. Create a Google Cloud project at [console.cloud.google.com](https://console.cloud.google.com/)
2. Enable the Google Sheets API and Gmail API
3. Create a service account with appropriate permissions
4. Download the service account JSON key file
5. Place the key file in the `credentials/` directory
6. Update the `.env` file with the path to the credentials file

#### Gemini API
1. Sign up for Gemini API access at [ai.google.dev](https://ai.google.dev/)
2. Generate an API key
3. Add the API key to your `.env` file

For local development and testing, you can use mock APIs instead of real API credentials. See the [Mock APIs](#17-mock-apis-for-development) section for details.

### 1.7 Mock APIs for Development

The application includes mock implementations of all external APIs for development and testing:

```bash
# Start the mock API server
python src/scripts/development/mock_api_server.py
```

This will start a local server that simulates the responses from:
- Capital One API
- Google Sheets API
- Gemini API
- Gmail API

To use the mock APIs, set the following in your `.env` file:
```
MOCK_API_ENABLED=True
LOCAL_PORT=8080  # Port for the mock API server
```

The mock API server provides predefined responses based on test data in the `src/test/fixtures/json/api_responses/` directory. You can customize these responses for your development needs.

## 2. Project Structure

This section provides an overview of the project structure to help you navigate the codebase.

### 2.1 Directory Structure

The Budget Management Application follows a modular structure:

```
src/backend/
├── api_clients/         # API integration clients
│   ├── capital_one_client.py
│   ├── gemini_client.py
│   ├── gmail_client.py
│   ├── google_sheets_client.py
│   └── __init__.py
├── components/          # Core business logic components
│   ├── budget_analyzer.py
│   ├── insight_generator.py
│   ├── report_distributor.py
│   ├── savings_automator.py
│   ├── transaction_categorizer.py
│   ├── transaction_retriever.py
│   └── __init__.py
├── config/              # Application configuration
│   ├── logging_config.py
│   ├── settings.py
│   └── __init__.py
├── deploy/              # Deployment configuration
│   ├── terraform/
│   ├── cloud_build.yaml
│   └── __init__.py
├── docs/                # Documentation
│   ├── architecture.md
│   ├── api_integration.md
│   ├── deployment.md
│   ├── development.md
│   ├── monitoring.md
│   ├── testing.md
│   ├── security.md
│   └── __init__.py
├── models/              # Data models
│   ├── budget.py
│   ├── category.py
│   ├── report.py
│   ├── transaction.py
│   ├── transfer.py
│   └── __init__.py
├── services/            # Shared services
│   ├── authentication_service.py
│   ├── data_transformation_service.py
│   ├── error_handling_service.py
│   ├── logging_service.py
│   └── __init__.py
├── templates/           # Email and AI prompt templates
│   ├── ai_prompts/
│   ├── email_template.html
│   └── __init__.py
├── tests/               # Test suite
│   ├── fixtures/
│   ├── mocks/
│   ├── unit/
│   ├── integration/
│   ├── conftest.py
│   └── __init__.py
├── utils/               # Utility functions
│   ├── date_utils.py
│   ├── error_handlers.py
│   ├── formatters.py
│   ├── validation.py
│   └── __init__.py
├── .env.example         # Environment variables template
├── Dockerfile           # Container definition
├── main.py              # Application entry point
├── pyproject.toml       # Project metadata
├── requirements.txt     # Python dependencies
└── setup.py             # Package setup script
```

Additional directories at the project root:

```
src/scripts/            # Utility scripts for development, deployment, etc.
├── config/
├── development/
├── deployment/
├── maintenance/
├── monitoring/
└── setup/

src/test/               # Comprehensive test suite
├── fixtures/
├── mocks/
├── unit/
├── integration/
├── e2e/
└── performance/

infrastructure/         # Infrastructure configuration
├── monitoring/
├── environments/
├── diagrams/
└── docs/
```

### 2.2 Key Components

The application is structured around the following key components:

1. **Transaction Retriever** (`components/transaction_retriever.py`)
   - Extracts transaction data from Capital One
   - Stores transactions in Google Sheets

2. **Transaction Categorizer** (`components/transaction_categorizer.py`)
   - Uses Gemini AI to categorize transactions
   - Updates transaction categories in Google Sheets

3. **Budget Analyzer** (`components/budget_analyzer.py`)
   - Compares actual spending to budgeted amounts
   - Calculates variances and determines budget status

4. **Insight Generator** (`components/insight_generator.py`)
   - Uses Gemini AI to generate spending insights
   - Creates visualizations of budget performance

5. **Report Distributor** (`components/report_distributor.py`)
   - Formats and sends email reports via Gmail
   - Includes insights and visualizations

6. **Savings Automator** (`components/savings_automator.py`)
   - Calculates surplus amount for savings
   - Transfers funds via Capital One API

Each component follows a similar structure with an `execute()` method that serves as the main entry point and returns a status dictionary that's passed to the next component in the workflow.

For detailed information about each component, refer to the [Architecture Documentation](architecture.md).

### 2.3 API Clients

The application includes dedicated clients for each external API:

1. **Capital One Client** (`api_clients/capital_one_client.py`)
   - Handles authentication with Capital One API
   - Retrieves transaction data
   - Initiates savings transfers

2. **Google Sheets Client** (`api_clients/google_sheets_client.py`)
   - Handles authentication with Google Sheets API
   - Reads budget data and transaction data
   - Updates sheets with new data

3. **Gemini Client** (`api_clients/gemini_client.py`)
   - Handles authentication with Gemini API
   - Sends prompts for transaction categorization
   - Generates spending insights

4. **Gmail Client** (`api_clients/gmail_client.py`)
   - Handles authentication with Gmail API
   - Formats and sends email reports

Each client encapsulates the details of interacting with its respective API, including authentication, error handling, and retry logic.

For detailed information about API integrations, refer to the [API Integration Documentation](api_integration.md).

### 2.4 Data Models

The application uses domain models to represent key business entities:

1. **Transaction** (`models/transaction.py`)
   - Represents a financial transaction
   - Properties: location, amount, timestamp, category

2. **Category** (`models/category.py`)
   - Represents a budget category
   - Properties: name, weekly_amount

3. **Budget** (`models/budget.py`)
   - Represents the budget with categories and analysis
   - Methods for analyzing transactions against budget

4. **Transfer** (`models/transfer.py`)
   - Represents a savings transfer
   - Properties: source_account, destination_account, amount, status

5. **Report** (`models/report.py`)
   - Represents an email report
   - Properties: subject, body, recipients, attachments

These models provide type safety, validation, and encapsulate business logic related to their respective entities.

### 2.5 Shared Services

The application includes several shared services used across components:

1. **Authentication Service** (`services/authentication_service.py`)
   - Manages authentication with external APIs
   - Handles token refresh and credential management

2. **Logging Service** (`services/logging_service.py`)
   - Provides structured logging with context
   - Includes performance logging and log formatting

3. **Error Handling Service** (`services/error_handling_service.py`)
   - Standardizes error handling across the application
   - Implements retry logic with exponential backoff

4. **Data Transformation Service** (`services/data_transformation_service.py`)
   - Handles data format conversions between systems
   - Transforms API responses to internal models

These services provide cross-cutting functionality used by multiple components.

### 2.6 Configuration

Application configuration is managed through several mechanisms:

1. **Environment Variables** (`.env`)
   - API credentials and endpoints
   - Feature flags and operational settings
   - Environment-specific configuration

2. **Settings Module** (`config/settings.py`)
   - Loads environment variables with defaults
   - Provides structured access to configuration
   - Validates configuration values

3. **Logging Configuration** (`config/logging_config.py`)
   - Configures logging format and levels
   - Sets up log handlers for different environments

For local development, copy `.env.example` to `.env` and update the values as needed.

## 3. Development Workflow

This section covers the recommended development workflow for the Budget Management Application.

### 3.1 Local Development

For local development, you can run the application using the provided script:

```bash
# Navigate to the project root
cd <project-root>

# Activate the virtual environment if not already activated
source src/backend/venv/bin/activate  # On Windows: src\backend\venv\Scripts\activate

# Run the application locally
python src/scripts/development/local_run.py
```

The `local_run.py` script provides several options:

```bash
# Run with debug logging
python src/scripts/development/local_run.py --debug

# Run with mock APIs (if not already enabled in .env)
python src/scripts/development/local_run.py --mock-api

# Skip actual financial transactions (dry run)
python src/scripts/development/local_run.py --dry-run

# Skip sending emails
python src/scripts/development/local_run.py --skip-email

# Skip savings transfer
python src/scripts/development/local_run.py --skip-transfer
```

You can combine these options as needed for your development scenario.

### 3.2 Development Cycle

Follow this development cycle for making changes to the application:

1. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Implement your changes following the coding standards
   - Add or update tests as needed

3. **Run Tests**
   ```bash
   # Run unit tests
   python -m pytest src/backend/tests/unit

   # Run integration tests
   python -m pytest src/backend/tests/integration

   # Run with coverage
   python -m pytest --cov=src/backend src/backend/tests/
   ```

4. **Run Linting**
   ```bash
   # Run flake8 for linting
   flake8 src/backend

   # Run mypy for type checking
   mypy src/backend
   ```

5. **Local Execution**
   ```bash
   # Run the application locally to test your changes
   python src/scripts/development/local_run.py
   ```

6. **Commit Changes**
   ```bash
   git add .
   git commit -m "Descriptive commit message"
   ```

7. **Push Changes**
   ```bash
   git push origin feature/your-feature-name
   ```

8. **Create Pull Request**
   - Create a pull request on GitHub
   - Fill in the PR template with details about your changes
   - Request reviews from team members

9. **Address Review Feedback**
   - Make requested changes
   - Push additional commits to the same branch

10. **Merge Pull Request**
    - Once approved, merge your pull request
    - Delete the feature branch after merging

### 3.3 Coding Standards

Follow these coding standards for consistency across the codebase:

#### Python Style Guide
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use 4 spaces for indentation (no tabs)
- Maximum line length of 88 characters (compatible with Black formatter)
- Use snake_case for variables, functions, and methods
- Use PascalCase for classes
- Use UPPER_CASE for constants

#### Documentation
- Use docstrings for all modules, classes, and functions
- Follow [Google style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- Include type hints for function parameters and return values
- Document exceptions that may be raised

Example docstring:
```python
def calculate_transfer_amount(budget_analysis: Dict[str, Any]) -> Decimal:
    """Calculate the amount to transfer to savings based on budget surplus.

    Args:
        budget_analysis: Dictionary containing budget analysis results,
            including total_variance and status.

    Returns:
        Decimal amount to transfer to savings (0 if no surplus).

    Raises:
        ValueError: If budget_analysis is missing required keys.
    """
```

#### Error Handling
- Use specific exception types rather than generic exceptions
- Handle exceptions at the appropriate level
- Log exceptions with context information
- Use the provided error handling utilities in `utils/error_handlers.py`

#### Testing
- Write tests for all new functionality
- Maintain high code coverage (target: 85%+)
- Use descriptive test names that explain the scenario and expected behavior
- Follow the Arrange-Act-Assert pattern in tests

#### Commits and Pull Requests
- Use descriptive commit messages
- Keep commits focused on a single change
- Reference issue numbers in commit messages and PR descriptions
- Keep PRs focused on a single feature or bug fix

### 3.4 Adding New Features

When adding new features to the application, follow these guidelines:

1. **Understand the Architecture**
   - Review the [Architecture Documentation](architecture.md) to understand how components interact
   - Identify where your feature fits in the existing architecture

2. **Plan Your Implementation**
   - Define the requirements and acceptance criteria
   - Design the solution considering existing patterns
   - Identify any new dependencies or API changes

3. **Implement the Feature**
   - Follow the coding standards
   - Implement the feature in the appropriate component(s)
   - Add appropriate error handling and logging

4. **Add Tests**
   - Write unit tests for new functions and methods
   - Add integration tests for component interactions
   - Update existing tests if behavior changes

5. **Update Documentation**
   - Update relevant documentation files
   - Add docstrings to new code
   - Update README if necessary

6. **Review and Refine**
   - Review your own code before submitting
   - Address any issues found during testing
   - Refactor for clarity and maintainability

Example workflow for adding a new feature:

```bash
# Create a feature branch
git checkout -b feature/new-budget-alert

# Implement the feature
# Edit files, add tests, etc.

# Run tests to verify
python -m pytest

# Run linting
flake8 src/backend

# Commit changes
git add .
git commit -m "Add new budget alert feature"

# Push changes
git push origin feature/new-budget-alert

# Create pull request on GitHub
```

### 3.5 Debugging

Use these techniques for debugging the application:

#### Logging
The application uses structured logging via the `logging_service.py` module. To enable debug logging:

1. Set `LOG_LEVEL=DEBUG` in your `.env` file, or
2. Run with the `--debug` flag: `python src/scripts/development/local_run.py --debug`

Log messages include component name, operation, and context information to help with debugging.

#### Interactive Debugging
You can use Python's built-in debugger (pdb) or an IDE like VS Code or PyCharm for interactive debugging:

```python
# Add a breakpoint in your code
import pdb; pdb.set_trace()
```

Or use the `breakpoint()` function in Python 3.7+:

```python
# Add a breakpoint in your code
breakpoint()
```

#### Debugging API Interactions
For debugging API interactions:

1. Enable debug logging for requests:
   ```python
   import logging
   logging.getLogger('urllib3').setLevel(logging.DEBUG)
   ```

2. Use the mock API server with debug mode:
   ```bash
   python src/scripts/development/mock_api_server.py --debug
   ```

3. Inspect request/response data in the logs

#### Common Issues and Solutions

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| API Authentication Failure | Invalid or expired credentials | Check API credentials in `.env` file |
| Missing Transactions | Date range issue or API error | Verify date range calculation and API response |
| Categorization Issues | Prompt format or AI response parsing | Check AI prompt template and response parsing logic |
| Email Delivery Failure | Gmail API permissions or formatting | Verify Gmail credentials and email format |

## 4. Testing

This section covers the testing approach and practices for the Budget Management Application to ensure code quality and reliability.

### 4.1 Testing Approach

The application uses a comprehensive testing approach with multiple levels of testing:

1. **Unit Testing**: Testing individual functions and classes in isolation with mocked dependencies
2. **Integration Testing**: Testing interactions between components with mocked external services
3. **End-to-End Testing**: Testing the complete application workflow with mock APIs
4. **Performance Testing**: Testing application performance under various conditions
5. **Security Testing**: Testing security aspects of the application

The testing framework is pytest, with additional plugins for mocking, coverage, and other testing needs. All tests are located in the `src/backend/tests/` and `src/test/` directories, organized by test type.

### 4.2 Running Tests

Run tests using the pytest command:

```bash
# Run all tests
python -m pytest

# Run unit tests only
python -m pytest src/backend/tests/unit

# Run integration tests only
python -m pytest src/backend/tests/integration

# Run tests with coverage
python -m pytest --cov=src/backend src/backend/tests/

# Generate coverage report
python -m pytest --cov=src/backend --cov-report=html src/backend/tests/
```

You can also use the provided script for running tests:

```bash
bash src/scripts/development/run_tests.sh
```

This script runs all tests and generates a coverage report. The application targets high test coverage:

- Overall coverage: 85%+
- Core logic: 90%+
- API clients: 85%+
- Utility functions: 80%+

Coverage is measured using pytest-cov and reported in both HTML and XML formats.

### 4.3 Writing Tests

Follow these guidelines when writing tests:

#### Unit Tests

Unit tests should test a single function or method in isolation. Use mocks for external dependencies.

Example unit test:

```python
def test_calculate_transfer_amount_with_surplus():
    # Arrange
    budget_analysis = {
        "total_variance": Decimal("50.00"),
        "status": "surplus"
    }
    
    # Act
    result = calculate_transfer_amount(budget_analysis)
    
    # Assert
    assert result == Decimal("50.00")
```

#### Integration Tests

Integration tests should test interactions between components. Use mock API clients but test real component interactions.

Example integration test:

```python
def test_transaction_flow():
    # Arrange
    mock_capital_one = MockCapitalOneClient()
    mock_sheets = MockGoogleSheetsClient()
    
    # Configure mocks
    transactions = create_test_transactions(5)
    mock_capital_one.set_transactions(transactions)
    
    retriever = TransactionRetriever(
        capital_one_client=mock_capital_one,
        sheets_client=mock_sheets
    )
    
    # Act
    result = retriever.execute()
    
    # Assert
    assert result["status"] == "success"
    assert result["transaction_count"] == 5
    # Verify data was written to sheets
    assert len(mock_sheets.get_sheet_data("Weekly Spending")) == 5
```

#### Test Fixtures

Use pytest fixtures for common test setup. Fixtures are defined in `conftest.py`.

Example fixture usage:

```python
def test_categorize_transactions(transaction_categorizer, uncategorized_transactions, categories):
    # Arrange - fixtures provide the test objects
    
    # Act
    result = transaction_categorizer.categorize_transactions(uncategorized_transactions, categories)
    
    # Assert
    assert len(result) == len(uncategorized_transactions)
    assert all(t.category is not None for t in result)
```

#### Mocking External Services

Use the provided mock implementations for external services:

```python
# Example of using mock clients in tests
def test_with_mock_clients():
    # Arrange
    mock_capital_one = MockCapitalOneClient()
    mock_sheets = MockGoogleSheetsClient()
    mock_gemini = MockGeminiClient()
    mock_gmail = MockGmailClient()
    
    # Configure mock behavior
    mock_capital_one.set_transactions([...])
    mock_sheets.set_sheet_data("Master Budget", [...])
    mock_gemini.set_categorization_response([...])
    
    # Create component with mock dependencies
    component = YourComponent(
        capital_one_client=mock_capital_one,
        sheets_client=mock_sheets,
        gemini_client=mock_gemini,
        gmail_client=mock_gmail
    )
    
    # Act and Assert...
```

### 4.4 Test Best Practices

Follow these best practices when writing tests:

1. **Descriptive Test Names**: Use descriptive names that clearly indicate what is being tested and the expected outcome
2. **Arrange-Act-Assert Pattern**: Structure tests with clear setup, action, and verification phases
3. **Test Independence**: Each test should run independently without relying on the state from other tests
4. **Focused Tests**: Each test should verify a single behavior or aspect of functionality
5. **Realistic Test Data**: Use realistic test data that resembles production data
6. **Error Case Testing**: Test both successful and failure scenarios
7. **Boundary Testing**: Test edge cases and boundary conditions
8. **Mocking External Services**: Always mock external services for faster and more reliable tests
9. **Test Coverage**: Aim for high code coverage, especially for critical business logic
10. **Performance Considerations**: Keep tests fast to encourage regular testing

To view a generated coverage report:

```bash
# Generate HTML coverage report
python -m pytest --cov=src/backend --cov-report=html src/backend/tests/

# Open the report in your browser
open htmlcov/index.html  # On macOS
# or
xdg-open htmlcov/index.html  # On Linux
# or
start htmlcov/index.html  # On Windows
```

## 5. Deployment

This section covers the deployment process for the Budget Management Application. For detailed information, refer to the [Deployment Documentation](deployment.md).

### 5.1 Deployment Environments

The application supports multiple deployment environments:

1. **Development**: For development and testing
2. **Testing**: For integration testing and QA
3. **Production**: For production use

Each environment has its own configuration and resources.

### 5.2 Deployment Process

The application is deployed using Google Cloud Run jobs with Terraform for infrastructure management:

1. **Build Docker Image**
   ```bash
   # Build the Docker image
   docker build -t gcr.io/[PROJECT_ID]/budget-management:latest src/backend/
   
   # Push to Google Container Registry
   docker push gcr.io/[PROJECT_ID]/budget-management:latest
   ```

2. **Deploy Infrastructure**
   ```bash
   # Navigate to Terraform directory
   cd src/backend/deploy/terraform
   
   # Initialize Terraform
   terraform init
   
   # Apply Terraform configuration
   terraform apply -var-file=environments/[ENV].tfvars
   ```

3. **Configure Cloud Scheduler**
   ```bash
   # Set up Cloud Scheduler to trigger the job weekly
   gcloud scheduler jobs create http budget-management-weekly \
     --schedule="0 12 * * 0" \
     --uri="https://[REGION]-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/[PROJECT_ID]/jobs/budget-management-job:run" \
     --http-method=POST \
     --oauth-service-account-email=[SERVICE_ACCOUNT]@[PROJECT_ID].iam.gserviceaccount.com \
     --time-zone="America/New_York"
   ```

For automated deployment, the application uses GitHub Actions. The workflow is defined in `.github/workflows/cd.yml`.

### 5.3 Manual Execution

You can manually trigger the Cloud Run job:

```bash
# Trigger the job manually
gcloud run jobs execute budget-management-job --region=[REGION]
```

This is useful for testing or running the job outside the regular schedule.

### 5.4 Monitoring Deployments

Monitor deployments using Google Cloud Console:

1. **Cloud Run Jobs**: View job execution history and logs
2. **Cloud Logging**: View application logs
3. **Cloud Monitoring**: View performance metrics and alerts

You can also use the provided monitoring scripts:

```bash
# Check job status
python src/scripts/monitoring/check_job_status.py

# Analyze logs
python src/scripts/monitoring/analyze_logs.py

# Generate performance report
python src/scripts/monitoring/performance_report.py
```

## 6. Troubleshooting

This section provides guidance for troubleshooting common issues during development and deployment.

### 6.1 Common Development Issues

#### Environment Setup Issues

| Issue | Solution |
|-------|----------|
| Missing dependencies | Run `pip install -r requirements.txt` |
| Environment variables not loaded | Check that `.env` file exists and is properly formatted |
| Python version mismatch | Ensure you're using Python 3.11+ |

#### API Integration Issues

| Issue | Solution |
|-------|----------|
| Capital One API authentication failure | Verify API credentials in `.env` file |
| Google Sheets API access denied | Check service account permissions and credentials |
| Gemini API rate limiting | Implement backoff strategy or reduce request frequency |
| Gmail API authentication failure | Verify service account has domain-wide delegation |

#### Testing Issues

| Issue | Solution |
|-------|----------|
| Tests failing due to missing fixtures | Ensure `conftest.py` is properly set up |
| Mock API not responding | Check that mock API server is running |
| Coverage report not generating | Install pytest-cov with `pip install pytest-cov` |

#### Local Execution Issues

| Issue | Solution |
|-------|----------|
| Module not found errors | Ensure Python path includes the project root |
| Permission denied errors | Check file permissions for credentials and data directories |
| Timeout errors | Increase timeout settings or check network connectivity |

### 6.2 Deployment Issues

#### Docker Build Issues

| Issue | Solution |
|-------|----------|
| Build failures | Check Dockerfile and dependencies |
| Image size too large | Use multi-stage builds and optimize dependencies |
| Push failures | Verify Google Cloud authentication |

#### Terraform Issues

| Issue | Solution |
|-------|----------|
| Initialization failures | Check Terraform version and provider configuration |
| Apply failures | Check error messages and Google Cloud permissions |
| State lock issues | Release the state lock if safe to do so |

#### Cloud Run Issues

| Issue | Solution |
|-------|----------|
| Job execution failures | Check logs in Google Cloud Console |
| Permission issues | Verify service account permissions |
| Resource constraints | Adjust memory and CPU allocation |

#### Cloud Scheduler Issues

| Issue | Solution |
|-------|----------|
| Job not triggering | Check schedule format and time zone |
| Authentication failures | Verify service account permissions |
| HTTP errors | Check Cloud Run job URL and accessibility |

### 6.3 Logging and Debugging

#### Viewing Logs

```bash
# View local logs
cat data/logs/application.log

# View Cloud Run job logs
gcloud logging read 'resource.type="cloud_run_job" resource.labels.job_name="budget-management-job"'

# Filter logs by severity
gcloud logging read 'resource.type="cloud_run_job" resource.labels.job_name="budget-management-job" severity>=ERROR'

# Filter logs by component
gcloud logging read 'resource.type="cloud_run_job" resource.labels.job_name="budget-management-job" jsonPayload.component="transaction_retriever"'
```

#### Debugging Techniques

1. **Enable Debug Logging**
   - Set `LOG_LEVEL=DEBUG` in `.env`
   - Run with `--debug` flag

2. **Use Interactive Debugger**
   - Add `breakpoint()` in code
   - Run with `python -m pdb src/scripts/development/local_run.py`

3. **Inspect API Interactions**
   - Enable request logging
   - Use mock API server with verbose output

4. **Check Environment Variables**
   - Print environment variables with `env | grep BUDGET`
   - Verify `.env` file is loaded correctly

5. **Verify API Access**
   - Use `src/scripts/utils/check_capital_one_status.py`
   - Test Google API access with `src/scripts/setup/verify_api_access.py`

### 6.4 Getting Help

If you encounter issues that you can't resolve, use these resources for help:

1. **Documentation**
   - Check the documentation in the `docs/` directory
   - Review code comments and docstrings

2. **Issue Tracker**
   - Search existing issues on GitHub
   - Create a new issue with detailed information

3. **Team Communication**
   - Reach out to team members on Slack
   - Discuss issues in team meetings

4. **External Resources**
   - Capital One API documentation
   - Google API documentation
   - Gemini API documentation
   - Python and library documentation

## 7. Contributing

This section provides guidelines for contributing to the Budget Management Application.

### 7.1 Contribution Process

To contribute to the project:

1. **Fork the Repository**
   - Fork the repository on GitHub
   - Clone your fork locally

2. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name