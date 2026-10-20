#!/usr/bin/env python3
"""Vergleicht eine Bildfolge aus Original und HD-Komposition Bild fuer Bild.

Erwartet gepaarte Aufnahmen in zwei Verzeichnissen, gleicher Name bis auf das Praefix:
  /tmp/hd_refscan/r003_raum40_cam216.ppm   Original (8-Bit, sichtbarer Ausschnitt)
  /tmp/hd_scan/s003_raum40_cam216.ppm      HD-Komposition (durch 2 verkleinert)

Gemeldet wird je Raum:
  versatz_max  groesster Betrag des Versatzes in der Folge. Nicht null heisst, HD-Ebene
               und Original sitzen nicht uebereinander.
  drift_x/y    Aenderung des Versatzes von der ersten bis zur letzten Aufnahme. Ein
               wachsender Wert heisst, die HD-Ebene scrollt anders als das Original.
               Genau das ist der Fehler "senkrechte Achse fehlt" in hohen Raeumen.
  ohne_hd_max  groesster Anteil Kacheln, in denen kein HD-Asset gezeichnet wurde.
  kanten_max   groesster Kantenfehler der Folge.

Mit einem Videoverzeichnis als viertes Argument entstehen dort die Vergleichsbilder
(Original | HD | Abweichung) fuer die Videoaufnahme.

Aufruf: python3 harness/ab_scroll.py <ref-dir> <hd-dir> <csv> [videodir] [breite]
"""
import glob
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ab_compare import BLOCK, FLAT_MEAN, best_shift, dilate, gray, load_rgb, shifted, sobel  # noqa: E402


def room_of(name):
    m = re.search(r"_raum(\d+)", name)
    return int(m.group(1)) if m else -1


def frame_no(name):
    m = re.match(r"[a-z](\d+)", os.path.basename(name))
    return int(m.group(1)) if m else 0


def analyse_pair(ref_path, hd_path):
    ref = load_rgb(ref_path)
    hd = load_rgb(hd_path)
    ref_up = np.asarray(Image.fromarray(ref).resize((hd.shape[1], hd.shape[0]), Image.NEAREST))
    dx, dy, q = best_shift(ref_up, hd)
    hd_al = shifted(hd, dx, dy)

    diff = np.abs(hd_al.astype(np.int16) - ref_up.astype(np.int16)).astype(np.uint8)
    bh, bw = hd.shape[0] // BLOCK, hd.shape[1] // BLOCK
    blocks = (diff.max(axis=2) < FLAT_MEAN)[:bh * BLOCK, :bw * BLOCK].reshape(bh, BLOCK, bw, BLOCK)
    nohd = blocks.mean(axis=(1, 3)) > 0.98
    nohd_full = np.zeros(hd.shape[:2], dtype=bool)
    nohd_full[:bh * BLOCK, :bw * BLOCK] = np.repeat(np.repeat(nohd, BLOCK, axis=0), BLOCK, axis=1)

    e_ref = dilate(sobel(gray(ref_up).astype(np.float32)) > 24, 2)
    e_hd = sobel(gray(hd_al).astype(np.float32)) > 24
    kanten = 100.0 * (e_hd & ~e_ref).sum() / max(1, e_hd.sum())
    return dict(dx=dx, dy=dy, guete=q, ohne_hd=100.0 * nohd.mean(), kanten=kanten), (ref_up, hd, diff, nohd_full)


def montage(ref_up, hd, diff, nohd_full, width, label):
    h, w = hd.shape[:2]
    scale = width / (2 * w + 8)
    size = (max(1, int(w * scale)), max(1, int(h * scale)))
    ref_s = Image.fromarray(ref_up).resize(size, Image.LANCZOS)
    hd_s = Image.fromarray(hd).resize(size, Image.LANCZOS)
    heat = np.clip(diff.astype(np.int32) * 4, 0, 255).astype(np.uint8)
    heat[nohd_full] = (255, 0, 0)
    heat_s = Image.fromarray(heat).resize(size, Image.LANCZOS)
    out = Image.new("RGB", (size[0] * 3 + 8, size[1]), (255, 255, 255))
    out.paste(ref_s, (0, 0))
    out.paste(hd_s, (size[0] + 4, 0))
    out.paste(heat_s, (2 * size[0] + 8, 0))
    ImageDraw.Draw(out).text((6, 6), label, fill=(255, 255, 0))
    return out


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    refdir, hddir, csv = sys.argv[1], sys.argv[2], sys.argv[3]
    videodir = sys.argv[4] if len(sys.argv) > 4 else None
    width = int(sys.argv[5]) if len(sys.argv) > 5 else 1280
    room_arg = int(sys.argv[6]) if len(sys.argv) > 6 else None

    refs = {frame_no(p): p for p in glob.glob(os.path.join(refdir, "*.ppm"))}
    hds = {frame_no(p): p for p in glob.glob(os.path.join(hddir, "*.ppm"))}
    pairs = sorted(set(refs) & set(hds))
    if not pairs:
        print(f"keine Paare in {refdir} / {hddir}")
        return 1

    rows = []
    if videodir:
        os.makedirs(videodir, exist_ok=True)
    for i, n in enumerate(pairs):
        room = room_of(os.path.basename(hds[n]))
        m, imgs = analyse_pair(refs[n], hds[n])
        rows.append((n, room, m))
        if videodir and i % 2 == 0:
            montage(*imgs, width, f"Aufnahme {n}  Versatz {m['dx']},{m['dy']}  ohne HD {m['ohne_hd']:.0f}%") \
                .save(os.path.join(videodir, "f%05d.png" % (i // 2)))

    dxs = np.array([r[2]["dx"] for r in rows], dtype=float)
    dys = np.array([r[2]["dy"] for r in rows], dtype=float)
    nos = np.array([r[2]["ohne_hd"] for r in rows], dtype=float)
    kas = np.array([r[2]["kanten"] for r in rows], dtype=float)
    n = len(rows)
    idx = np.arange(n)
    slope_x = np.polyfit(idx, dxs, 1)[0] * (n - 1) if n > 2 else 0.0
    slope_y = np.polyfit(idx, dys, 1)[0] * (n - 1) if n > 2 else 0.0

    room = room_arg if room_arg is not None else rows[0][1]
    out = dict(raum=room, bilder=n,
               versatz_max=int(max(abs(dxs).max(), abs(dys).max())),
               drift_x=round(float(slope_x), 1), drift_y=round(float(slope_y), 1),
               ohne_hd_max=round(float(nos.max()), 1), ohne_hd_mit=round(float(nos.mean()), 1),
               kanten_max=round(float(kas.max()), 1))
    head = not os.path.exists(csv)
    with open(csv, "a", encoding="utf-8") as f:
        if head:
            f.write("raum;bilder;versatz_max;drift_x;drift_y;ohne_hd_max;ohne_hd_mit;kanten_max\n")
        f.write(";".join(str(out[k]) for k in ["raum", "bilder", "versatz_max", "drift_x",
                                                "drift_y", "ohne_hd_max", "ohne_hd_mit", "kanten_max"]) + "\n")
    print("Raum %d: %d Bilder, Versatz max %+d, Drift x %+.1f y %+.1f, ohne HD max %.1f%%, Kanten max %.1f%%"
          % (out["raum"], out["bilder"], out["versatz_max"], out["drift_x"], out["drift_y"],
             out["ohne_hd_max"], out["kanten_max"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
