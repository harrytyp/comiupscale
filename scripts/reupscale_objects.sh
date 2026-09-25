#!/usr/bin/env bash
# Neu-Upscale der Objekt- und Ebenentexturen mit dem dokumentierten Modell
# (RealESRGAN x4plus-anime_6B, dieselbe Gewichtung, die die NCNN-Route als
# realesrgan-x4plus-anime benutzt).
#
# Quelle sind die Rohbilder aus comi-original-assets.zip. Die Maske wird vor dem Skalieren aus der
# Nachbarschaft ergaenzt (naechster Randpixel) und das Alpha binaer gesetzt, wie das Spiel es
# fuehrt. Objektebenen erzwingen Index 39, ihre Palettenfarbe ist beliebig.
#
# Aufruf: bash scripts/reupscale_objects.sh <--room3|--objects|--layers> [LIMIT]
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv-upscale/bin/python"
ZIP=/opt/data/dist/comi-original-assets.zip
SCOPE="${1:---room3}"
LIMIT="${2:-0}"

case "$SCOPE" in
  --room3)   PREFIX="objects/";         FILTER="0003_"; WORK="reupscale";        EXTRA=() ;;
  --objects) PREFIX="objects/";         FILTER="";      WORK="reupscale";        EXTRA=() ;;
  --layers)  PREFIX="objects_layers/";  FILTER="";      WORK="reupscale_layers"; EXTRA=(--mask-index 39) ;;
  *) echo "Unbekannter Umfang: $SCOPE"; exit 2 ;;
esac

WORKDIR="$ROOT/.pipeline/$WORK"
RAW="$WORKDIR/raw"
OUT="$WORKDIR/out"
[ -x "$PY" ] || { echo "Upscale-Umgebung fehlt: $PY"; exit 1; }
mkdir -p "$RAW" "$OUT"

echo "=== Rohbilder entpacken ($SCOPE aus $PREFIX) ==="
"$PY" - "$ZIP" "$RAW" "$PREFIX" "$FILTER" <<'PYEOF'
import sys, zipfile, os
zip_path, out, prefix, filt = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
z = zipfile.ZipFile(zip_path)
picked = []
for name in z.namelist():
    if not name.startswith(prefix) or not name.endswith(".png"):
        continue
    base = os.path.basename(name)
    if filt and not base.startswith(filt):
        continue
    picked.append((name, base))
for name, base in picked:
    with open(os.path.join(out, base), "wb") as fh:
        fh.write(z.read(name))
print("  %d Rohbilder nach %s" % (len(picked), out))
PYEOF

# Fertige Ergebnisse nicht erneut skalieren: ihre Rohdateien werden beiseite gelegt
for f in "$OUT"/*.png; do
  [ -e "$f" ] || continue
  b=$(basename "$f")
  [ -e "$RAW/$b" ] && mv "$RAW/$b" "$RAW/.done_$b"
done

echo "=== Upscale (Modell RealESRGAN_x4plus_anime_6B) ==="
ARGS=(--input "$RAW" --output "$OUT" --pattern "*.png")
[ "$LIMIT" != "0" ] && ARGS+=(--limit "$LIMIT")
[ ${#EXTRA[@]} -gt 0 ] && ARGS+=("${EXTRA[@]}")
"$PY" "$ROOT/scripts/upscale_esrgan.py" "${ARGS[@]}" 2>&1

echo
echo "Ergebnis: $(ls -1 "$OUT"/*.png 2>/dev/null | wc -l) Dateien in $OUT"
