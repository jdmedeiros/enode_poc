#!/bin/bash

set -e

echo "Setting up Enode Python environment..."

# Step 1: Ensure python3-venv is installed
echo "Installing system dependencies..."
sudo apt update
sudo apt install -y python3-venv

# Step 2: Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv

# Step 3: Activate virtual environment and install packages
echo "Activating virtualenv and installing required packages..."
source venv/bin/activate
pip install --upgrade pip
pip install flask gunicorn python-dotenv mysql-connector-python

# Step 4: Create .env file if it doesn't exist
ENV_FILE=".env"
if [[ ! -f $ENV_FILE ]]; then
    echo "Creating .env file..."
    cat <<EOF > $ENV_FILE
DB_HOST=database-mysql.ctl4ffo64vfd.us-east-1.rds.amazonaws.com
DB_USER=admin
DB_PASS=Passw0rd
DB_NAME=enode
EOF
else
    echo ".env file already exists, skipping creation."
fi

# Step 5: Generate requirements.txt
echo "Install requirements.txt..."
pip install -r requirements.txt || echo "requirements.txt not found, skipping installation."

# Step 6: Generate secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
