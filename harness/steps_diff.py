#!/usr/bin/env python3
"""Wo aendert eine Aufbaustufe das Bild? Gibt Anteil, Bereich und mittlere Farbe aus.

Aufruf: python3 harness/steps_diff.py 25 2_vordergrund 3_objekte
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dumps import load_ppm, scale_to  # noqa: E402

DUMPS = os.environ.get("HD_DUMP_DIR", "/opt/data/projects/comi-hd/work/dumps")


def main():
    room = sys.argv[1]
    a_name = sys.argv[2] if len(sys.argv) > 2 else "2_vordergrund"
    b_name = sys.argv[3] if len(sys.argv) > 3 else "3_objekte"
    a = load_ppm(os.path.join(DUMPS, "hd_step_%s.ppm" % a_name))
    b = scale_to(load_ppm(os.path.join(DUMPS, "hd_step_%s.ppm" % b_name)), a.shape[1], a.shape[0])
    d = np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=2)
    maske = d > 20
    anteil = maske.mean() * 100
    print("Raum %s: %s -> %s" % (room, a_name, b_name))
    print("  geaenderte Flaeche: %.1f%%" % anteil)
    if maske.any():
        ys, xs = np.where(maske)
        print("  Bereich x %d..%d, y %d..%d" % (xs.min(), xs.max(), ys.min(), ys.max()))
        vorher = a[maske].mean(axis=0)
        nachher = b[maske].mean(axis=0)
        print("  Farbe vorher  R %.0f G %.0f B %.0f" % tuple(vorher))
        print("  Farbe nachher R %.0f G %.0f B %.0f" % tuple(nachher))
        # Wie viele verschiedene Farben hat die neue Flaeche?
        neu = b[maske].reshape(-1, 3)
        print("  verschiedene Farben nachher: %d" % len(np.unique(neu, axis=0)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
