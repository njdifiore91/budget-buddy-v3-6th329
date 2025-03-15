# Budget Management Application

An automated system designed to help individuals track, analyze, and optimize their personal spending habits against predefined budgets. This backend-only solution integrates with financial services, AI, and communication platforms to provide actionable financial insights without requiring user intervention.

## Features

- **Transaction Retrieval**: Automatically extract transaction data from Capital One checking account on a weekly basis
- **Transaction Categorization**: AI-powered mapping of transactions to budget categories using Gemini AI
- **Budget Analysis**: Comparison of actual spending to budgeted amounts by category
- **Insight Generation**: AI-generated summary of spending patterns with emphasis on budget status
- **Automated Reporting**: Email delivery of spending insights to specified recipients
- **Automated Savings**: Transfer of unspent budget amounts to a designated savings account

## Architecture

The Budget Management Application follows a serverless, event-driven architecture designed to operate autonomously on a scheduled basis. It is implemented as a Google Cloud Run job that executes on a weekly schedule.

### Key Components

- **Transaction Retriever**: Extracts transaction data from Capital One and stores in Google Sheets
- **Transaction Categorizer**: Uses Gemini AI to categorize transactions based on transaction locations
- **Budget Analyzer**: Compares actual spending to budgeted amounts and calculates variances
- **Insight Generator**: Creates spending analysis and recommendations using Gemini AI
- **Report Distributor**: Formats and sends email reports via Gmail
- **Savings Automator**: Transfers surplus funds to savings account

### External Integrations

- **Capital One API**: For transaction retrieval and fund transfers
- **Google Sheets API**: For storing transaction data and budget information
- **Gemini API**: For AI-powered transaction categorization and insight generation
- **Gmail API**: For sending automated reports

### Infrastructure

- **Google Cloud Run**: Serverless execution environment
- **Google Cloud Scheduler**: For weekly job triggering
- **Google Secret Manager**: For secure credential storage
- **Google Cloud Logging**: For application monitoring

## Prerequisites

- Python 3.11 or higher
- Docker (for containerized deployment)
- Google Cloud Platform account
- Capital One developer account with API access
- Google Workspace account (for Sheets and Gmail access)
- Gemini AI API key

## Setup

Follow these steps to set up the Budget Management Application:

### Local Development Setup

1. Clone the repository
   ```bash
   git clone <repository-url>
   cd budget-management-app/src/backend
   ```

2. Create a virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on `.env.example`
   ```bash
   cp .env.example .env
   # Edit .env with your API credentials and configuration
   ```

5. Run the application locally
   ```bash
   python main.py
   ```

### Google Cloud Setup

1. Create a Google Cloud project
   ```bash
   gcloud projects create budget-management-app
   gcloud config set project budget-management-app
   ```

2. Enable required APIs
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable cloudscheduler.googleapis.com
   gcloud services enable secretmanager.googleapis.com
   gcloud services enable logging.googleapis.com
   ```

3. Create a service account
   ```bash
   gcloud iam service-accounts create budget-management-service
   ```

4. Grant necessary permissions
   ```bash
   gcloud projects add-iam-policy-binding budget-management-app \
     --member="serviceAccount:budget-management-service@budget-management-app.iam.gserviceaccount.com" \
     --role="roles/run.invoker"
   
   gcloud projects add-iam-policy-binding budget-management-app \
     --member="serviceAccount:budget-management-service@budget-management-app.iam.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```

5. Store API credentials in Secret Manager
   ```bash
   # Example for storing Capital One API key
   echo -n "your-api-key" | gcloud secrets create capital-one-api-key --data-file=-
   
   # Repeat for other credentials
   ```

### Google Sheets Setup

1. Create two Google Sheets:
   - **Master Budget**: Contains budget categories and allocated amounts
   - **Weekly Spending**: Will store transaction data and categorization

2. Share both sheets with the service account email
   ```
   budget-management-service@budget-management-app.iam.gserviceaccount.com
   ```

3. Store the Sheet IDs in Secret Manager
   ```bash
   echo -n "your-master-budget-sheet-id" | gcloud secrets create master-budget-sheet-id --data-file=-
   echo -n "your-weekly-spending-sheet-id" | gcloud secrets create weekly-spending-sheet-id --data-file=-
   ```

## Deployment

The application can be deployed to Google Cloud Run using Terraform or manually.

### Using Terraform

1. Navigate to the Terraform directory
   ```bash
   cd deploy/terraform
   ```

2. Initialize Terraform
   ```bash
   terraform init
   ```

3. Create a `terraform.tfvars` file with your configuration
   ```
   project_id = "budget-management-app"
   region = "us-east1"
   app_name = "budget-management"
   container_image = "gcr.io/budget-management-app/budget-management:latest"
   service_account_email = "budget-management-service@budget-management-app.iam.gserviceaccount.com"
   schedule_cron = "0 12 * * 0"  # Sunday at 12 PM
   schedule_timezone = "America/New_York"
   ```

4. Apply the Terraform configuration
   ```bash
   terraform apply
   ```

### Manual Deployment

1. Build the Docker image
   ```bash
   docker build -t gcr.io/budget-management-app/budget-management:latest .
   ```

2. Push the image to Google Container Registry
   ```bash
   docker push gcr.io/budget-management-app/budget-management:latest
   ```

