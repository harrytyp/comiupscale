#!/usr/bin/env bash
# Uebersichtsbild der Kostueme in Raum 40, um ein Banjo unter den Figuren zu finden.
set -u
REPO=/opt/data/local/comi-hd-repo
cd "$REPO/release/linux/hd/costumes" || exit 1
"$REPO/.venv-upscale/bin/python" - <<'PY'
import glob
from PIL import Image

files = sorted(glob.glob("LFLF_0040_AKOS_*_aframe_*.png"))
print("Dateien:", len(files))
ims = []
for f in files:
    im = Image.open(f).convert("RGBA")
    # Nur Bilder, die ueberhaupt sichtbare Pixel haben
    if im.getbbox():
        ims.append((f, im))
print("mit Inhalt:", len(ims))
if not ims:
    raise SystemExit
w = max(i.width for _, i in ims)
h = max(i.height for _, i in ims)
cols = 12
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGBA", (w * cols, h * rows), (0, 0, 0, 255))
for k, (f, im) in enumerate(ims):
    sheet.paste(im, ((k % cols) * w, (k // cols) * h), im)
sheet = sheet.resize((min(1600, sheet.width), int(sheet.height * min(1600, sheet.width) / sheet.width)))
sheet.convert("RGB").save("/tmp/ak40_sheet.png")
print("Sheet:", sheet.size)
for f, _ in ims[:80]:
    print("  ", f)
PY
