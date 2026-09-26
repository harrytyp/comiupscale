#!/usr/bin/env bash
# Neu-Upscale der Objektebenen mit dem zweiten dokumentierten Modell realesrgan-x4plus.
#
# Warum ein anderes Modell als bei den Objekten: Die Ebenen sind flaechige Grafik (Logos, Schilder,
# Bedienelemente). Das Anime-Modell glaettet dort und verliert Detail (gemessen: Haftungsausschluss
# 545 auf 385). Das x4plus-Modell liefert bei denselben Dateien die hoechste Detail- und Farbtreue
# (gemessen: 13.787 gegen 9.029 Farben, Sichtpruefung bestaetigt schaerfere Kanten).
#
# Verarbeitet nur die Rohbilder, deren Name zu einer vorhandenen Ebene der Installation passt.
# Aufruf: bash scripts/reupscale_layers_x4plus.sh
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv-upscale/bin/python"
ZIP=/opt/data/dist/comi-original-assets.zip
HD="$ROOT/release/linux/hd/objects_layers"
WORK="$ROOT/.pipeline/reupscale_layers_x4plus"
RAW="$WORK/raw"
OUT="$WORK/out"
mkdir -p "$RAW" "$OUT"

echo "=== Rohbilder auswaehlen (nur Ebenen der Installation) ==="
"$PY" - "$ZIP" "$RAW" "$HD" <<'PYEOF'
import sys, zipfile, os
zip_path, raws, hd = sys.argv[1], sys.argv[2], sys.argv[3]
installed = sorted(f for f in os.listdir(hd) if f.endswith(".png"))
installed_set = set(installed)
by_suffix = {}
for name in installed:
    by_suffix.setdefault(name.split("_", 1)[1], name)
z = zipfile.ZipFile(zip_path)
picked = 0
for name in z.namelist():
    if not name.startswith("objects_layers/") or not name.endswith(".png"):
        continue
    base = os.path.basename(name)
    if base in installed_set or base.split("_", 1)[1] in by_suffix:
        open(os.path.join(raws, base), "wb").write(z.read(name))
        picked += 1
print("  %d von %d Ebenen ausgewaehlt" % (picked, len(installed)))
PYEOF

echo "=== Upscale mit RealESRGAN_x4plus ==="
# Weiche Fuellung: die Leinwandmaske der Ebenen ist eine grosse Flaeche. Mit der
# Randpixel-Fuellung entstehen dort harte Farbstufen, die das Netz in weisse Stoerpixel
# verwandelt (gemessen 2026-09-26, im Vergleich sichtbar).
COMI_UPSCALE_MODEL=RealESRGAN_x4plus COMI_FILL_MODE=smooth "$PY" "$ROOT/scripts/upscale_esrgan.py" \
  --input "$RAW" --output "$OUT" --pattern "*.png" --mask-index 39 2>&1 | tail -3

echo
echo "Ergebnis: $(ls -1 "$OUT"/*.png 2>/dev/null | wc -l) Dateien in $OUT"
echo "Herkunft: $(ls -1 "$OUT"/upscale_manifest.json 2>/dev/null)"
