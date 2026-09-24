#!/usr/bin/env python3
"""Erzeugt pro Asset-Typ ein Vorher/Nachher-Uebersichtsbild zur Sichtpruefung.

Aufruf:
    python3 scripts/asset_review_sheets.py --before BK_DIR --after HD_DIR --out OUT_DIR

Jede Zeile zeigt links den Zustand vor dem Magenta-Fix und rechts danach,
dazu Dateiname und Anzahl sichtbarer (opaker) Magenta-Pixel.
Grün umrandete Zellen heissen: vorher sichtbares Magenta, nachher keins.
"""
import argparse
import glob
import os

import numpy as np
from PIL import Image, ImageDraw

CELL = 250          # Kantenlaenge einer Zelle
LABEL = 20
BG = (45, 45, 45)


def magenta_count(path):
    """Zaehlt sichtbares (opakes) Maskenmagenta — dieselbe harte Regel wie v7."""
    a = np.array(Image.open(path).convert("RGBA")).astype(int)
    r, g, b, al = a[:, :, 0], a[:, :, 1], a[:, :, 2], a[:, :, 3]
    pink = (r > 140) & (b > 120) & (g < 100)
    return int((pink & (al > 128)).sum())


def cell(path):
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, (*BG, 255))
    bg.alpha_composite(im)
    im = bg.convert("RGB")
    im.thumbnail((CELL, CELL), Image.Resampling.NEAREST)
    out = Image.new("RGB", (CELL, CELL), BG)
    out.paste(im, ((CELL - im.width) // 2, (CELL - im.height) // 2))
    return out


def sheet(rows, title, out_path):
    """rows = Liste von (dateiname, magentavorher, magentanachher)"""
    h = 40 + len(rows) * (CELL + LABEL)
    w = CELL * 2 + 30
    canvas = Image.new("RGB", (w, h), (20, 20, 20))
    d = ImageDraw.Draw(canvas)
    d.text((8, 8), title, fill=(255, 255, 255))
    y = 34
    for name, mb, ma in rows:
        cb = cell(os.path.join(ARGS.before, name))
        ca = cell(os.path.join(ARGS.after, name))
        canvas.paste(cb, (10, y))
        canvas.paste(ca, (CELL + 20, y))
        d.text((10, y + CELL), "%s  (Magenta opak: %d -> %d)" % (name, mb, ma), fill=(230, 230, 230))
        d.text((12, y + 4), "vorher", fill=(255, 200, 200))
        d.text((CELL + 22, y + 4), "nachher", fill=(200, 255, 200))
        y += CELL + LABEL
    canvas.save(out_path)
    return out_path


def main():
    global ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--out", required=True)
    ARGS = ap.parse_args()
    os.makedirs(ARGS.out, exist_ok=True)

    files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(ARGS.after, "*.png")))
    stats = []
    for n in files:
        if not os.path.exists(os.path.join(ARGS.before, n)):
            continue
        mb = magenta_count(os.path.join(ARGS.before, n))
        if mb < 500:                     # nur sichtbare Faelle
            continue
        ma = magenta_count(os.path.join(ARGS.after, n))
        stats.append((mb - ma, n, mb, ma))
    stats.sort(reverse=True)
    print("Assets mit >=500 opaken Magenta-Pixeln:", len(stats))

    def pick(pred, limit=6):
        return [(n, mb, ma) for _, n, mb, ma in stats if pred(n)][:limit]

    groups = [
        ("1_system_ui", "System-UI und Cursor",
         lambda n: n.startswith("0003_system") or "dialog-" in n or "inventory-bg" in n),
        ("2_inventar_icons", "Inventar-Icons (Raum 3)",
         lambda n: n.startswith("0003") and ("icon" in n or "logo" not in n) and not n.startswith("0003_system")
                   and "dialog-" not in n and "inventory-bg" not in n),
        ("3_logo_intro", "Logo und Intro (Raum 1)", lambda n: n.startswith("0001")),
        ("4_raumobjekte", "Raumobjekte (Beispiele aus mehreren Raeumen)",
         lambda n: not n.startswith("0003") and not n.startswith("0001")),
        ("5_alle_top", "Staerkste Faelle insgesamt", lambda n: True),
    ]
    for tag, title, pred in groups:
        rows = pick(pred, 6)
        if not rows:
            print("leer:", title)
            continue
        p = sheet(rows, title, os.path.join(ARGS.out, "%s.png" % tag))
        print("geschrieben:", p, "| Zeilen:", len(rows), "| Magenta vorher gesamt:", sum(r[1] for r in rows),
              "nachher:", sum(r[2] for r in rows))


if __name__ == "__main__":
    main()
