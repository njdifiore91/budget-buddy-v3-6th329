# Deployment Guide for Budget Management Application

This guide provides comprehensive instructions for deploying the Budget Management Application to Google Cloud Platform. The application is designed as a serverless Cloud Run job that executes on a weekly schedule to perform budget analysis and automated financial actions.

## Prerequisites

Before beginning the deployment process, ensure you have the following prerequisites in place:

- Google Cloud Platform account with billing enabled
- Google Cloud SDK installed and configured locally
- Docker installed for container image building
- Terraform CLI installed for infrastructure provisioning
- Git repository access
- Required API credentials:
  - Capital One API credentials
  - Google Sheets API credentials
  - Gemini API key
  - Gmail API credentials

## Deployment Architecture Overview

The Budget Management Application is deployed as a containerized application running on Google Cloud Run jobs. The deployment architecture includes:

- Google Cloud Run job for application execution
- Google Cloud Scheduler for weekly triggering
- Google Secret Manager for secure credential storage
- Google Container Registry for container image storage
- Google Cloud Logging for application monitoring

The deployment process follows infrastructure-as-code principles using Terraform for consistent and repeatable deployments.

## Environment Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd budget-management-app
```

### 2. Configure Environment Variables

Create a `.env` file based on the provided `.env.example` template:

```bash
cp src/backend/.env.example src/backend/.env
```

Edit the `.env` file to include your specific configuration values.

### 3. Install Dependencies

```bash
pip install -r src/backend/requirements.txt
```

## Infrastructure Provisioning

The application infrastructure is provisioned using Terraform:

### 1. Initialize Terraform

```bash
cd src/backend/deploy/terraform
terraform init
```

### 2. Configure Terraform Variables

Create a `terraform.tfvars` file based on your environment requirements:

```hcl
project_id         = "your-gcp-project-id"
region             = "us-east1"
service_account    = "budget-management-service@your-gcp-project-id.iam.gserviceaccount.com"
container_image    = "gcr.io/your-gcp-project-id/budget-management:latest"
```

### 3. Review Terraform Plan

```bash
terraform plan -var-file=terraform.tfvars
```

### 4. Apply Terraform Configuration

```bash
terraform apply -var-file=terraform.tfvars
```

This will provision the following resources:
- Cloud Run job configuration
- Cloud Scheduler job
- Secret Manager secrets
- Required IAM permissions

## Secret Management

Sensitive credentials must be stored securely in Google Secret Manager:

### 1. Create Secrets

Use the provided script to create necessary secrets:

```bash
src/scripts/deployment/setup_secrets.sh
```

Alternatively, create secrets manually:

```bash
gcloud secrets create capital-one-credentials --data-file=./capital_one_credentials.json
gcloud secrets create google-sheets-credentials --data-file=./google_sheets_credentials.json
gcloud secrets create gemini-api-key --data-file=./gemini_api_key.txt
gcloud secrets create gmail-credentials --data-file=./gmail_credentials.json
```

### 2. Grant Access to Service Account

Ensure the Cloud Run service account has access to the secrets:

```bash
gcloud secrets add-iam-policy-binding capital-one-credentials \
    --member="serviceAccount:budget-management-service@your-gcp-project-id.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

Repeat for each secret.

## Application Deployment

### 1. Build Docker Image

```bash
docker build -t gcr.io/your-gcp-project-id/budget-management:latest src/backend/
```

### 2. Push to Container Registry

```bash
docker push gcr.io/your-gcp-project-id/budget-management:latest
```

### 3. Deploy Cloud Run Job

If not using Terraform, deploy manually:

```bash
gcloud run jobs create budget-management \
    --image gcr.io/your-gcp-project-id/budget-management:latest \
    --service-account budget-management-service@your-gcp-project-id.iam.gserviceaccount.com \
    --set-secrets=CAPITAL_ONE_CREDENTIALS=capital-one-credentials:latest \
    --set-secrets=GOOGLE_SHEETS_CREDENTIALS=google-sheets-credentials:latest \
    --set-secrets=GEMINI_API_KEY=gemini-api-key:latest \
    --set-secrets=GMAIL_CREDENTIALS=gmail-credentials:latest \
    --region us-east1 \
    --memory 2Gi \
    --cpu 1 \
    --max-retries 3 \
    --task-timeout 10m
```

### 4. Configure Cloud Scheduler

If not using Terraform, set up the scheduler manually:

```bash
gcloud scheduler jobs create http budget-management-weekly \
    --schedule="0 12 * * 0" \
    --time-zone="America/New_York" \
    --uri="https://us-east1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/your-gcp-project-id/jobs/budget-management:run" \
    --http-method=POST \
    --oauth-service-account-email=budget-management-service@your-gcp-project-id.iam.gserviceaccount.com
```

## Automated Deployment with CI/CD

The repository includes GitHub Actions workflows for automated deployment:

### 1. Configure GitHub Secrets

Add the following secrets to your GitHub repository:

- `GCP_PROJECT_ID`: Your Google Cloud project ID
- `GCP_SA_KEY`: Base64-encoded service account key with required permissions
- `GCP_REGION`: Deployment region (e.g., us-east1)

### 2. CI/CD Workflow

The deployment workflow is defined in `.github/workflows/cd.yml` and includes:

1. Building and testing the application
2. Building the Docker image
3. Pushing to Container Registry
4. Applying Terraform configuration
5. Updating the Cloud Run job

Push changes to the main branch to trigger the deployment workflow.

## Post-Deployment Verification

After deployment, verify the setup with these steps:

### 1. Verify Cloud Run Job

```bash
gcloud run jobs describe budget-management --region us-east1
```

### 2. Verify Cloud Scheduler

```bash
gcloud scheduler jobs describe budget-management-weekly
```

### 3. Test Manual Execution

```bash
gcloud run jobs execute budget-management --region us-east1
```

### 4. Verify Logs

Check execution logs in Google Cloud Console under Cloud Logging.

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Verify secret values are correctly configured
   - Check service account permissions

2. **Job Execution Failures**
   - Review Cloud Logging for detailed error messages
   - Verify API credentials are valid
   - Check resource allocation (memory/CPU)

3. **Scheduler Trigger Issues**
   - Verify service account permissions
   - Check scheduler job configuration
   - Validate cron expression

### Rollback Procedure

If deployment fails or causes issues:

```bash
# Revert to previous container version
gcloud run jobs update budget-management \
    --image gcr.io/your-gcp-project-id/budget-management:previous-version \
    --region us-east1

# Or use the rollback script
src/scripts/deployment/rollback.sh
```

## Maintenance

### Regular Maintenance Tasks

1. **Update Dependencies**
   - Periodically update Python dependencies
   - Rebuild and deploy container image

2. **Rotate Credentials**
   - Regularly rotate API credentials
   - Update secrets in Secret Manager

3. **Monitor Resource Usage**
   - Review execution logs and performance metrics
   - Adjust resource allocation if needed

### Updating the Application

To deploy application updates:

1. Push changes to the repository
2. Let CI/CD pipeline handle deployment, or
3. Manually build and deploy new container image
4. Verify execution after update