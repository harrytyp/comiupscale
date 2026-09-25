#!/usr/bin/env python3
"""Prueft alle HD-Texturen auf Lesbarkeit (PNG-Integritaet) und meldet kaputte Dateien.

Aufruf: python3 scripts/check_texture_integrity.py <ordner> [<ordner> ...]
Exitcode 1, wenn kaputte Dateien gefunden wurden.
"""
import os
import sys

from PIL import Image


def main():
    bad = []
    total = 0
    for d in sys.argv[1:]:
        if not os.path.isdir(d):
            print("fehlt:", d)
            continue
        for n in sorted(os.listdir(d)):
            if not n.endswith(".png"):
                continue
            total += 1
            p = os.path.join(d, n)
            try:
                with Image.open(p) as im:
                    im.verify()
                with Image.open(p) as im:
                    im.load()
            except Exception as exc:  # noqa: BLE001
                bad.append((d, n, str(exc)[:60]))
    print("geprueft: %d Dateien | kaputt: %d" % (total, len(bad)))
    for d, n, err in bad:
        print("   KAPUTT %s/%s (%s)" % (d, n, err))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
