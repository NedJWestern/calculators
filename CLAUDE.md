# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A collection of miscellaneous calculators in Python. Requires Python 3.13+.

## Setup

```bash
uv sync        # install dependencies
uv run python  # run scripts
```

## Testing

No test framework is configured yet. When adding one, prefer `pytest` and run tests with:

```bash
uv run pytest
uv run pytest path/to/test_file.py::test_name  # single test
```
