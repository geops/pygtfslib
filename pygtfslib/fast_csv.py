import os
import csv
import logging
from collections import namedtuple
from itertools import starmap

logger = logging.getLogger(__name__)


# TODO: provide a more user-friendly interface (context manager) for better control
# of lifetime of file handles


def iter_rows(directory, filename):
    """Iterate over a CSV file yielding rows as dicts.

    Attention: The file handle will only close once the generator is consumed
    or closed explicitly!
    """
    path = os.path.join(directory, filename)
    logger.info("reading from %r ...", path)
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle, strict=True)
        fieldnames = next(reader)
        # we cannot return directly since this would close the handle
        yield from (dict(zip(fieldnames, row)) for row in reader)


def iter_rows_as_namedtuples(directory, filename, optional_fieldnames=()):
    """Iterate over a CSV file yielding rows as namedtuples.

    Attention: The file handle will only close once the generator is consumed
    or closed explicitly!
    """
    path = os.path.join(directory, filename)
    logger.info("reading from %r ...", path)
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle, strict=True)
        fieldnames = next(reader)
        missing_optional_fieldnames = set(optional_fieldnames) - set(fieldnames)
        fieldnames.extend(missing_optional_fieldnames)
        # rename for possible extra columns which may not be a python name
        cls = namedtuple(
            "Row", fieldnames, defaults=[None] * len(fieldnames), rename=True
        )
        # we cannot return directly since this would close the handle
        yield from starmap(cls, reader)
