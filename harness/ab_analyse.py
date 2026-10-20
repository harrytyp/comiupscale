#!/usr/bin/env python3
"""Auswertung des Bildvergleichs: welche Raeume haben echte Probleme und welche.

Liest die Geraden <raum>_ref.ppm (Original, 8-Bit) und <raum>_hd.ppm (HD-Komposition)
aus einem Ordner und schreibt:

  befunde.csv    eine Zeile je Raum mit den Zahlen und einer Zuordnung
  <raum>_mark.ppm/png  Markierung: rot = kein HD-Asset, blau = Struktur passt nicht

Die drei Befundarten:

  ausrichtung  Versatz zwischen HD-Ebene und Original. Nicht null heisst, die HD-Ebene
               sitzt oder scrollt anders.
  ohne_hd      Kacheln, in denen die HD-Ebene nichts gegenueber dem hochskalierten
               Original gewinnt, und in denen das Original Struktur hat (Kanten). Dort
               wurde kein HD-Asset gezeichnet: Textur fehlt, nichts geladen, Objekt
               nicht gezeichnet. Flaechige Bereiche wie Himmel oder Wasser zaehlen nicht.
  struktur     HD-Bild auf Originalgroesse zurueckgerechnet und gegen das Original
               gestellt. Grosse Abweichung bei vorhandener Struktur heisst: Objekt
               fehlt, sitzt falsch oder hat die falsche Groesse.

Aufruf: python3 harness/ab_analyse.py <ordner> [threshold-faktoren]
"""
import glob
import os
import re
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ab_compare import best_shift, gray, load_rgb, shifted  # noqa: E402

BLOCK = 16
FLAT_MAX = 8        # Kachel gilt als "kein HD", wenn kein Pixel staerker abweicht
STRUCT_STD = 6.0    # ab dieser Streuung hat das Original in der Kachel Struktur
MISMATCH = 40.0     # mittlere Abweichung, ab der die Struktur nicht mehr passt
BLOCKY = 0.90       # Anteil Pixel, der auf dem Kachelraster klebt, ab dem es "hochskaliert" ist
COVER_STD = 3.0     # HD-Flaeche gilt als leer, wenn ihre Streuung darunter liegt
COVER_REF_STD = 25.0  # das Original muss dort aber Struktur haben


def blockiness(hd, factor):
    """Anteil Pixel, die genau auf dem Raster ihres Nachbarpixels liegen.

    Ein fehlendes HD-Asset wird als hochskaliertes Original gezeichnet: dort sind
    alle Pixel eines Faktors x Faktor-Quadrats gleich. Ein echtes HD-Bild hat das
    nicht. Das Merkmal haengt nicht am Original, deshalb faellt es auch in dunklen
    Flaechen nicht falsch aus.
    """
    h, w = hd.shape[0] // factor * factor, hd.shape[1] // factor * factor
    a = hd[:h, :w].astype(np.int16)
    ref_y = np.arange(h)[:, None] // factor * factor
    ref_x = np.arange(w)[None, :] // factor * factor
    base = a[ref_y, ref_x]
    return (np.abs(a - base).max(axis=2) == 0)


def boxes(mask, min_area=3):
    """Zusammenhaengende Bereiche einer Kachelmaske als Rechtecke (Kachelkoordinaten)."""
    bh, bw = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    out = []
    for y in range(bh):
        for x in range(bw):
            if not mask[y, x] or seen[y, x]:
                continue
            stack = [(y, x)]
            seen[y, x] = True
            ys, xs = [], []
            while stack:
                cy, cx = stack.pop()
                ys.append(cy)
                xs.append(cx)
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < bh and 0 <= nx < bw and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            if len(ys) >= min_area:
                out.append((min(xs) * BLOCK, min(ys) * BLOCK,
                            (max(xs) - min(xs) + 1) * BLOCK, (max(ys) - min(ys) + 1) * BLOCK))
    out.sort(key=lambda b: -b[2] * b[3])
    return out


