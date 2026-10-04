#!/bin/bash
# Lance l'AppImage sur un écran virtuel, vérifie qu'elle tourne et sert l'interface, puis fait une capture.
# Usage : packaging/ci_window_test_linux.sh <fichier.AppImage> <capture.png>
set -uo pipefail
APPIMAGE="$1"
SHOT="$2"
export APPIMAGE_EXTRACT_AND_RUN=1
export MINI_OSC_DATA_DIR="$(mktemp -d)"

Xvfb :99 -screen 0 1440x960x24 &
XVFB_PID=$!
export DISPLAY=:99
sleep 2

"$APPIMAGE" > app.log 2>&1 &
APP_PID=$!

status=1
for _ in $(seq 1 40); do
    if curl -fs -o /dev/null http://127.0.0.1:5009/; then status=0; break; fi
    if ! kill -0 "$APP_PID" 2>/dev/null; then break; fi
    sleep 0.5
done

# Laisse WebKit le temps de dessiner, puis vérifie que l'app tourne toujours
sleep 8
if ! kill -0 "$APP_PID" 2>/dev/null; then
    echo "L'application s'est arrêtée."
    status=1
fi
import -window root "$SHOT" || true

echo "----- app.log -----"
cat app.log
echo "----- console.log -----"
cat "$MINI_OSC_DATA_DIR/console.log" 2>/dev/null || true

kill "$APP_PID" 2>/dev/null
kill "$XVFB_PID" 2>/dev/null
if [ "$status" -eq 0 ]; then echo "WINDOW TEST OK"; else echo "WINDOW TEST FAILED"; fi
exit "$status"
