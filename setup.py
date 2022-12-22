#!/usr/bin/env python3

"""The setup script."""

from setuptools import setup, find_packages

with open("README.md") as readme_file:
    readme = readme_file.read()

setup(
    python_requires=">=3.7",
    description="A Python Library for GTFS",
    long_description=readme,
    long_description_content_type="text/markdown",
    include_package_data=True,
    name="pygtfslib",
    packages=find_packages(include=["pygtfslib", "pygtfslib.*"]),
    zip_safe=False,
    install_requires=["python-dateutil"],
)
