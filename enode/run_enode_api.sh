#!/bin/bash

# Navigate to script directory (optional safety)
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Run the Enode API client script
python3 enode_api.py
