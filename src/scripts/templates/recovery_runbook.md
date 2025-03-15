# Budget Management Application - Disaster Recovery Runbook

## Introduction

This disaster recovery runbook provides comprehensive procedures for recovering the Budget Management Application from various failure scenarios. It is intended for system administrators and operators responsible for maintaining the application. The procedures outlined here should be followed in the event of system failures, data corruption, or security incidents that require recovery actions.

## Recovery Scenarios

| Scenario | Description | Severity | Impact | Recovery Time Objective |
|----------|-------------|----------|--------|-------------------------|
| Job Execution Failure | Weekly Cloud Run job fails to execute or completes with errors | Medium | Budget analysis and reporting delayed, no financial actions taken | < 1 hour |
| Infrastructure Corruption | Cloud infrastructure components (Cloud Run, Scheduler, etc.) are misconfigured or corrupted | High | System unable to function, requires complete infrastructure rebuild | < 4 hours |
| Data Access Issue | Unable to access Google Sheets data or API authentication failures | High | System cannot retrieve or store budget data | < 2 hours |
| Google Sheets Data Corruption | Budget or transaction data in Google Sheets is corrupted or accidentally modified | High | Incorrect budget analysis and potential erroneous financial actions | < 2 hours |
| API Authentication Failure | Credentials for external APIs (Capital One, Gemini, Gmail) are invalid or expired | Medium | System cannot perform specific functions related to the affected API | < 2 hours |
| Code Deployment Issue | Deployed application code contains errors or is incompatible with infrastructure | Medium | System functions incorrectly or fails to execute | < 30 minutes |
| Security Incident | Unauthorized access or potential compromise of system components | Critical | Potential data breach or unauthorized financial actions | < 1 hour |

## Prerequisites

Before executing any recovery procedures, ensure you have:

1. **Access Permissions** - Administrator access to Google Cloud Platform project, Google Sheets, and all API services
2. **Local Environment** - Development environment with required tools installed (gcloud CLI, Python 3.11+, Terraform, Docker)
3. **Backup Access** - Access to backup storage location and ability to restore from backups
4. **API Credentials** - Access to API credentials or ability to generate new credentials if needed
5. **Documentation** - Access to system documentation including configuration details and API integration information

## Emergency Response

### 1. Assess the Situation
- Review error logs and monitoring alerts
- Identify affected components and services
- Determine if this is a known scenario from the Recovery Scenarios section
- Estimate impact on system functionality and data integrity

### 2. Emergency Stop (if needed)
If the system is actively causing harm (e.g., incorrect financial transactions), execute emergency stop:

```bash
python src/scripts/disaster_recovery/emergency_stop.py --project-id [PROJECT_ID] --reason "[REASON FOR EMERGENCY STOP]" --notify
```

Verify that Cloud Scheduler jobs are paused and no Cloud Run jobs are executing.

### 3. Notify Stakeholders
- Send email notification with incident details
- Provide estimated recovery time
- Advise on any manual actions users should avoid during recovery

### 4. Document the Incident
- Record time and date of incident detection
- Document observed symptoms and affected components
- Save relevant logs and error messages
- Note any actions already taken

## Recovery Procedures

### Job Execution Failure

1. **Verify Job Status**
   ```bash
   gcloud run jobs executions list --job budget-management --region [REGION]
   ```
   Check the status and error details of recent job executions.

2. **Check Logs**
   ```bash
   gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=budget-management" --limit 50
   ```
   Review logs for error messages and stack traces.

3. **Verify API Access**
   ```bash
   python src/scripts/maintenance/health_check.py --api-only
   ```
   Confirm all required APIs are accessible.

4. **Manual Job Trigger**
   ```bash
   python src/scripts/manual/trigger_job.py
   ```
   Manually trigger the job execution with additional logging.
   
   Verification: Check logs to confirm successful execution or identify specific errors.

5. **Resolve Specific Issues**
   
   Based on error logs, take appropriate action:
   - API Authentication Error: Rotate credentials using `src/scripts/maintenance/rotate_credentials.py`
   - Data Format Error: Verify Google Sheets structure using `src/scripts/utils/validate_budget.py`
   - Resource Constraints: Increase Cloud Run job resources using Terraform
   - Code Error: Rollback to previous version using `src/scripts/deployment/rollback.sh`

### Infrastructure Corruption

1. **Execute Emergency Stop**
   ```bash
   python src/scripts/disaster_recovery/emergency_stop.py --project-id [PROJECT_ID] --reason "Infrastructure rebuild" --notify
   ```
   Stop all running components before rebuilding.

2. **Backup Current State**
   ```bash
   bash src/scripts/disaster_recovery/rebuild_environment.sh --backup-only
   ```
   Create backup of current configuration before rebuilding.

3. **Rebuild Environment**
   ```bash
   bash src/scripts/disaster_recovery/rebuild_environment.sh --project-id [PROJECT_ID] --region [REGION] --environment [ENV] --force
   ```
   Execute complete environment rebuild using Terraform.
   
   Verification: Check Terraform output for successful resource creation.

