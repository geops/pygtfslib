# PyGTFSLib

A python library for the [GTFS format](https://gtfs.org/).

So far, this is only a loose, incomplete collection of rather low-level tools for parsing GTFS feeds.
The motivation for this library is to consolidate GTFS related code used at [geOps](https://geops.com/en)
in a single library. This is still work in progress, so breaking changes are to be expected.

This library aims to be efficient in terms of parsing time and memory usage to allow processing
a large number of feeds.

## Installation

Install the latest stable release from PyPI with pip:

```bash
pip install pygtfslib
```

## Modules

### Spatial

The `pygtfslib.spatial` module contains classes and functions related to spatial data.
So far, there is only one function `read_shapes` that can be used to parse `shapes.txt` using
a generic factory that accepts an iterable of `pygtfslib.spatial.ShapeRow` instances.

### Temporal

The `pygtfslib.temporal` module contains classes and functions related to temporal data.
So far, it provides functions to parse calendar and frequency entries and stop times.
It also provides a `TimeCache` class that accelerates conversion of GTFS timezone, operating day
and time delta to a timezone-aware python `datetime.datetime`.

### MOT

The `pygtfslib.mot` module contains tools related to GTFS route types / mode of transportation.
So far, there is a function `route_type_to_mot` that can convert a GTFS route type or extended route type
to a MOT string that can be used in the [geOps routing engine](https://geops.com/en/solution/routing).

### CSV

The `pygtfslib.fast_csv` module contains low-level tools for CSV parsing.
There are two generator functions that allow to iterate over a CSV file yielding rows as `dict`s
or `namedtuple`s. They are built on top of the builtin python CSV reader but they are faster than
the builtin `DictReader`.

## Issue Tracker

Please use [the GitHub issue tracker](https://github.com/geops/pygtfslib/issues) to report bugs/issues.

## Development

### Contributing

If you want to contribute to the pygtfslib library, you can make a pull request at [GitHub](https://github.com/geops/pygtfslib).
Before working on major features/changes, please consider contacting us about your plans.
See [our GitHub page](https://github.com/geops) for contact details.

### Editable Installation

Clone this repo and enter the corresponding directory.
Create a virtual environment, then install frozen requirements, dev-requirements
and this library in editable mode:

```bash
python3.11 -m venv env
. env/bin/activate
pip install -U pip
pip install -r requirements.txt -r dev-requirements.txt -e .
```

Keep env activated for all following instructions.

### Pre-Commit Hooks

Enable pre-commit hooks:

```bash
pre-commit install
```

From time to time (not automated yet) run

```bash
pre-commit autoupdate
```

to update frozen revs.

### Run tests

Run tests and analyze code coverage:

```bash
pytest --cov=pygtfslib --cov-report term --cov-fail-under=40 pygtfslib
```
