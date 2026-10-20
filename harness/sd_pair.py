#!/usr/bin/env python3
"""Zu einem HD-Bild das passende SD-Bild suchen und das Paar vergleichen.

Ein Lauf der SD-Engine und ein Lauf des Forks sind nie bildgenau gleich getaktet.
Deshalb wird zu jedem HD-Bild das SD-Bild mit der besten Deckung gesucht und nur
verglichen, wenn die Deckung belastbar ist. Ohne belastbare Deckung gibt es kein
Ergebnis statt eines falschen.

Aufruf: python3 harness/sd_pair.py <hd-ordner> <sd-ordner> <ausgabeordner> <name> [anzahl]
"""
import glob
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ab_compare import best_shift, load_rgb  # noqa: E402
from sd_compare import compare_pair  # noqa: E402

MIN_QUALITY = 2.5


def match(hd_path, sd_paths):
    hd = load_rgb(hd_path)
    # Zum Suchen reicht ein Viertel der Groesse, das vergleicht sich zehnmal schneller.
    small = (max(2, hd.shape[1] // 4), max(2, hd.shape[0] // 4))
    hd_small = np.asarray(Image.fromarray(hd).resize(small, Image.BILINEAR))
    out = []
    for p in sd_paths:
        sd = load_rgb(p)
        sd_small = np.asarray(Image.fromarray(sd).resize(small, Image.BILINEAR))
        dx, dy, q = best_shift(sd_small, hd_small)
        out.append((q, p, dx, dy))
    out.sort(key=lambda t: -t[0])
    return out


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        return 1
    hddir, sddir, outdir, name = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    count = int(sys.argv[5]) if len(sys.argv) > 5 else 3

    hds = [hddir] if os.path.isfile(hddir) else sorted(glob.glob(os.path.join(hddir, "*.ppm")))
    sds = sorted(glob.glob(os.path.join(sddir, "*.png")) + glob.glob(os.path.join(sddir, "*.ppm")))
    if not hds or not sds:
        print(f"keine Bilder: {len(hds)} HD, {len(sds)} SD")
        return 1

    used = set()
    done = 0
    for hd_path in reversed(hds):
        if done >= count:
            break
        ranked = match(hd_path, sds)
        if not ranked or ranked[0][0] < MIN_QUALITY:
            print(f"  {os.path.basename(hd_path)}: keine passende SD-Aufnahme (Guete {ranked[0][0]:.2f})")
            continue
        q, sd_path, dx, dy = ranked[0]
        if sd_path in used:
            continue
        used.add(sd_path)
        done += 1
        print(f"  {os.path.basename(hd_path)} <-> {os.path.basename(sd_path)} (Guete {q:.2f})")
        compare_pair(sd_path, hd_path, outdir, f"{name}_f{done}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
