import os
import csv
import logging

logger = logging.getLogger(__name__)


def iter_rows(directory, filename):
    path = os.path.join(directory, filename)
    logger.info("reading from %r ...", path)
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, strict=True)
        # DictReader is slow, we use it just to parse headers.
        # Not using DictReader.__next__ gives factor 3 speedup
        # (we don't need default values for missing columns or ordered dict).
        fieldnames = reader.fieldnames
        # we cannot return directly since this would close the handle
        yield from (dict(zip(fieldnames, row)) for row in reader.reader)
