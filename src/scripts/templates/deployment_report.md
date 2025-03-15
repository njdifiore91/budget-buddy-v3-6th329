**Deployment Date:** [YYYY-MM-DD]
**Deployment Time:** [HH:MM:SS] [Timezone]
**Environment:** [development/production]
**Version:** [version number]
**Deployed By:** [name/email]

---

## Deployment Summary

This report documents the deployment of the Budget Management Application version [version] to the [environment] environment. The deployment [was successful/encountered issues] and [includes/does not include] all planned features and fixes.

**Deployment Status:** [SUCCESS/PARTIAL SUCCESS/FAILURE]
**Deployment Duration:** [duration in minutes]
**Rollback Required:** [Yes/No]

### Key Changes

- [Brief description of major feature or change 1]
- [Brief description of major feature or change 2]
- [Brief description of major feature or change 3]

---

## Deployment Details

### Infrastructure Components

| Component | Type | Configuration | Status |
|-----------|------|---------------|--------|
| Cloud Run Job | [job name] | CPU: [cpu], Memory: [memory], Timeout: [timeout] | [DEPLOYED/FAILED] |
| Cloud Scheduler | [scheduler name] | Schedule: [cron expression] | [DEPLOYED/FAILED] |
| Secret Manager | [secret count] secrets | - | [DEPLOYED/FAILED] |
| Service Account | [service account name] | - | [DEPLOYED/FAILED] |

### Container Image

- **Repository:** [container registry path]
- **Image:** [image name]
- **Tag:** [image tag]
- **Digest:** [image digest]
- **Size:** [image size]
- **Build Date:** [build date/time]

### Environment Configuration

| Setting | Value | Source |
|---------|-------|--------|
| PROJECT_ID | [project id] | Terraform variable |
| REGION | [region] | Terraform variable |
| WEEKLY_SPENDING_SHEET_ID | [sheet id] | Secret Manager |
| MASTER_BUDGET_SHEET_ID | [sheet id] | Secret Manager |
| [Other environment variables] | [values] | [sources] |

---

## Deployment Validation

### Validation Checks

| Check | Expected | Actual | Status | Notes |
|-------|----------|--------|--------|-------|
| Container Image | [expected image] | [actual image] | [PASS/FAIL] | - |
| CPU Allocation | [expected cpu] | [actual cpu] | [PASS/FAIL] | - |
| Memory Allocation | [expected memory] | [actual memory] | [PASS/FAIL] | - |
| Timeout Setting | [expected timeout] | [actual timeout] | [PASS/FAIL] | - |
| Service Account | [expected service account] | [actual service account] | [PASS/FAIL] | - |
| Secret Mounts | [expected secrets] | [actual secrets] | [PASS/FAIL] | - |

### API Connectivity Tests

| API | Status | Response Time | Notes |
|-----|--------|---------------|-------|
| Capital One API | [PASS/FAIL] | [response time] | - |
| Google Sheets API | [PASS/FAIL] | [response time] | - |
| Gemini API | [PASS/FAIL] | [response time] | - |
| Gmail API | [PASS/FAIL] | [response time] | - |

### Manual Job Execution Test

- **Execution ID:** [execution id]
- **Status:** [SUCCEEDED/FAILED]
- **Duration:** [duration]
- **Logs:** [link to logs]

---

## Changes and Updates

### Features

| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| [Feature 1] | [Description] | [DEPLOYED/PARTIAL/FAILED] | - |
| [Feature 2] | [Description] | [DEPLOYED/PARTIAL/FAILED] | - |

### Bug Fixes

| Bug ID | Description | Status | Notes |
|--------|-------------|--------|-------|
| [Bug ID 1] | [Description] | [FIXED/PARTIAL/FAILED] | - |
| [Bug ID 2] | [Description] | [FIXED/PARTIAL/FAILED] | - |

### Configuration Changes

| Component | Previous Value | New Value | Reason |
|-----------|----------------|-----------|--------|
| [Component 1] | [Previous value] | [New value] | [Reason for change] |
| [Component 2] | [Previous value] | [New value] | [Reason for change] |

### Dependencies

| Dependency | Previous Version | New Version | Change Impact |
|------------|------------------|-------------|---------------|
| [Dependency 1] | [Previous version] | [New version] | [Impact description] |
| [Dependency 2] | [Previous version] | [New version] | [Impact description] |

---

## Issues and Resolutions

| Issue | Severity | Description | Resolution | Status |
|-------|----------|-------------|------------|--------|
| [Issue 1] | [HIGH/MEDIUM/LOW] | [Description] | [Resolution steps] | [RESOLVED/PENDING] |
| [Issue 2] | [HIGH/MEDIUM/LOW] | [Description] | [Resolution steps] | [RESOLVED/PENDING] |

---

