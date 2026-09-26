#!/usr/bin/env python3
"""Vergleicht die im Sweep geladenen HD-Hintergruende mit den Raumbildern aus den Spieldaten.

Aufruf: python3 harness/sweep_rooms_report.py /tmp/hd_sweep

Je Raum wird der Zwischenstand nach dem Hintergrundschritt (der sichtbare Ausschnitt)
gegen das passende Fenster des Raumbilds aus den Spieldaten gehalten. Dazu wird das
Raumbild auf HD-Groesse gebracht und das Fenster an der Kameraposition ausgeschnitten,
die der Zustandslog nennt. Grosse Abweichung heisst: falsches Bild, falsche Zuordnung
oder ein Hintergrund, der nicht geladen wurde.
"""
import os, re, sys, glob
import numpy as np
from PIL import Image

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/hd_sweep"
EXTRACT = "/tmp/comi_extract/COMI/IMAGES/backgrounds"

def load_ppm(p):
    with open(p, "rb") as fh:
        fh.readline()
        w, h = map(int, fh.readline().split())
        fh.readline()
        return np.frombuffer(fh.read(w * h * 3), dtype=np.uint8).reshape(h, w, 3).astype(np.int16)

rows = []
for line in open(os.path.join(OUT, "sweep.csv"), errors="replace"):
    parts = line.strip().split("|")
    if len(parts) < 2:
        continue
    room = int(parts[0])
    geo = parts[1]
    m = re.search(r"camX=(-?\d+) bg=(\d+)x(\d+) room=(\d+)x(\d+)", geo)
    camX = int(m.group(1)) if m else None
    bgw = int(m.group(2)) if m else None
    bgh = int(m.group(3)) if m else None
    dump = os.path.join(OUT, "%d_hd_hintergrund.ppm" % room)
    src = sorted(glob.glob(os.path.join(EXTRACT, "%04d_*.png" % room)))
    if not src:
        rows.append((room, "kein Raumbild in den Spieldaten", None, camX, bgw)); continue
    if not os.path.exists(dump):
        rows.append((room, "kein HD-Zwischenstand erzeugt", None, camX, bgw)); continue
    d = load_ppm(dump)
    a = np.array(Image.open(src[0]).convert("RGB")).astype(np.int16)
    up = np.array(Image.fromarray(a.astype(np.uint8)).resize((a.shape[1] * 4, a.shape[0] * 4),
                                                            Image.Resampling.NEAREST)).astype(np.int16)
    h = min(d.shape[0], up.shape[0])
    w = min(d.shape[1], up.shape[1])
    x0 = 0 if camX is None else max(0, min(camX, up.shape[1] - w))
    win = up[:h, x0:x0 + w]
    dev = float(np.abs(d[:h, :w] - win).mean())
    verdict = "ok" if dev < 25 else ("auffaellig" if dev < 60 else "FALSCH")
    rows.append((room, verdict, round(dev, 1), camX, bgw))

print("%-6s %-28s %10s %8s %10s" % ("Raum", "Urteil", "Abweichung", "camX", "bg-Breite"))
bad = 0
for room, verdict, dev, camX, bgw in rows:
    if verdict != "ok":
        bad += 1
    print("%-6d %-28s %10s %8s %10s" % (room, verdict, dev if dev is not None else "-",
                                        camX if camX is not None else "-", bgw if bgw is not None else "-"))
print()
print("Geprueft: %d Raeume, davon auffaellig oder falsch: %d" % (len(rows), bad))
