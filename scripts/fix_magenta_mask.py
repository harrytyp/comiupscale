#!/usr/bin/env python3
"""Entfernt die Magenta-Maske aus HD-Objekt-Assets.

Hintergrund: Die Upscale-Pipeline fuellt maskierte (transparente) Pixel mit Magenta
(ca. 230,0,200) statt sie auf Alpha 0 zu setzen. Dadurch entsteht ein lila Rand/Halo
um Objekte, sichtbar z.B. an der Verb-Muenze (0003_system-cursor-icon_*).

Der Filter ist absichtlich weich: Pixel mit Magenta-Anteil werden anteilig
transparent, damit der weichgezeichnete Halo nicht als harte Kante stehen bleibt.

Aufruf:
    python3 fix_magenta_mask.py --dry-run  <dateien...>   # nur messen
    python3 fix_magenta_mask.py --apply    <dateien...>   # schreiben
Originale werden nicht geloescht; vorher Sicherung anlegen.
"""
import argparse
import os
import shutil
import sys
import time

import numpy as np
from PIL import Image

# Magenta-Maske der Pipeline: r und b hoch, g praktisch 0.
G_MIN = 80      # ab diesem Gruen-Anteil gilt ein Pixel nicht mehr als Magenta
R_MIN = 150
B_MIN = 130


def magenta_amount(rgb):
    """Wie stark ein Pixel Magenta ist: min(r,b) - g, begrenzt auf 0..255."""
    r, g, b = rgb[:, :, 0].astype(int), rgb[:, :, 1].astype(int), rgb[:, :, 2].astype(int)
    amt = np.minimum(r, b) - g
    return np.clip(amt, 0, 255)


def clean(path, apply_changes):
    img = Image.open(path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    a = np.asarray(img).astype(int)
    alpha = a[:, :, 3]
    amt = magenta_amount(a)

    # Zwei Kriterien: (1) sattes Masken-Magenta, (2) Magenta-Ton in den weichen
    # Upscaler-Raendern (rot UND blau deutlich ueber gruen, z.B. 200/150/190).
    # Gold/Braun der Spielfiguren hat blau < gruen und wird nicht getroffen.
    is_magenta = ((a[:, :, 0] > R_MIN) & (a[:, :, 2] > B_MIN) & (a[:, :, 1] < G_MIN)) | \
                 ((a[:, :, 0] > a[:, :, 1] + 40) & (a[:, :, 2] > a[:, :, 1] + 40))
    rep = {
        "file": os.path.basename(path),
        "size": img.size,
        "opaque_before": int((alpha > 128).sum()),
        "magenta_pixels": int(is_magenta.sum()),
        "magenta_opaque": int((is_magenta & (alpha > 128)).sum()),
    }

    if rep["magenta_opaque"] == 0 and rep["magenta_pixels"] == 0:
        rep["status"] = "sauber"
        return rep

    # Anteilige Transparenz: 0 Magenta -> volle Deckkraft, 255 Magenta -> voll transparent.
    factor = np.clip((255.0 - amt) / 255.0, 0.0, 1.0) ** 2
    new_alpha = np.clip(alpha * factor, 0, 255).astype(np.uint8)
    changed = int((new_alpha != alpha).sum())
    rep["pixel_geaendert"] = changed
    rep["opaque_after"] = int((new_alpha > 128).sum())

    if apply_changes:
        out = np.dstack([a[:, :, 0].astype(np.uint8), a[:, :, 1].astype(np.uint8),
                         a[:, :, 2].astype(np.uint8), new_alpha])
        Image.fromarray(out, "RGBA").save(path)
        rep["status"] = "geschrieben"
    else:
        rep["status"] = "dry-run"
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--apply", action="store_true", help="Aenderungen schreiben")
    ap.add_argument("--backup-dir", default=None, help="Zielordner fuer Sicherungskopien")
    args = ap.parse_args()

    if args.apply and args.backup_dir:
        os.makedirs(args.backup_dir, exist_ok=True)
        for p in args.files:
            shutil.copy2(p, os.path.join(args.backup_dir, os.path.basename(p)))
        print("Sicherung nach", args.backup_dir)

    for p in args.files:
        rep = clean(p, args.apply)
        print(" ".join("%s=%s" % (k, v) for k, v in rep.items()))


if __name__ == "__main__":
    main()
