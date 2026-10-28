#!/bin/sh
#
# docsource: Parse, check and update doc-string documentation.
# Copyright 2025-2026, Levente Hunyadi
# https://github.com/hunyadi/docsource

set -e

PYTHON_EXECUTABLE=${PYTHON:-python3}

# Run static type checker and verify formatting guidelines
$PYTHON_EXECUTABLE -m ruff check
$PYTHON_EXECUTABLE -m ruff format --check
$PYTHON_EXECUTABLE -m mypy docsource
$PYTHON_EXECUTABLE -m mypy tests

# Run unit tests
$PYTHON_EXECUTABLE -m unittest discover