## Performance Metrics

### Deployment Performance

| Metric | Value | Previous Value | Change | Notes |
|--------|-------|----------------|--------|-------|
| Deployment Time | [time] | [previous time] | [change] | - |
| Container Build Time | [time] | [previous time] | [change] | - |
| Validation Time | [time] | [previous time] | [change] | - |

### Application Performance

| Metric | Value | Previous Value | Change | Notes |
|--------|-------|----------------|--------|-------|
| Job Execution Time | [time] | [previous time] | [change] | - |
| Transaction Processing Time | [time] | [previous time] | [change] | - |
| API Response Times | [time] | [previous time] | [change] | - |
| Memory Usage | [usage] | [previous usage] | [change] | - |

---

## Security Considerations

### Credential Rotation

| Credential | Rotated | Expiration | Notes |
|------------|---------|------------|-------|
| Capital One API | [Yes/No] | [expiration date] | - |
| Google Sheets API | [Yes/No] | [expiration date] | - |
| Gemini API | [Yes/No] | [expiration date] | - |
| Gmail API | [Yes/No] | [expiration date] | - |

### Vulnerability Scan Results

| Severity | Count | Addressed | Notes |
|----------|-------|-----------|-------|
| Critical | [count] | [count] | - |
| High | [count] | [count] | - |
| Medium | [count] | [count] | - |
| Low | [count] | [count] | - |

### Security Configuration Changes

| Component | Change | Reason |
|-----------|--------|--------|
| [Component 1] | [Change description] | [Reason] |
| [Component 2] | [Change description] | [Reason] |

---

## Monitoring and Alerts

### Monitoring Configuration

| Metric | Threshold | Alert | Notification Channel |
|--------|-----------|-------|----------------------|
| Job Execution Status | Failure | Critical | Email |
| API Integration Health | Failure | High | Email |
| Memory Usage | > 1.5GB | Warning | Dashboard |
| Execution Time | > 5 minutes | Warning | Dashboard |

### Dashboard Updates

| Dashboard | Changes | URL |
|-----------|---------|-----|
| Budget Management Dashboard | [Changes description] | [URL] |
| Financial Operations Dashboard | [Changes description] | [URL] |

---

## Rollback Plan

In case critical issues are discovered post-deployment, follow these steps to rollback to the previous version:

1. Execute the rollback script: `bash src/scripts/deployment/rollback.sh --to-version [previous_version]`
2. Verify rollback success: `python src/scripts/deployment/validate_deployment.py`
3. Test functionality: `python src/scripts/manual/trigger_job.py --dry-run`
4. Notify stakeholders of rollback

### Previous Version Details

- **Version:** [previous version]
- **Container Image:** [previous image]
- **Deployment Date:** [previous deployment date]
- **Known Issues:** [list of known issues in previous version]

---

## Approval and Sign-off

| Role | Name | Approval Date | Comments |
|------|------|---------------|----------|
| Deployer | [name] | [date] | [comments] |
| Reviewer | [name] | [date] | [comments] |
| Approver | [name] | [date] | [comments] |

---

## Next Steps

| Action | Assignee | Due Date | Priority | Status |
|--------|----------|----------|----------|--------|
| [Action 1] | [assignee] | [due date] | [HIGH/MEDIUM/LOW] | [PENDING/IN PROGRESS/COMPLETED] |
| [Action 2] | [assignee] | [due date] | [HIGH/MEDIUM/LOW] | [PENDING/IN PROGRESS/COMPLETED] |

### Upcoming Deployments

| Version | Planned Date | Major Features | Dependencies |
|---------|--------------|----------------|-------------|
| [version] | [planned date] | [features] | [dependencies] |

---

## Appendix

### References

- Deployment Logs: [link to logs]
- Build Artifacts: [link to artifacts]
- CI/CD Pipeline: [link to pipeline]
- Pull Request: [link to PR]
- Documentation: [link to documentation]

### Command Reference

```bash
# Deployment command
bash src/scripts/deployment/deploy_cloud_run.sh --project-id [PROJECT_ID] --region [REGION] --environment [ENVIRONMENT]

# Validation command
python src/scripts/deployment/validate_deployment.py --project-id [PROJECT_ID] --region [REGION] --job-name [JOB_NAME]

# Manual trigger command
python src/scripts/manual/trigger_job.py --project-id [PROJECT_ID] --region [REGION]
```

### Environment Variables

```
PROJECT_ID=[project_id]
REGION=[region]
ENVIRONMENT=[environment]
APP_NAME=[app_name]
SERVICE_ACCOUNT=[service_account]
CONTAINER_IMAGE=[container_image]
CPU=[cpu]
MEMORY=[memory]
TIMEOUT_SECONDS=[timeout]
```

---

*This report was generated on [generation date] using the deployment report template.*