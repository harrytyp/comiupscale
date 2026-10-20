"""Baut aus Vorher- und Nachher-Bildern eine Tafel: oben vorher, unten nachher."""
import os
import sys

from PIL import Image, ImageDraw

import sys as _sys
BEFORE = _sys.argv[1] if len(_sys.argv) > 1 else "/opt/data/projects/comi-hd/reports/sd"
AFTER = _sys.argv[2] if len(_sys.argv) > 2 else "/opt/data/projects/comi-hd/reports/sd2"
OUT = "/opt/data/projects/comi-hd/reports/vergleich"


def load(path, width):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    return img.resize((width, int(h * width / w)), Image.LANCZOS)


def main():
    rooms = sys.argv[3:] or ["41", "43", "79", "82"]
    os.makedirs(OUT, exist_ok=True)
    for room in rooms:
        b = os.path.join(BEFORE, f"{room}_f1_sd_ab.png")
        a = os.path.join(AFTER, f"{room}_f1_sd_ab.png")
        if not (os.path.exists(b) and os.path.exists(a)):
            print(f"Raum {room}: Bild fehlt")
            continue
        w = 1200
        ib, ia = load(b, w), load(a, w)
        canvas = Image.new("RGB", (w, ib.size[1] + ia.size[1] + 30), (255, 255, 255))
        canvas.paste(ib, (0, 20))
        canvas.paste(ia, (0, ib.size[1] + 30))
        d = ImageDraw.Draw(canvas)
        d.text((6, 4), f"Raum {room}: vorher (HD gegen SD)", fill=(200, 0, 0))
        d.text((6, ib.size[1] + 24), f"Raum {room}: nachher (HD gegen SD)", fill=(0, 150, 0))
        path = os.path.join(OUT, f"raum{room}_vorher_nachher.png")
        canvas.save(path)
        print(path, canvas.size)


if __name__ == "__main__":
    main()
