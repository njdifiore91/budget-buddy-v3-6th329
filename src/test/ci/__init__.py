"""
Initialization module for the CI (Continuous Integration) testing package.
This module exports key components for validating and testing the CI/CD pipeline configuration and functionality of the Budget Management Application.
"""

import logging  # standard library
from typing import Optional  # standard library

# Internal imports
from .test_pipeline import PipelineValidator  # src/test/ci/test_pipeline.py
from .test_pipeline import load_github_actions_config  # src/test/ci/test_pipeline.py
from .test_pipeline import load_cloud_build_config  # src/test/ci/test_pipeline.py
from .test_pipeline import validate_github_actions_steps  # src/test/ci/test_pipeline.py
from .test_pipeline import validate_cloud_build_steps  # src/test/ci/test_pipeline.py
from .test_pipeline import simulate_pipeline_execution  # src/test/ci/test_pipeline.py

__version__ = "0.1.0"
LOGGER = logging.getLogger(__name__)
GITHUB_ACTIONS_PATHS = ['.github/workflows/ci.yml', '.github/workflows/cd.yml', 'src/test/ci/github_actions_test.yml']
CLOUD_BUILD_PATHS = ['src/backend/deploy/cloud_build.yaml']


def setup_logging(log_level: str) -> None:
    """
    Configure logging for the CI testing package

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        None: None
    """
    # Configure basic logging format
    log_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    # Set log level based on parameter or default to INFO
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format=log_format)
    # Configure LOGGER with the specified settings


__all__ = [
    "PipelineValidator",
    "load_github_actions_config",
    "load_cloud_build_config",
    "validate_github_actions_steps",
    "validate_cloud_build_steps",
    "simulate_pipeline_execution",
    "setup_logging",
    "__version__",
    "GITHUB_ACTIONS_PATHS",
    "CLOUD_BUILD_PATHS"
]