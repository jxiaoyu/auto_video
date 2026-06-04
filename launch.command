#!/bin/bash
# Auto Video Generator — launcher
# Double-click this file to start the app.

INSTALL_DIR="$HOME/auto_video"

# Keep Terminal window open if something goes wrong, so errors are visible
trap 'echo ""; echo "❌ An error occurred. Press any key to close..."; read -n1' ERR

if [ ! -d "$INSTALL_DIR" ]; then
  echo "❌ Not found: $INSTALL_DIR"
  echo "Please run install.sh first."
  read -n1
  exit 1
fi

cd "$INSTALL_DIR"

if [ ! -f venv/bin/activate ]; then
  osascript -e 'display alert "Setup required" message "Please run install.sh first."'
  exit 1
fi

source venv/bin/activate
echo "Starting Auto Video Generator..."
echo "Opening http://localhost:8000 in your browser..."
echo "(Press Ctrl+C in this window to stop the server)"
echo ""
python web_app.py
