#!/usr/bin/env python3
"""Maskenindex eines Quellbildes bestimmen (reproduzierbare Regel, kein Farbraten).

Die Quellbilder sind 8-Bit-Palettenbilder. Die Maske ist der Paletteneintrag,
dessen Farbe in der Magentafamilie liegt UND dessen Flaeche den Bildrand
beruehrt. Nur dann ist es die transparente Umgebung des Sprites.

Belegt an den Quellen (comi-original-assets.zip):

    Objekt                      Index  Anteil  Beruehrt Bildrand
    system-cursor-icon_0000       255   96.1%  100.0%    -> Maske
    lice-icon-object_0000         255   97.6%  100.0%    -> Maske
    inventory-bg-object_0000      255   14.4%   76.5%    -> Maske
    logo-logo-object_0000          33   14.9%    0.0%    -> keine Maske (Magenta liegt innen, bleibt Grafik)
    clring-a-balcony-door_0000      -       -       -     -> kein Magenta in der Palette (Violett ist Grafik)
    ramrod-object_0000              -       -       -     -> kein Magenta in der Palette

Damit faellt die Regel genau so aus wie Koljas Sichturteil: Icons und
System-UI ja, Logo und Raumobjekte nein.
"""
import numpy as np

MAGENTA_R_MIN = 200
MAGENTA_B_MIN = 150
MAGENTA_G_MAX = 60
BORDER_MIN_SHARE = 0.10      # mindestens 10 % der Randpixel muessen dazugehoeren


def magenta_palette_entries(palette):
    """Indizes der Palette, deren Farbe in der Magentafamilie liegt."""
    pal = np.array(palette[:768], dtype=int).reshape(256, 3)
    mask = (pal[:, 0] > MAGENTA_R_MIN) & (pal[:, 2] > MAGENTA_B_MIN) & (pal[:, 1] < MAGENTA_G_MAX)
    return [int(i) for i in np.nonzero(mask)[0]]


def border_pixels(arr):
    return np.concatenate([arr[0, :], arr[-1, :], arr[:, 0], arr[:, -1]])


def mask_index(source_image, border_min_share=BORDER_MIN_SHARE, extra_indices=()):
    """Maskenindex oder None. source_image ist ein PIL-Bild im Modus P.

    `extra_indices` erlaubt weitere Maskenindizes, die nicht magentafarben sind.
    Fuer Objektebenen ist das Index 39: `extract_all_raw.py` setzt ihn beim
    Zusammensetzen der Ebene als transparenten Index, seine Palettenfarbe ist
    beliebig. Auch dort muss die Flaeche den Bildrand beruehren.
    """
    if source_image.mode != "P":
        return None
    palette = source_image.getpalette()
    if not palette:
        return None
    arr = np.array(source_image)
    border = border_pixels(arr)
    candidates = list(magenta_palette_entries(palette)) + [int(i) for i in extra_indices]
    best = None
    for idx in candidates:
        region = (arr == idx)
        share = float(region.mean())
        if share == 0.0:
            continue
        border_share = float((border == idx).mean())
        if border_share >= border_min_share:
            # groesste zusammenhaengende Magentaflaeche gewinnt
            if best is None or border_share > best[1]:
                best = (idx, border_share, share)
    if best is None:
        return None
    return {"index": best[0], "border_share": best[1], "image_share": best[2], "from_extra": best[0] in tuple(extra_indices)}


if __name__ == "__main__":
    import sys
    from PIL import Image
    for path in sys.argv[1:]:
        im = Image.open(path)
        info = mask_index(im)
        print("%s -> %s" % (path, info))
