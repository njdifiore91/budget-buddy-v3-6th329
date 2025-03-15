# Budget Management Application - Utility Scripts

This directory contains utility scripts for setting up, configuring, deploying, monitoring, and maintaining the Budget Management Application. These scripts automate common tasks and provide tools for troubleshooting and development.

## Directory Structure

The scripts directory is organized into the following subdirectories:

- `config/`: Configuration files and settings for scripts
- `templates/`: Template files used by scripts
- `utils/`: Utility functions and helper scripts
- `tools/`: Standalone tools for specific tasks
- `setup/`: Scripts for initial environment setup
- `development/`: Scripts for local development
- `maintenance/`: Scripts for system maintenance
- `deployment/`: Scripts for deploying to Google Cloud
- `monitoring/`: Scripts for monitoring and alerting
- `cron/`: Scripts designed to be run on a schedule
- `manual/`: Scripts for manual operations
- `disaster_recovery/`: Scripts for handling system failures

## Configuration

Script configuration is managed through environment variables and the `.env` file at the project root. Key configuration files:

- `config/path_constants.py`: Defines standard paths used throughout the scripts
- `config/script_settings.py`: Centralizes script settings with environment variable support
- `config/logging_setup.py`: Configures structured logging for all scripts

To customize script behavior, edit the `.env` file or set environment variables before running scripts.

## Common Usage

### Initial Setup

```bash
# Set up the complete environment
./src/scripts/setup/setup_environment.sh

# Configure API credentials
python src/scripts/setup/configure_credentials.py

# Initialize Google Sheets
python src/scripts/setup/initialize_sheets.py
```

### Development

```bash
# Set up local development environment
./src/scripts/development/setup_local_env.sh

# Generate test data
python src/scripts/development/generate_test_data.py

# Run the application locally
python src/scripts/development/local_run.py
```

### Deployment

```bash
# Build Docker image
./src/scripts/deployment/build_docker_image.sh

# Deploy to Google Cloud Run
./src/scripts/deployment/deploy_cloud_run.sh

# Set up Cloud Scheduler
./src/scripts/deployment/setup_cloud_scheduler.sh
```

### Maintenance

```bash
# Run health check
python src/scripts/maintenance/health_check.py

# Rotate API credentials
python src/scripts/maintenance/rotate_credentials.py

# Backup Google Sheets data
python src/scripts/maintenance/backup_sheets.py
```

### Monitoring

```bash
# Check job status
python src/scripts/monitoring/check_job_status.py

# Analyze logs
python src/scripts/monitoring/analyze_logs.py

# Generate performance report
python src/scripts/monitoring/performance_report.py
```

### Disaster Recovery

```bash
# Emergency stop of all services
python src/scripts/disaster_recovery/emergency_stop.py

# Rebuild environment
./src/scripts/disaster_recovery/rebuild_environment.sh

# Restore from backup
python src/scripts/disaster_recovery/restore_from_backup.py
```

## API Testing

The `utils/api_testing.py` module provides tools for testing API integrations:

```bash
# Test all API integrations
python -m src.scripts.utils.api_testing --test-all

# Test specific API
python -m src.scripts.utils.api_testing --test capital_one
```

Available API tests:
- `capital_one`: Tests Capital One API connectivity and authentication
- `google_sheets`: Tests Google Sheets API access and operations
- `gemini`: Tests Gemini AI API for categorization and insights
- `gmail`: Tests Gmail API for email delivery

## Logging

All scripts use a standardized logging configuration defined in `config/logging_setup.py`. Logs are written to the `logs/` directory with the following features:

- Structured JSON logging for machine readability
- Sensitive data masking for security
- Correlation IDs for request tracing
- Context enrichment for better debugging

Log files are named with timestamps and script identifiers for easy identification.

## Error Handling

Scripts implement consistent error handling with:

- Retry mechanisms with exponential backoff for transient failures
- Circuit breakers to prevent repeated failures
- Detailed error logging with context information
- Graceful degradation when possible

Error handling is provided by the `backend/services/error_handling_service.py` module.

## Maintenance Schedule

Recommended maintenance schedule:

- Daily: Run `health_check.py` to verify system status
- Weekly: Run `backup_sheets.py` to backup Google Sheets data
- Monthly: Run `update_dependencies.sh` to update dependencies
- Quarterly: Run `rotate_credentials.py` to rotate API credentials

These tasks can be automated using the scripts in the `cron/` directory.

## Contributing

When adding new scripts:

1. Follow the existing directory structure
2. Use the templates in `templates/` directory
3. Implement consistent logging and error handling
4. Add appropriate documentation
5. Include usage examples

All scripts should be executable and include proper shebang lines.

## Troubleshooting

Common issues and solutions:

- **API Authentication Failures**: Run `configure_credentials.py` to update credentials
- **Google Sheets Access Issues**: Verify sheet IDs and permissions
- **Deployment Failures**: Check `deploy_cloud_run.sh` logs for details
- **Job Execution Failures**: Run `check_job_status.py` to diagnose issues

For detailed troubleshooting, check the logs in the `logs/` directory.