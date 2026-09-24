#!/usr/bin/env python3
"""Alpha/Masken-Schritt v7 — repariert die Magenta-Maske der HD-Objekt-Assets.

Was in v6 schiefging (Code-Beleg in add_object_alpha_v6.py, Zeilen 119-141):

    if os.path.exists(src_path):
        if orig.mode == 'P':   ... Maske aus Paletten-Index ...
        else:                  hd_out = np.array(hd.convert('RGBA'))   # <-- kaputt
    else:
        hd_out = np.array(hd.convert('RGBA'))                          # <-- kaputt

Fehlt die Quelldatei oder ist sie kein Palettenbild, behaelt der Schritt die
HD-Alpha des Upscaler-Ergebnisses. Die maskierten Flaechen sind dort aber mit
Magenta (ca. 230,0,200) gefuellt und bleiben sichtbar. Genau diese Magenta-
Flaechen sind der lila Rand an der Verb-Muenze und an 377 weiteren Assets.

v7 macht zwei Dinge:
 1. Maske immer aus der Quelle ableiten, auch bei RGB/RGBA-Quellen
    (Alpha-Kanal, sonst Magenta-Erkennung), nicht mehr "Alpha behalten".
 2. Magenta- und Pinktoene im HD-Bild auf Alpha 0 setzen. Nur diese Pixel.
    Alle anderen Toene (Schwarz, Weiss, Metall, Holz) bleiben unangetastet.
    Das war der Fehler des Einmal-Filters: der hat auch andere Toene erwischt.

Aufruf:
    python3 scripts/add_object_alpha_v7.py --scan HD_DIR              # nur Bericht
    python3 scripts/add_object_alpha_v7.py --apply HD_DIR [--src SRC_DIR] [--backup DIR]
    python3 scripts/add_object_alpha_v7.py --apply HD_DIR --file 0003_system-cursor-icon_0000.png
"""

import argparse
import glob
import os
import shutil
import sys

import numpy as np
from PIL import Image

# Magenta-Maske der Pipeline: Rot und Blau hoch, Gruen praktisch null.
SAT = dict(r=140, b=120, g=100)          # sattes Maskenmagenta
BLEND_MARGIN = 30                        # weiche Upscaler-Raender
BLEND_G_MAX = 170
BLEND_MIN_R = 120                        # Helligkeitsschwelle: dunkle Pixel mit
BLEND_MIN_B = 100                        # leichtem Magenta-Stich gehoeren zur Grafik
BLEND_RADIUS = 6                         # nur Magenta-Rand in dieser Naehe zur harten Maske


def magenta_mask(rgb):
    """True fuer sattes Maskenmagenta und fuer dessen weichen Upscaler-Rand.

    Wichtig: der weiche Rand wird nur dort entfernt, wo er unmittelbar an
    satten Maskenmagenta grenzt (Radius siehe BLEND_RADIUS). Sonst frisst die
    Regel echte Pinktoene der Grafik, z.B. helles Rosa (250,154,207) im Asset
    0028_pink-chest-anim-object.
    """
    r, g, b = rgb[:, :, 0].astype(int), rgb[:, :, 1].astype(int), rgb[:, :, 2].astype(int)
    sat = (r > SAT["r"]) & (b > SAT["b"]) & (g < SAT["g"])
    blend = (r > g + BLEND_MARGIN) & (b > g + BLEND_MARGIN) & (g < BLEND_G_MAX) \
            & (r > BLEND_MIN_R) & (b > BLEND_MIN_B)
    return sat | (blend & _near(sat, BLEND_RADIUS))


def _near(mask, radius):
    """Flaeche um `mask` herum (einfache Dilatation, ohne Zusatzpakete)."""
    out = mask.copy()
    for _ in range(radius):
        out = (out | np.roll(out, 1, 0) | np.roll(out, -1, 0)
                   | np.roll(out, 1, 1) | np.roll(out, -1, 1))
    return out


