#!/usr/bin/env bash
# Raum 25 (Riesiges Banjo): den richtigen Hintergrund erzeugen und einsetzen.
#
# Befund 2026-09-26: Im HD-Paket lag unter dem Namen, den die Engine fuer Raum 25 laedt
# (backgrounds/0025_banjo.png), eine Aussenlandschaft. Raum 25 ist innen die Holzbuehne mit dem
# riesigen Banjo. Folge im Bild: gruener Farbschleier um die Figur, Partikelrauschen und eine
# hell ausgewaschene Flaeche, wo der Hintergrund fehlte.
#
# Das Roharchiv hat das richtige Raumbild als backgrounds/0060_bg.png, 1280x480, also genau die
# 8-Bit-Raumbreite mal Hoehe. Es wird mit dem dokumentierten Modell (realesrgan-x4plus-anime)
# vervierfacht und unter dem Namen eingesetzt, den die Engine laedt. Der alte Stand bleibt als
# .prev erhalten.
#
# Aufruf: bash scripts/fix_room25_background.sh
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv-upscale/bin/python"
WORK="${WORK:-/tmp/raum25_bg}"
mkdir -p "$WORK/in" "$WORK/out"

echo "=== Rohbild entpacken (backgrounds/0060_bg.png) ==="
"$PY" - "$WORK/in" <<'PYEOF'
import sys, zipfile
out = sys.argv[1]
z = zipfile.ZipFile("/opt/data/dist/comi-original-assets.zip")
open(out + "/0060_bg.png", "wb").write(z.read("backgrounds/0060_bg.png"))
print("  entpackt")
PYEOF

echo "=== Hochskalieren (4x, RealESRGAN_x4plus_anime_6B) ==="
"$PY" "$ROOT/scripts/upscale_esrgan.py" --input "$WORK/in" --output "$WORK/out" --pattern "*.png" 2>&1 | tail -3

echo "=== Einsetzen (alle vier Kopien) ==="
"$PY" - "$WORK/out/0060_bg.png" "$ROOT" <<'PYEOF'
import sys, os, shutil
from PIL import Image
src, root = sys.argv[1], sys.argv[2]
print("  neue Groesse:", Image.open(src).size)
for rel in ("release/linux/hd", "release/linux/game/hd", "release/windows/hd", "scummvm/fork/hd"):
    dst = os.path.join(root, rel, "backgrounds", "0025_banjo.png")
    if os.path.exists(dst):
        shutil.copyfile(dst, dst + ".prev")
    shutil.copyfile(src, dst)
    print("  %-24s gesetzt" % rel)
PYEOF
echo "fertig"
