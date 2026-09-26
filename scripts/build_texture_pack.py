#!/usr/bin/env python3
"""Baut das grosse Textur-Paket part1 (backgrounds, objects, objects_layers, fonts).

Das ist der Ersatz fuer hd_assets_part1.zip: dieselben Ordner, aber mit den
korrigierten Objekttexturen (maskenbasierter Alpha-Schritt).

Aufruf:
    python3 scripts/build_texture_pack.py --dir release/linux/hd --out /opt/data/dist/hd_assets_part1.zip --folders backgrounds objects objects_layers fonts
"""
import argparse
import os
import time
import zipfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="HD-Wurzel, z.B. release/linux/hd")
    ap.add_argument("--out", required=True)
    ap.add_argument("--folders", nargs="+", default=["objects", "objects_layers"])
    args = ap.parse_args()

    t0 = time.time()
    total = 0
    bytes_raw = 0
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        for folder in args.folders:
            src = os.path.join(args.dir, folder)
            if not os.path.isdir(src):
                print("fehlt:", folder)
                continue
            names = sorted(n for n in os.listdir(src) if os.path.isfile(os.path.join(src, n)))
            for n in names:
                p = os.path.join(src, n)
                z.write(p, "hd/%s/%s" % (folder, n))
                total += 1
                bytes_raw += os.path.getsize(p)
            print("%-16s %4d Dateien" % (folder, len(names)))
        # Die Objektzuordnung gehoert mit ins Paket: die Engine sucht Objekttexturen ueber
        # object_map.json (obj_nr -> Name/Raum/Zustaende). Ohne die Datei findet sie keine
        # Objekte und zeichnet alles aus dem 8-Bit-Bild.
        for extra in ("object_map.json",):
            p = os.path.join(args.dir, extra)
            if os.path.isfile(p):
                z.write(p, "hd/%s" % extra)
                total += 1
                bytes_raw += os.path.getsize(p)
                print("%-16s %4d Dateien" % (extra, 1))
    print("ZIP: %s | %.1f MB (roh %.1f MB) | %d Dateien | %.0f s" %
          (args.out, os.path.getsize(args.out) / 1e6, bytes_raw / 1e6, total, time.time() - t0))


if __name__ == "__main__":
    main()