def mask_from_source(src_path, size):
    """Deckkraftmaske (0-255) aus dem SD-Original, auf HD-Groesse skaliert."""
    if not src_path or not os.path.exists(src_path):
        return None
    src = Image.open(src_path)
    if src.mode == "P":
        a = np.array(src)
        border = np.concatenate([a[0, :], a[-1, :], a[:, 0], a[:, -1]])
        unique, counts = np.unique(border, return_counts=True)
        bg = int(unique[np.argmax(counts)])
        m = (a != bg).astype(np.uint8) * 255
    elif "A" in src.mode:
        a = np.array(src.convert("RGBA"))
        m = (a[:, :, 3] > 128).astype(np.uint8) * 255
    else:
        a = np.array(src.convert("RGB"))
        m = (~magenta_mask(a)).astype(np.uint8) * 255
    return np.array(Image.fromarray(m, mode="L").resize(size, Image.Resampling.BILINEAR), dtype=np.uint8)


def process(path, src_path=None, apply_changes=False):
    img = Image.open(path)
    rgb = np.array(img.convert("RGB"))
    alpha = np.array(img.convert("RGBA"))[:, :, 3]
    h, w = alpha.shape[:2]

    pink = magenta_mask(rgb)
    new_alpha = alpha.copy()

    # 1) Maske aus der Quelle, falls vorhanden
    src_mask_used = False
    m = mask_from_source(src_path, (w, h))
    if m is not None:
        new_alpha = np.minimum(new_alpha, m)
        src_mask_used = True

    # 2) Magenta/Pink restlos entfernen
    new_alpha = np.where(pink, 0, new_alpha)

    changed = new_alpha != alpha
    collateral = int((changed & ~pink).sum())        # muss 0 sein
    report = {
        "file": os.path.basename(path),
        "size": "%dx%d" % (w, h),
        "src_mask": src_mask_used,
        "magenta_pixel": int(pink.sum()),
        "davon_opak": int((pink & (alpha > 128)).sum()),
        "opak_vorher": int((alpha > 128).sum()),
        "opak_nachher": int((new_alpha > 128).sum()),
        "pixel_geaendert": int(changed.sum()),
        "andere_toene_geaendert": collateral,
    }

    if apply_changes and collateral == 0 and changed.any():
        out = np.dstack([rgb, new_alpha]).astype(np.uint8)
        Image.fromarray(out, "RGBA").save(path)
        report["status"] = "geschrieben"
    elif not changed.any():
        report["status"] = "sauber"
    elif collateral:
        report["status"] = "ABBRUCH: fremde Pixel betroffen"
    else:
        report["status"] = "dry-run"
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hd_dir")
    ap.add_argument("--src", default=None, help="Ordner mit den SD-Originalen (optional)")
    ap.add_argument("--file", action="append", default=None, help="nur diese Datei(en)")
    ap.add_argument("--scan", action="store_true", help="nur messen, nichts schreiben")
    ap.add_argument("--apply", action="store_true", help="Aenderungen schreiben")
    ap.add_argument("--backup", default=None, help="Sicherungsordner vor dem Schreiben")
    args = ap.parse_args()

    names = args.file or sorted(os.path.basename(p) for p in glob.glob(os.path.join(args.hd_dir, "*.png")))
    if args.apply and args.backup:
        os.makedirs(args.backup, exist_ok=True)
        for n in names:
            shutil.copy2(os.path.join(args.hd_dir, n), os.path.join(args.backup, n))
        print("Sicherung nach", args.backup)

    total_pink = total_coll = total_opak = 0
    affected = 0
    for n in names:
        p = os.path.join(args.hd_dir, n)
        if not os.path.exists(p):
            print("fehlt:", n)
            continue
        src = os.path.join(args.src, n) if args.src else None
        rep = process(p, src, apply_changes=args.apply and not args.scan)
        total_pink += rep["magenta_pixel"]
        total_coll += rep["andere_toene_geaendert"]
        if rep["davon_opak"]:
            affected += 1
        if rep["davon_opak"] or args.file:
            print(" ".join("%s=%s" % (k, v) for k, v in rep.items()))
    print("-" * 70)
    print("Dateien: %d | mit sichtbarem Magenta: %d | Magenta-Pixel: %d | fremde Toene geaendert: %d"
          % (len(names), affected, total_pink, total_coll))
    if total_coll:
        print("WARNUNG: fremde Pixel betroffen, bitte pruefen")
        sys.exit(2)


if __name__ == "__main__":
    main()
