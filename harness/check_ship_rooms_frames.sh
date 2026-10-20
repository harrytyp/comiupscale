#!/usr/bin/env bash
# Baut neu, nimmt die Schiffskampfräume auf und legt je Raum vier Bilder in ein Raster.
# Die Stichprobe von einem Bild pro Raum war zu klein, deshalb hier vier pro Raum.
set -u
REPO=/opt/data/local/comi-hd-repo
BIN=$REPO/scummvm/fork/scummvm
cd "$REPO/scummvm/fork" || exit 1
LIBRARY_PATH=$REPO/build/x11link:/opt/data/tmp/devlibs make -j"$(nproc)" scummvm > /tmp/build_inv4.log 2>&1
echo "Buildfehler: $(grep -c 'error:' /tmp/build_inv4.log)"
grep -m3 "error:" /tmp/build_inv4.log

cd "$REPO/release/linux" || exit 1
for R in 40 41 42 43 25; do
	rm -f /tmp/hd_scan/*.ppm hd_state.log 2>/dev/null
	HD_SCROLL_TEST=1 HD_AUTO_SHOTS=1 timeout 18 "$BIN" --config=scummvm_video.ini --path=game --boot-param="$R" comi > /dev/null 2>&1
	echo "--- Raum $R: rc=$? Frames=$(ls -1 /tmp/hd_scan/*_raum${R}_*.ppm 2>/dev/null | wc -l) ---"
	echo "  Inventarobjekt: $(grep -oE '(CULL|RENDER) obj=114[^\"]*' hd_state.log 2>/dev/null | tail -1)"
	mkdir -p /tmp/pr_$R && rm -f /tmp/pr_$R/*.ppm 2>/dev/null
	ls -1 /tmp/hd_scan/*_raum${R}_*.ppm 2>/dev/null | awk 'NR%7==1' | head -4 | while read -r f; do cp "$f" /tmp/pr_$R/; done
done

"$REPO/.venv-upscale/bin/python" - <<'PY'
import glob
from PIL import Image

tiles = []
for R in (40, 41, 42, 43, 25):
    fs = sorted(glob.glob(f"/tmp/pr_{R}/*.ppm"))[:4]
    for f in fs:
        tiles.append(Image.open(f).convert("RGB"))
print("Bilder im Raster:", len(tiles))
if tiles:
    w, h = tiles[0].size
    cols = 4
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (w * cols, h * rows))
    for k, t in enumerate(tiles):
        sheet.paste(t.resize((w, h)), ((k % cols) * w, (k // cols) * h))
    sheet = sheet.resize((1800, int(sheet.height * 1800 / sheet.width)))
    sheet.save("/tmp/schiff_pruefung.png")
    print("Raster:", sheet.size)
PY
