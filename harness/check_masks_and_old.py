#!/usr/bin/env python3
"""Prueft Punkt 5 (#22, #24) und Punkt 6 (#16, #20) der offenen Liste.

Punkt 5: Sind in den ausgelieferten Ebenen- und Objekttexturen noch undurchsichtige
Magenta-Flaechen als Maskenersatz enthalten? Ein Pixel gilt als Magenta, wenn Rot und Blau
hoch sind und Gruen deutlich niedriger liegt, also der typische SCUMM-Maskenwert 255.

Punkt 6: Werden die alten Meldungen noch reproduziert? Dazu werden die Bilder der letzten
Laeufe aus /tmp/hd_scan ausgewertet, falls vorhanden.
"""
import glob
import os
import sys
from PIL import Image
import numpy as np

REPO = "/opt/data/local/comi-hd-repo"
HD = os.path.join(REPO, "release/linux/hd")


def magenta_share(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im, dtype=np.uint8)
    r, g, b = a[:, :, 0].astype(np.int16), a[:, :, 1].astype(np.int16), a[:, :, 2].astype(np.int16)
    mask = (r > 200) & (b > 200) & (g < 80)
    return float(mask.mean()) * 100.0, im.size


def main():
    print("=== Punkt 5: Magenta-Masken in den Texturen ===")
    for folder in ("objects_layers", "objects"):
        files = sorted(glob.glob(os.path.join(HD, folder, "*.png")))
        if not files:
            print("%-15s keine Dateien" % folder)
            continue
        step = max(1, len(files) // 120)
        sampled = files[::step]
        hits = 0
        worst = ("", 0.0, (0, 0))
        for p in sampled:
            try:
                share, size = magenta_share(p)
            except Exception as e:
                print("  Fehler bei %s: %s" % (os.path.basename(p), e))
                continue
            if share > 2.0:
                hits += 1
                if share > worst[1]:
                    worst = (os.path.basename(p), share, size)
        print("%-15s %d von %d geprueft, %d mit ueber 2%% Magenta" %
              (folder, len(sampled), len(files), hits))
        if hits:
            print("      schlimmster Fall: %s %.1f%% %dx%d" % (worst[0], worst[1], *worst[2]))

    print()
    print("=== Punkt 6: Bilder der alten Meldungen 16 und 20 ===")
    for room in (16, 20):
        found = sorted(glob.glob("/tmp/hd_fg/raum%d_*.ppm" % room)) or \
                sorted(glob.glob("/tmp/hd_scan/*_raum%d_*.ppm" % room))
        print("Raum %d: %d Bilder gefunden" % (room, len(found)))
        if found:
            print("      %s" % found[len(found) // 2])


if __name__ == "__main__":
    main()
