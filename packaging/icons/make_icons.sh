#!/bin/bash
# Régénère les icônes de l'app (macOS uniquement : ImageMagick + iconutil).
#
# - mini-osc-macos.png / mini-osc.icns : carré plein, sans transparence. macOS 26 (Tahoe) le découpe
#   lui-même en forme arrondie ; une icône .icns avec coins transparents serait enfermée dans un carré gris.
# - mini-osc.png / mini-osc.ico : forme arrondie (superellipse, gabarit 824/1024) avec coins transparents,
#   pour Windows et Linux qui n'arrondissent pas les icônes.
set -euo pipefail
cd "$(dirname "$0")"

GRADIENT="gradient:#7c6cff-#4f3fd8"
TMP="$(mktemp -d)"

# Carré plein (macOS)
magick -size 1024x1024 "$GRADIENT" \
    -fill none -stroke white -strokewidth 72 \
    -draw "stroke-linecap round stroke-linejoin round polyline 205,560 380,560 461,317 589,723 681,457 751,560 819,560" \
    -alpha off -depth 8 mini-osc-macos.png

# Forme arrondie (Windows, Linux)
python3 - > "$TMP/squircle.txt" <<'EOF'
import math
cx = cy = 512; a = 412; n = 5.0
pts = []
for i in range(720):
    t = 2 * math.pi * i / 720
    c, s = math.cos(t), math.sin(t)
    pts.append(f"{cx + a * math.copysign(abs(c) ** (2 / n), c):.2f},{cy + a * math.copysign(abs(s) ** (2 / n), s):.2f}")
print("polygon " + " ".join(pts))
EOF
magick -size 1024x1024 "$GRADIENT" \
    \( -size 1024x1024 xc:black -fill white -draw "@$TMP/squircle.txt" \) -alpha off -compose CopyOpacity -composite \
    -compose Over -fill none -stroke white -strokewidth 60 \
    -draw "stroke-linecap round stroke-linejoin round polyline 243,555 386,555 453,355 558,689 634,470 691,555 781,555" \
    -depth 8 mini-osc.png

# .icns (macOS)
ICONSET="$TMP/mini-osc.iconset"
mkdir -p "$ICONSET"
for s in 16 32 128 256 512; do
    magick mini-osc-macos.png -resize "${s}x${s}" "$ICONSET/icon_${s}x${s}.png"
    magick mini-osc-macos.png -resize "$((s * 2))x$((s * 2))" "$ICONSET/icon_${s}x${s}@2x.png"
done
iconutil -c icns "$ICONSET" -o mini-osc.icns

# .ico (Windows)
magick mini-osc.png -define icon:auto-resize=256,128,64,48,32,16 mini-osc.ico

rm -r "$TMP"
echo "OK : mini-osc.icns, mini-osc.ico, mini-osc.png, mini-osc-macos.png"