3. Create the Cloud Run job
   ```bash
   gcloud run jobs create budget-management \
     --image gcr.io/budget-management-app/budget-management:latest \
     --service-account budget-management-service@budget-management-app.iam.gserviceaccount.com \
     --region us-east1 \
     --memory 2Gi \
     --cpu 1 \
     --max-retries 3 \
     --task-timeout 10m
   ```

4. Create the Cloud Scheduler job
   ```bash
   gcloud scheduler jobs create http budget-management-weekly \
     --schedule="0 12 * * 0" \
     --time-zone="America/New_York" \
     --uri="https://us-east1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/budget-management-app/jobs/budget-management:run" \
     --http-method=POST \
     --oauth-service-account-email=budget-management-service@budget-management-app.iam.gserviceaccount.com
   ```

## Usage

Once deployed, the Budget Management Application will run automatically every Sunday at 12 PM EST. It will:

1. Retrieve transactions from the past week from Capital One
2. Categorize transactions using Gemini AI
3. Compare spending to budget categories
4. Generate insights about spending patterns
5. Send an email report to configured recipients
6. Transfer any budget surplus to the savings account

No manual intervention is required for normal operation.

### Manual Execution

To manually trigger the job:

```bash
# Using gcloud
gcloud run jobs execute budget-management --region us-east1

# Or locally
python main.py
```

### Command Line Options

When running locally, the following command line options are available:

```
--debug            Enable debug logging
--dry-run          Skip actual financial transactions
--skip-email       Skip sending email reports
--skip-transfer    Skip savings transfer
```

Example:
```bash
python main.py --debug --dry-run
```

## Configuration

The application is configured through environment variables or Secret Manager secrets in production.

### Environment Variables

Key environment variables include:

- `ENVIRONMENT`: Set to `development` or `production`
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- `WEEKLY_SPENDING_SHEET_ID`: ID of the Weekly Spending Google Sheet
- `MASTER_BUDGET_SHEET_ID`: ID of the Master Budget Google Sheet
- `CAPITAL_ONE_CHECKING_ACCOUNT_ID`: ID of the Capital One checking account
- `CAPITAL_ONE_SAVINGS_ACCOUNT_ID`: ID of the Capital One savings account

See `.env.example` for a complete list of configuration options.

### Secrets

Sensitive information should be stored in Secret Manager:

- `capital-one-credentials`: Capital One API credentials
- `google-sheets-credentials`: Google Sheets API credentials
- `gmail-credentials`: Gmail API credentials
- `gemini-api-key`: Gemini AI API key

## Monitoring

The application logs execution details to Google Cloud Logging. You can monitor the application using the Google Cloud Console or the gcloud CLI.

### Viewing Logs

```bash
# View logs for the Cloud Run job
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=budget-management" --limit=10
```

### Metrics

Key metrics to monitor:

- Job execution success/failure
- Execution duration
- Transaction count
- Categorization accuracy
- Email delivery status
- Transfer success status

## Maintenance

Regular maintenance tasks include:

### Dependency Updates

Update Python dependencies periodically:

```bash
pip install --upgrade -r requirements.txt
```

Update the Docker base image:

```bash
# In Dockerfile
FROM python:3.11-slim  # Update version as needed
```

### Credential Rotation

Rotate API credentials regularly:

1. Generate new credentials in the respective service consoles
2. Update the secrets in Secret Manager

```bash
echo -n "new-api-key" | gcloud secrets versions add capital-one-api-key --data-file=-
```

### Backup Procedures

Google Sheets data is automatically backed up by Google. For additional backup:

1. Export Google Sheets data periodically
2. Back up the application code repository
3. Document Secret Manager secrets (securely)

## Troubleshooting

Common issues and their solutions:

### Authentication Failures

- Verify API credentials are correct and not expired
- Check service account permissions
- Ensure OAuth scopes are properly configured

### Transaction Retrieval Issues

- Verify Capital One API is operational
- Check account IDs are correct
- Ensure date ranges are properly formatted

### Categorization Problems

- Verify Gemini API key is valid
- Check that budget categories exist in Master Budget sheet
- Review AI prompt templates for issues

### Email Delivery Failures

- Verify Gmail API credentials
- Check recipient email addresses
- Ensure email content is properly formatted

### Transfer Failures

- Verify Capital One transfer API access
- Check account balances and status
- Ensure transfer amount meets minimum requirements

## Development

Guidelines for developing and extending the application:

### Project Structure

```
src/backend/
├── api_clients/       # API client implementations
├── components/        # Core application components
├── config/            # Configuration management
├── deploy/            # Deployment configurations
│   └── terraform/     # Terraform IaC files
├── models/            # Data models
├── services/          # Shared services
├── templates/         # Email and AI prompt templates
├── tests/             # Test suite
├── utils/             # Utility functions
├── .env.example       # Example environment variables
├── Dockerfile         # Container definition
├── main.py            # Application entry point
├── README.md          # This documentation
└── requirements.txt   # Python dependencies
```

### Adding New Features

To add a new feature:

1. Create appropriate models in `models/`
2. Implement API clients if needed in `api_clients/`
3. Create a new component in `components/`
4. Update `main.py` to include the new component in the workflow
5. Add tests in `tests/`
6. Update documentation

### Testing

Run tests using pytest:

```bash
python -m pytest

# With coverage
python -m pytest --cov=. --cov-report=term-missing
```

Mock external APIs during testing using the mock classes in `tests/mocks/`.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For questions or support, contact:
- Email: njdifiore@gmail.com