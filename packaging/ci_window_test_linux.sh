#!/bin/bash
# Lance Mini-OSC sur un écran virtuel et vérifie que la fenêtre charge vraiment l'interface :
# WebKit doit demander vendor/bulma.min.css au serveur (une simple requête HTTP de test ne suffit pas).
# Usage : packaging/ci_window_test_linux.sh <capture.png> <commande...>
set -uo pipefail
SHOT="$1"
shift
export APPIMAGE_EXTRACT_AND_RUN=1
export MINI_OSC_DATA_DIR="$(mktemp -d)"
export PYWEBVIEW_LOG=debug

Xvfb :99 -screen 0 1440x960x24 > /dev/null 2>&1 &
XVFB_PID=$!
export DISPLAY=:99
sleep 2

"$@" > app.log 2>&1 &
APP_PID=$!

status=1
for _ in $(seq 1 60); do
    if grep -qs "GET /vendor/bulma.min.css" app.log "$MINI_OSC_DATA_DIR/console.log"; then status=0; break; fi
    if ! kill -0 "$APP_PID" 2>/dev/null; then echo "L'application s'est arrêtée."; break; fi
    sleep 0.5
done

sleep 3
import -window root "$SHOT" || true
xwininfo -root -tree 2>/dev/null | grep -i "mini" || true

echo "----- app.log -----"
cat app.log
echo "----- console.log -----"
cat "$MINI_OSC_DATA_DIR/console.log" 2>/dev/null || true

kill "$APP_PID" 2>/dev/null
kill "$XVFB_PID" 2>/dev/null
if [ "$status" -eq 0 ]; then echo "WINDOW TEST OK"; else echo "WINDOW TEST FAILED"; fi
exit "$status"