4. **Validate Deployment**
   ```bash
   python src/scripts/deployment/validate_deployment.py
   ```
   Verify all components are correctly deployed and configured.

5. **Test System Functionality**
   ```bash
   python src/scripts/manual/trigger_job.py --dry-run
   ```
   Test job execution in dry-run mode to verify functionality.
   
   Verification: Check logs to confirm all components are working correctly.

### Data Access Issue

1. **Verify API Credentials**
   ```bash
   python src/scripts/maintenance/health_check.py --api-only
   ```
   Check if API credentials are valid and accessible.

2. **Rotate Credentials (if needed)**
   ```bash
   python src/scripts/maintenance/rotate_credentials.py --service [SERVICE_NAME]
   ```
   Generate new credentials for the affected service.
   
   Available services: google-sheets, capital-one, gemini, gmail

3. **Update Secret Manager**
   ```bash
   python src/scripts/deployment/setup_secrets.sh --update-only
   ```
   Update credentials in Secret Manager.

4. **Verify Access**
   ```bash
   python src/scripts/maintenance/health_check.py --api-only
   ```
   Confirm API access is restored with new credentials.

5. **Resume Normal Operation**
   ```bash
   gcloud scheduler jobs resume --project [PROJECT_ID] --location [REGION] budget-management-weekly
   ```
   Resume scheduled job execution if it was paused.

### Google Sheets Data Corruption

1. **Assess Data Corruption**
   ```bash
   python src/scripts/utils/validate_budget.py
   ```
   Verify the extent of data corruption in Google Sheets.

2. **Find Latest Valid Backup**
   ```bash
   python src/scripts/disaster_recovery/restore_from_backup.py --list
   ```
   List available backups to identify the most recent valid one.

3. **Restore from Backup**
   ```bash
   python src/scripts/disaster_recovery/restore_from_backup.py --latest --clear-existing
   ```
   Restore Google Sheets data from the latest backup.
   
   Alternatives:
   - Restore from specific date:
     ```bash
     python src/scripts/disaster_recovery/restore_from_backup.py --date YYYY-MM-DD --clear-existing
     ```
   - Restore from specific backup directory:
     ```bash
     python src/scripts/disaster_recovery/restore_from_backup.py --backup-dir [BACKUP_DIR_PATH] --clear-existing
     ```

4. **Validate Restored Data**
   ```bash
   python src/scripts/disaster_recovery/verify_integrity.py
   ```
   Verify that restored data has the expected structure and content.

5. **Test Data Access**
   ```bash
   python src/scripts/manual/trigger_job.py --data-only
   ```
   Test data retrieval and processing functionality.
   
   Verification: Check logs to confirm data can be accessed and processed correctly.

### API Authentication Failure

1. **Identify Failed API**
   ```bash
   python src/scripts/maintenance/health_check.py --api-only --verbose
   ```
   Determine which API is experiencing authentication issues.

2. **Check Credential Status**
   ```bash
   python src/scripts/maintenance/rotate_credentials.py --check --service [SERVICE_NAME]
   ```
   Verify if credentials are expired or revoked.

3. **Rotate Credentials**
   ```bash
   python src/scripts/maintenance/rotate_credentials.py --service [SERVICE_NAME]
   ```
   Generate new credentials for the affected service.

4. **Update Secret Manager**
   ```bash
   python src/scripts/deployment/setup_secrets.sh --update-only --service [SERVICE_NAME]
   ```
   Update the new credentials in Secret Manager.

5. **Verify Authentication**
   ```bash
   python src/scripts/maintenance/health_check.py --api-only --service [SERVICE_NAME]
   ```
   Confirm authentication is working with new credentials.

### Code Deployment Issue

1. **Identify Deployment Issue**
   ```bash
   gcloud run jobs describe budget-management --region [REGION]
   ```
   Check current deployment configuration and container image.

2. **Check Container Image**
   ```bash
   gcloud container images describe [CONTAINER_IMAGE]
   ```
   Verify container image exists and is properly configured.

3. **Rollback to Previous Version**
   ```bash
   python src/scripts/deployment/rollback.sh --to-version [PREVIOUS_VERSION]
   ```
   Rollback to the last known good version.
   
   Alternatives:
   - Rollback to specific version:
     ```bash
     python src/scripts/deployment/rollback.sh --to-version [SPECIFIC_VERSION]
     ```
   - Automatic rollback to last stable version:
     ```bash
     python src/scripts/deployment/rollback.sh --auto
     ```

4. **Verify Deployment**
   ```bash
   python src/scripts/deployment/validate_deployment.py
   ```
   Confirm deployment is successful and properly configured.

5. **Test Functionality**
   ```bash
   python src/scripts/manual/trigger_job.py --dry-run
   ```
   Test job execution in dry-run mode.
   
   Verification: Check logs to confirm functionality is restored.

### Security Incident

