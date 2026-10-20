#!/usr/bin/env python3
"""Original (8-Bit) neben die HD-Komposition legen und die Abweichung beziffern.

Eingabe:  das Originalbild   (hd_ref.ppm,      sichtbarer 8-Bit-Ausschnitt, 1:1)
          die HD-Komposition (hd_step_*.ppm,   Zwischenstand, durch 2 verkleinert)
Ausgabe:  <out>/<name>_ab.png    Original und HD nebeneinander, gleiche Groesse
          <out>/<name>_diff.png  Abweichung, fehlende HD-Texturen rot markiert
          <out>/ab.csv           eine Zeile je Fall mit den Zahlen

Die drei Zahlen, die zaehlen:
  versatz    x/y-Verschiebung mit der besten Deckung. Nicht null heisst: die
             HD-Ebene scrollt oder sitzt anders als das Original.
  ohne_hd    Anteil der Kacheln, in denen die HD-Komposition genauso aussieht wie
             das hochskalierte Original. Dort wurde kein HD-Asset gezeichnet:
             fehlende Textur, nichts geladen, Objekt nicht gezeichnet.
  kanten     Anteil der HD-Kanten, die im Original keine Entsprechung haben.
             Zeigt zusaetzliche oder verschobene Struktur.

Aufruf: python3 harness/ab_compare.py <ref.ppm> <hd.ppm> <ausgabeordner> [name]
"""
import os
import sys

import numpy as np
from PIL import Image

BLOCK = 16          # Kachelgroesse in HD-Pixeln fuer die "ohne_hd"-Auswertung
FLAT_MEAN = 8.0     # mittlere Abweichung unter der eine Kachel als "kein HD" gilt
MAX_SHIFT = 12      # Suchbereich fuer den Versatz, in HD-Pixeln


def load_rgb(path):
    img = Image.open(path).convert("RGB")
    return np.asarray(img, dtype=np.uint8)


def gray(a):
    return (0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2])


def best_shift(a, b):
    """Versatz von b gegen a in Pixeln, aus der Kreuzkorrelation im Frequenzraum.

    Der ganze Suchbereich wird ausgewertet, nicht nur die Nahe. Ein senkrecht nicht
    mitfahrender HD-Hintergrund in hohen Raeumen liegt schnell hunderte Pixel daneben,
    mit einem kleinen Fenster waere das nur ein Randwert. Liegt der Spitzenwert bei
    null, sitzen beide Bilder uebereinander.

    Rueckgabe: dx, dy, Guete. Die Guete ist der Spitzenwert im Verhaeltnis zum Mittel
    der Umgebung. Werte nahe 1 heissen: die beiden Bilder haben nichts gemeinsam, der
    Versatz ist dann Zufall und darf nicht als Befund gelesen werden.
    """
    ga, gb = gray(a), gray(b)
    ga = ga - ga.mean()
    gb = gb - gb.mean()
    fa = np.fft.rfft2(ga)
    fb = np.fft.rfft2(gb)
    cc = np.fft.fftshift(np.fft.irfft2(fa * np.conj(fb), s=ga.shape))
    h, w = cc.shape
    cy, cx = h // 2, w // 2
    dy, dx = np.unravel_index(np.argmax(cc), cc.shape)
    peak = float(cc.max())
    rest = float(np.median(np.abs(cc))) + 1e-9
    quality = peak / rest if peak > 0 else 0.0
    if quality < 1.05:
        return 0, 0, round(quality, 2)
    return int(dx - cx), int(dy - cy), round(quality, 2)


def shifted(a, dx, dy):
    """a um (dx,dy) verschieben, Ränder werden wiederholt."""
    return np.roll(np.roll(a, dy, axis=0), dx, axis=1)


def sobel(g):
    gx = np.zeros_like(g)
    gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    gy[1:-1, :] = g[2:, :] - g[:-2, :]
    return np.hypot(gx, gy)


def dilate(mask, r=2):
    out = mask.copy()
    for _ in range(r):
        m = out
        out = m.copy()
        out[1:, :] |= m[:-1, :]
        out[:-1, :] |= m[1:, :]
        out[:, 1:] |= m[:, :-1]
        out[:, :-1] |= m[:, 1:]
    return out


def compare(ref_path, hd_path, outdir, name):
    ref = load_rgb(ref_path)
    hd = load_rgb(hd_path)
    factor = max(1, hd.shape[0] // ref.shape[0])
    ref_up = np.asarray(Image.fromarray(ref).resize(
        (hd.shape[1], hd.shape[0]), Image.NEAREST))

    dx, dy, q = best_shift(ref_up, hd)
    hd_al = shifted(hd, dx, dy)
    ref_al = ref_up

    diff = np.abs(hd_al.astype(np.int16) - ref_al.astype(np.int16)).astype(np.uint8)
    flat = diff.max(axis=2) < FLAT_MEAN

    # Kacheln, in denen die HD-Ebene nichts gegenüber dem Original gewinnt
    bh, bw = hd.shape[0] // BLOCK, hd.shape[1] // BLOCK
    blocks = flat[:bh * BLOCK, :bw * BLOCK].reshape(bh, BLOCK, bw, BLOCK)
    frac = blocks.mean(axis=(1, 3))
    nohd = frac > 0.98
    nohd_pct = 100.0 * nohd.mean()

    e_ref = dilate(sobel(gray(ref_al).astype(np.float32)) > 24, 2)
    e_hd = sobel(gray(hd_al).astype(np.float32)) > 24
    edge_mismatch = 100.0 * (e_hd & ~e_ref).sum() / max(1, e_hd.sum())

    os.makedirs(outdir, exist_ok=True)
    sep = np.full((hd.shape[0], 4, 3), 255, np.uint8)
    ab = np.concatenate([ref_al, sep, hd_al], axis=1)
    Image.fromarray(ab).save(os.path.join(outdir, f"{name}_ab.png"))

    heat = np.clip(diff.astype(np.int32) * 4, 0, 255).astype(np.uint8)
    nohd_full = np.zeros(hd.shape[:2], dtype=bool)
    nohd_full[:bh * BLOCK, :bw * BLOCK] = np.repeat(
        np.repeat(nohd, BLOCK, axis=0), BLOCK, axis=1)
    heat[nohd_full] = (255, 0, 0)
    Image.fromarray(heat).save(os.path.join(outdir, f"{name}_diff.png"))

    row = dict(name=name, ref=f"{ref.shape[1]}x{ref.shape[0]}",
               hd=f"{hd.shape[1]}x{hd.shape[0]}", faktor=factor,
               versatz=f"({dx},{dy})", guete=q, ohne_hd=f"{nohd_pct:.1f}",
               kanten=f"{edge_mismatch:.1f}",
               farbe=f"{diff.mean():.1f}")
    return row, nohd_pct, edge_mismatch


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    ref, hd, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    name = sys.argv[4] if len(sys.argv) > 4 else os.path.basename(ref).split(".")[0]
    row, nohd, edges = compare(ref, hd, outdir, name)
    csv = os.path.join(outdir, "ab.csv")
    head = not os.path.exists(csv)
    with open(csv, "a", encoding="utf-8") as f:
        if head:
            f.write("name;ref;hd;faktor;versatz;guete;ohne_hd%;kanten%;farbe\n")
        f.write(";".join(str(row[k]) for k in
                         ["name", "ref", "hd", "faktor", "versatz", "guete", "ohne_hd", "kanten", "farbe"]) + "\n")
    for k, v in row.items():
        print(f"{k:10s} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
