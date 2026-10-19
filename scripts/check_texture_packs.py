#!/usr/bin/env python3
"""Prueft, ob die Texture-Packs genau die Dateien aus release/linux/hd enthalten.

Rueckgabewert 0, wenn jede Datei genau einmal in den drei Packs liegt.
"""
import glob
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HD = os.path.join(ROOT, "release", "linux", "hd")


def main():
    if not os.path.isdir(HD):
        print("kein HD-Ordner: %s" % HD)
        return 2

    dateien = set()
    for base, _dirs, files in os.walk(HD):
        for name in files:
            dateien.add(os.path.relpath(os.path.join(base, name), HD).replace(os.sep, "/"))

    packs = sorted(glob.glob(os.path.join(ROOT, "release", "hd_assets_part*.zip")))
    if not packs:
        print("keine Packs gefunden")
        return 2

    zaehler = {}
    for pack in packs:
        with zipfile.ZipFile(pack) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                name = info.filename.replace("./", "")
                if name.startswith("hd/"):
                    name = name[3:]
                zaehler[name] = zaehler.get(name, 0) + 1

    fehlt = sorted(dateien - set(zaehler))
    fremd = sorted(set(zaehler) - dateien)
    doppelt = sorted(name for name, n in zaehler.items() if n > 1)

    print("HD-Dateien: %d, Pack-Eintraege: %d in %d Packs" % (len(dateien), sum(zaehler.values()), len(packs)))
    print("fehlt: %d, doppelt: %d, fremd: %d" % (len(fehlt), len(doppelt), len(fremd)))
    for label, items in (("fehlt", fehlt), ("doppelt", doppelt), ("fremd", fremd)):
        for name in items[:10]:
            print("  %s: %s" % (label, name))
    return 0 if not (fehlt or doppelt or fremd) else 1


if __name__ == "__main__":
    sys.exit(main())
