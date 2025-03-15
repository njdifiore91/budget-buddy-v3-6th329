# Budget Management Application

A serverless, event-driven system designed to help individuals track, analyze, and optimize their personal spending habits against predefined budgets. This backend-only solution integrates with financial services, AI, and communication platforms to provide actionable financial insights without requiring user intervention.

## Features

- **Automated Transaction Retrieval**: Weekly extraction of transaction data from Capital One checking account
- **AI-Powered Categorization**: Automatic categorization of transactions using Gemini AI
- **Budget Analysis**: Comparison of actual spending to budgeted amounts by category
- **Intelligent Insights**: AI-generated summary of spending patterns with actionable recommendations
- **Automated Reporting**: Email delivery of spending insights to specified recipients
- **Automated Savings**: Transfer of unspent budget amounts to a designated savings account

## Architecture

The application follows a serverless architecture using Google Cloud Run jobs with scheduled execution via Google Cloud Scheduler. It integrates with the following external services:

- **Capital One API**: For transaction retrieval and fund transfers
- **Google Sheets API**: For budget data storage and retrieval
- **Gemini API**: For transaction categorization and insight generation
- **Gmail API**: For sending automated spending reports

## Prerequisites

- Python 3.11+
- Google Cloud Platform account
- Capital One developer account with API access
- Google Workspace account with access to Sheets and Gmail
- Gemini API access
- Docker (for local development and testing)

## Setup and Installation

### Local Development

1. Clone the repository
   ```bash
   git clone <repository-url>
   cd budget-management-application
   ```

2. Set up a virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r src/backend/requirements.txt
   ```

4. Configure environment variables
   ```bash
   cp src/backend/.env.example src/backend/.env
   # Edit .env with your API credentials and configuration
   ```

5. Run tests
   ```bash
   cd src/backend
   pytest
   ```

### Cloud Deployment

1. Set up Google Cloud project
   ```bash
   gcloud projects create budget-management-app
   gcloud config set project budget-management-app
   ```

2. Enable required APIs
   ```bash
   gcloud services enable run.googleapis.com cloudscheduler.googleapis.com secretmanager.googleapis.com
   ```

3. Deploy using Terraform
   ```bash
   cd src/backend/deploy/terraform
   terraform init
   terraform apply
   ```

4. Set up secrets in Google Secret Manager
   ```bash
   cd src/scripts/deployment
   ./setup_secrets.sh
   ```

5. Deploy the Cloud Run job
   ```bash
   cd src/scripts/deployment
   ./deploy_cloud_run.sh
   ```

6. Configure Cloud Scheduler
   ```bash
   cd src/scripts/deployment
   ./setup_cloud_scheduler.sh
   ```

## Configuration

The application requires the following configuration:

### Google Sheets Setup

1. Create two Google Sheets:
   - **Master Budget**: Contains budget categories and weekly amounts
   - **Weekly Spending**: Will store transaction data and categorization

2. Share both sheets with the service account email (generated during deployment)

### API Credentials

- **Capital One API**: Client ID, Client Secret, and Account IDs
- **Google APIs**: Service Account credentials with access to Sheets and Gmail
- **Gemini API**: API Key

Store these credentials in Google Secret Manager or in the .env file for local development.

## Usage

### Automated Execution

Once deployed, the application will run automatically every Sunday at 12 PM EST, performing the following actions:

1. Retrieve transactions from the past week from Capital One
2. Categorize transactions using Gemini AI
3. Compare actual spending to budgeted amounts
4. Generate spending insights
5. Send email report to configured recipients
6. Transfer any budget surplus to savings account

### Manual Execution

To trigger the job manually:

```bash
# Using Google Cloud Console
gcloud run jobs execute budget-management-job --region us-east1

# Or using the provided script
cd src/scripts/manual
python trigger_job.py
```

## Monitoring

Monitor the application using Google Cloud tools:

- **Cloud Run Jobs**: View execution history and logs
- **Cloud Logging**: Review detailed application logs
- **Cloud Monitoring**: Set up alerts for job failures

Custom dashboards can be deployed using the templates in `infrastructure/monitoring/dashboards/`.

## Development

### Project Structure

```
src/
├── backend/         # Main application code
│   ├── api_clients/   # API integration clients
│   ├── components/    # Core functional components
│   ├── models/        # Data models
│   ├── services/      # Shared services
│   ├── templates/     # Email and AI prompt templates
│   ├── utils/         # Utility functions
│   └── main.py        # Application entry point
├── scripts/         # Utility scripts for setup, deployment, etc.
└── test/            # Test suite
```

### Running Tests

```bash
# Run unit tests
cd src/backend
python -m pytest tests/unit

# Run integration tests
python -m pytest tests/integration

# Run with coverage
python -m pytest --cov=. tests/
```

### Local Development

Use the development utilities to simulate the weekly process:

```bash
cd src/scripts/development
python local_run.py
```

## Troubleshooting

### Common Issues

- **API Authentication Failures**: Verify credentials in Secret Manager or .env file
- **Missing Transactions**: Check Capital One API access and date range configuration
- **Categorization Issues**: Review Gemini API prompts and test with sample transactions
- **Email Delivery Failures**: Verify Gmail API permissions and recipient addresses

### Logs

Check Cloud Run job execution logs for detailed error information:

```bash
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=budget-management-job" --limit=10
```

### Health Checks

Run the health check script to verify all integrations:

```bash
cd src/scripts/maintenance
python health_check.py
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure all tests pass before submitting a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.