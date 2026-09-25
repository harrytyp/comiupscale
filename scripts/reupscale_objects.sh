#!/usr/bin/env bash
# Neu-Upscale der Objekttexturen mit dem dokumentierten Modell (RealESRGAN x4plus-anime_6B,
# dieselbe Gewichtung, die die NCNN-Route als realesrgan-x4plus-anime benutzt).
#
# Quelle sind die Rohbilder aus comi-original-assets.zip, damit die Maske sauber behandelt wird:
# derive_upscale laesst die Maskenfarbe vor dem Skalieren aus der Nachbarschaft ergaenzen und
# setzt das Alpha binaer, wie das Spiel es fuehrt.
#
# Aufruf: bash scripts/reupscale_objects.sh [--all | --room3 | --limit N]
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv-upscale/bin/python"
ZIP=/opt/data/dist/comi-original-assets.zip
WORK="$ROOT/.pipeline/reupscale"
RAW="$WORK/raw"
OUT="$WORK/out"
SCOPE="${1:---room3}"
LIMIT="${2:-0}"

[ -x "$PY" ] || { echo "Upscale-Umgebung fehlt: $PY"; exit 1; }
mkdir -p "$RAW" "$OUT"

echo "=== Rohbilder entpacken ($SCOPE) ==="
"$PY" - "$ZIP" "$RAW" "$SCOPE" <<'PYEOF'
import sys, zipfile, os
zip_path, out, scope = sys.argv[1], sys.argv[2], sys.argv[3]
z = zipfile.ZipFile(zip_path)
picked = []
for name in z.namelist():
    if not name.startswith("objects/") or not name.endswith(".png"):
        continue
    base = os.path.basename(name)
    if scope == "--room3" and not base.startswith("0003_"):
        continue
    picked.append((name, base))
for name, base in picked:
    with open(os.path.join(out, base), "wb") as fh:
        fh.write(z.read(name))
print("  %d Rohbilder in %s" % (len(picked), out))
PYEOF

if [ "$SCOPE" = "--room3" ]; then
  # Schon vorhandene Ergebnisse nicht erneut skalieren
  for f in "$OUT"/*.png; do
    [ -e "$f" ] || continue
    b=$(basename "$f")
    [ -e "$RAW/$b" ] && mv "$RAW/$b" "$RAW/.done_$b" 2>/dev/null
  done
fi

echo "=== Upscale ==="
ARGS=(--input "$RAW" --output "$OUT")
[ "$LIMIT" != "0" ] && ARGS+=(--limit "$LIMIT")
"$PY" "$ROOT/scripts/upscale_esrgan.py" "${ARGS[@]}" --pattern "*.png" 2>&1

echo
echo "Ergebnis: $(ls -1 "$OUT"/*.png 2>/dev/null | wc -l) Dateien in $OUT"
