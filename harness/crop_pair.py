#!/usr/bin/env python3
"""Ausschnitt zweier Aufnahmen nebeneinander legen (8-Bit gegen HD-Komposition).

Aufruf:
  python3 harness/crop_pair.py <raum> <stufe> <x> <y> <breite> <hoehe> [zoom]

Die Koordinaten beziehen sich auf das 8-Bit-Bild (640x480). Ergebnis:
projects/comi-hd/work/dumps/raum<raum>_<stufe>_ausschnitt.png
"""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dumps import load_ppm, scale_to  # noqa: E402

DUMPS = os.environ.get("HD_DUMP_DIR", "/opt/data/projects/comi-hd/work/dumps")


def main():
    room, stufe = sys.argv[1], sys.argv[2]
    x, y, w, h = [int(v) for v in sys.argv[3:7]]
    zoom = int(sys.argv[7]) if len(sys.argv) > 7 else 3

    ref = load_ppm(os.path.join(DUMPS, "hd_ref.ppm"))
    hd = scale_to(load_ppm(os.path.join(DUMPS, "hd_step_%s.ppm" % stufe)),
                  ref.shape[1], ref.shape[0])
    a = Image.fromarray(ref[y:y + h, x:x + w])
    b = Image.fromarray(hd[y:y + h, x:x + w])
    a = a.resize((w * zoom, h * zoom), Image.NEAREST)
    b = b.resize((w * zoom, h * zoom), Image.NEAREST)
    out = Image.new("RGB", (a.width * 2 + 8, a.height + 14), (20, 20, 20))
    out.paste(a, (0, 14))
    out.paste(b, (a.width + 8, 14))
    path = os.path.join(DUMPS, "raum%s_%s_ausschnitt.png" % (room, stufe))
    out.save(path)
    print("%s %s" % (path, out.size))


if __name__ == "__main__":
    main()
