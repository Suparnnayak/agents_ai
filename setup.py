"""
Setup configuration for forecast_system package.

Install in development mode:
    pip install -e .

This makes the package importable from anywhere.
"""

from setuptools import setup, find_packages

setup(
    name="forecast_system",
    version="2.0.0",
    description="Hospital Admissions 7-Day Forecasting System",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        # Core dependencies
        "pandas>=1.5.0",
        "numpy>=1.20.0",
        "scikit-learn>=1.0.0",
        # ML frameworks
        "lightgbm>=4.0.0",
        "xgboost>=2.0.0",
        # Optional: uncomment if using TFT
        # "torch>=1.12.0",
        # "pytorch-forecasting>=1.0.0",
        # Utilities
        "joblib>=1.0.0",
    ],
)

