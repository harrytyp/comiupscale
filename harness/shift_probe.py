#!/usr/bin/env python3
"""Sucht den besten Versatz zwischen 8-Bit-Bild und HD-Bild und misst dort.

Fuer bewegte Szenen (Raum 40: gescriptete Schiffsschlacht) ist der rohe Vergleich sinnlos,
weil der Ausschnitt im Aufnahmebild wandert. Wenn der Restfehler beim besten Versatz klein
ist, fehlt kein Inhalt, sondern nur die Uebereinstimmung des Moments.

Aufruf: shift_probe.py <ref.ppm> <hd.ppm> [maxversatz]
"""
import sys
import os

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dumps import load_ppm, scale_to  # noqa: E402


def lum(img):
    return img[..., :3].astype(np.int16).mean(axis=2)


def main():
    ref_p, hd_p = sys.argv[1], sys.argv[2]
    maxv = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    ref = load_ppm(ref_p)
    hd = scale_to(load_ppm(hd_p), ref.shape[1], ref.shape[0])
    a, b = lum(ref), lum(hd)
    h, w = a.shape
    beste = (1e9, 0, 0)
    for dy in range(-maxv, maxv + 1, 2):
        for dx in range(-maxv, maxv + 1, 2):
            y0, y1 = max(0, dy), min(h, h + dy)
            x0, x1 = max(0, dx), min(w, w + dx)
            if y1 - y0 < h // 2 or x1 - x0 < w // 2:
                continue
            d = np.abs(a[y0:y1, x0:x1] - b[y0 - dy:y1 - dy, x0 - dx:x1 - dx])
            m = float(d.mean())
            if m < beste[0]:
                beste = (m, dx, dy)
    roh = float(np.abs(a - b).mean())
    print("roh %.1f, bester Versatz dx=%d dy=%d mit %.1f" % (roh, beste[1], beste[2], beste[0]))


if __name__ == "__main__":
    main()
