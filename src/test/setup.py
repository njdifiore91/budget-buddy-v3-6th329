#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import io
from setuptools import setup

# Get the absolute path of the directory where this file is located
here = os.path.abspath(os.path.dirname(__file__))

def read(filename):
    """Read and return the content of a file.
    
    Args:
        filename (str): Name of the file to read
        
    Returns:
        str: Content of the file
    """
    filepath = os.path.join(here, filename)
    with io.open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def read_requirements():
    """Read and parse requirements from requirements.txt file.
    
    Returns:
        list: List of requirement strings
    """
    content = read('requirements.txt')
    # Split by lines and filter out empty lines and comments
    requirements = [line.strip() for line in content.split('\n')
                   if line.strip() and not line.startswith('#')]
    return requirements

# Read long description from README file if it exists
long_description = ''
if os.path.exists(os.path.join(here, 'README.md')):
    long_description = read('README.md')

setup(
    name='budget-management-test',
    version='1.0.0',
    description='Test suite and utilities for the Budget Management Application',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Budget Management Team',
    author_email='njdifiore@gmail.com',
    url='https://github.com/username/budget-management',
    packages=['test'],
    package_dir={'': 'src'},
    include_package_data=True,
    python_requires='>=3.11',
    install_requires=read_requirements(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
        'Topic :: Software Development :: Testing',
    ],
    entry_points={
        'pytest11': ['budget_management_test = test.conftest'],
        'console_scripts': [
            'budget-test-run = test.utils.test_helpers:run_tests',
            'budget-test-env = test.utils.test_helpers:setup_test_environment',
            'budget-test-data = test.utils.test_helpers:generate_test_data',
        ],
    },
)