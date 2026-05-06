"""
Setup configuration for etl_core package.

Install in editable mode:
    pip install -e .
"""

from setuptools import setup, find_packages

setup(
    name="etl-core",
    version="0.1.0",
    description="Core ETL business logic for ServiceNow → PostgreSQL pipeline",
    author="Data Engineering",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
        "psycopg2-binary>=2.9.0",
        "python-dotenv>=0.20.0",
    ],
    include_package_data=True,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
