from setuptools import setup, find_packages

import os

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "README.md")) as f:
    README = f.read()

setup(
    name="pygtfslib",
    version="0.0",
    description="A Python Library for GTFS",
    long_description=README,
    long_description_content_type="text/markdown",
    zip_safe=False,
    packages=find_packages(),
    include_package_data=True,
    install_requires=["python-dateutil"],
)
