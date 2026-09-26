#!/usr/bin/env bash
# Benchmark und Korrektheitsprobe fuer den HD-Zeichenweg.
#
# Legt pro Stand einen Ordner an. Vergleichen lassen sich zwei Staende mit
#   bash harness/benchmark_hd.sh --compare /tmp/hd_bench/vorher /tmp/hd_bench/nachher
# Die Frames werden nach Kameraposition benannt, deshalb sind Aufnahmen desselben
# Raums zwischen zwei Staenden pixelgenau vergleichbar.
#
# Messwerte kommen aus den Zeitmessern der Engine (hdperf) und der Bildzeit (FRAME-TIMING).
set -u
REPO=/opt/data/local/comi-hd-repo
BIN="$REPO/scummvm/fork/scummvm"
PY=/opt/hermes/.venv/bin/python

if [ "${1:-}" = "--compare" ]; then
    "$PY" - "$2" "$3" <<'PYEOF'
import sys, os, glob
import numpy as np
def load(p):
    with open(p, "rb") as fh:
        fh.readline(); w, h = map(int, fh.readline().split()); fh.readline()
        return np.frombuffer(fh.read(w*h*3), dtype=np.uint8).reshape(h, w, 3).astype(np.int16)
a, b = sys.argv[1], sys.argv[2]
fa = {os.path.basename(p).split("_")[-1]: p for p in glob.glob(a + "/*_raum15_*.ppm")}
fb = {os.path.basename(p).split("_")[-1]: p for p in glob.glob(b + "/*_raum15_*.ppm")}
common = sorted(set(fa) & set(fb))
print("Vergleich %s gegen %s" % (os.path.basename(a), os.path.basename(b)))
print("  Frames vorher %d, nachher %d, gemeinsam %d" % (len(fa), len(fb), len(common)))
if not common:
    print("  KEINE gemeinsamen Kamerapositionen, Vergleich nicht moeglich")
    sys.exit(1)
worst = 0.0; tot = 0.0
for k in common:
    x, y = load(fa[k]), load(fb[k])
    if x.shape != y.shape:
        print("  %s: unterschiedliche Groesse %s vs %s" % (k, x.shape, y.shape)); continue
    d = float(np.abs(x - y).mean())
    tot += d; worst = max(worst, d)
ident = sum(1 for k in common if float(np.abs(load(fa[k]) - load(fb[k])).mean()) == 0.0)
print("  pixelgleich: %d von %d" % (ident, len(common)))
print("  mittlere Abweichung %.3f von 255, schlechteste %.3f" % (tot / len(common), worst))
print("  Urteil:", "identisch" if worst == 0.0 else ("praktisch identisch" if worst < 1.0 else "UNTERSCHIEDLICH"))
# Zusaetzlich die beiden Zwischenstaende, die deterministisch sind: der reine
# Hintergrund und der Stand nach dem Vordergrund. Hier muss pixelgleich gelten,
# sonst hat eine Aenderung am Zeichenweg die Texturen veraendert.
for name in ("unten_hintergrund.ppm", "unten_vordergrund.ppm"):
    pa, pb = os.path.join(a, name), os.path.join(b, name)
    if not (os.path.exists(pa) and os.path.exists(pb)):
        print("  %-22s nicht in beiden Staenden vorhanden, uebersprungen" % name); continue
    x, y = load(pa), load(pb)
    d = float(np.abs(x - y).mean())
    print("  %-22s Abweichung %.3f  %s" % (name, d, "pixelgleich" if d == 0.0 else "UNTERSCHIEDLICH"))
PYEOF
    exit 0
fi

OUT="${1:-/tmp/hd_bench/$(date +%H%M%S)}"
mkdir -p "$OUT" /tmp/hd_scan
cd "$REPO/release/linux" || exit 1

echo "=== Lauf A: Raum 15, Scrollraum, getriebene Kamera, mit Frameaufnahme ==="
rm -f /tmp/hd_scan/*.ppm hd_state.log 2>/dev/null
HD_SCROLL_TEST=1 HD_AUTO_SHOTS=1 timeout 30 "$BIN" --config=scummvm.ini --path=game --boot-param=15 comi > /dev/null 2>&1
cp -f /tmp/hd_scan/*.ppm "$OUT/" 2>/dev/null
cp -f hd_state.log "$OUT/state_15.log" 2>/dev/null
echo "  Frames: $(ls -1 "$OUT"/*_raum15_*.ppm 2>/dev/null | wc -l)"

echo "=== Lauf B: Raum 67, Einzelbildraum, nur Zeitmessung ==="
rm -f hd_state.log 2>/dev/null
timeout 30 "$BIN" --config=scummvm.ini --path=game --boot-param=67 comi > /dev/null 2>&1
cp -f hd_state.log "$OUT/state_67.log" 2>/dev/null

echo "=== Lauf C: Raum 67 mit Zwischenstaenden fuer den Pixelvergleich ==="
echo "    (getrennter Lauf, weil der Dump zwei Dateien je Bild schreibt und die"
echo "     Zeitmessung sonst unbrauchbar macht)"
rm -f hd_state.log /tmp/hd_step_*.ppm 2>/dev/null
HD_DUMP_STEPS=1 timeout 30 "$BIN" --config=scummvm.ini --path=game --boot-param=67 comi > /dev/null 2>&1
cp -f /tmp/hd_step_1_hintergrund.ppm "$OUT/unten_hintergrund.ppm" 2>/dev/null
cp -f /tmp/hd_step_2_vordergrund.ppm "$OUT/unten_vordergrund.ppm" 2>/dev/null
echo "  Hintergrundstand: $(ls -1 "$OUT/unten_hintergrund.ppm" 2>/dev/null | wc -l), Vordergrundstand: $(ls -1 "$OUT/unten_vordergrund.ppm" 2>/dev/null | wc -l)"

echo "=== Messwerte ==="
"$PY" - "$OUT" <<'PYEOF'
import sys, os, re, statistics
out = sys.argv[1]
for room in (15, 67):
    p = os.path.join(out, "state_%d.log" % room)
    if not os.path.exists(p):
        print("Raum %d: kein Log" % room); continue
    txt = open(p, errors="replace").read()
    print("Raum %d:" % room)
    for key in ("komposition gesamt", "hintergrund", "vordergrund",
                "objekte+kostueme+schrift", "uebergabe an die grafik", "vorladung"):
        vals = [int(m) for m in re.findall(r"hdperf: " + re.escape(key) + r" (\d+) ms", txt)]
        if vals:
            print("   %-26s Schnitt %3d ms   Spitze %3d ms   (letzte Messung)" % (key, vals[-1], max(vals)))
    ft = re.findall(r"FRAME-TIMING: avg=(\d+)ms max=(\d+)ms", txt)
    if ft:
        avgs = [int(a) for a, b in ft]; maxs = [int(b) for a, b in ft]
        print("   %-26s Schnitt %3d ms   Spitze %3d ms" % ("Bildzeit (ohne HD)", statistics.mean(avgs), max(maxs)))
    prew = re.findall(r"PREWARM: room (\d+) . (\d+) objects, (\d+) costume frames", txt)
    if prew:
        print("   Vorladen beim Raumwechsel: %s" % ", ".join("%s Objekte %s Figurenbilder" % (o, c) for _, o, c in prew))
PYEOF
echo "Stand gespeichert in $OUT"
