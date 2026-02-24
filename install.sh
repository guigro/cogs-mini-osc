#!/bin/bash

# ================================
# Mini-OSC for Cogs — Installer
# ================================

set -e

cd "$(dirname "$0")"

echo "==================================="
echo "  Mini-OSC for Cogs — Installation"
echo "==================================="
echo ""

# Check Python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "[ERROR] Python is not installed."
    echo "Install Python 3.7+ from https://www.python.org/downloads/"
    exit 1
fi

PY_VERSION=$($PYTHON --version 2>&1)
echo "[OK] Found $PY_VERSION"

# Create venv
if [ -d "venv" ]; then
    echo "[OK] Virtual environment already exists"
else
    echo "[..] Creating virtual environment..."
    $PYTHON -m venv venv
    echo "[OK] Virtual environment created"
fi

# Activate venv
source venv/bin/activate
echo "[OK] Virtual environment activated"

# Install dependencies
echo "[..] Installing dependencies..."
pip install -r requirements.txt --quiet
echo "[OK] Dependencies installed"

# Check config.json
if [ ! -f "config.json" ]; then
    echo "[..] Creating default config.json..."
    cat > config.json << 'EOF'
{
    "osc_server": {
        "listen_ip": "127.0.0.1",
        "listen_port": 53000
    },
    "flask_server": {
        "ip": "127.0.0.1",
        "port": 5000
    },
    "connections": []
}
EOF
    echo "[OK] Default config.json created"
else
    echo "[OK] config.json found"
fi

echo ""
echo "==================================="
echo "  Installation complete!"
echo "==================================="
echo ""
echo "To start the application:"
echo ""
echo "  source venv/bin/activate"
echo "  python mini_osc.py"
echo ""
echo "Then open http://127.0.0.1:5000 in your browser."
echo ""
