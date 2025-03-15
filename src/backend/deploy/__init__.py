import os

# Version information
__version__ = "1.0.0"

# Base directory calculations
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))

# Deployment constants
TERRAFORM_DIR = os.path.join(PROJECT_ROOT, "terraform")
CLOUD_BUILD_CONFIG = os.path.join(PROJECT_ROOT, "cloud_build.yaml")
DEFAULT_REGION = "us-east1"
DEFAULT_APP_NAME = "budget-management"
DEFAULT_SCHEDULE_CRON = "0 12 * * 0"  # Sunday at 12 PM
DEFAULT_SCHEDULE_TIMEZONE = "America/New_York"  # EST

def get_terraform_dir():
    """
    Returns the absolute path to the Terraform configuration directory.
    
    Returns:
        str: Absolute path to the Terraform directory
    """
    return TERRAFORM_DIR

def get_cloud_build_config():
    """
    Returns the absolute path to the Cloud Build configuration file.
    
    Returns:
        str: Absolute path to the cloud_build.yaml file
    """
    return CLOUD_BUILD_CONFIG

def get_deployment_environment():
    """
    Returns the current deployment environment (dev, test, or prod).
    
    Returns:
        str: Current deployment environment
    """
    return os.environ.get("DEPLOYMENT_ENV", "dev")