1. **Execute Emergency Stop**
   ```bash
   python src/scripts/disaster_recovery/emergency_stop.py --project-id [PROJECT_ID] --reason "Security incident" --notify --force
   ```
   Immediately stop all system operations.

2. **Secure Credentials**
   ```bash
   python src/scripts/maintenance/rotate_credentials.py --all --revoke-existing
   ```
   Rotate all credentials and revoke existing ones.

3. **Audit Access Logs**
   ```bash
   gcloud logging read "protoPayload.serviceName=secretmanager.googleapis.com" --project [PROJECT_ID] --limit 100
   ```
   Review Secret Manager access logs for unauthorized access.

4. **Check for Unauthorized Changes**
   ```bash
   python src/scripts/security/test_credential_handling.py --audit
   ```
   Audit system for unauthorized changes or access.

5. **Rebuild Environment**
   ```bash
   bash src/scripts/disaster_recovery/rebuild_environment.sh --project-id [PROJECT_ID] --region [REGION] --environment [ENV] --force
   ```
   Completely rebuild environment with new credentials.

6. **Verify Data Integrity**
   ```bash
   python src/scripts/disaster_recovery/verify_integrity.py --comprehensive
   ```
   Perform comprehensive data integrity check.

7. **Document Incident**
   Create detailed security incident report including:
   - Timeline of events
   - Affected components
   - Actions taken
   - Preventive measures implemented

## Post-Recovery Validation

1. **Run Comprehensive Health Check**
   ```bash
   python src/scripts/disaster_recovery/recovery_validation.py --comprehensive
   ```
   Verify all system components are functioning correctly.
   
   Verification: Check validation report for any remaining issues.

2. **Verify API Connectivity**
   ```bash
   python src/scripts/maintenance/health_check.py --api-only --all
   ```
   Confirm all external API integrations are working.

3. **Test Data Processing**
   ```bash
   python src/scripts/manual/trigger_job.py --data-only
   ```
   Test data retrieval and processing functionality.

4. **Verify Email Delivery**
   ```bash
   python src/scripts/manual/send_test_email.py
   ```
   Confirm email reporting functionality is working.

5. **Check Scheduled Execution**
   ```bash
   gcloud scheduler jobs describe budget-management-weekly --location [REGION]
   ```
   Verify Cloud Scheduler is properly configured.

6. **Generate Recovery Report**
   ```bash
   python src/scripts/disaster_recovery/recovery_validation.py --report --email
   ```
   Generate and send a comprehensive recovery report.

## Recovery Time Objectives

| Scenario | Severity | Recovery Time Objective | Typical Recovery Time |
|---------|----------|--------------------------|----------------------|
| Job Execution Failure | Medium | < 1 hour | 15-30 minutes |
| Infrastructure Corruption | High | < 4 hours | 1-2 hours |
| Data Access Issue | High | < 2 hours | 30-60 minutes |
| Google Sheets Data Corruption | High | < 2 hours | 30-60 minutes |
| API Authentication Failure | Medium | < 2 hours | 15-30 minutes |
| Code Deployment Issue | Medium | < 30 minutes | 10-15 minutes |
| Security Incident | Critical | < 1 hour | 30-60 minutes |

## Recovery Log

| Date | Time | Incident Type | Recovery Procedure | Performed By | Recovery Time | Success | Notes |
|------|------|--------------|-------------------|--------------|---------------|---------|-------|
| YYYY-MM-DD | HH:MM | [Scenario] | [Procedure] | [Name] | [Duration] | Yes/No | [Notes] |

## Appendix: Common Error Messages

### Authentication failed for Capital One API
**Possible Causes**:
- Expired credentials
- Revoked access
- Incorrect client ID or secret

**Solution**: Rotate Capital One API credentials using `src/scripts/maintenance/rotate_credentials.py --service capital-one`

### Google Sheets API quota exceeded
**Possible Causes**:
- Too many API requests in short period
- Infinite loop in code
- Multiple concurrent executions

**Solution**: Wait for quota reset or optimize code to reduce API calls

### Container failed to start: Error response from daemon
**Possible Causes**:
- Missing dependencies
- Incorrect environment variables
- Resource constraints

**Solution**: Check container logs and rebuild with correct configuration

### Gemini API returned error: 400 Bad Request
**Possible Causes**:
- Invalid prompt format
- Token limit exceeded
- API version mismatch

**Solution**: Check Gemini prompt templates and update if needed

### Cloud Scheduler job failed: DEADLINE_EXCEEDED
**Possible Causes**:
- Job execution time exceeds timeout
- Resource constraints
- Infinite loop in code

**Solution**: Increase Cloud Run job timeout or optimize code execution

## Appendix: Contact Information

| Role | Name | Email | Phone | Escalation Level |
|------|------|-------|-------|----------------|
| Primary Contact | [Name] | [Email] | [Phone] | 1 |
| Secondary Contact | [Name] | [Email] | [Phone] | 2 |
| Emergency Contact | [Name] | [Email] | [Phone] | 3 |