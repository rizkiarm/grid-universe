#!/bin/bash
set -e

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# Upgrade pip
. .venv/bin/activate
pip install --upgrade pip

# Install dependencies
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
elif [ -f "pyproject.toml" ]; then
    pip install -e .[dev]
fi

# For convenience: add venv activate command to .bashrc if not already present
if ! grep -Fxq ". .venv/bin/activate" ~/.bashrc; then
    echo ". /workspaces/$(basename $PWD)/.venv/bin/activate" >> ~/.bashrc
fi
