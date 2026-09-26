#!/usr/bin/env bash
# Fehlende Hintergruende fuer die scrollbaren Raeume erzeugen.
#
# Befund 2026-09-26: Von den 24 scrollbaren Raeumen haben nur 5 (14, 15, 22, 25, 33) einen
# eigenen breiten Hintergrund im HD-Paket. Bei den anderen 19 laedt die Engine eine 2560 Pixel
# breite Ersatztextur (Einzelbildgroesse), das Bild scrollt also nicht. Die Engine ordnet
# Hintergrunddateien ueber die fuehrende Raumnummer zu (hd_asset_manager.cpp: sscanf '%d' bzw.
# 'bg_%d'), der Dateiname dahinter ist frei.
#
# Quelle: die frische Extraktion aus den Spieldaten (tools/nutcracker, Weg in export_all.sh),
# dort liegen alle 24 breiten Raumbilder als <raum>_bg.png in 8-Bit-Raumgroesse.
#
# Aufruf: bash scripts/fix_scroll_backgrounds.sh
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv-upscale/bin/python"
EXTRACT="${EXTRACT:-/tmp/comi_extract/COMI/IMAGES/backgrounds}"
WORK="${WORK:-/tmp/scroll_bg}"
ROOMS="${ROOMS:-40 41 42 43 44 45 46 47 48 49 50 51 53 55 60 61 70 75 86}"

mkdir -p "$WORK/in" "$WORK/out"
echo "=== Rohbilder einsammeln ==="
"$PY" - "$EXTRACT" "$WORK/in" "$ROOMS" <<'PYEOF'
import sys, os, glob, shutil
extract, out, rooms = sys.argv[1], sys.argv[2], sys.argv[3].split()
n = 0
for r in rooms:
    hits = sorted(glob.glob(os.path.join(extract, "%04d_*.png" % int(r))))
    if not hits:
        print("  Raum %s: kein Rohbild" % r)
        continue
    shutil.copyfile(hits[0], os.path.join(out, os.path.basename(hits[0])))
    n += 1
print("  %d Rohbilder, Groessen:" % n)
from PIL import Image
for p in sorted(glob.glob(out + "/*.png")):
    print("    %-22s %s" % (os.path.basename(p), Image.open(p).size))
PYEOF

echo "=== Hochskalieren (4x, Modell RealESRGAN_x4plus_anime_6B) ==="
COMI_UPSCALE_MODEL=RealESRGAN_x4plus_anime_6B "$PY" "$ROOT/scripts/upscale_esrgan.py" \
  --input "$WORK/in" --output "$WORK/out" --pattern "*.png" 2>&1 | tail -3

echo "=== Einsetzen (alle vier Kopien) ==="
"$PY" - "$WORK/out" "$ROOT" <<'PYEOF'
import sys, os, glob, shutil
src, root = sys.argv[1], sys.argv[2]
files = sorted(glob.glob(src + "/*.png"))
n = 0
for rel in ("release/linux/hd", "release/linux/game/hd", "release/windows/hd", "scummvm/fork/hd"):
    dst_dir = os.path.join(root, rel, "backgrounds")
    for p in files:
        shutil.copyfile(p, os.path.join(dst_dir, os.path.basename(p)))
        n += 1
    print("  %-24s %d Dateien" % (rel, len(files)))
print("  gesamt: %d" % n)
PYEOF
echo fertig
