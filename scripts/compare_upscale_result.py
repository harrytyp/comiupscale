#!/usr/bin/env python3
"""Vergleicht einen neuen Upscale-Lauf gegen die ausgelieferten Texturen.

Beantwortet die Frage "ist das neue Ergebnis besser?" mit Messwerten und einem Pruefblatt:
Kantensteilheit (wie hart ist der Uebergang vom Motiv zum Rand), Detailgehalt (Laplace-Varianz
in der sichtbaren Flaeche) und Restmagenta. Alles auf der sichtbaren Flaeche, der Maskenrand
wird ausgespart, weil harte Maskenkanten jedes Detailmass verfaelschen.

Aufruf:
  python3 scripts/compare_upscale_result.py --old release/linux/hd/objects \
      --new .pipeline/reupscale/out --sheet /pfad/blatt.png [--limit 8]
"""
import os
import sys
import glob
import argparse

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load(path):
    return np.array(Image.open(path).convert("RGBA"))


def visible_metrics(a):
    """Kennzahlen auf der sichtbaren Flaeche, ohne 3 px Maskenrand."""
    vis = a[:, :, 3] > 128
    for _ in range(3):
        vis &= (np.roll(vis, 1, 0) & np.roll(vis, -1, 0) & np.roll(vis, 1, 1) & np.roll(vis, -1, 1))
    if not vis.any():
        return None
    rgb = a[:, :, :3].astype(np.int16)
    grey = rgb.mean(axis=2)
    lap = (-4 * grey[1:-1, 1:-1] + grey[:-2, 1:-1] + grey[2:, 1:-1] + grey[1:-1, :-2] + grey[1:-1, 2:])
    detail = float(lap[vis[1:-1, 1:-1]].var()) if vis[1:-1, 1:-1].any() else 0.0
    magenta = int(((rgb[:, :, 0] > 200) & (rgb[:, :, 2] > 150) & (rgb[:, :, 1] < 60))[vis].sum())
    # Kantensteilheit: mittlerer Gradient der Helligkeit entlang der sichtbaren Flaeche
    gy, gx = np.gradient(grey)
    edge = float(np.sqrt(gy ** 2 + gx ** 2)[vis].mean())
    return {"detail": detail, "edge": edge, "magenta": magenta, "pixels": int(vis.sum())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True, help="ausgelieferte Texturen")
    ap.add_argument("--new", required=True, help="neu skalierte Texturen")
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--limit", type=int, default=8)
    args = ap.parse_args()

    names = sorted(os.path.basename(p) for p in glob.glob(os.path.join(args.new, "*.png")))
    names = names[:args.limit]
    if not names:
        raise SystemExit("keine neuen Texturen in " + args.new)

    rows = []
    print("%-40s %-22s %-22s" % ("Datei", "ausgeliefert", "neu"))
    for n in names:
        old_p = os.path.join(args.old, n)
        new_p = os.path.join(args.new, n)
        if not os.path.exists(old_p) or not os.path.exists(new_p):
            continue
        o, w = load(old_p), load(new_p)
        mo, mw = visible_metrics(o), visible_metrics(w)
        if not mo or not mw or o.shape != w.shape:
            continue
        print("%-40s Detail %8.1f Kant %5.2f M %4d | Detail %8.1f Kant %5.2f M %4d"
              % (n[:40], mo["detail"], mo["edge"], mo["magenta"],
                 mw["detail"], mw["edge"], mw["magenta"]))
        rows.append((n, o, w, mo, mw))

    if not rows:
        raise SystemExit("keine vergleichbaren Dateien")

    CELL = 260
    sheet = Image.new("RGB", (CELL * 3 + 40, 46 + len(rows) * (CELL + 30)), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    d.text((8, 8), "links ausgelieferte Textur, Mitte neu mit x4plus_anime_6B, rechts Differenz",
           fill=(255, 255, 255))
    y = 42
    for n, o, w, mo, mw in rows:
        diff = np.abs(w[:, :, :3].astype(np.int16) - o[:, :, :3].astype(np.int16)).sum(axis=2)
        dimg = np.dstack([np.clip(diff, 0, 255).astype(np.uint8)] * 3)
        tiles = [Image.fromarray(o[:, :, :3]).convert("RGB"),
                 Image.fromarray(w[:, :, :3]).convert("RGB"),
                 Image.fromarray(dimg)]
        for i, t in enumerate(tiles):
            t2 = t.copy(); t2.thumbnail((CELL, CELL), Image.Resampling.LANCZOS)
            sheet.paste(t2, (10 + i * (CELL + 10), y))
        d.text((10, y + CELL + 4),
               "%s  Detail %0.0f -> %0.0f   Kante %0.2f -> %0.2f" % (n[:34], mo["detail"], mw["detail"], mo["edge"], mw["edge"]),
               fill=(220, 220, 220))
        y += CELL + 30
    os.makedirs(os.path.dirname(args.sheet), exist_ok=True)
    sheet.save(args.sheet)
    print("\nPruefblatt: %s" % args.sheet)


if __name__ == "__main__":
    main()
