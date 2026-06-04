#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "Updating Auto Video Generator..."

git pull

source venv/bin/activate
pip install -r requirements.txt --quiet

echo ""
echo "✅ Update complete! Restart the app to use the new version."
