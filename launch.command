#!/bin/bash
# Auto Video Generator — launcher
# Double-click this file to start the app.

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if [ ! -f venv/bin/activate ]; then
  osascript -e 'display alert "Setup required" message "Please run install.sh first."'
  exit 1
fi

source venv/bin/activate
echo "Starting Auto Video Generator at http://localhost:8000 ..."
python web_app.py
