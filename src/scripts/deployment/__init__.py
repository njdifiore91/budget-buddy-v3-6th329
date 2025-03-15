"""
Initialization module for the deployment package that exposes key deployment functions and utilities 
for the Budget Management Application.

This module provides a centralized access point for deployment-related operations including 
Docker image building, Cloud Run deployment, Terraform infrastructure management, and deployment validation.
"""

import logging
import os
import subprocess
from typing import Dict, List, Optional, Union

# Import the validate_deployment function from the Python module
from .validate_deployment import validate_deployment

# Set up logging
logger = logging.getLogger(__name__)

# Define exports
__all__ = [
    "run_deployment", 
    "build_docker_image", 
    "deploy_cloud_run_job", 
    "terraform_apply", 
    "setup_cloud_scheduler", 
    "validate_deployment", 
    "rollback_deployment"
]

def _run_shell_script(script_name: str, args: List[str]) -> bool:
    """
    Run a shell script with the given arguments.
    
    Args:
        script_name: Name of the script file
        args: List of arguments to pass to the script
        
    Returns:
        bool: True if the script executed successfully, False otherwise
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, script_name)
    
    logger.debug(f"Executing script: {script_path} with args: {args}")
    
    try:
        result = subprocess.run(
            [script_path] + args,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.debug(f"Script output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Script failed with return code {e.returncode}")
        logger.error(f"Error output: {e.stderr}")
        return False

def build_docker_image(config: Dict) -> bool:
    """
    Build Docker image for the Budget Management Application.
    
    Args:
        config: Configuration dictionary containing build settings
        
    Returns:
        bool: True if image build was successful, False otherwise
    """
    args = []
    
    if config.get('project_id'):
        args.extend(["--project-id", config['project_id']])
    
    if config.get('app_name'):
        args.extend(["--app-name", config['app_name']])
    
    if config.get('version'):
        args.extend(["--version", config['version']])
    
    if config.get('push_image', True):
        args.append("--push")
    
    if config.get('scan_image', False):
        args.append("--scan")
    
    if config.get('dockerfile'):
        args.extend(["--dockerfile", config['dockerfile']])
    
    if config.get('context'):
        args.extend(["--context", config['context']])
    
    if config.get('build_args'):
        for arg in config['build_args']:
            args.extend(["--build-arg", arg])
    
    return _run_shell_script("build_docker_image.sh", args)

def deploy_cloud_run_job(config: Dict) -> bool:
    """
    Deploy the application to Google Cloud Run.
    
    Args:
        config: Configuration dictionary containing deployment settings
        
    Returns:
        bool: True if deployment was successful, False otherwise
    """
    args = []
    
    if config.get('project_id'):
        args.extend(["--project-id", config['project_id']])
    
    if config.get('region'):
        args.extend(["--region", config['region']])
    
    if config.get('environment'):
        args.extend(["--environment", config['environment']])
    
    if config.get('app_name'):
        args.extend(["--app-name", config['app_name']])
    
    if config.get('service_account'):
        args.extend(["--service-account", config['service_account']])
    
    if config.get('container_image'):
        args.extend(["--container-image", config['container_image']])
    
    if config.get('cpu'):
        args.extend(["--cpu", str(config['cpu'])])
    
    if config.get('memory'):
        args.extend(["--memory", str(config['memory'])])
    
    if config.get('timeout'):
        args.extend(["--timeout", str(config['timeout'])])
    
    if config.get('max_retries'):
        args.extend(["--max-retries", str(config['max_retries'])])
    
    # Handle boolean flags
    if config.get('build_image'):
        args.append("--build-image")
    
    if config.get('setup_scheduler') is False:
        args.append("--no-scheduler")
    
    if config.get('validate_deployment') is False:
        args.append("--no-validate")
    
    return _run_shell_script("deploy_cloud_run.sh", args)

def terraform_apply(config: Dict) -> bool:
    """
    Apply Terraform configurations for infrastructure deployment.
    
    Args:
        config: Configuration dictionary containing Terraform settings
        
    Returns:
        bool: True if Terraform apply was successful, False otherwise
    """
    args = []
    
    if config.get('environment'):
        args.extend(["--environment", config['environment']])
    
    if config.get('tfvars_file'):
        args.extend(["--tfvars-file", config['tfvars_file']])
    
    if config.get('auto_approve', False):
        args.append("--auto-approve")
    
    if config.get('init_reconfigure', False):
        args.append("--init-reconfigure")
    
    if config.get('backend_config'):
        args.extend(["--backend-config", config['backend_config']])
    
    if config.get('plan_file'):
        args.extend(["--plan-file", config['plan_file']])
    
    return _run_shell_script("apply_terraform.sh", args)

def setup_cloud_scheduler(config: Dict) -> bool:
    """
    Set up Cloud Scheduler for the deployed application.
    
    Args:
        config: Configuration dictionary containing scheduler settings
        
    Returns:
        bool: True if scheduler setup was successful, False otherwise
    """
    args = []
    
    if config.get('project_id'):
        args.extend(["--project-id", config['project_id']])
    
    if config.get('region'):
        args.extend(["--region", config['region']])
    
    if config.get('environment'):
        args.extend(["--environment", config['environment']])
    
    if config.get('app_name'):
        args.extend(["--app-name", config['app_name']])
    
    if config.get('service_account'):
        args.extend(["--service-account", config['service_account']])
    
    if config.get('cloud_run_job'):
        args.extend(["--cloud-run-job", config['cloud_run_job']])
    
    if config.get('scheduler_name'):
        args.extend(["--scheduler-name", config['scheduler_name']])
    
    if config.get('schedule'):
        args.extend(["--schedule", config['schedule']])
    
    if config.get('timezone'):
        args.extend(["--timezone", config['timezone']])
    
    if config.get('retry_count'):
        args.extend(["--retry-count", str(config['retry_count'])])
    
    if config.get('use_terraform', False):
        args.append("--use-terraform")
    
    return _run_shell_script("setup_cloud_scheduler.sh", args)

def rollback_deployment(config: Dict) -> bool:
    """
    Roll back deployment to previous version in case of issues.
    
    Args:
        config: Configuration dictionary containing rollback settings
        
    Returns:
        bool: True if rollback was successful, False otherwise
    """
    args = []
    
    if config.get('project_id'):
        args.extend(["--project-id", config['project_id']])
    
    if config.get('region'):
        args.extend(["--region", config['region']])
    
    if config.get('environment'):
        args.extend(["--environment", config['environment']])
    
    if config.get('app_name'):
        args.extend(["--app-name", config['app_name']])
    
    if config.get('previous_version'):
        args.extend(["--previous-version", config['previous_version']])
    
    if config.get('rollback_type'):
        args.extend(["--rollback-type", config['rollback_type']])
    
    if config.get('force', False):
        args.append("--force")
    
    if config.get('skip_validation', False):
        args.append("--skip-validation")
    
    return _run_shell_script("rollback.sh", args)

def run_deployment(config: Dict) -> bool:
    """
    Orchestrates the complete deployment process for the Budget Management Application.
    
    Args:
        config: Configuration dictionary containing deployment settings
               Required keys depend on what operations are being performed,
               but commonly include:
               - build_image (bool): Whether to build a new Docker image
               - apply_terraform (bool): Whether to apply Terraform configurations
               - deploy_cloud_run (bool): Whether to deploy to Cloud Run
               - setup_scheduler (bool): Whether to set up Cloud Scheduler
               - validate_deployment (bool): Whether to validate the deployment
               - project_id (str): Google Cloud project ID
               - region (str): Deployment region
               - environment (str): Deployment environment
               - app_name (str): Application name
    
    Returns:
        bool: True if deployment was successful, False otherwise
    """
    logger.info("Starting deployment process for Budget Management Application")
    
    try:
        # Extract configuration parameters
        build_image_flag = config.get('build_image', False)
        apply_terraform_flag = config.get('apply_terraform', True)
        deploy_to_cloud_run = config.get('deploy_cloud_run', True)
        setup_scheduler_flag = config.get('setup_scheduler', True)
        validate_after_deployment = config.get('validate_deployment', True)
        
        # Build Docker image if requested
        if build_image_flag:
            logger.info("Building Docker image")
            if not build_docker_image(config):
                logger.error("Docker image build failed")
                return False
        
        # Apply Terraform infrastructure if requested
        if apply_terraform_flag:
            logger.info("Applying Terraform infrastructure")
            if not terraform_apply(config):
                logger.error("Terraform apply failed")
                return False
        
        # Deploy to Cloud Run if requested
        if deploy_to_cloud_run:
            logger.info("Deploying to Cloud Run")
            if not deploy_cloud_run_job(config):
                logger.error("Cloud Run deployment failed")
                return False
        
        # Set up Cloud Scheduler if requested
        if setup_scheduler_flag:
            logger.info("Setting up Cloud Scheduler")
            scheduler_result = setup_cloud_scheduler(config)
            if not scheduler_result:
                logger.warning("Cloud Scheduler setup had issues, but continuing deployment")
                # Don't abort the deployment for scheduler issues
        
        # Validate the deployment if requested
        if validate_after_deployment:
            logger.info("Validating deployment")
            validation_result = validate_deployment(
                project_id=config.get('project_id'),
                region=config.get('region', 'us-east1'),
                app_name=config.get('app_name', 'budget-management'),
                service_account=config.get('service_account'),
                cpu=config.get('cpu'),
                memory=config.get('memory'),
                timeout=config.get('timeout'),
                check_execution=config.get('check_execution', False)
            )
            if not validation_result:
                logger.warning("Deployment validation had issues, deployment may not be fully functional")
                # Don't abort the deployment for validation issues
        
        logger.info("Deployment process completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Deployment failed with error: {str(e)}", exc_info=True)
        return False