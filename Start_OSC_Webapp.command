#!/bin/bash

# ================================
# OSC HTTP WebApp - Launcher Mac
# ================================

echo "Starting OSC HTTP WebApp..."
echo "=================================="

cd "$(dirname "$0")" || exit 1

if [ ! -d "venv" ]; then
    echo "Error: venv directory not found. Run install.sh first."
    read -p "Press Enter to close..."
    exit 1
fi

echo "Working directory: $(pwd)"

# Activate venv first - this puts the right python in PATH
source venv/bin/activate

# Find working python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "Error: No Python found after activating venv."
    read -p "Press Enter to close..."
    exit 1
fi
echo "Using: $PYTHON ($($PYTHON --version 2>&1))"

# Check dependencies
if [ -f "requirements.txt" ]; then
    echo "Checking dependencies..."
    $PYTHON -m pip install -r requirements.txt --quiet 2>/dev/null
fi

if [ ! -f "mini_osc.py" ]; then
    echo "Error: mini_osc.py not found."
    read -p "Press Enter to close..."
    exit 1
fi

if [ ! -f "config.json" ]; then
    echo "Error: config.json not found."
    read -p "Press Enter to close..."
    exit 1
fi

FLASK_IP=$($PYTHON -c "import json; cfg=json.load(open('config.json')); print(cfg['flask_server']['ip'])" 2>/dev/null)
FLASK_PORT=$($PYTHON -c "import json; cfg=json.load(open('config.json')); print(cfg['flask_server']['port'])" 2>/dev/null)

if [ -z "$FLASK_IP" ] || [ -z "$FLASK_PORT" ]; then
    FLASK_IP="127.0.0.1"
    FLASK_PORT="5000"
fi

echo "=================================="
echo "Flask server: http://$FLASK_IP:$FLASK_PORT"
echo "=================================="

sleep 3 && open "http://$FLASK_IP:$FLASK_PORT" &

echo "Launching application..."
echo "Press Ctrl+C to stop"
echo "=================================="

# Loop: restart app when it exits with code 42 (restart requested from web UI)
while true; do
    $PYTHON mini_osc.py
    EXIT_CODE=$?
    if [ $EXIT_CODE -ne 42 ]; then
        break
    fi
    echo ""
    echo "Restarting application..."
    sleep 2
done

echo ""
echo "Application stopped"
read -p "Press Enter to close..."
