import setuptools
import os
import io

# Get the absolute path of the directory containing this file
here = os.path.abspath(os.path.dirname(__file__))

def read(filename):
    """Read and return the content of a file."""
    try:
        with io.open(os.path.join(here, filename), encoding='utf-8') as f:
            return f.read()
    except IOError:
        if filename == "README.md":
            return "Automated Budget Management Application"
        return ""

def read_requirements():
    """Read and parse requirements from requirements.txt file."""
    content = read('requirements.txt')
    requirements = []
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            requirements.append(line)
    return requirements

setuptools.setup(
    name="budget-management",
    version="1.0.0",
    description="Automated Budget Management Application for tracking, analyzing, and optimizing personal spending habits",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    author="Budget Management Team",
    author_email="njdifiore@gmail.com",
    url="https://github.com/username/budget-management",
    packages=["backend"],
    package_dir={"": "src"},
    include_package_data=True,
    python_requires=">=3.11",
    install_requires=read_requirements(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial :: Accounting",
    ],
    entry_points={
        "console_scripts": [
            "budget-management=backend.main:main",
        ],
    },
)