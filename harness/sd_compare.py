#!/usr/bin/env python3
"""HD-Komposition gegen die SD-Engine stellen: fehlende und falsch sitzende Texturen.

Referenz ist das Bild der unveraenderten ScummVM (SD). Sie zeichnet das Spiel so, wie
es gedacht ist. Verglichen wird Block fuer Block:

  fehlt     Im SD-Bild steht Struktur, im HD-Bild ist an derselben Stelle nichts
            (leer, schwarz oder einfarbig). Das Asset wird nicht gezeichnet.
  verrutscht Der Inhalt ist da, sitzt aber woanders als im SD-Bild. Gemessen wird
            der Versatz je Kachel; weicht er vom Gesamtversatz ab, liegt dort eine
            falsche Position oder eine falsche Kamera vor.
  versatz   Gesamtversatz beider Bilder. Nicht null heisst, die HD-Ebene sitzt
            gegenueber dem Original verschoben.

Aufruf: python3 harness/sd_compare.py <sd.ppm> <hd.ppm> <ausgabeordner> [name]
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ab_compare import best_shift, gray, load_rgb  # noqa: E402

TILE = 128          # Kachelgroesse in SD-Pixeln fuer den oertlichen Versatz
STRUCT_STD = 8.0    # ab dieser Streuung hat das SD-Bild an der Stelle Struktur
EMPTY_STD = 3.0     # darunter gilt die HD-Flaeche als leer
LOCAL_LIMIT = 4     # ab dieser Abweichung vom Gesamtversatz gilt sie als verrutscht


def edge(img, thr=28.0):
    """Kantenkarte: wo im Bild Struktur liegt. Wird fuer den Inhaltsvergleich gebraucht."""
    g = gray(img).astype(np.float32)
    gx = np.zeros_like(g)
    gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    gy[1:-1, :] = g[2:, :] - g[:-2, :]
    return np.hypot(gx, gy) > thr


def local_shift(sd, hd, size):
    """Versatz je Kachel, gesucht im kleinen Umfeld.

    Gesucht wird nur im Umfeld von 16 Pixeln. Ein grosser Suchbereich liefert in kleinen
    Kacheln ohne viel Struktur Zufallsspitzen, und die wuerden als "verrutscht" gelesen.
    """
    out = {}
    step = TILE
    lag = 16
    for y in range(0, size[1] - step + 1, step):
        for x in range(0, size[0] - step + 1, step):
            a = sd[y:y + step, x:x + step]
            b = hd[y:y + step, x:x + step]
            if a.std() < 2 or b.std() < 2:
                out[(x, y)] = None
                continue
            ga = gray(a).astype(np.float32)
            gb = gray(b).astype(np.float32)
            ga -= ga.mean()
            gb -= gb.mean()
            cc = np.fft.fftshift(np.fft.irfft2(np.fft.rfft2(ga) * np.conj(np.fft.rfft2(gb)),
                                              s=ga.shape))
            cy, cx = cc.shape[0] // 2, cc.shape[1] // 2
            win = cc[cy - lag:cy + lag + 1, cx - lag:cx + lag + 1]
            dy, dx = np.unravel_index(np.argmax(win), win.shape)
            peak = float(win.max())
            rest = float(np.median(np.abs(win))) + 1e-9
            q = peak / rest if peak > 0 else 0.0
            out[(x, y)] = (int(dx - lag), int(dy - lag)) if q >= 1.30 else None
    return out


def compare_pair(sd_path, hd_path, outdir, name):
    sd = load_rgb(sd_path)
    hd = load_rgb(hd_path)
    factor = hd.shape[0] // sd.shape[0]
    # SD auf HD-Groesse bringen, damit beide dieselbe Geometrie haben.
    sd_up = np.asarray(Image.fromarray(sd).resize((hd.shape[1], hd.shape[0]), Image.NEAREST))

    dx, dy, q = best_shift(sd_up, hd)
    hd_al = np.roll(np.roll(hd, dy, axis=0), dx, axis=1)

    bh, bw = hd.shape[0] // TILE, hd.shape[1] // TILE
    cut = lambda a: a[:bh * TILE, :bw * TILE].reshape(bh, TILE, bw, TILE)
    sd_std = cut(gray(sd_up)).std(axis=(1, 3))
    hd_std = cut(gray(hd_al)).std(axis=(1, 3))
    hd_mean = cut(gray(hd_al)).mean(axis=(1, 3))

    struktur = sd_std > STRUCT_STD
    # "Fehlt" heisst: im Soll-Bild liegen Kanten, im HD-Bild ist an der Stelle keine Spur
    # davon. Ueber Kanten statt ueber Helligkeit, sonst gilt jede dunkle Nachtstelle als leer.
    sd_kanten = cut(edge(sd_up, 18.0)).sum(axis=(1, 3))
    hd_kanten = cut(edge(hd_al, 18.0)).sum(axis=(1, 3))
    fehlt = (sd_kanten > 60) & (hd_kanten < 0.15 * sd_kanten)

    lok = local_shift(np.asarray(Image.fromarray(sd).resize((sd.shape[1] * factor, sd.shape[0] * factor), Image.NEAREST)),
                      hd_al, (hd.shape[1], hd.shape[0]))
    verrutscht = np.zeros((bh, bw), dtype=bool)
    abweichend = np.zeros((bh, bw), dtype=bool)
    versatz_karte = np.zeros((bh, bw, 2), dtype=int)
    for (x, y), val in lok.items():
        tx, ty = x // TILE, y // TILE
        if tx >= bw or ty >= bh:
            continue
        if val is None:
            continue
        versatz_karte[ty, tx] = val
        if abs(val[0] - dx) > LOCAL_LIMIT or abs(val[1] - dy) > LOCAL_LIMIT:
            verrutscht[ty, tx] = True

    # Abweichend: beide Bilder haben an der Stelle Kanten, sie passen aber nicht
    # zusammen (auch nicht nach dem Versatz). Dort steht Inhalt, aber der falsche.
    sd_e = cut(edge(sd_up))
    hd_e = cut(edge(hd_al))
    sd_edges = sd_e.sum(axis=(1, 3))
    hd_edges = hd_e.sum(axis=(1, 3))
    treffer = (sd_e & hd_e).sum(axis=(1, 3))
    genug = (sd_edges > 80) & (hd_edges > 80)
    abweichend = genug & (treffer < 0.25 * np.minimum(sd_edges, hd_edges))

    mark = np.zeros(hd.shape[:2], dtype=np.uint8)
    for ty in range(bh):
        for tx in range(bw):
            if fehlt[ty, tx]:
                mark[ty * TILE:(ty + 1) * TILE, tx * TILE:(tx + 1) * TILE] = 1
            elif verrutscht[ty, tx]:
                mark[ty * TILE:(ty + 1) * TILE, tx * TILE:(tx + 1) * TILE] = 2
            elif abweichend[ty, tx]:
                mark[ty * TILE:(ty + 1) * TILE, tx * TILE:(tx + 1) * TILE] = 3

    os.makedirs(outdir, exist_ok=True)
    sep = np.full((hd.shape[0], 6, 3), 255, np.uint8)
    Image.fromarray(np.concatenate([sd_up, sep, hd_al], axis=1)).save(
        os.path.join(outdir, f"{name}_sd_ab.png"))
    over = np.zeros_like(hd)
    over[mark == 1] = (255, 0, 0)
    over[mark == 2] = (0, 90, 255)
    over[mark == 3] = (0, 200, 0)
    blend = np.clip(hd_al.astype(np.int16) * 0.55 + over.astype(np.int16) * 0.85, 0, 255).astype(np.uint8)
    Image.fromarray(blend).save(os.path.join(outdir, f"{name}_sd_mark.png"))

    fehlt_pct = 100.0 * (mark == 1).sum() / mark.size
    verr_pct = 100.0 * (mark == 2).sum() / mark.size
    abw_pct = 100.0 * (mark == 3).sum() / mark.size
    row = dict(name=name, versatz=f"({dx},{dy})", guete=q,
               fehlt=f"{fehlt_pct:.1f}", verrutscht=f"{verr_pct:.1f}", abweichend=f"{abw_pct:.1f}")
    csv = os.path.join(outdir, "sd_befunde.csv")
    head = not os.path.exists(csv)
    with open(csv, "a", encoding="utf-8") as f:
        if head:
            f.write("name;versatz;guete;fehlt%;verrutscht%;abweichend%\n")
        f.write(";".join(str(row[k]) for k in
                         ["name", "versatz", "guete", "fehlt", "verrutscht", "abweichend"]) + "\n")
    for k, v in row.items():
        print(f"{k:12s} {v}")
    return row


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    sd_path, hd_path, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    name = sys.argv[4] if len(sys.argv) > 4 else os.path.basename(sd_path).split(".")[0]
    compare_pair(sd_path, hd_path, outdir, name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
