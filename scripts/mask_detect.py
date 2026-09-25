#!/usr/bin/env python3
"""Maskenerkennung fuer die Rohbilder: reproduzierbare Regel, kein Farbraten.

Die Quellbilder sind 8-Bit-Palettenbilder. Die Maske ist der Paletteneintrag, der den Bildrand
stellt. Ihre Farbe unterscheidet sich je Raum (Magenta im Systemraum, Gruen im Schiff, Violett
anderswo), der Index also auch. Deshalb wird der Index gemessen: je Raum gewinnt der Eintrag,
den die Mehrheit der Objektbilder am Rand traegt.

Gemessen an comi-original-assets.zip:

    Raum 3 (System/Inventar)   Index 255, Farbe (227,0,195) Magenta
    Raum 9 (Laderaum)          Index 5,   Farbe (107,199,27) Gruen
    Objektebenen               Index 39,  gesetzt vom Zusammensetzen der Leinwand

Bewusst keine Farbregel: eine reine Magentapruefung uebersieht die gruenen und violetten Masken,
und eine reine Randregel wuerde das Logo treffen, dessen heller Rand Grafik ist.
"""

import numpy as np

MASK_BORDER_MIN = 0.60      # mindestens 60 % der Randpixel
MASK_AREA_MIN = 0.15        # mindestens 15 % der Bildflaeche
MASK_VOTE_MIN_SHARE = 0.8   # so viele Objektbilder des Raums muessen den Eintrag stellen

# Maskenfarben, gemessen in den System- und Schiffstraeumen des Spiels. Eine reine Randregel
# ohne diese Liste traefe den Logoraum, dessen blauer Rand Grafik ist (Raum 1, Index 53, (0,87,171)):
# genau die Verwechslung, die Koljas Sichturteil schon einmal korrigiert hat.
MASK_COLOURS = ((227, 0, 195), (107, 199, 27), (141, 47, 255), (0, 255, 0))
MASK_COLOUR_TOLERANCE = 24


def dominant_border_index(arr, border_min=MASK_BORDER_MIN, area_min=MASK_AREA_MIN):
    """(Index, Randanteil, Flaechenanteil) des Eintrags, der den Rand stellt, oder None."""
    border = np.concatenate([arr[0, :], arr[-1, :], arr[:, 0], arr[:, -1]])
    best = None
    for idx in np.unique(arr):
        area = float((arr == idx).mean())
        share = float((border == idx).mean())
        if share >= border_min and area >= area_min and (best is None or share > best[1]):
            best = (int(idx), share, area)
    return best


def colour_is_mask_like(colour, tolerance=MASK_COLOUR_TOLERANCE):
    """Liegt die Palettenfarbe in der Naehe einer gemessenen Maskenfarbe?"""
    if colour is None:
        return False
    return any(max(abs(int(colour[i]) - c[i]) for i in range(3)) <= tolerance for c in MASK_COLOURS)


def room_mask_index(images, vote_min_share=MASK_VOTE_MIN_SHARE):
    """(Index, Stimmen, Gesamtzahl). Ohne klare Mehrheit (None, ...), dann wird nichts geschrieben.

    Geschrieben wird nur, wenn sowohl die Mehrheit der Objektbilder den Eintrag am Rand traegt als
    auch seine Palettenfarbe einer gemessenen Maskenfarbe entspricht. Im Zweifel passiert nichts:
    eine falsch gesetzte Maske schneidet Grafik weg, das ist der teurere Fehler.
    """
    votes = {}
    for im in images:
        found = dominant_border_index(np.array(im)) if im.mode == "P" else None
        if found:
            votes[found[0]] = votes.get(found[0], 0) + 1
    if not votes:
        return None, 0, len(images)
    idx, count = max(votes.items(), key=lambda kv: kv[1])
    if count < max(2, vote_min_share * len(images)):
        return None, count, len(images)
    palette = images[0].getpalette() if images and images[0].mode == "P" else None
    colour = tuple(int(v) for v in palette[idx * 3:idx * 3 + 3]) if palette and len(palette) >= idx * 3 + 3 else None
    if not colour_is_mask_like(colour):
        return None, count, len(images)
    return idx, count, len(images)


def save_with_mask(im, path, mask_index, palette=None):
    """Paletten-PNG schreiben und die Maske als Transparenz (tRNS) ablegen."""
    if palette is not None:
        im.putpalette(palette)
    if mask_index is None:
        im.save(str(path))
        return False
    im.save(str(path), transparency=int(mask_index))
    return True


def mask_from_transparency(im):
    """Binaere Maske aus der tRNS-Angabe eines Palettenbildes, sonst None."""
    trans = im.info.get("transparency")
    if im.mode != "P" or trans is None:
        return None
    idx = trans[0] if isinstance(trans, (tuple, list)) else trans
    return (np.array(im) == int(idx)).astype(np.uint8) * 255


def fill_masked_area(rgb, mask, iterations=24):
    """Maskierte Pixel aus der Nachbarschaft auffuellen (Referenz ohne cv2).

    Jede Runde waechst der bekannte Bereich um einen Pixel und uebernimmt den Mittelwert der
    schon bekannten Nachbarn. Der Upscaler nutzt stattdessen cv2.inpaint; beide Wege sollen die
    Maskenfarbe vor dem Skalieren entfernen, damit kein Saum ins Motiv gezogen wird.
    """
    rgb = np.asarray(rgb).astype(np.float64)
    known = (np.asarray(mask) < 128)
    if known.all():
        return np.clip(rgb, 0, 255).astype(np.uint8)
    for _ in range(iterations):
        if known.all():
            break
        acc = np.zeros_like(rgb)
        wsum = np.zeros(known.shape, dtype=np.float64)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                acc += np.roll(np.roll(rgb * known[:, :, None], dy, axis=0), dx, axis=1)
                wsum += np.roll(np.roll(known.astype(np.float64), dy, axis=0), dx, axis=1)
        fresh = (~known) & (wsum > 0)
        if fresh.any():
            rgb[fresh] = (acc / np.maximum(wsum, 1)[:, :, None])[fresh]
            known = known | fresh
    return np.clip(rgb, 0, 255).astype(np.uint8)
