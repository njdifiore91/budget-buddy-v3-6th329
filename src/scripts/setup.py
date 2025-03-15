#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import io
import setuptools  # version: 68.2.2

# Get the absolute path of the current directory
here = os.path.abspath(os.path.dirname(__file__))

def read(filename):
    """
    Read and return the content of a file
    
    Args:
        filename (str): Name of the file to read
        
    Returns:
        str: Content of the file
    """
    filepath = os.path.join(here, filename)
    with io.open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def read_requirements():
    """
    Read and parse requirements from requirements.txt file
    
    Returns:
        list: List of requirement strings
    """
    content = read('requirements.txt')
    requirements = []
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            requirements.append(line)
    return requirements

setuptools.setup(
    name="budget-management-scripts",
    version="1.0.0",
    description="Utility scripts for the Budget Management Application",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    author="Budget Management Team",
    author_email="njdifiore@gmail.com",
    url="https://github.com/username/budget-management",
    packages=["scripts"],
    package_dir={"": "src"},
    include_package_data=True,
    python_requires=">=3.11",
    install_requires=read_requirements(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Topic :: Utilities",
    ],
    entry_points={
        "console_scripts": [
            "budget-setup=scripts.setup.setup_environment:main",
            "budget-configure=scripts.setup.configure_credentials:main",
            "budget-deploy=scripts.deployment.deploy_cloud_run:main",
            "budget-monitor=scripts.monitoring.check_job_status:main",
            "budget-health=scripts.maintenance.health_check:main",
            "budget-backup=scripts.maintenance.backup_sheets:main",
            "budget-test-api=scripts.utils.api_testing:main",
        ],
    },
)