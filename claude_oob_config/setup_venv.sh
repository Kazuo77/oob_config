#!/bin/bash

# Create and setup virtual environment for claude_oob_config

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate and install requirements
echo "Activating virtual environment and installing requirements..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "Setup complete! To activate the virtual environment, run:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "To run the script:"
echo "  python DeviceIPbyCSV_v2.py"