def analyse(ref_path, hd_path):
    ref = load_rgb(ref_path)
    hd = load_rgb(hd_path)
    factor = max(1, hd.shape[0] // ref.shape[0])
    ref_up = np.asarray(Image.fromarray(ref).resize((hd.shape[1], hd.shape[0]), Image.NEAREST))
    dx, dy, q = best_shift(ref_up, hd)
    hd_al = shifted(hd, dx, dy)

    bh, bw = hd.shape[0] // BLOCK, hd.shape[1] // BLOCK
    cut = lambda a: a[:bh * BLOCK, :bw * BLOCK].reshape(bh, BLOCK, bw, BLOCK)
    ref_blocks = cut(gray(ref_up))
    hd_blocks = cut(gray(hd_al))
    rstd = ref_blocks.std(axis=(1, 3))
    hstd = hd_blocks.std(axis=(1, 3))
    structural = rstd > STRUCT_STD

    # Fehlendes HD-Asset: das HD-Bild klebt dort auf dem Kachelraster (hochskaliertes Original).
    blocky = cut(blockiness(hd_al, factor)).mean(axis=(1, 3)) > BLOCKY
    ohne = blocky & structural
    # Verdeckt: im HD-Bild ist die Flaeche leer, im Original steht dort Struktur.
    # Klassischer Platzhalter, der Inhalt zudeckt.
    verdeckt = (hstd < COVER_STD) & (rstd > COVER_REF_STD)

    hd_down = np.asarray(Image.fromarray(hd_al).resize((ref.shape[1], ref.shape[0]), Image.BOX))
    rueck = np.abs(gray(hd_down) - gray(ref)).mean()

    mark = np.zeros(hd.shape[:2], dtype=np.uint8)
    for y in range(bh):
        for x in range(bw):
            if ohne[y, x]:
                mark[y * BLOCK:(y + 1) * BLOCK, x * BLOCK:(x + 1) * BLOCK] = 1
            elif verdeckt[y, x]:
                mark[y * BLOCK:(y + 1) * BLOCK, x * BLOCK:(x + 1) * BLOCK] = 2

    area_ohne = 100.0 * (mark == 1).sum() / mark.size
    area_verdeckt = 100.0 * (mark == 2).sum() / mark.size
    return dict(versatz=(dx, dy), guete=q, ohne_hd=round(area_ohne, 1),
                verdeckt=round(area_verdeckt, 1),
                markiert=round(area_ohne + area_verdeckt, 1), rueck=round(float(rueck), 1),
                ohne_boxes=boxes(ohne), verdeckt_boxes=boxes(verdeckt)), mark, ref, hd_al


def severity(r, reliable):
    """Schweregrad: Ausrichtung am schwersten, dann zudeckende Flaechen, dann fehlende Assets.

    Ohne belastbare Deckung darf der Versatz nicht in die Wertung: leere Flaeche oder
    eine voellig andere Szene liefert dort Zufallswerte.
    """
    s = 1.5 * r["ohne_hd"] + 2.0 * r["verdeckt"]
    if reliable:
        s += 10.0 * max(abs(r["versatz"][0]), abs(r["versatz"][1]))
    return round(s, 1)


def classify(r, reliable):
    out = []
    if reliable and max(abs(r["versatz"][0]), abs(r["versatz"][1])) > 2:
        out.append("ausrichtung")
    if r["ohne_hd"] >= 2.0:
        out.append("ohne_hd")
    if r["verdeckt"] >= 1.0:
        out.append("verdeckt")
    if not out:
        out.append("unauffaellig" if reliable else "nicht_bewertbar")
    return ",".join(out)


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "/opt/data/projects/comi-hd/reports/ab"
    refs = {os.path.basename(p).split("_")[0]: p for p in glob.glob(os.path.join(folder, "*_ref.ppm"))}
    rows = []
    for room, ref_path in sorted(refs.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0):
        hd_path = os.path.join(folder, f"{room}_hd.ppm")
        if not os.path.exists(hd_path):
            continue
        r, mark, ref, hd = analyse(ref_path, hd_path)
        r["raum"] = room
        reliable = r["guete"] >= 1.25
        r["schwere"] = severity(r, reliable)
        r["befund"] = classify(r, reliable)
        if not reliable:
            r["versatz"] = (0, 0)
        rows.append(r)

        over = np.zeros_like(hd)
        over[mark == 1] = (255, 0, 0)
        over[mark == 2] = (0, 90, 255)
        blend = np.clip(hd.astype(np.int16) * 0.55 + over.astype(np.int16) * 0.85, 0, 255).astype(np.uint8)
        Image.fromarray(blend).save(os.path.join(folder, f"{room}_mark.png"))

    rows.sort(key=lambda r: -r["schwere"])
    csv = os.path.join(folder, "befunde.csv")
    with open(csv, "w", encoding="utf-8") as f:
        f.write("raum;schwere;befund;guete;versatz_x;versatz_y;ohne_hd%;verdeckt%;rueck;flaeche1;flaeche2;flaeche3\n")
        for r in rows:
            bs = r["ohne_boxes"] + r["verdeckt_boxes"]
            f.write(";".join(str(v) for v in [
                r["raum"], r["schwere"], r["befund"], r["guete"], r["versatz"][0], r["versatz"][1],
                r["ohne_hd"], r["verdeckt"], r["rueck"],
                f"{bs[0][2]}x{bs[0][3]}@{bs[0][0]},{bs[0][1]}" if len(bs) > 0 else "-",
                f"{bs[1][2]}x{bs[1][3]}@{bs[1][0]},{bs[1][1]}" if len(bs) > 1 else "-",
                f"{bs[2][2]}x{bs[2][3]}@{bs[2][0]},{bs[2][1]}" if len(bs) > 2 else "-"]) + "\n")

    print(f"Raeume ausgewertet: {len(rows)}  ->  {csv}")
    for r in rows[:20]:
        print("  Raum %-4s Schwere %-6s %-22s ohne HD %5.1f%%  verdeckt %5.1f%%  Versatz %s  Guete %s"
              % (r["raum"], r["schwere"], r["befund"], r["ohne_hd"], r["verdeckt"], r["versatz"], r["guete"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
