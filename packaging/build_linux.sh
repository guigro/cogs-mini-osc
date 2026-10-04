#!/bin/bash
# Construit l'AppImage Linux. Usage : VERSION=v2.0.0 packaging/build_linux.sh
# Prérequis (Ubuntu 22.04) : libgirepository1.0-dev libcairo2-dev gir1.2-webkit2-4.1 libwebkit2gtk-4.1-0
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${VERSION:-dev}"
ARCH="${ARCH:-$(uname -m)}"
PYTHON="${PYTHON:-python3}"
APPIMAGETOOL="${APPIMAGETOOL:-appimagetool}"

"$PYTHON" -m PyInstaller --noconfirm --clean packaging/mini_osc.spec

echo "Smoke test..."
dist/Mini-OSC/Mini-OSC --smoke-test

APPDIR="AppDir"
if [ -d "$APPDIR" ]; then rm -r "$APPDIR"; fi
mkdir -p "$APPDIR/usr/bin"
cp -R dist/Mini-OSC "$APPDIR/usr/bin/Mini-OSC"
cp packaging/mini-osc.desktop "$APPDIR/mini-osc.desktop"
cp packaging/icons/mini-osc.png "$APPDIR/mini-osc.png"
ln -s mini-osc.png "$APPDIR/.DirIcon"
cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/Mini-OSC/Mini-OSC" "$@"
EOF
chmod +x "$APPDIR/AppRun"

OUT="dist/Mini-OSC-${VERSION}-linux-${ARCH}.AppImage"
ARCH="$ARCH" "$APPIMAGETOOL" --no-appstream "$APPDIR" "$OUT"
chmod +x "$OUT"
echo "OK: $OUT"
