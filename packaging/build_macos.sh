#!/bin/bash
# Construit Mini-OSC.app puis le .dmg. Usage : VERSION=v2.0.0 packaging/build_macos.sh
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${VERSION:-dev}"
case "$(uname -m)" in
    arm64) ARCH="${ARCH:-arm64}" ;;
    *) ARCH="${ARCH:-intel}" ;;
esac
PYTHON="${PYTHON:-python3}"

"$PYTHON" -m PyInstaller --noconfirm --clean packaging/mini_osc.spec

echo "Smoke test..."
dist/Mini-OSC.app/Contents/MacOS/Mini-OSC --smoke-test

DMG="dist/Mini-OSC-${VERSION}-macos-${ARCH}.dmg"
STAGE="$(mktemp -d)"
cp -R dist/Mini-OSC.app "$STAGE/"
ln -s /Applications "$STAGE/Applications"
hdiutil create -volname Mini-OSC -srcfolder "$STAGE" -ov -format UDZO "$DMG"
rm -r "$STAGE"
echo "OK: $DMG"
