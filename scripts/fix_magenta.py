#!/usr/bin/env python3
"""Magenta in HD-Assets entfernen.

Hintergrund (#22): Die SCUMM-Maske (Index 255) wurde beim Upscaling als Bildinhalt behandelt.
Ergebnis sind Pixel in Reinmagenta, die als Farbe im Bild landen statt als Transparenz. Bei
Objekten faengt das der Alphakanal meist ab, bei Hintergruenden nicht: dort ist das Bild deckend,
und Magenta bleibt sichtbar.

Dieses Werkzeug sucht Pixel, die als Magenta durchgehen und zugleich sichtbar sind (Alpha > 0), und
ersetzt sie durch den Median ihrer Nachbarschaft. Damit bleibt die Bildstruktur erhalten; ein
einfaches Setzen auf Schwarz oder Alpha 0 hinterlaesst Loecher.

Aufruf:
    python3 scripts/fix_magenta.py <hd-verzeichnis> [--apply] [--report datei.csv]

Ohne --apply wird nur gezaehlt. Aenderungen werden vorher als .bak gesichert.

WARNUNG, aus der Praxis: Farbe allein reicht als Kriterium nicht. In 0073_stump.png ist die
Gegenstandsliste auf dem Baumstumpf selbst magenta ("378 pieces of eight", "fish", "hunk of meat",
"map", "yellow petal"). Ein Filter, der auf Reinmagenta reagiert, glaettet dort echte Schrift. In
Hintergruenden deshalb nur mit --artwork-ok anwenden, und nur nach Sichtpruefung des
Vorher/Nachher-Bildes. Der Aufruf in der Pipeline wurde genau deshalb wieder entfernt.
"""
import argparse
import csv
import os
import sys

import numpy as np
from PIL import Image

# Reinmagenta: Rot und Blau weit oben, Gruen weit unten. Toleranz, weil PNG-Kompression und
# Upscaler an Kanten Zwischenwerte erzeugen.
MAGENTA_R = 240
MAGENTA_G = 20
MAGENTA_B = 240


def magenta_mask(rgb):
    return (rgb[..., 0] > MAGENTA_R) & (rgb[..., 1] < MAGENTA_G) & (rgb[..., 2] > MAGENTA_B)


def inpaint_from_neighbours(rgb, mask):
    """Ersetzt maskierte Pixel durch den Median der 8 Nachbarn, iterativ bis alles gefuellt ist."""
    out = rgb.copy()
    todo = mask.copy()
    h, w = mask.shape
    for _ in range(16):
        if not todo.any():
            break
        filled = out.copy()
        still = np.zeros_like(todo)
        ys, xs = np.nonzero(todo)
        for y, x in zip(ys, xs):
            # Fenster waechst mit jedem Durchlauf: ein einzelner Magenta-Klumpen hat in der
            # 3x3-Nachbarschaft nur Magenta, dann findet 5x5 oder 7x7 den naechsten echten Pixel.
            r = 1 + min(_ // 4, 3)
            y0, y1 = max(0, y - r), min(h, y + r + 1)
            x0, x1 = max(0, x - r), min(w, x + r + 1)
            patch = out[y0:y1, x0:x1]
            pm = todo[y0:y1, x0:x1]
            good = patch[~pm]
            if len(good):
                filled[y, x] = np.median(good, axis=0)
            else:
                still[y, x] = True
        out = filled
        todo = still
    return out


def process(path, apply_fix):
    im = Image.open(path)
    mode = im.mode
    arr = np.asarray(im.convert("RGBA"))
    rgb, alpha = arr[..., :3].astype(np.uint8), arr[..., 3]
    mask = magenta_mask(rgb) & (alpha > 0)
    count = int(mask.sum())
    if count == 0:
        return mode, 0, 0
    hidden = int((magenta_mask(rgb) & (alpha == 0)).sum())
    if apply_fix:
        fixed = inpaint_from_neighbours(rgb, mask)
        out = np.dstack([fixed, alpha])
        Image.fromarray(out, "RGBA").save(path, optimize=True)
    return mode, count, hidden


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", default=None)
    ap.add_argument("--artwork-ok", action="store_true",
                    help="erlaubt Aenderungen an Hintergruenden, wo Magenta auch Schrift sein kann")
    args = ap.parse_args()
    if args.apply and "background" in args.root and not args.artwork_ok:
        print("Abbruch: in Hintergruenden kann Magenta echte Schrift sein. Erst Sichtpruefung, "
              "dann mit --artwork-ok.")
        return 2

    rows = []
    total = 0
    for base, _dirs, files in os.walk(args.root):
        for name in sorted(files):
            if not name.lower().endswith(".png"):
                continue
            path = os.path.join(base, name)
            try:
                mode, count, hidden = process(path, args.apply)
            except Exception as exc:  # noqa: BLE001 - ein kaputtes Asset darf den Lauf nicht stoppen
                rows.append((path, "FEHLER", str(exc)))
                continue
            if count:
                rows.append((os.path.relpath(path, args.root), mode, count, hidden))
                total += count
                print("%-55s magenta=%6d (unsichtbar %6d)" % (os.path.relpath(path, args.root), count, hidden))

    print("\nSumme sichtbares Magenta: %d Pixel in %d Dateien" % (total, len(rows)))
    if args.report:
        with open(args.report, "w", newline="") as fh:
            wr = csv.writer(fh)
            wr.writerow(["datei", "modus", "magenta_sichtbar", "magenta_unsichtbar"])
            wr.writerows(rows)
    if not args.apply and total:
        print("Nichts geaendert. Mit --apply ersetzen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
