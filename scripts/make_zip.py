#!/usr/bin/env python3
"""Packt einen Ordner als ZIP (Ersatz fuer das zip-Kommando, das hier fehlt).

Aufruf: python3 scripts/make_zip.py <ordner> <ziel.zip>
"""
import os
import sys
import zipfile


def main():
    quelle, ziel = sys.argv[1], sys.argv[2]
    if not os.path.isdir(quelle):
        print("Ordner fehlt: %s" % quelle)
        return 2
    basis = os.path.basename(quelle.rstrip("/"))
    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, _dirs, files in os.walk(quelle):
            for name in sorted(files):
                voll = os.path.join(root, name)
                rel = os.path.relpath(voll, os.path.dirname(quelle))
                z.write(voll, rel)
    print("%s (%.1f MB, %d Dateien)" % (ziel, os.path.getsize(ziel) / 1e6,
                                        len(zipfile.ZipFile(ziel).namelist())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
