#!/usr/bin/env python3
"""Baut das Textur-Paket (objects + objects_layers) fuer den GitHub-Release.

Aufruf:
    python3 scripts/build_texture_pack.py --dir release/linux/hd --out /opt/data/dist/hd_textures_v1.0.5.zip

Das ZIP enthaelt hd/objects/*.png und hd/objects_layers/*.png, also genau die
Ordner, die im Spiel-Ordner ueberschrieben werden muessen.
"""
import argparse
import os
import time
import zipfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="HD-Wurzel, z.B. release/linux/hd")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    folders = ["objects", "objects_layers"]
    t0 = time.time()
    total = 0
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        for folder in folders:
            src = os.path.join(args.dir, folder)
            names = sorted(n for n in os.listdir(src) if n.endswith(".png"))
            for i, n in enumerate(names, 1):
                z.write(os.path.join(src, n), "hd/%s/%s" % (folder, n))
                total += 1
            print("%s: %d Dateien" % (folder, len(names)))
    size = os.path.getsize(args.out)
    print("ZIP: %s | %.1f MB | %d Dateien | %.0f s" % (args.out, size / 1e6, total, time.time() - t0))


if __name__ == "__main__":
    main()
