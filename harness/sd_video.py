#!/usr/bin/env python3
"""Videozutaten: SD-Bild, HD-Bild und Markierung je Bild nebeneinander.

Zu jedem HD-Bild der Folge wird das passende SD-Bild gesucht (gleicher Raum, gleicher
Moment) und mit sd_compare verglichen. Daraus entsteht je Bild ein Streifen aus drei
Teilen: Soll (SD), Ist (HD), Abweichung (rot fehlt, blau verrutscht, gruen abweichend).

Aufruf: python3 harness/sd_video.py <hd-folge-ordner> <sd-ordner> <ziel-ordner> [fenster]
"""
import glob
import os
import re
import shutil
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ab_compare import best_shift, load_rgb  # noqa: E402
from sd_compare import compare_pair  # noqa: E402


def frame_no(path):
    m = re.search(r"h(\d+)", os.path.basename(path))
    return int(m.group(1)) if m else -1


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    hddir, sddir, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    window = int(sys.argv[4]) if len(sys.argv) > 4 else 4

    hds = sorted(glob.glob(os.path.join(hddir, "h*.ppm")), key=frame_no)
    sds = sorted(glob.glob(os.path.join(sddir, "*.png")) + glob.glob(os.path.join(sddir, "*.ppm")))
    if not hds or not sds:
        print(f"keine Bilder: {len(hds)} HD, {len(sds)} SD")
        return 1
    os.makedirs(outdir, exist_ok=True)
    for old in glob.glob(os.path.join(outdir, "f*.png")):
        os.remove(old)

    tmp = tempfile.mkdtemp(prefix="sdvideo")
    written = 0
    for idx, hd_path in enumerate(hds):
        if written >= 14:
            break
        hd_paths = load_rgb(hd_path)
        small = (max(2, hd_paths.shape[1] // 4), max(2, hd_paths.shape[0] // 4))
        hd_s = np.asarray(Image.fromarray(hd_paths).resize(small, Image.BILINEAR))
        best = None
        for cand in sds:
            sd_s = np.asarray(Image.fromarray(load_rgb(cand)).resize(small, Image.BILINEAR))
            _, _, q = best_shift(sd_s, hd_s)
            if best is None or q > best[0]:
                best = (q, cand)
        if best is None or best[0] < 1.15:
            print(f"  {os.path.basename(hd_path)}: kein passendes SD-Bild")
            continue
        q, sd_path = best
        name = f"v{written:03d}"
        compare_pair(sd_path, hd_path, tmp, name)
        ab = Image.open(os.path.join(tmp, f"{name}_sd_ab.png"))
        mk = Image.open(os.path.join(tmp, f"{name}_sd_mark.png")).convert("RGB")
        w, h = ab.size
        half = w // 2
        canvas = Image.new("RGB", (half + w + 6, h), (255, 255, 255))
        canvas.paste(ab.crop((0, 0, half, h)), (0, 0))
        canvas.paste(ab.crop((half, 0, w, h)), (half + 6, 0))
        canvas = canvas.resize((1200, int(canvas.size[1] * 1200 / canvas.size[0])), Image.LANCZOS)
        mk = mk.resize((600, int(mk.size[1] * 600 / mk.size[0])), Image.LANCZOS)
        canvas.paste(mk, (0, canvas.size[1] - mk.size[1]))
        ImageDraw.Draw(canvas).text((8, 8), f"SD | HD | Abweichung   ({os.path.basename(sd_path)})",
                                    fill=(255, 255, 0))
        canvas.save(os.path.join(outdir, f"f{written:05d}.png"))
        written += 1

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"{written} Videobilder in {outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
