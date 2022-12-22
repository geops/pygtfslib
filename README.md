# PyGTFSLib

A Python Library for GTFS.

## Development

### Installation

```bash
python3 -m venv env
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt -r dev-requirements.txt -e .
```

Keep env activated for all following instructions.

### Pre-Commit Hooks

```bash
pre-commit install
```

From time to time (not automated yet) run

```bash
pre-commit autoupdate
```

to update frozen revs.
