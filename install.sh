#!/bin/bash
set -e

echo ""
echo "╔══════════════════════════════════════╗"
echo "║  Auto Video Generator — Installer   ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── 1. Homebrew ───────────────────────────────────────────────────────────────
if ! command -v brew &>/dev/null; then
  echo "Installing Homebrew (requires your password)..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  # Add brew to PATH for Apple Silicon
  eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || true)"
  eval "$(/usr/local/bin/brew shellenv 2>/dev/null || true)"
else
  echo "✓ Homebrew already installed"
fi

# ── 2. Python & ffmpeg ────────────────────────────────────────────────────────
echo "Installing Python 3.12 and ffmpeg..."
brew install python@3.12 ffmpeg

# ── 3. Clone repo ─────────────────────────────────────────────────────────────
INSTALL_DIR="$HOME/auto_video"
REPO_URL="https://github.com/jxiaoyu/auto_video.git"

if [ -d "$INSTALL_DIR/.git" ]; then
  echo "✓ Repository already cloned at $INSTALL_DIR"
else
  echo "Cloning repository to $INSTALL_DIR ..."
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# ── 4. Python virtual environment ─────────────────────────────────────────────
if [ ! -f venv/bin/activate ]; then
  echo "Creating Python virtual environment..."
  python3.12 -m venv venv
fi

source venv/bin/activate
echo "Installing Python dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# ── 5. API key ────────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
  echo ""
  echo "A Gemini API key is required for video generation."
  read -p "Paste your Gemini API key: " api_key
  echo "GEMINI_API_KEY=$api_key" > .env
  echo "✓ API key saved to .env"
else
  echo "✓ .env already configured"
fi

# ── 6. Desktop shortcut ───────────────────────────────────────────────────────
DESKTOP_LINK="$HOME/Desktop/Auto Video Generator.command"
cp "$INSTALL_DIR/launch.command" "$DESKTOP_LINK"
chmod +x "$DESKTOP_LINK"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║  ✅  Installation complete!          ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "  Double-click 'Auto Video Generator' on your Desktop to start."
echo ""
