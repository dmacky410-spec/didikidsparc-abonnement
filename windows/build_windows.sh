#!/bin/bash
# Assemble le paquet Windows autonome : dist/DidikidsParc-Windows.zip
# Usage : ./windows/build_windows.sh CHEMIN/python-embed.zip CHEMIN/pyscard.whl
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY_EMBED="${1:?chemin vers python-X.Y.Z-embed-amd64.zip}"
PYSCARD_WHL="${2:?chemin vers pyscard-*-win_amd64.whl}"

PKG="$ROOT/dist/DidikidsParc"
rm -rf "$ROOT/dist"
mkdir -p "$PKG"

# --- application
cp "$ROOT/server.py" "$ROOT/README.md" "$PKG/"
cp -R "$ROOT/park" "$ROOT/public" "$ROOT/bridge" "$PKG/"
find "$PKG" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

# --- python embarque
mkdir -p "$PKG/python"
unzip -q "$PY_EMBED" -d "$PKG/python"

# sys.path du python embarque : stdlib + racine app + site-packages (pyscard)
PTH_FILE=$(ls "$PKG/python/"python*._pth)
STDLIB_ZIP=$(basename "$PKG/python/"python*.zip)
printf '%s\r\n.\r\n..\r\nLib\\site-packages\r\n' "$STDLIB_ZIP" > "$PTH_FILE"

# --- pyscard (lecteur ACR122U), extrait du wheel officiel
mkdir -p "$PKG/python/Lib/site-packages"
unzip -q "$PYSCARD_WHL" -d "$PKG/python/Lib/site-packages"

# --- lanceurs + notice (convertis en CRLF pour Windows)
python3 - "$ROOT" "$PKG" <<'EOF'
import sys, pathlib
root, pkg = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
for name in ["Didikids Parc.bat", "Lecteur RFID (ACR122U).bat", "LISEZMOI.txt"]:
    text = (root / "windows" / name).read_text(encoding="utf-8")
    data = text.replace("\r\n", "\n").replace("\n", "\r\n")
    if name.endswith(".txt"):
        (pkg / name).write_bytes(b"\xef\xbb\xbf" + data.encode("utf-8"))
    else:
        # les .bat sont volontairement sans accents -> encodage sur
        (pkg / name).write_bytes(data.encode("cp1252", errors="replace"))
EOF

# --- archive finale
cd "$ROOT/dist"
zip -qr DidikidsParc-Windows.zip DidikidsParc
echo "OK : $ROOT/dist/DidikidsParc-Windows.zip"
du -h DidikidsParc-Windows.zip | cut -f1
