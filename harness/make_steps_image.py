#!/usr/bin/env python3
"""Legt 8-Bit-Aufnahme und zwei Aufbaustufen nebeneinander, um zu sehen was eine Stufe aendert.

Aufruf: python3 harness/make_steps_image.py 25 [stufe1] [stufe2]
"""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dumps import load_ppm, scale_to  # noqa: E402

DUMPS = os.environ.get("HD_DUMP_DIR", "/opt/data/projects/comi-hd/work/dumps")


def main():
    room = sys.argv[1] if len(sys.argv) > 1 else "25"
    a_name = sys.argv[2] if len(sys.argv) > 2 else "2_vordergrund"
    b_name = sys.argv[3] if len(sys.argv) > 3 else "3_objekte"
    ref = load_ppm(os.path.join(DUMPS, "hd_ref.ppm"))
    h, w = ref.shape[0], ref.shape[1]
    a = scale_to(load_ppm(os.path.join(DUMPS, "hd_step_%s.ppm" % a_name)), w, h)
    b = scale_to(load_ppm(os.path.join(DUMPS, "hd_step_%s.ppm" % b_name)), w, h)
    out = Image.new("RGB", (w * 3 + 12, h), (20, 20, 20))
    out.paste(Image.fromarray(ref), (0, 0))
    out.paste(Image.fromarray(a), (w + 6, 0))
    out.paste(Image.fromarray(b), (2 * w + 12, 0))
    path = os.path.join(DUMPS, "raum%s_stufen.png" % room)
    out.save(path)
    print("%s %s" % (path, out.size))


if __name__ == "__main__":
    main()
