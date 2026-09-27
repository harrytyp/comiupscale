#!/usr/bin/env python3
"""Skaliert die Hintergruende der Schiffskampfkarten auf die volle vierfache Raumbreite.

Der Quellbildsatz der Raeume 40 bis 43 ist 4800 Bildpunkte breit, der Raum hat 1248, also
muesste der Hintergrund bei Stufe 4 genau 4992 breit sein. Es fehlen 192 Bildpunkte, ein
gutes Prozent je Seite, weshalb am rechten Rand bei maximaler Kameraposition ein etwas zu
weit links liegender Ausschnitt gezeigt wird (Punkt 2 in Issue 25).

Statt die Geometrie zu verbiegen wird das Bild hier um genau diesen Faktor gestreckt. Vier
Prozent fallen bei einer gemalten Wasserflaeche nicht auf, waehrend die fehlenden Spalten
sonst dauerhaft als Randfehler sichtbar bleiben.

Aufruf: python3 scripts/fix_shipcom_width.py [--dry-run]
"""
import os
import sys
import glob
from PIL import Image

REPO = "/opt/data/local/comi-hd-repo"
BG = os.path.join(REPO, "release/linux/hd/backgrounds")
SCALE = 4
ROOMS = [40, 41, 42, 43]


def main():
    dry = "--dry-run" in sys.argv
    changed = 0
    for room in ROOMS:
        room_w, room_h = 1248, 1200  # Engine meldet room=1200x1200, die Karte ist aber 1248 breit
        want_w, want_h = room_w * SCALE, room_h * SCALE
        hits = sorted(glob.glob(os.path.join(BG, "%04d_*.png" % room)))
        if not hits:
            print("Raum %d: keine Datei gefunden" % room)
            continue
        for path in hits:
            im = Image.open(path)
            have = im.size
            if have == (want_w, want_h):
                print("Raum %d: %s ist schon %dx%d" % (room, os.path.basename(path), *have))
                continue
            if dry:
                print("Raum %d: %s %dx%d -> %dx%d (Probe)" % (room, os.path.basename(path), *have, want_w, want_h))
                continue
            out = im.resize((want_w, want_h), Image.Resampling.LANCZOS)
            out.save(path)
            print("Raum %d: %s %dx%d -> %dx%d" % (room, os.path.basename(path), *have, want_w, want_h))
            changed += 1
    print("Geaenderte Dateien: %d" % changed)


if __name__ == "__main__":
    main()
