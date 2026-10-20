#!/usr/bin/env python3
"""Sortiert Aufnahmebilder aus, auf denen das Inventar zu sehen ist.

Der Raumsprung per boot-param laesst die Oberflaeche offen, und obwohl der Aufnahmelauf
dagegen klickt, bleibt das Inventar in einzelnen Bildern sichtbar: in Raum 42 geht es erst
am Ende auf, in Raum 25 gleich am Anfang. Das Brett hat eine eigene Farbe, deshalb wird sie
gemessen statt geraten.

Betroffene Bilder werden NICHT geloescht, sondern in einen Unterordner 'verworfen' verschoben.

Aufruf: skip_inventory_frames.py <verzeichnis> [grenze]
"""
import glob
import os
import shutil
import sys

GRENZE = 15  # Prozent braune Pixel in den oberen 14 Prozent gelten als geoeffnetes Inventar


def braun_oben(pfad):
    from PIL import Image
    im = Image.open(pfad).convert("RGB")
    w, h = im.size
    oben = im.crop((0, 0, w, int(h * 0.14)))
    px = list(oben.get_flattened_data() if hasattr(oben, "get_flattened_data") else oben.getdata())
    n = sum(1 for r, g, b in px if r > 80 and r < 210 and r > b + 30 and g > r * 0.4)
    return n * 100 // len(px)


def main():
    if len(sys.argv) < 2:
        print("Aufruf: skip_inventory_frames.py <verzeichnis> [grenze]")
        return 1
    d = sys.argv[1]
    grenze = int(sys.argv[2]) if len(sys.argv) > 2 else GRENZE
    ziel = os.path.join(d, "verworfen")
    raus = []
    for f in sorted(glob.glob(os.path.join(d, "*.ppm"))):
        v = braun_oben(f)
        if v >= grenze:
            raus.append((os.path.basename(f), v))
    if raus:
        os.makedirs(ziel, exist_ok=True)
        for name, v in raus:
            shutil.move(os.path.join(d, name), os.path.join(ziel, name))
            print(f"  verworfen: {name} ({v}% braun oben)")
    print(f"Aussortiert: {len(raus)} Bilder, Grenze {grenze}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
