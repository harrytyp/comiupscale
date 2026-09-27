#!/usr/bin/env bash
# Faehrt jeden scrollbaren Raum einmal durch und baut daraus ein Video.
# Waagerecht fahren alle, senkrecht die, die hoeher sind als der Bildschirm
# (Schiffskampfkarten 40-43, hochkante Raeume 77, 79, 82). Der Kameraantrieb ist
# der Testhaken HD_SCROLL_TEST im Fork, kein Spielverhalten.
#
# Aufruf: bash harness/make_scroll_montage.sh [ausgabe.mp4]
set -u
REPO=/opt/data/local/comi-hd-repo
BIN="$REPO/scummvm/fork/scummvm"
PY=/opt/hermes/.venv/bin/python
OUT="${1:-/opt/data/projects/comi-hd/reports/scroll-alle-raeume.mp4}"
WORK=/tmp/scroll_montage
ROOMS="14 15 22 25 33 40 41 42 43 44 45 46 47 48 49 50 51 53 55 60 61 70 75 77 79 82 86"

mkdir -p "$WORK"
rm -f "$WORK"/*.ppm 2>/dev/null
cd "$REPO/release/linux" || exit 1

for R in $ROOMS; do
  rm -f /tmp/hd_scan/*.ppm hd_state.log 2>/dev/null
  HD_SCROLL_TEST=1 HD_AUTO_SHOTS=1 timeout 18 "$BIN" \
    --config=scummvm.ini --path=game --boot-param=$R comi > /dev/null 2>&1
  n=0
  for f in /tmp/hd_scan/*_raum${R}_*.ppm; do
    [ -f "$f" ] || continue
    # Jeden dritten Frame nehmen, sonst wird das Video zu lang
    n=$((n + 1))
    [ $((n % 3)) -eq 0 ] || continue
    cp -f "$f" "$WORK/$(printf 'raum%03d_%s' "$R" "$(basename "$f" | sed 's/^s//')")"
  done
  GEO=$(grep -o 'hdgeom: scale=[0-9]* camX=[0-9-]* camY=[0-9-]*' hd_state.log 2>/dev/null | tail -1)
  echo "Raum $R: $(ls -1 "$WORK"/raum0${R}_* 2>/dev/null | wc -l) Frames | $GEO"
done
echo MONTAGE_LAEUFE_DURCH
echo "Frames gesamt: $(ls -1 "$WORK"/*.ppm 2>/dev/null | wc -l)"

"$PY" - "$WORK" "$OUT" <<'PYEOF'
import glob, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw
work, out = sys.argv[1], sys.argv[2]
files = sorted(glob.glob(os.path.join(work, "*.ppm")))
if not files:
    print("keine Frames"); sys.exit(1)
W, H = 768, 576          # klein genug fuer Telegram
tmp = "/tmp/scroll_montage_frames"
os.makedirs(tmp, exist_ok=True)
for i, path in enumerate(files):
    room = os.path.basename(path)[4:7].lstrip("0") or "0"
    with open(path, "rb") as fh:
        fh.readline(); w, h = map(int, fh.readline().split()); fh.readline()
        arr = np.frombuffer(fh.read(w * h * 3), dtype=np.uint8).reshape(h, w, 3)
    img = Image.fromarray(arr).resize((W, H), Image.Resampling.LANCZOS)
    ImageDraw.Draw(img).text((8, 8), "Raum %s" % room, fill=(255, 255, 0))
    img.save(os.path.join(tmp, "f%05d.png" % i))
subprocess.run(["ffmpeg", "-y", "-framerate", "16", "-i", os.path.join(tmp, "f%05d.png"),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-movflags", "+faststart", out],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("Video:", out, "%.1f MB" % (os.path.getsize(out) / 1e6), "%d Frames" % len(files))
PYEOF
