#!/usr/bin/env bash
# Prueft den sauberen Weg: Oberflaeche per _userPut = 0 abschalten statt gegenklicken.
# Nimmt die Schiffskampfräume auf, misst den Inventaranteil in den oberen Bildzeilen und
# legt je Raum vier Bilder in ein Raster. Ohne rm, die Bilder werden nur kopiert.
set -u
REPO=/opt/data/local/comi-hd-repo
BIN=$REPO/scummvm/fork/scummvm
cd "$REPO/scummvm/fork" || exit 1
LIBRARY_PATH=$REPO/build/x11link:/opt/data/tmp/devlibs make -j"$(nproc)" scummvm > /tmp/b5.log 2>&1
echo "Buildfehler: $(grep -c 'error:' /tmp/b5.log)"
grep -m3 "error:" /tmp/b5.log

cd "$REPO/release/linux" || exit 1
mkdir -p /tmp/put0
for R in 40 41 42 43 25; do
	HD_SCROLL_TEST=1 HD_AUTO_SHOTS=1 timeout 18 "$BIN" --config=scummvm_video.ini --path=game --boot-param="$R" comi > /dev/null 2>&1
	echo "--- Raum $R: rc=$? Frames=$(ls -1 /tmp/hd_scan/*_raum${R}_*.ppm 2>/dev/null | wc -l) ---"
	echo "  Inventarobjekt: $(grep -oE '(CULL|RENDER) obj=114[^\"]*' hd_state.log 2>/dev/null | tail -1)"
	ls -1 /tmp/hd_scan/*_raum${R}_*.ppm 2>/dev/null | awk 'NR%7==1' | head -4 | while read -r f; do
		cp "$f" "/tmp/put0/r${R}_$(basename "$f")"
	done
done

"$REPO/.venv-upscale/bin/python" -W ignore - <<'PY'
import glob
from PIL import Image
ts, misses = [], []
for f in sorted(glob.glob("/tmp/put0/*.ppm")):
    im = Image.open(f).convert("RGB"); w, h = im.size
    top = im.crop((0, 0, w, int(h * 0.14)))
    px = list(top.get_flattened_data() if hasattr(top, "get_flattened_data") else top.getdata())
    n = sum(1 for r, g, b in px if r > 80 and r < 210 and r > b + 30 and g > r * 0.4)
    v = n * 100 // len(px)
    if v >= 15:
        misses.append((f.split("/")[-1], v))
    ts.append(im)
print("Bilder geprueft:", len(ts))
print("Mit Inventar:", len(misses))
for n, v in misses:
    print(f"  {n}: {v}% braun oben")
if ts:
    w, h = ts[0].size
    cols = 4
    rows = (len(ts) + cols - 1) // cols
    s = Image.new("RGB", (w * cols, h * rows))
    for k, t in enumerate(ts):
        s.paste(t, ((k % cols) * w, (k // cols) * h))
    s = s.resize((1760, int(s.height * 1760 / s.width)))
    s.save("/tmp/put0_raster.png")
    print("Raster:", s.size)
PY
echo PRUEFUNG_DURCH
