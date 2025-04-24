from setuptools import setup, find_packages

setup(
    name="battery_project",
    version="0.1",
    packages=["battery_components"],
    install_requires=[
        "pandas",
        "numpy",
        "linopy",
        "xarray",
    ],
) 