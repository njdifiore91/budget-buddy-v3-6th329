"""
Initialization module for the Docker-based testing infrastructure of the Budget Management Application.

This file exposes Docker container configuration utilities, environment setup functions, 
and container management helpers to facilitate containerized testing across different environments.

This module supports the following requirements:
- Test Environment Architecture: Provides a unified interface to the containerized test environment
  for consistent test execution
- Test Automation: Supports automated test execution in CI/CD pipelines with Docker containers
- Containerization: Implements container management utilities for testing infrastructure
"""

import os
import sys  # For accessing command-line arguments and exit codes
import subprocess
import yaml  # pyyaml 6.0+

# Directory paths and container configuration
DOCKER_DIR = os.path.dirname(os.path.abspath(__file__))
DOCKER_COMPOSE_FILE = os.path.join(DOCKER_DIR, 'docker-compose.test.yml')
DOCKERFILE_TEST = os.path.join(DOCKER_DIR, 'Dockerfile.test')
TEST_CONTAINER_NAME = 'budget-test'
MOCK_SERVICES = ['mock-capital-one', 'mock-google-sheets', 'mock-gemini', 'mock-gmail']

# Public API of this module
__all__ = [
    'DockerTestEnvironment', 
    'run_tests_in_container', 
    'is_docker_available', 
    'get_docker_compose_config', 
    'start_test_environment', 
    'stop_test_environment', 
    'get_container_logs'
]


def is_docker_available():
    """
    Check if Docker is installed and available on the system.
    
    Returns:
        bool: True if Docker is available, False otherwise
    """
    try:
        result = subprocess.run(
            ['docker', '--version'], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_docker_compose_config():
    """
    Load and parse the docker-compose.test.yml configuration file.
    
    Returns:
        dict: Parsed Docker Compose configuration
    """
    try:
        with open(DOCKER_COMPOSE_FILE, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print(f"Error: Docker Compose file not found at {DOCKER_COMPOSE_FILE}")
        return None
    except yaml.YAMLError as e:
        print(f"Error parsing Docker Compose YAML: {e}")
        return None


def start_test_environment(detached=True):
    """
    Start the Docker test environment using docker-compose.
    
    Args:
        detached (bool): Run containers in the background if True
        
    Returns:
        bool: True if environment started successfully, False otherwise
    """
    if not is_docker_available():
        print("Error: Docker is not available")
        return False
    
    cmd = ['docker-compose', '-f', DOCKER_COMPOSE_FILE, 'up']
    if detached:
        cmd.append('-d')
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except subprocess.SubprocessError as e:
        print(f"Error starting Docker test environment: {e}")
        return False


def stop_test_environment(remove_volumes=True):
    """
    Stop and clean up the Docker test environment.
    
    Args:
        remove_volumes (bool): Remove volumes if True
        
    Returns:
        bool: True if environment stopped successfully, False otherwise
    """
    if not is_docker_available():
        print("Error: Docker is not available")
        return False
    
    cmd = ['docker-compose', '-f', DOCKER_COMPOSE_FILE, 'down']
    if remove_volumes:
        cmd.append('-v')
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except subprocess.SubprocessError as e:
        print(f"Error stopping Docker test environment: {e}")
        return False


def get_container_logs(container_name, tail=None):
    """
    Retrieve logs from a specific container in the test environment.
    
    Args:
        container_name (str): Name of the container
        tail (int): Number of lines to retrieve from the end of logs
        
    Returns:
        str: Container logs as a string
    """
    if not is_docker_available():
        print("Error: Docker is not available")
        return ""
    
    cmd = ['docker-compose', '-f', DOCKER_COMPOSE_FILE, 'logs']
    if tail:
        cmd.extend(['--tail', str(tail)])
    cmd.append(container_name)
    
    try:
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            check=False,
            text=True
        )
        return result.stdout
    except subprocess.SubprocessError as e:
        print(f"Error retrieving container logs: {e}")
        return ""


def run_tests_in_container(test_path=".", pytest_args=None):
    """
    Run pytest tests inside the test container.
    
    Args:
        test_path (str): Path to test files or directory
        pytest_args (list): Additional pytest arguments
        
    Returns:
        int: Return code from the test execution
    """
    if not is_docker_available():
        print("Error: Docker is not available")
        return 1
    
    # Ensure test environment is running
    if not start_test_environment():
        print("Error: Could not start Docker test environment")
        return 1
    
    cmd = [
        'docker-compose', 
        '-f', 
        DOCKER_COMPOSE_FILE, 
        'exec',
        '-T',  # Disable pseudo-TTY allocation
        TEST_CONTAINER_NAME,
        'python', 
        '-m', 
        'pytest'
    ]
    
    # Add test path
    cmd.append(test_path)
    
    # Add any additional pytest arguments
    if pytest_args:
        cmd.extend(pytest_args)
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except subprocess.SubprocessError as e:
        print(f"Error running tests in container: {e}")
        return 1


class DockerTestEnvironment:
    """
    Context manager for setting up and tearing down the Docker test environment.
    
    This class provides a convenient way to ensure the Docker test environment
    is properly set up before tests and cleaned up afterwards.
    """
    
    def __init__(self, detached=True, remove_volumes=True):
        """
        Initialize the Docker test environment context manager.
        
        Args:
            detached (bool): Run containers in the background if True
            remove_volumes (bool): Remove volumes when stopping if True
        """
        self.detached = detached
        self.remove_volumes = remove_volumes
        self.started = False
    
    def __enter__(self):
        """
        Set up the Docker test environment when entering the context.
        
        Returns:
            DockerTestEnvironment: Self reference for context manager
        """
        self.started = start_test_environment(self.detached)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Tear down the Docker test environment when exiting the context.
        
        Args:
            exc_type: Exception type if an exception was raised in the context
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        if self.started:
            stop_test_environment(self.remove_volumes)
            self.started = False
    
    def run_tests(self, test_path=".", pytest_args=None):
        """
        Run tests in the Docker test environment.
        
        Args:
            test_path (str): Path to test files or directory
            pytest_args (list): Additional pytest arguments
            
        Returns:
            int: Return code from test execution
        """
        if not self.started:
            print("Error: Docker test environment not started")
            return 1
        
        return run_tests_in_container(test_path, pytest_args)
    
    def get_logs(self, container_name, tail=None):
        """
        Get logs from a container in the test environment.
        
        Args:
            container_name (str): Name of the container
            tail (int): Number of lines to retrieve from the end of logs
            
        Returns:
            str: Container logs
        """
        if not self.started:
            print("Error: Docker test environment not started")
            return ""
        
        return get_container_logs(container_name, tail)