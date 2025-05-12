from setuptools import setup, find_packages

setup(
    name="battery_project",
    version="0.1",
    packages=["battery_components"],
    install_requires=[
        "pandas>=2.2.2",
        "numpy>=1.26.4",
        "linopy>=1.2.0",
        "xarray>=2024.3.0",
        "matplotlib>=3.8.4",
        "scipy>=1.13.0",
        "openpyxl>=3.1.2",
        "requests>=2.31.0",
        "pyomo>=6.7.0",
    ],
) 